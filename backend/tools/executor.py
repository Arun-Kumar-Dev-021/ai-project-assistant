"""
Tool executor — receives tool_use blocks from Claude and runs them,
then returns tool_result blocks back into the conversation.
"""
import os, base64, httpx, json
from db.supabase import get_supabase

HUGGINGFACE_API_KEY = os.getenv("HUGGINGFACE_API_KEY", "")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")


async def execute_tool(tool_name: str, tool_input: dict, project_id: str) -> str:
    """Route a tool call and return a string result."""
    db = get_supabase()

    if tool_name == "save_memory":
        return await _save_memory(db, project_id, tool_input)

    elif tool_name == "get_memory":
        return await _get_memory(db, project_id, tool_input)

    elif tool_name == "generate_image":
        return await _generate_image(db, project_id, tool_input)

    elif tool_name == "analyze_image":
        return await _analyze_image(db, project_id, tool_input)

    elif tool_name == "list_project_images":
        return await _list_images(db, project_id)

    elif tool_name == "search_web":
        return await _search_web(tool_input.get("query", ""))

    return f"Unknown tool: {tool_name}"


# ── Memory tools ───────────────────────────────────────────

async def _save_memory(db, project_id: str, inp: dict) -> str:
    key = inp["key"]
    value = inp["value"]
    category = inp.get("category", "general")
    db.table("memory").upsert({
        "project_id": project_id,
        "key": key,
        "value": value,
        "category": category,
        "source": "chat"
    }, on_conflict="project_id,key").execute()
    return f"✓ Saved memory: [{category}] {key}"


async def _get_memory(db, project_id: str, inp: dict) -> str:
    category = inp.get("category")
    query = db.table("memory").select("*").eq("project_id", project_id)
    if category:
        query = query.eq("category", category)
    res = query.order("category").execute()
    if not res.data:
        return "No memories found for this project yet."
    lines = [f"[{m['category']}] {m['key']}: {m['value']}" for m in res.data]
    return "Project memories:\n" + "\n".join(lines)


# ── Image tools ────────────────────────────────────────────

async def _generate_image(db, project_id: str, inp: dict) -> str:
    prompt = inp["prompt"]
    image_url = None

    # Try Hugging Face Stable Diffusion (free)
    if HUGGINGFACE_API_KEY:
        try:
            async with httpx.AsyncClient(timeout=60) as client:
                resp = await client.post(
                    "https://api-inference.huggingface.co/models/stabilityai/stable-diffusion-xl-base-1.0",
                    headers={"Authorization": f"Bearer {HUGGINGFACE_API_KEY}"},
                    json={"inputs": prompt}
                )
                if resp.status_code == 200:
                    b64 = base64.b64encode(resp.content).decode()
                    image_url = f"data:image/jpeg;base64,{b64}"
        except Exception as e:
            print(f"HuggingFace error: {e}")

    # Fallback: placeholder image via picsum
    if not image_url:
        seed = abs(hash(prompt)) % 1000
        image_url = f"https://picsum.photos/seed/{seed}/512/512"

    # Store in DB
    res = db.table("images").insert({
        "project_id": project_id,
        "prompt": prompt,
        "url": image_url,
        "source": "generated",
        "metadata": {"model": "stable-diffusion-xl" if HUGGINGFACE_API_KEY else "placeholder"}
    }).execute()

    image_id = res.data[0]["id"] if res.data else "unknown"
    return json.dumps({
        "image_id": image_id,
        "url": image_url,
        "prompt": prompt,
        "message": "Image generated and saved to project."
    })


async def _analyze_image(db, project_id: str, inp: dict) -> str:
    image_id = inp["image_id"]
    question = inp.get("question", "Describe this image.")

    # Fetch image from DB
    res = db.table("images").select("*").eq("id", image_id).eq("project_id", project_id).execute()
    if not res.data:
        return f"Image {image_id} not found in this project."

    image = res.data[0]
    image_url = image["url"]

    if not GEMINI_API_KEY:
        return f"[Mock Gemini Analysis] The image shows: {image['prompt']}. {question} — Gemini API key not configured."

    try:
        # Prepare image data for Gemini
        if image_url.startswith("data:"):
            # base64 data URI
            header, b64data = image_url.split(",", 1)
            mime = header.split(":")[1].split(";")[0]
            image_part = {"inline_data": {"mime_type": mime, "data": b64data}}
        else:
            # URL
            async with httpx.AsyncClient(timeout=30) as client:
                img_resp = await client.get(image_url)
                b64data = base64.b64encode(img_resp.content).decode()
            image_part = {"inline_data": {"mime_type": "image/jpeg", "data": b64data}}

        # Call Gemini
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}",
                json={"contents": [{"parts": [image_part, {"text": question}]}]}
            )
            result = resp.json()
            analysis = result["candidates"][0]["content"]["parts"][0]["text"]

        # Save analysis back to image record
        db.table("images").update({"analysis": analysis}).eq("id", image_id).execute()
        return f"Gemini analysis: {analysis}"

    except Exception as e:
        return f"Image analysis error: {str(e)}"


async def _list_images(db, project_id: str) -> str:
    res = db.table("images").select("id, prompt, url, source, created_at").eq("project_id", project_id).order("created_at", desc=True).limit(20).execute()
    if not res.data:
        return "No images found for this project."
    lines = [f"- ID: {img['id']} | Prompt: {img['prompt']} | Source: {img['source']}" for img in res.data]
    return "Project images:\n" + "\n".join(lines)


# ── Web search ─────────────────────────────────────────────

async def _search_web(query: str) -> str:
    """Use DuckDuckGo instant answer API (free, no key needed)."""
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(
                "https://api.duckduckgo.com/",
                params={"q": query, "format": "json", "no_html": "1", "skip_disambig": "1"}
            )
            data = resp.json()
            abstract = data.get("AbstractText", "")
            results = [r.get("Text", "") for r in data.get("RelatedTopics", [])[:3] if isinstance(r, dict)]
            if abstract:
                return f"Search results for '{query}':\n{abstract}\n\nRelated: {'; '.join(results)}"
            elif results:
                return f"Search results for '{query}':\n" + "\n".join(results)
            else:
                return f"No instant results found for '{query}'. Try a more specific query."
    except Exception as e:
        return f"Search error: {str(e)}"
