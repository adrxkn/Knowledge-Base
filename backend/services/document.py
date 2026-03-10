import os
import fitz 
from database import SessionLocal, Document, Chunk
from services.models import embedding_model


def extract_text_from_pdf(file_path: str) -> str:
    text = ""
    with fitz.open(file_path) as doc:
        for page in doc:
            text += page.get_text()
    return text


def chunk_text(text: str, size: int = 1000, overlap: int = 150) -> list[str]:
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
        embeddings = embedding_model.encode(
            chunks,
            batch_size=64,
            show_progress_bar=False
        )

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