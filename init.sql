CREATE EXTENSION IF NOT EXISTS vector;

ALTER TABLE IF EXISTS documents
  ADD COLUMN IF NOT EXISTS status VARCHAR DEFAULT 'ready',
  ADD COLUMN IF NOT EXISTS status_message TEXT,
  ADD COLUMN IF NOT EXISTS file_hash VARCHAR;

ALTER TABLE IF EXISTS chunks
  ADD COLUMN IF NOT EXISTS content_tsv tsvector
    GENERATED ALWAYS AS (to_tsvector('english', content)) STORED;

CREATE INDEX IF NOT EXISTS chunks_content_tsv_idx
  ON chunks USING GIN (content_tsv);

CREATE TABLE IF NOT EXISTS workspace_members (
    id SERIAL PRIMARY KEY,
    workspace_id INTEGER NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    role VARCHAR NOT NULL DEFAULT 'pending',
    joined_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS workspace_invites (
    id SERIAL PRIMARY KEY,
    workspace_id INTEGER NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    invited_by INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    code VARCHAR UNIQUE NOT NULL,
    role VARCHAR NOT NULL DEFAULT 'pending',
    max_uses INTEGER,
    uses INTEGER DEFAULT 0,
    expires_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS system_settings (
    key VARCHAR PRIMARY KEY,
    value TEXT,
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

INSERT INTO system_settings (key, value) VALUES
  ('ollama_url',       'http://host.docker.internal:11434'),
  ('model_name',       'llama3.2'),
  ('chunk_size',       '1000'),
  ('chunk_overlap',    '150'),
  ('retrieval_top_k',  '5')
ON CONFLICT (key) DO NOTHING;