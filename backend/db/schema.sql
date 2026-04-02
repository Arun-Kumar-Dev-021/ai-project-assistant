-- ============================================================
--  AI PROJECT ASSISTANT — SUPABASE SCHEMA
--  Run this in your Supabase SQL Editor
-- ============================================================

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- -----------------------------------------------
-- PROJECTS
-- Each project is the top-level container.
-- brief holds all metadata as JSONB for flexibility.
-- -----------------------------------------------
CREATE TABLE projects (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name        TEXT NOT NULL,
    description TEXT,
    goals       TEXT,
    status      TEXT DEFAULT 'active' CHECK (status IN ('active', 'archived', 'completed')),
    brief       JSONB DEFAULT '{}',   -- flexible bag: tech_stack, deadline, team, reference_links, tags, etc.
    created_at  TIMESTAMPTZ DEFAULT NOW(),
    updated_at  TIMESTAMPTZ DEFAULT NOW()
);

-- -----------------------------------------------
-- CONVERSATIONS
-- One conversation belongs to one project.
-- -----------------------------------------------
CREATE TABLE conversations (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id  UUID REFERENCES projects(id) ON DELETE CASCADE,
    title       TEXT DEFAULT 'New Chat',
    created_at  TIMESTAMPTZ DEFAULT NOW(),
    updated_at  TIMESTAMPTZ DEFAULT NOW()
);

-- -----------------------------------------------
-- MESSAGES
-- Every chat message (user or assistant).
-- tool_calls / tool_results stored as JSONB.
-- -----------------------------------------------
CREATE TABLE messages (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    conversation_id UUID REFERENCES conversations(id) ON DELETE CASCADE,
    project_id      UUID REFERENCES projects(id) ON DELETE CASCADE,
    role            TEXT NOT NULL CHECK (role IN ('user', 'assistant', 'tool')),
    content         TEXT,
    tool_calls      JSONB,   -- raw tool_use blocks from Claude
    tool_results    JSONB,   -- tool_result blocks we sent back
    tokens_used     INTEGER DEFAULT 0,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- -----------------------------------------------
-- IMAGES
-- Generated or uploaded images linked to a project.
-- -----------------------------------------------
CREATE TABLE images (
    id           UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id   UUID REFERENCES projects(id) ON DELETE CASCADE,
    prompt       TEXT,                     -- generation prompt
    url          TEXT,                     -- public URL or base64 data URI
    source       TEXT DEFAULT 'generated' CHECK (source IN ('generated', 'uploaded', 'analyzed')),
    analysis     TEXT,                     -- Gemini analysis text
    metadata     JSONB DEFAULT '{}',       -- width, height, model used, etc.
    created_at   TIMESTAMPTZ DEFAULT NOW()
);

-- -----------------------------------------------
-- MEMORY
-- Per-project memory entries created by Claude's memory tool.
-- category lets us slice memory by type.
-- -----------------------------------------------
CREATE TABLE memory (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id  UUID REFERENCES projects(id) ON DELETE CASCADE,
    category    TEXT NOT NULL DEFAULT 'general',  -- e.g. 'goal', 'decision', 'context', 'note'
    key         TEXT NOT NULL,                    -- short identifier / topic
    value       TEXT NOT NULL,                    -- the actual memory content
    source      TEXT DEFAULT 'chat',              -- 'chat' | 'agent' | 'manual'
    created_at  TIMESTAMPTZ DEFAULT NOW(),
    updated_at  TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(project_id, key)
);

-- -----------------------------------------------
-- AGENT JOBS
-- Background agent runs triggered via API.
-- status is polled by the client.
-- -----------------------------------------------
CREATE TABLE agent_jobs (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id  UUID REFERENCES projects(id) ON DELETE CASCADE,
    status      TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'running', 'completed', 'failed')),
    triggered_by TEXT DEFAULT 'api',
    result      JSONB,         -- summary of what the agent did
    error       TEXT,          -- error message if failed
    started_at  TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

-- -----------------------------------------------
-- INDEXES
-- -----------------------------------------------
CREATE INDEX idx_messages_conversation ON messages(conversation_id);
CREATE INDEX idx_messages_project      ON messages(project_id);
CREATE INDEX idx_memory_project        ON memory(project_id);
CREATE INDEX idx_images_project        ON images(project_id);
CREATE INDEX idx_agent_jobs_project    ON agent_jobs(project_id);
CREATE INDEX idx_agent_jobs_status     ON agent_jobs(status);

-- -----------------------------------------------
-- AUTO-UPDATE updated_at
-- -----------------------------------------------
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN NEW.updated_at = NOW(); RETURN NEW; END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_projects_updated    BEFORE UPDATE ON projects    FOR EACH ROW EXECUTE FUNCTION update_updated_at();
CREATE TRIGGER trg_conversations_updated BEFORE UPDATE ON conversations FOR EACH ROW EXECUTE FUNCTION update_updated_at();
CREATE TRIGGER trg_memory_updated      BEFORE UPDATE ON memory      FOR EACH ROW EXECUTE FUNCTION update_updated_at();
