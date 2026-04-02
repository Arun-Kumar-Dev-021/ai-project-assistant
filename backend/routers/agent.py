import asyncio
from fastapi import APIRouter, HTTPException, BackgroundTasks
from db.supabase import get_supabase
from models.schemas import AgentTriggerRequest
from agents.organization_agent import run_organization_agent

router = APIRouter()


@router.post("/trigger")
async def trigger_agent(req: AgentTriggerRequest, background_tasks: BackgroundTasks):
    """Trigger the background organization agent for a project."""
    db = get_supabase()

    # Verify project exists
    proj = db.table("projects").select("id").eq("id", req.project_id).execute()
    if not proj.data:
        raise HTTPException(404, "Project not found")

    # Check if agent is already running for this project
    running = db.table("agent_jobs")\
        .select("id")\
        .eq("project_id", req.project_id)\
        .eq("status", "running")\
        .execute()
    if running.data:
        raise HTTPException(409, "Agent already running for this project. Wait for it to complete.")

    # Create job record
    job = db.table("agent_jobs").insert({
        "project_id": req.project_id,
        "status": "pending",
        "triggered_by": "api"
    }).execute()
    job_id = job.data[0]["id"]

    # Run in background
    background_tasks.add_task(run_organization_agent, job_id, req.project_id)

    return {
        "job_id": job_id,
        "status": "pending",
        "message": "Agent started. Poll /api/agent/status/{job_id} to check progress."
    }


@router.get("/status/{job_id}")
async def get_job_status(job_id: str):
    """Poll agent job status."""
    db = get_supabase()
    res = db.table("agent_jobs").select("*").eq("id", job_id).execute()
    if not res.data:
        raise HTTPException(404, "Job not found")
    return res.data[0]


@router.get("/jobs/{project_id}")
async def list_jobs(project_id: str):
    """List all agent jobs for a project."""
    db = get_supabase()
    res = db.table("agent_jobs")\
        .select("*")\
        .eq("project_id", project_id)\
        .order("created_at", desc=True)\
        .execute()
    return res.data
