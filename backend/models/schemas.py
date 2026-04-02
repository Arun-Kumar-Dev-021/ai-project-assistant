from pydantic import BaseModel, Field
from typing import Optional, Any, List
from datetime import datetime


# ── Projects ──────────────────────────────────────────────
class ProjectCreate(BaseModel):
    name: str
    description: Optional[str] = None
    goals: Optional[str] = None
    brief: Optional[dict] = Field(default_factory=dict)
    # brief can contain: tech_stack, deadline, team_members, reference_links, tags, priority, etc.

class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    goals: Optional[str] = None
    status: Optional[str] = None
    brief: Optional[dict] = None

class ProjectOut(BaseModel):
    id: str
    name: str
    description: Optional[str]
    goals: Optional[str]
    status: str
    brief: dict
    created_at: str
    updated_at: str


# ── Conversations & Messages ──────────────────────────────
class ConversationCreate(BaseModel):
    project_id: str
    title: Optional[str] = "New Chat"

class ChatRequest(BaseModel):
    project_id: str
    conversation_id: Optional[str] = None   # if None, creates new conversation
    message: str
    image_id: Optional[str] = None           # attach an existing image to the message


# ── Images ────────────────────────────────────────────────
class ImageGenerateRequest(BaseModel):
    project_id: str
    prompt: str

class ImageAnalyzeRequest(BaseModel):
    project_id: str
    image_id: str
    question: Optional[str] = "Describe this image in detail."


# ── Memory ────────────────────────────────────────────────
class MemoryCreate(BaseModel):
    project_id: str
    category: Optional[str] = "general"
    key: str
    value: str

class MemoryUpdate(BaseModel):
    value: str
    category: Optional[str] = None


# ── Agent ─────────────────────────────────────────────────
class AgentTriggerRequest(BaseModel):
    project_id: str
