from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional

from dependencies import get_db, get_current_user
from database import SystemSettings, User

router = APIRouter(prefix="/settings")

ALLOWED_KEYS = {"ollama_url", "model_name", "chunk_size", "chunk_overlap", "retrieval_top_k"}

DEFAULTS = {
    "ollama_url":       "http://localhost:11434",
    "model_name":       "llama3.2",
    "chunk_size":       "1000",
    "chunk_overlap":    "150",
    "retrieval_top_k":  "5",
}


def get_setting(db: Session, key: str) -> str:
    row = db.query(SystemSettings).filter(SystemSettings.key == key).first()
    return row.value if row else DEFAULTS.get(key)


class SettingsUpdate(BaseModel):
    ollama_url:      Optional[str] = None
    model_name:      Optional[str] = None
    chunk_size:      Optional[str] = None
    chunk_overlap:   Optional[str] = None
    retrieval_top_k: Optional[str] = None


@router.get("")
def read_settings(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return {key: get_setting(db, key) for key in ALLOWED_KEYS}


@router.patch("")
def write_settings(
    data: SettingsUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    updates = data.model_dump(exclude_none=True)
    for key, value in updates.items():
        if key not in ALLOWED_KEYS:
            continue
        row = db.query(SystemSettings).filter(SystemSettings.key == key).first()
        if row:
            row.value = value
        else:
            db.add(SystemSettings(key=key, value=value))
    db.commit()
    return {key: get_setting(db, key) for key in ALLOWED_KEYS}