import os
import uuid
import hashlib
import shutil

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, BackgroundTasks
from sqlalchemy.orm import Session

from dependencies import get_db, require_role
from database import Document, WorkspaceMember
from auth import get_current_user
from database import User
from services.document import process_document

router = APIRouter()


@router.get("/documents/{workspace_id}")
def list_documents(
    workspace_id: int,
    db: Session = Depends(get_db),
    member: WorkspaceMember = Depends(require_role("viewer")),
):
    docs = db.query(Document).filter(
        Document.workspace_id == workspace_id,
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


@router.post("/upload/{workspace_id}")
async def upload_document(
    workspace_id: int,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    member: WorkspaceMember = Depends(require_role("editor")),
):
    os.makedirs("uploads", exist_ok=True)

    safe_name = f"{member.user_id}_{uuid.uuid4().hex}_{file.filename}"
    file_path = os.path.join("uploads", safe_name)

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    with open(file_path, "rb") as f:
        file_hash = hashlib.sha256(f.read()).hexdigest()

    existing = db.query(Document).filter(
        Document.workspace_id == workspace_id,
        Document.file_hash == file_hash,
    ).first()

    if existing:
        os.remove(file_path)
        raise HTTPException(
            status_code=409,
            detail=f"This file already exists in the workspace as '{existing.filename}'"
        )

    doc = Document(
        filename=file.filename,
        file_path=file_path,
        file_size=os.path.getsize(file_path),
        file_hash=file_hash,
        user_id=member.user_id,
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


@router.get("/document-status/{doc_id}")
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


@router.delete("/documents/{doc_id}")
def delete_document(
    doc_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    doc = db.query(Document).filter(Document.id == doc_id).first()

    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    member = db.query(WorkspaceMember).filter(
        WorkspaceMember.workspace_id == doc.workspace_id,
        WorkspaceMember.user_id == user.id,
    ).first()

    if not member or member.role not in ("editor", "owner"):
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    if os.path.exists(doc.file_path):
        os.remove(doc.file_path)

    db.delete(doc)
    db.commit()
    return {"detail": "Document deleted"}