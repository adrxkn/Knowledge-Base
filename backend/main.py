import os
import json
import shutil
import uuid

import PyPDF2
import requests as http_requests

from datetime import timedelta
from pydantic import BaseModel

from fastapi import FastAPI, UploadFile, File, Depends, HTTPException, status, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.security import OAuth2PasswordRequestForm

from sqlalchemy.orm import Session
from sqlalchemy import text

from sentence_transformers import SentenceTransformer, CrossEncoder

from database import SessionLocal, Document, User, Workspace, Chunk, ChatMessage
from auth import (
    get_password_hash,
    authenticate_user,
    create_access_token,
    get_current_user,
    ACCESS_TOKEN_EXPIRE_MINUTES,
)

embedding_model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
rerank_model    = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

os.makedirs("uploads", exist_ok=True)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Schemas

class UserCreate(BaseModel):
    username: str
    email: str
    password: str


class WorkspaceCreate(BaseModel):
    name: str


class Token(BaseModel):
    access_token: str
    token_type: str


def extract_text_from_pdf(file_path: str) -> str:
    text = ""
    with open(file_path, "rb") as f:
        reader = PyPDF2.PdfReader(f)
        for page in reader.pages:
            extracted = page.extract_text()
            if extracted:
                text += extracted
    return text


def chunk_text(text: str, size: int = 500, overlap: int = 100) -> list[str]:
    chunks = []
    start = 0
    while start < len(text):
        chunks.append(text[start:start + size])
        start += size - overlap
    return chunks

def process_document(doc_id: int, file_path: str, filename: str, workspace_id: int):
    db = SessionLocal()
    try:
        doc = db.query(Document).filter(Document.id == doc_id).first()
        if not doc:
            return

        doc.status = "processing"
        db.commit()

        text_content = ""
        if filename.lower().endswith(".pdf"):
            text_content = extract_text_from_pdf(file_path)
        elif filename.lower().endswith((".txt", ".md")):
            with open(file_path, "r", errors="ignore") as f:
                text_content = f.read()

        if not text_content.strip():
            doc.status = "failed"
            doc.status_message = "Could not extract text from file."
            db.commit()
            return

        doc.content_text = text_content
        db.commit()

        chunks = chunk_text(text_content)
        embeddings = embedding_model.encode(chunks, show_progress_bar=False)

        for chunk, emb in zip(chunks, embeddings):
            db.add(Chunk(
                document_id=doc_id,
                workspace_id=workspace_id,
                content=chunk,
                embedding=emb.tolist(),
            ))

        db.commit()

        doc.status = "ready"
        doc.status_message = None
        db.commit()

    except Exception as e:
        db.rollback()
        try:
            doc = db.query(Document).filter(Document.id == doc_id).first()
            if doc:
                doc.status = "failed"
                doc.status_message = str(e)
                db.commit()
        except Exception:
            pass
    finally:
        db.close()

def get_workspace_or_404(workspace_id: int, user: User, db: Session) -> Workspace:
    ws = db.query(Workspace).filter(
        Workspace.id == workspace_id,
        Workspace.user_id == user.id,
    ).first()
    if not ws:
        raise HTTPException(status_code=404, detail="Workspace not found")
    return ws


