from fastapi import APIRouter, HTTPException
from db.supabase import get_supabase
from models.schemas import ImageGenerateRequest, ImageAnalyzeRequest
from tools.executor import execute_tool
import json

router = APIRouter()


@router.post("/generate")
async def generate_image(req: ImageGenerateRequest):
    result = await execute_tool("generate_image", {"prompt": req.prompt}, req.project_id)
    return json.loads(result)


@router.post("/analyze")
async def analyze_image(req: ImageAnalyzeRequest):
    result = await execute_tool("analyze_image", {
        "image_id": req.image_id,
        "question": req.question
    }, req.project_id)
    return {"analysis": result}


@router.get("/{project_id}")
async def list_images(project_id: str):
    db = get_supabase()
    res = db.table("images").select("*").eq("project_id", project_id).order("created_at", desc=True).execute()
    return res.data


@router.delete("/{image_id}")
async def delete_image(image_id: str):
    db = get_supabase()
    db.table("images").delete().eq("id", image_id).execute()
    return {"deleted": True}
