from dotenv import load_dotenv
load_dotenv()

from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session

from database import SessionLocal, User, WorkspaceMember
from auth import get_current_user

ROLE_HIERARCHY = ["pending", "viewer", "editor", "owner"]


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def require_role(minimum_role: str):
    def checker(
        workspace_id: int,
        db: Session = Depends(get_db),
        user: User = Depends(get_current_user),
    ) -> WorkspaceMember:
        member = db.query(WorkspaceMember).filter(
            WorkspaceMember.workspace_id == workspace_id,
            WorkspaceMember.user_id == user.id,
        ).first()

        if not member:
            raise HTTPException(status_code=404, detail="Workspace not found")

        if ROLE_HIERARCHY.index(member.role) < ROLE_HIERARCHY.index(minimum_role):
            raise HTTPException(status_code=403, detail="Insufficient permissions")

        return member

    return checker


def get_member(
    workspace_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> WorkspaceMember:
    member = db.query(WorkspaceMember).filter(
        WorkspaceMember.workspace_id == workspace_id,
        WorkspaceMember.user_id == user.id,
    ).first()

    if not member:
        raise HTTPException(status_code=404, detail="Workspace not found")

    return member