@app.post("/register")
def register(user: UserCreate, db: Session = Depends(get_db)):
    if db.query(User).filter(User.username == user.username).first():
        raise HTTPException(status_code=400, detail="Username already taken")
    if db.query(User).filter(User.email == user.email).first():
        raise HTTPException(status_code=400, detail="Email already registered")

    new_user = User(
        username=user.username,
        email=user.email,
        hashed_password=get_password_hash(user.password),
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return {"id": new_user.id, "username": new_user.username, "email": new_user.email}


@app.post("/login", response_model=Token)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = create_access_token(
        data={"sub": str(user.id)},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
    )
    return {"access_token": token, "token_type": "bearer"}


# Workspace

@app.post("/workspaces")
def create_workspace(
    data: WorkspaceCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    ws = Workspace(name=data.name, user_id=user.id)
    db.add(ws)
    db.commit()
    db.refresh(ws)
    return {"id": ws.id, "name": ws.name, "created_at": ws.created_at}


@app.get("/workspaces")
def list_workspaces(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    workspaces = db.query(Workspace).filter(Workspace.user_id == user.id).all()
    return [{"id": w.id, "name": w.name, "created_at": w.created_at} for w in workspaces]


# Documents

@app.get("/documents/{workspace_id}")
def list_documents(
    workspace_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    get_workspace_or_404(workspace_id, user, db) 
    docs = db.query(Document).filter(
        Document.workspace_id == workspace_id,
        Document.user_id == user.id,
    ).all()
    return [
        {
            "id": d.id,
            "filename": d.filename,
            "file_size": d.file_size,
            "upload_date": d.upload_date,
            "status": d.status, 
        }
        for d in docs
    ]


@app.post("/upload/{workspace_id}")
async def upload_document(
    workspace_id: int,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    get_workspace_or_404(workspace_id, user, db)

    safe_name = f"{user.id}_{uuid.uuid4().hex}_{file.filename}"
    file_path = os.path.join("uploads", safe_name)

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    doc = Document(
        filename=file.filename,
        file_path=file_path,
        file_size=os.path.getsize(file_path),
        user_id=user.id,
        workspace_id=workspace_id,
        status="pending",
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)

    background_tasks.add_task(
        process_document, doc.id, file_path, file.filename, workspace_id
    )

    return {"id": doc.id, "filename": doc.filename, "status": "pending"}

@app.get("/document-status/{doc_id}")
def get_document_status(
    doc_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    doc = db.query(Document).filter(
        Document.id == doc_id,
        Document.user_id == user.id,
    ).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return {
        "id": doc.id,
        "filename": doc.filename,
        "status": doc.status,
        "status_message": doc.status_message,
    }

@app.get("/search/{workspace_id}")
def semantic_search(
    workspace_id: int,
    query: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    get_workspace_or_404(workspace_id, user, db) 

    q_embedding = embedding_model.encode([query])[0].tolist()
    sql = text("""
        SELECT d.filename, c.content
        FROM chunks c
        JOIN documents d ON d.id = c.document_id
        WHERE c.workspace_id = :workspace_id
        ORDER BY c.embedding <-> CAST(:embedding AS vector)
        LIMIT 10
    """)
    results = db.execute(sql, {"workspace_id": workspace_id, "embedding": q_embedding})
    return [{"document": r[0], "snippet": r[1][:200]} for r in results]


# Chat history

@app.get("/chat-history/{workspace_id}")
def get_chat_history(
    workspace_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    get_workspace_or_404(workspace_id, user, db)  

    messages = (
        db.query(ChatMessage)
        .filter(
            ChatMessage.workspace_id == workspace_id,
            ChatMessage.user_id == user.id,
        )
        .order_by(ChatMessage.created_at)
        .all()
    )
    return [
        {"question": m.question, "answer": m.answer, "timestamp": m.created_at}
        for m in messages
    ]


# LLM part

def build_prompt(context: str, history_text: str, question: str) -> str:
    return f"""You are a helpful assistant that answers questions strictly from the provided document context.

Rules:
- Base ALL factual claims and terminology ONLY on the Context section below.
- The Conversation history is provided so you understand what the user is asking about, but NEVER treat it as a factual source. If the user used a wrong term in a previous message, do not repeat or validate that wrong term — use the correct term from the Context instead.
- If the Context does not contain enough information to answer, say so clearly.
- Do not invent, assume, or infer information not present in the Context.
- Format your response using Markdown: use **bold** for key terms, headers (##) for sections when the answer is long, bullet points or numbered lists where appropriate, and code blocks for any code or technical syntax.

Conversation history (for understanding intent only — not a factual source):
{history_text}

Context (the only source of truth):
{context}

Question:
{question}

Answer:"""


def fetch_recent_history(workspace_id: int, user_id: int, db: Session, limit: int = 5) -> str:
    history = (
        db.query(ChatMessage)
        .filter(
            ChatMessage.workspace_id == workspace_id,
            ChatMessage.user_id == user_id,
        )
        .order_by(ChatMessage.created_at.desc())
        .limit(limit)
        .all()
    )
    return "".join(
        f"User: {h.question}\nAI: {h.answer}\n" for h in reversed(history)
    )

def hybrid_retrieve(workspace_id: int, question: str, q_embedding: list, db: Session, candidate_limit: int = 20) -> list[tuple]:
    vector_sql = text("""
        SELECT c.id, c.content, d.filename,
               ROW_NUMBER() OVER (ORDER BY c.embedding <-> CAST(:embedding AS vector)) AS rnk
        FROM chunks c
        JOIN documents d ON d.id = c.document_id
        WHERE c.workspace_id = :workspace_id
        ORDER BY c.embedding <-> CAST(:embedding AS vector)
        LIMIT :lim
    """)
    vector_rows = db.execute(vector_sql, {
        "workspace_id": workspace_id,
        "embedding": q_embedding,
        "lim": candidate_limit,
    }).fetchall()

    fts_sql = text("""
        SELECT c.id, c.content, d.filename,
               ROW_NUMBER() OVER (ORDER BY ts_rank(c.content_tsv, query) DESC) AS rnk
        FROM chunks c
        JOIN documents d ON d.id = c.document_id,
        plainto_tsquery('english', :question) query
        WHERE c.workspace_id = :workspace_id
          AND c.content_tsv @@ query
        ORDER BY ts_rank(c.content_tsv, query) DESC
        LIMIT :lim
    """)
    fts_rows = db.execute(fts_sql, {
        "workspace_id": workspace_id,
        "question": question,
        "lim": candidate_limit,
    }).fetchall()

    K = 60
    scores: dict[int, float] = {}
    chunks_by_id: dict[int, tuple] = {}

    for row in vector_rows:
        cid = row[0]
        scores[cid] = scores.get(cid, 0.0) + 1.0 / (K + row[3])
        chunks_by_id[cid] = (row[1], row[2])

    for row in fts_rows:
        cid = row[0]
        scores[cid] = scores.get(cid, 0.0) + 1.0 / (K + row[3])
        chunks_by_id[cid] = (row[1], row[2])

    ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:candidate_limit]
    return [(chunks_by_id[cid][0], chunks_by_id[cid][1]) for cid, _ in ranked]


def rerank(question: str, candidates: list[tuple], top_k: int = 5) -> list[tuple]:
    if not candidates:
        return []

    pairs = [[question, c[0]] for c in candidates]
    scores = rerank_model.predict(pairs)

    scored = sorted(zip(scores, candidates), key=lambda x: x[0], reverse=True)
    return [c for _, c in scored[:top_k]]


def fetch_context_chunks(workspace_id: int, question: str, q_embedding: list, db: Session, top_k: int = 5) -> list[tuple]:
    candidates = hybrid_retrieve(workspace_id, question, q_embedding, db, candidate_limit=20)
    return rerank(question, candidates, top_k=top_k)


@app.post("/ask/{workspace_id}")
def ask_ai(
    workspace_id: int,
    question: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    get_workspace_or_404(workspace_id, user, db)  

    q_embedding = embedding_model.encode([question])[0].tolist()
    rows = fetch_context_chunks(workspace_id, question, q_embedding, db)

    context = "\n\n".join(r[0] for r in rows)
    sources = [{"document": r[1], "snippet": r[0][:200]} for r in rows]
    history_text = fetch_recent_history(workspace_id, user.id, db)
    prompt = build_prompt(context, history_text, question)

    response = http_requests.post(
        "http://localhost:11434/api/generate",
        json={"model": "llama3.2", "prompt": prompt, "stream": False},
    )
    answer = response.json().get("response", "")

    db.add(ChatMessage(
        workspace_id=workspace_id,
        user_id=user.id,
        question=question,
        answer=answer,
    ))
    db.commit()

    return {"answer": answer, "sources": sources}


@app.post("/ask-stream/{workspace_id}")
def ask_ai_stream(
    workspace_id: int,
    question: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    get_workspace_or_404(workspace_id, user, db)

    q_embedding = embedding_model.encode([question])[0].tolist()
    rows = fetch_context_chunks(workspace_id, question, q_embedding, db)

    context = "\n\n".join(r[0] for r in rows)
    history_text = fetch_recent_history(workspace_id, user.id, db)
    prompt = build_prompt(context, history_text, question)

    full_answer_parts: list[str] = []

    def stream_and_save():
        response = http_requests.post(
            "http://localhost:11434/api/generate",
            json={"model": "llama3.2", "prompt": prompt, "stream": True},
            stream=True,
        )
        for line in response.iter_lines():
            if line:
                data = json.loads(line)
                token = data.get("response", "")
                if token:
                    full_answer_parts.append(token)
                    yield f"0:{json.dumps(token)}\n"  # text token
                if data.get("done"):
                    full_answer = "".join(full_answer_parts)
                    save_db = SessionLocal()
                    try:
                        save_db.add(ChatMessage(
                            workspace_id=workspace_id,
                            user_id=user.id,
                            question=question,
                            answer=full_answer,
                        ))
                        save_db.commit()
                    finally:
                        save_db.close()

                    source_list = [
                        {"document": r[1], "snippet": r[0][:200]}
                        for r in rows
                    ]
                    yield f"1:{json.dumps(source_list)}\n"

    return StreamingResponse(stream_and_save(), media_type="text/plain")