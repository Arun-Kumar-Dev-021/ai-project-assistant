"""
Chat router — manages the full Claude tool loop:
1. Load project context + memory
2. Send to Claude with tools
3. Execute any tool calls
4. Feed results back
5. Get final response
6. Persist everything
"""
import os, json
from fastapi import APIRouter, HTTPException
from anthropic import Anthropic
from db.supabase import get_supabase
from models.schemas import ChatRequest
from tools.definitions import TOOLS
from tools.executor import execute_tool

router = APIRouter()
claude = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

SYSTEM_PROMPT = """You are an expert AI project assistant. You help users plan, build, and manage their projects.

At the START of every conversation, call get_memory to recall what you know about this project.
During conversation, call save_memory whenever the user shares important information.

You can:
- Help plan and structure projects
- Generate images with generate_image tool
- Analyze images with analyze_image tool  
- Search the web for information
- Remember anything important with save_memory

Be proactive: if you learn something important, save it. Always check memory first.
Be concise but thorough. Use markdown for structured responses."""


@router.post("/")
async def chat(req: ChatRequest):
    db = get_supabase()

    # Verify project exists
    proj = db.table("projects").select("*").eq("id", req.project_id).execute()
    if not proj.data:
        raise HTTPException(404, "Project not found")
    project = proj.data[0]

    # Get or create conversation
    conv_id = req.conversation_id
    if not conv_id:
        conv = db.table("conversations").insert({
            "project_id": req.project_id,
            "title": req.message[:60] + ("..." if len(req.message) > 60 else "")
        }).execute()
        conv_id = conv.data[0]["id"]

    # Load conversation history
    hist = db.table("messages")\
        .select("role, content, tool_calls, tool_results")\
        .eq("conversation_id", conv_id)\
        .order("created_at")\
        .execute()

    # Build messages array for Claude
    messages = []
    for m in hist.data:
        if m["role"] == "user":
            messages.append({"role": "user", "content": m["content"] or ""})
        elif m["role"] == "assistant":
            if m["tool_calls"]:
                # Reconstruct assistant message with tool_use blocks
                content = []
                if m["content"]:
                    content.append({"type": "text", "text": m["content"]})
                for tc in m["tool_calls"]:
                    content.append(tc)
                messages.append({"role": "assistant", "content": content})
                # Add tool results
                if m["tool_results"]:
                    messages.append({"role": "user", "content": m["tool_results"]})
            else:
                messages.append({"role": "assistant", "content": m["content"] or ""})

    # Add current user message
    user_content = req.message
    messages.append({"role": "user", "content": user_content})

    # Save user message
    db.table("messages").insert({
        "conversation_id": conv_id,
        "project_id": req.project_id,
        "role": "user",
        "content": req.message
    }).execute()

    # ── Claude tool loop ───────────────────────────────────
    system = f"{SYSTEM_PROMPT}\n\nCurrent project: {project['name']}\nDescription: {project.get('description','')}\nGoals: {project.get('goals','')}"
    
    final_text = ""
    all_tool_calls = []
    all_tool_results = []
    total_tokens = 0

    while True:
        response = claude.messages.create(
            model="claude-opus-4-5",
            max_tokens=4096,
            system=system,
            tools=TOOLS,
            messages=messages
        )
        total_tokens += response.usage.input_tokens + response.usage.output_tokens

        if response.stop_reason == "end_turn":
            # Extract text
            for block in response.content:
                if hasattr(block, "text"):
                    final_text = block.text
            break

        elif response.stop_reason == "tool_use":
            # Collect tool calls from this response
            tool_use_blocks = [b for b in response.content if b.type == "tool_use"]
            text_blocks = [b for b in response.content if hasattr(b, "text")]

            if text_blocks:
                final_text = text_blocks[0].text

            # Build assistant message content
            asst_content = []
            if final_text:
                asst_content.append({"type": "text", "text": final_text})
            for b in tool_use_blocks:
                asst_content.append({"type": "tool_use", "id": b.id, "name": b.name, "input": b.input})
                all_tool_calls.append({"type": "tool_use", "id": b.id, "name": b.name, "input": b.input})

            messages.append({"role": "assistant", "content": asst_content})

            # Execute all tools
            tool_result_content = []
            for b in tool_use_blocks:
                result = await execute_tool(b.name, b.input, req.project_id)
                tool_result_content.append({
                    "type": "tool_result",
                    "tool_use_id": b.id,
                    "content": result
                })
                all_tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": b.id,
                    "content": result
                })

            messages.append({"role": "user", "content": tool_result_content})

        else:
            # Unexpected stop reason
            for block in response.content:
                if hasattr(block, "text"):
                    final_text = block.text
            break

    # Save assistant message with tool data
    db.table("messages").insert({
        "conversation_id": conv_id,
        "project_id": req.project_id,
        "role": "assistant",
        "content": final_text,
        "tool_calls": all_tool_calls if all_tool_calls else None,
        "tool_results": all_tool_results if all_tool_results else None,
        "tokens_used": total_tokens
    }).execute()

    # Update conversation title if first exchange
    if not req.conversation_id:
        db.table("conversations").update({"title": req.message[:60]}).eq("id", conv_id).execute()

    return {
        "conversation_id": conv_id,
        "message": final_text,
        "tool_calls": all_tool_calls,
        "tokens_used": total_tokens
    }


@router.get("/conversations/{project_id}")
async def list_conversations(project_id: str):
    db = get_supabase()
    res = db.table("conversations").select("*")\
        .eq("project_id", project_id)\
        .order("updated_at", desc=True)\
        .execute()
    return res.data


@router.get("/history/{conversation_id}")
async def get_history(conversation_id: str):
    db = get_supabase()
    res = db.table("messages").select("*")\
        .eq("conversation_id", conversation_id)\
        .order("created_at")\
        .execute()
    return res.data


@router.delete("/conversations/{conversation_id}")
async def delete_conversation(conversation_id: str):
    db = get_supabase()
    db.table("messages").delete().eq("conversation_id", conversation_id).execute()
    db.table("conversations").delete().eq("id", conversation_id).execute()
    return {"deleted": True}
