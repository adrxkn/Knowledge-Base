from sqlalchemy.orm import Session
from sqlalchemy import text
from services.models import embedding_model, rerank_model


def build_prompt(context: str, history_text: str, question: str) -> str:
    #math_example = r"Q·K^T / sqrt(dk)' not '\frac{QK^T}{\sqrt{d_k}}"
    return f"""You are a helpful assistant that answers questions strictly from the provided document context.

Rules:
- Base ALL factual claims and terminology ONLY on the Context section below.
- The Conversation history is provided so you understand what the user is asking about, but NEVER treat it as a factual source. If the user used a wrong term in a previous message, do not repeat or validate that wrong term — use the correct term from the Context instead.
- If the Context does not contain enough information to answer, say so clearly.
- Do not invent, assume, or infer information not present in the Context.
- Be comprehensive and detailed. If the context contains more relevant information, include it. Do not stop at a surface-level answer.
- Format your response using Markdown: use **bold** for key terms, headers (##) for sections when the answer is long, bullet points or numbered lists where appropriate.
- For code blocks, only use them for actual programming code or command-line instructions.
- Never output raw HTML tags like <br>. Use blank lines for paragraph breaks instead.

Conversation history (for understanding intent only — not a factual source):
{history_text}

Context (the only source of truth):
{context}

Question:
{question}

Answer:"""


def hybrid_retrieve(
    workspace_id: int,
    question: str,
    q_embedding: list,
    db: Session,
    candidate_limit: int = 20
) -> list[tuple]:
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


def fetch_context_chunks(
    workspace_id: int,
    question: str,
    q_embedding: list,
    db: Session,
    top_k: int = 5
) -> list[tuple]:
    candidates = hybrid_retrieve(workspace_id, question, q_embedding, db)
    return rerank(question, candidates, top_k=top_k)


def fetch_recent_history(
    workspace_id: int,
    user_id: int,
    db: Session,
    limit: int = 5
) -> str:
    from database import ChatMessage
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