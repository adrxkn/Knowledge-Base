import json

import requests as http_requests

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from dependencies import get_db, require_role
from database import ChatMessage, WorkspaceMember, SessionLocal
from services.models import embedding_model
from services.rag import fetch_context_chunks, build_prompt, fetch_recent_history
from routers.settings import get_setting

router = APIRouter()


@router.get("/chat-history/{workspace_id}")
def get_chat_history(
    workspace_id: int,
    db: Session = Depends(get_db),
    member: WorkspaceMember = Depends(require_role("viewer")),
):
    messages = (
        db.query(ChatMessage)
        .filter(
            ChatMessage.workspace_id == workspace_id,
            ChatMessage.user_id == member.user_id,
        )
        .order_by(ChatMessage.created_at)
        .all()
    )
    return [
        {"question": m.question, "answer": m.answer, "timestamp": m.created_at}
        for m in messages
    ]


@router.post("/ask/{workspace_id}")
def ask_ai(
    workspace_id: int,
    question: str,
    db: Session = Depends(get_db),
    member: WorkspaceMember = Depends(require_role("viewer")),
):
    ollama_url = get_setting(db, "ollama_url")
    model_name = get_setting(db, "model_name")
    top_k      = int(get_setting(db, "retrieval_top_k"))

    q_embedding = embedding_model.encode([question])[0].tolist()
    rows = fetch_context_chunks(workspace_id, question, q_embedding, db, top_k=top_k)

    context = "\n\n".join(r[0] for r in rows)
    sources = [{"document": r[1], "snippet": r[0][:200]} for r in rows]
    history_text = fetch_recent_history(workspace_id, member.user_id, db)
    prompt = build_prompt(context, history_text, question)

    response = http_requests.post(
        f"{ollama_url}/api/generate",
        json={"model": model_name, "prompt": prompt, "stream": False},
    )
    answer = response.json().get("response", "")

    db.add(ChatMessage(
        workspace_id=workspace_id,
        user_id=member.user_id,
        question=question,
        answer=answer,
    ))
    db.commit()

    return {"answer": answer, "sources": sources}


@router.post("/ask-stream/{workspace_id}")
def ask_ai_stream(
    workspace_id: int,
    question: str,
    db: Session = Depends(get_db),
    member: WorkspaceMember = Depends(require_role("viewer")),
):
    ollama_url = get_setting(db, "ollama_url")
    model_name = get_setting(db, "model_name")
    top_k      = int(get_setting(db, "retrieval_top_k"))

    q_embedding = embedding_model.encode([question])[0].tolist()
    rows = fetch_context_chunks(workspace_id, question, q_embedding, db, top_k=top_k)

    context = "\n\n".join(r[0] for r in rows)
    history_text = fetch_recent_history(workspace_id, member.user_id, db)
    prompt = build_prompt(context, history_text, question)

    user_id = member.user_id
    full_answer_parts: list[str] = []

    def stream_and_save():
        response = http_requests.post(
            f"{ollama_url}/api/generate",
            json={"model": model_name, "prompt": prompt, "stream": True},
            stream=True,
        )
        for line in response.iter_lines():
            if line:
                data = json.loads(line)
                token = data.get("response", "")
                if token:
                    full_answer_parts.append(token)
                    yield f"0:{json.dumps(token)}\n"
                if data.get("done"):
                    full_answer = "".join(full_answer_parts)
                    save_db = SessionLocal()
                    try:
                        save_db.add(ChatMessage(
                            workspace_id=workspace_id,
                            user_id=user_id,
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