"""
Background Agent — takes a project's full data (brief, conversations,
images, existing memory) and organizes it into structured memory entries.

Runs asynchronously. Status is tracked in agent_jobs table.
"""
import os, asyncio
from datetime import datetime, timezone
from anthropic import Anthropic
from db.supabase import get_supabase

claude = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

AGENT_SYSTEM = """You are a project knowledge organizer. 
Given raw project data, your job is to extract and structure key information into memory entries.

For each important piece of information, output a JSON block like:
{"key": "...", "value": "...", "category": "goal|decision|context|technical|team|note|general"}

Output ONLY these JSON blocks, one per line, nothing else.
Be thorough — extract: goals, tech choices, deadlines, team info, decisions made, important context."""


async def run_organization_agent(job_id: str, project_id: str):
    """Main agent function — runs in background."""
    db = get_supabase()

    # Mark as running
    db.table("agent_jobs").update({
        "status": "running",
        "started_at": datetime.now(timezone.utc).isoformat()
    }).eq("id", job_id).execute()

    try:
        # ── Gather all project data ────────────────────────
        proj = db.table("projects").select("*").eq("id", project_id).execute()
        if not proj.data:
            raise ValueError("Project not found")
        project = proj.data[0]

        # Get all messages
        messages_res = db.table("messages").select("role, content")\
            .eq("project_id", project_id)\
            .order("created_at")\
            .execute()

        # Get existing images
        images_res = db.table("images").select("prompt, analysis")\
            .eq("project_id", project_id)\
            .execute()

        # Get existing memory (agent will not duplicate, just supplement)
        existing_mem = db.table("memory").select("key")\
            .eq("project_id", project_id)\
            .execute()
        existing_keys = {m["key"] for m in existing_mem.data}

        # Build context document
        context_parts = [
            f"# Project: {project['name']}",
            f"Description: {project.get('description', 'N/A')}",
            f"Goals: {project.get('goals', 'N/A')}",
            f"Brief data: {project.get('brief', {})}",
            "",
            "## Conversation History:",
        ]

        for m in messages_res.data:
            if m["content"]:
                context_parts.append(f"{m['role'].upper()}: {m['content'][:500]}")

        if images_res.data:
            context_parts.append("\n## Generated Images:")
            for img in images_res.data:
                context_parts.append(f"- Prompt: {img['prompt']}")
                if img.get("analysis"):
                    context_parts.append(f"  Analysis: {img['analysis'][:200]}")

        context = "\n".join(context_parts)

        # ── Call Claude to extract structured memory ───────
        response = claude.messages.create(
            model="claude-haiku-4-5",
            max_tokens=2048,
            system=AGENT_SYSTEM,
            messages=[{
                "role": "user",
                "content": f"Extract and structure all important project knowledge from this data:\n\n{context}"
            }]
        )

        raw = response.content[0].text if response.content else ""

        # Parse JSON lines
        import json
        saved_count = 0
        errors = []

        for line in raw.strip().split("\n"):
            line = line.strip()
            if not line or not line.startswith("{"):
                continue
            try:
                entry = json.loads(line)
                key = entry.get("key", "").strip()
                value = entry.get("value", "").strip()
                category = entry.get("category", "general")

                if not key or not value:
                    continue

                # Skip if key already exists (don't overwrite user data)
                if key in existing_keys:
                    continue

                db.table("memory").upsert({
                    "project_id": project_id,
                    "key": key,
                    "value": value,
                    "category": category,
                    "source": "agent"
                }, on_conflict="project_id,key").execute()
                saved_count += 1
                existing_keys.add(key)

            except json.JSONDecodeError as e:
                errors.append(f"Parse error on line: {line[:50]}")

        # ── Mark complete ──────────────────────────────────
        db.table("agent_jobs").update({
            "status": "completed",
            "completed_at": datetime.now(timezone.utc).isoformat(),
            "result": {
                "memories_created": saved_count,
                "messages_processed": len(messages_res.data),
                "images_processed": len(images_res.data),
                "errors": errors[:5]
            }
        }).eq("id", job_id).execute()

    except Exception as e:
        db.table("agent_jobs").update({
            "status": "failed",
            "completed_at": datetime.now(timezone.utc).isoformat(),
            "error": str(e)
        }).eq("id", job_id).execute()
        raise
