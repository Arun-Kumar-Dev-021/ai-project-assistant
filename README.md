# AI Project Assistant

A full-stack AI-powered project management tool built with **Python + FastAPI + Claude + Gemini + Supabase**.

**Live features:**
- Chat with Claude about your projects (with tools)
- Generate images from prompts
- Analyze images using Gemini
- Claude remembers things across conversations (memory)
- Background AI agent that auto-organizes project knowledge

---

## Schema Design Decisions

I designed the schema around one core idea: **a project is the single source of truth**, and everything else (conversations, messages, images, memory, agent jobs) belongs to a project.

### Tables

**`projects`**
The top-level container. Has a `brief` column as JSONB instead of fixed columns like `tech_stack`, `deadline`, etc. This is intentional — project briefs vary wildly between teams, so JSONB lets you store anything without schema migrations.

**`conversations`**
Groups messages into threads. One project can have many conversations. Keeping conversations separate from messages means you can show a sidebar of past chats without loading all messages.

**`messages`**
Stores every chat turn. Has `tool_calls` and `tool_results` as JSONB columns — this is critical because Claude's API requires the full tool call/result history to continue a conversation. Storing them as-is means we can reconstruct the exact API payload for any conversation.

**`memory`**
A key-value store scoped per project. Has a `category` field (goal, technical, decision, team, note) for filtering. Uses `UNIQUE(project_id, key)` so Claude can upsert without creating duplicates. Has a `source` field (chat/agent/manual) so you know where each memory came from.

**`images`**
Stores generated images linked to a project. The `url` field accepts both real URLs and base64 data URIs. The `analysis` field is populated when Gemini analyzes the image. Keeping images in their own table means Claude can reference any project image in any conversation.

**`agent_jobs`**
Tracks background agent runs with status (pending → running → completed/failed), timestamps, and a `result` JSONB for the summary. This is what the frontend polls every 2 seconds to show live progress.

---

## API Endpoints

### Projects
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/projects/` | List all projects |
| POST | `/api/projects/` | Create a project |
| GET | `/api/projects/{id}` | Get project details |
| PATCH | `/api/projects/{id}` | Update project |
| DELETE | `/api/projects/{id}` | Delete project |
| GET | `/api/projects/{id}/summary` | Full overview with memory + images + stats |

### Chat
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/chat/` | Send message — runs full Claude tool loop |
| GET | `/api/chat/conversations/{project_id}` | List conversations |
| GET | `/api/chat/history/{conversation_id}` | Get message history |
| DELETE | `/api/chat/conversations/{id}` | Delete conversation |

### Images
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/images/generate` | Generate image from prompt |
| POST | `/api/images/analyze` | Analyze image with Gemini |
| GET | `/api/images/{project_id}` | List project images |

### Memory
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/memory/{project_id}` | Get all project memory |
| POST | `/api/memory/` | Save a memory entry |
| PATCH | `/api/memory/{id}` | Update memory |
| DELETE | `/api/memory/{id}` | Delete memory |

### Agent
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/agent/trigger` | Start background agent — returns job_id immediately |
| GET | `/api/agent/status/{job_id}` | Poll job status |
| GET | `/api/agent/jobs/{project_id}` | List all agent runs |

---

## How the Tool Loop Works

Every chat message in `routers/chat.py`:

```
User message → Claude (with 6 tools) → tool_use? → execute → feed back → repeat → final response → save to DB
```

**6 tools Claude can use:**
- `get_memory` — recalls project knowledge (called automatically at start of every chat)
- `save_memory` — saves important info for future sessions
- `generate_image` — creates image via Stable Diffusion
- `analyze_image` — sends image to Gemini for analysis
- `list_project_images` — lists all project images
- `search_web` — searches DuckDuckGo

---

## How the Agent System Works

The background agent (`agents/organization_agent.py`) is a sub-agent — a separate Claude instance (Haiku) that runs independently from the chat agent.

```
POST /api/agent/trigger
  → Create agent_jobs record (status: pending)
  → Return job_id immediately (non-blocking)
  → FastAPI BackgroundTasks runs agent async
      → Gathers all project data (brief + messages + images)
      → Claude Haiku extracts structured knowledge as JSON lines
      → Saves each entry to memory table (source: "agent")
      → Updates status → completed
  → Frontend polls /api/agent/status/{job_id} every 2s
```

**Why two agents?** Chat agent (Opus) is optimized for conversation. Organization agent (Haiku) is faster and cheaper for bulk structured extraction. They share the same memory table so agent insights improve future chats.

---

## Project Structure

```
ai-project-assistant/
├── backend/
│   ├── main.py                    # FastAPI app
│   ├── db/schema.sql              # Database schema
│   ├── models/schemas.py          # Pydantic models
│   ├── routers/
│   │   ├── chat.py                # Tool loop
│   │   ├── projects.py
│   │   ├── images.py
│   │   ├── memory.py
│   │   └── agent.py               # Trigger + polling
│   ├── tools/
│   │   ├── definitions.py         # Tool schemas for Claude
│   │   └── executor.py            # Tool execution
│   └── agents/
│       └── organization_agent.py  # Background sub-agent
└── frontend/
    └── src/
        ├── lib/api.js
        └── pages/
            ├── ProjectsPage.js
            └── ProjectPage.js     # Chat + Images + Memory + Agent
```

---

## Tech Stack

- **Backend:** Python + FastAPI
- **Chat AI:** Claude claude-opus-4-5 (tools + memory)
- **Agent AI:** Claude Haiku (background organization)
- **Image Analysis:** Google Gemini 1.5 Flash
- **Image Generation:** Hugging Face Stable Diffusion XL
- **Database:** Supabase (PostgreSQL)
- **Frontend:** React 18

---

## Local Setup

```bash
# 1. Run backend/db/schema.sql in Supabase SQL Editor
# 2. Add your API keys to .env

# Backend
cd backend && pip install -r requirements.txt && python main.py

# Frontend (new terminal)
cd frontend && npm install && npm start
```
