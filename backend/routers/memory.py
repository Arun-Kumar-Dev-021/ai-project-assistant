from fastapi import APIRouter, HTTPException
from db.supabase import get_supabase
from models.schemas import MemoryCreate, MemoryUpdate

router = APIRouter()


@router.get("/{project_id}")
async def get_memory(project_id: str, category: str = None):
    db = get_supabase()
    q = db.table("memory").select("*").eq("project_id", project_id)
    if category:
        q = q.eq("category", category)
    res = q.order("category").order("key").execute()
    return res.data


@router.post("/")
async def save_memory(data: MemoryCreate):
    db = get_supabase()
    res = db.table("memory").upsert({
        "project_id": data.project_id,
        "key": data.key,
        "value": data.value,
        "category": data.category or "general",
        "source": "manual"
    }, on_conflict="project_id,key").execute()
    return res.data[0]


@router.patch("/{memory_id}")
async def update_memory(memory_id: str, data: MemoryUpdate):
    db = get_supabase()
    update = {k: v for k, v in data.model_dump().items() if v is not None}
    res = db.table("memory").update(update).eq("id", memory_id).execute()
    return res.data[0]


@router.delete("/{memory_id}")
async def delete_memory(memory_id: str):
    db = get_supabase()
    db.table("memory").delete().eq("id", memory_id).execute()
    return {"deleted": True}


@router.delete("/project/{project_id}")
async def clear_project_memory(project_id: str):
    db = get_supabase()
    db.table("memory").delete().eq("project_id", project_id).execute()
    return {"cleared": True}
