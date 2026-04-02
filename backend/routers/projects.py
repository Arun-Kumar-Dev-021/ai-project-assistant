from fastapi import APIRouter, HTTPException
from db.supabase import get_supabase
from models.schemas import ProjectCreate, ProjectUpdate

router = APIRouter()


@router.post("/")
async def create_project(data: ProjectCreate):
    db = get_supabase()
    res = db.table("projects").insert({
        "name": data.name,
        "description": data.description,
        "goals": data.goals,
        "brief": data.brief or {}
    }).execute()
    return res.data[0]


@router.get("/")
async def list_projects():
    db = get_supabase()
    res = db.table("projects").select("*").order("created_at", desc=True).execute()
    return res.data


@router.get("/{project_id}")
async def get_project(project_id: str):
    db = get_supabase()
    res = db.table("projects").select("*").eq("id", project_id).execute()
    if not res.data:
        raise HTTPException(404, "Project not found")
    return res.data[0]


@router.patch("/{project_id}")
async def update_project(project_id: str, data: ProjectUpdate):
    db = get_supabase()
    update = {k: v for k, v in data.model_dump().items() if v is not None}
    if not update:
        raise HTTPException(400, "No fields to update")
    res = db.table("projects").update(update).eq("id", project_id).execute()
    return res.data[0]


@router.delete("/{project_id}")
async def delete_project(project_id: str):
    db = get_supabase()
    db.table("projects").delete().eq("id", project_id).execute()
    return {"deleted": True}


@router.get("/{project_id}/summary")
async def project_summary(project_id: str):
    """Full project overview: project + memory + images + conversations count."""
    db = get_supabase()
    proj = db.table("projects").select("*").eq("id", project_id).execute()
    if not proj.data:
        raise HTTPException(404, "Project not found")

    memories = db.table("memory").select("*").eq("project_id", project_id).execute()
    images = db.table("images").select("id, prompt, url, source, created_at").eq("project_id", project_id).execute()
    convs = db.table("conversations").select("id").eq("project_id", project_id).execute()
    jobs = db.table("agent_jobs").select("id, status, created_at").eq("project_id", project_id).order("created_at", desc=True).limit(5).execute()

    return {
        "project": proj.data[0],
        "memory_count": len(memories.data),
        "memories": memories.data,
        "image_count": len(images.data),
        "images": images.data,
        "conversation_count": len(convs.data),
        "recent_agent_jobs": jobs.data
    }
