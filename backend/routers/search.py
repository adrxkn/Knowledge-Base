from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text

from dependencies import get_db, require_role
from database import WorkspaceMember
from services.models import embedding_model

router = APIRouter()


@router.get("/search/{workspace_id}")
def semantic_search(
    workspace_id: int,
    query: str,
    db: Session = Depends(get_db),
    member: WorkspaceMember = Depends(require_role("viewer")),
):
    q_embedding = embedding_model.encode([query])[0].tolist()
    sql = text("""
        SELECT d.filename, c.content
        FROM chunks c
        JOIN documents d ON d.id = c.document_id
        WHERE c.workspace_id = :workspace_id
        ORDER BY c.embedding <-> CAST(:embedding AS vector)
        LIMIT 10
    """)
    results = db.execute(sql, {
        "workspace_id": workspace_id,
        "embedding": q_embedding
    })
    return [{"document": r[0], "snippet": r[1][:200]} for r in results]