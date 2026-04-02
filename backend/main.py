from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import chat, projects, images, memory, agent
import uvicorn

app = FastAPI(title="AI Project Assistant", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(projects.router, prefix="/api/projects", tags=["Projects"])
app.include_router(chat.router, prefix="/api/chat", tags=["Chat"])
app.include_router(images.router, prefix="/api/images", tags=["Images"])
app.include_router(memory.router, prefix="/api/memory", tags=["Memory"])
app.include_router(agent.router, prefix="/api/agent", tags=["Agent"])

@app.get("/")
def root():
    return {"status": "AI Project Assistant running", "version": "1.0.0"}

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
