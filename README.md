# Knowledge Management System

> A self-hosted, privacy-first AI knowledge workspace. Upload your documents and query them with a local LLM — nothing leaves your infrastructure.

## Features
 
- RAG pipeline with hybrid retrieval (pgvector semantic search + PostgreSQL FTS), Reciprocal Rank Fusion, and cross-encoder reranking
- Real-time streaming responses with follow-up prompt chips
- Multi-user RBAC — 4-tier roles (owner / editor / viewer / pending) with workspace invite codes
- Background document processing — no upload timeouts on large files
- Configurable LLM, chunk size, and retrieval settings via the settings page
- Privacy-first — all inference runs locally via Ollama, no data sent to third-party APIs

## Prerequisites
 
- Python 3.11+
- PostgreSQL with [pgvector](https://github.com/pgvector/pgvector) extension
- [Ollama](https://ollama.com) with a model pulled — `ollama pull llama3.2`
- Node.js 18+
 
---
 
## Setup
 
**1. Clone**
```bash
git clone https://github.com/adrxkn/Knowledge-Base.git
cd Knowledge-Base
```
 
**2. Backend**
```bash
cd backend
python -m venv venv
venv\Scripts\activate  # Windows
pip install -r requirements.txt
```
 
Create `backend/.env`:
```env
DATABASE_URL=postgresql://postgres:yourpassword@localhost:5432/knowledgebase
SECRET_KEY=your_random_secret
```
 
Run migrations in psql:
```sql
CREATE EXTENSION IF NOT EXISTS vector;
 
ALTER TABLE chunks ADD COLUMN IF NOT EXISTS content_tsv tsvector
  GENERATED ALWAYS AS (to_tsvector('english', content)) STORED;
CREATE INDEX IF NOT EXISTS chunks_content_tsv_idx ON chunks USING GIN (content_tsv);
 
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
  ('ollama_url', 'http://localhost:11434'),
  ('model_name', 'llama3.2'),
  ('chunk_size', '1000'),
  ('chunk_overlap', '150'),
  ('retrieval_top_k', '5')
ON CONFLICT (key) DO NOTHING;
```
 
Start backend:
```bash
uvicorn main:app
```
 
**3. Frontend**
```bash
cd frontend-react
npm install
npm run dev
```
 
Open [http://localhost:5173](http://localhost:5173), create an account, and configure your Ollama URL in ⚙ Settings.
 
---