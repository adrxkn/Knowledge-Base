import secrets
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel

from dependencies import get_db, require_role, get_member
from database import Workspace, WorkspaceMember, WorkspaceInvite, User
from auth import get_current_user

router = APIRouter(prefix="/workspaces")


class WorkspaceCreate(BaseModel):
    name: str


class WorkspaceRename(BaseModel):
    name: str


class RoleUpdate(BaseModel):
    role: str


# Workspace CRUD 

@router.post("")
def create_workspace(
    data: WorkspaceCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    ws = Workspace(name=data.name, user_id=user.id)
    db.add(ws)
    db.commit()
    db.refresh(ws)

    member = WorkspaceMember(
        workspace_id=ws.id,
        user_id=user.id,
        role="owner",
    )
    db.add(member)
    db.commit()

    return {"id": ws.id, "name": ws.name, "created_at": ws.created_at, "role": "owner"}


@router.get("")
def list_workspaces(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    memberships = db.query(WorkspaceMember).filter(
        WorkspaceMember.user_id == user.id,
    ).all()

    result = []
    for m in memberships:
        ws = db.query(Workspace).filter(Workspace.id == m.workspace_id).first()
        if ws:
            result.append({
                "id": ws.id,
                "name": ws.name,
                "created_at": ws.created_at,
                "role": m.role,
            })
    return result


@router.patch("/{workspace_id}")
def rename_workspace(
    workspace_id: int,
    data: WorkspaceRename,
    db: Session = Depends(get_db),
    member: WorkspaceMember = Depends(require_role("editor")),
):
    ws = db.query(Workspace).filter(Workspace.id == workspace_id).first()
    ws.name = data.name
    db.commit()
    return {"id": ws.id, "name": ws.name}


@router.delete("/{workspace_id}")
def delete_workspace(
    workspace_id: int,
    db: Session = Depends(get_db),
    member: WorkspaceMember = Depends(require_role("owner")),
):
    ws = db.query(Workspace).filter(Workspace.id == workspace_id).first()
    db.delete(ws)
    db.commit()
    return {"detail": "Workspace deleted"}


# Members

@router.get("/{workspace_id}/members")
def list_members(
    workspace_id: int,
    db: Session = Depends(get_db),
    member: WorkspaceMember = Depends(require_role("owner")),
):
    members = db.query(WorkspaceMember).filter(
        WorkspaceMember.workspace_id == workspace_id
    ).all()
    return [
        {
            "user_id": m.user_id,
            "username": m.user.username,
            "role": m.role,
            "joined_at": m.joined_at,
        }
        for m in members
    ]


@router.patch("/{workspace_id}/members/{user_id}")
def update_member_role(
    workspace_id: int,
    user_id: int,
    data: RoleUpdate,
    db: Session = Depends(get_db),
    member: WorkspaceMember = Depends(require_role("owner")),
):
    valid_roles = ["pending", "viewer", "editor", "owner"]
    if data.role not in valid_roles:
        raise HTTPException(status_code=400, detail=f"Invalid role. Must be one of {valid_roles}")

    target = db.query(WorkspaceMember).filter(
        WorkspaceMember.workspace_id == workspace_id,
        WorkspaceMember.user_id == user_id,
    ).first()

    if not target:
        raise HTTPException(status_code=404, detail="Member not found")

    target.role = data.role
    db.commit()
    return {"user_id": user_id, "role": data.role}


@router.delete("/{workspace_id}/members/{user_id}")
def remove_member(
    workspace_id: int,
    user_id: int,
    db: Session = Depends(get_db),
    member: WorkspaceMember = Depends(require_role("owner")),
):
    if user_id == member.user_id:
        raise HTTPException(status_code=400, detail="Cannot remove yourself from workspace")

    target = db.query(WorkspaceMember).filter(
        WorkspaceMember.workspace_id == workspace_id,
        WorkspaceMember.user_id == user_id,
    ).first()

    if not target:
        raise HTTPException(status_code=404, detail="Member not found")

    db.delete(target)
    db.commit()
    return {"detail": "Member removed"}


# Invites

@router.post("/{workspace_id}/invite")
def create_invite(
    workspace_id: int,
    db: Session = Depends(get_db),
    member: WorkspaceMember = Depends(require_role("owner")),
):
    code = secrets.token_urlsafe(12)
    expires_at = datetime.now(timezone.utc) + timedelta(days=7)

    invite = WorkspaceInvite(
        workspace_id=workspace_id,
        invited_by=member.user_id,
        code=code,
        role="pending",
        expires_at=expires_at,
    )
    db.add(invite)
    db.commit()

    return {
        "code": code,
        "expires_at": expires_at,
    }


@router.post("/join/{code}")
def join_workspace(
    code: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    invite = db.query(WorkspaceInvite).filter(
        WorkspaceInvite.code == code
    ).first()

    if not invite:
        raise HTTPException(status_code=404, detail="Invalid invite code")

    if invite.expires_at and invite.expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=400, detail="Invite code has expired")

    if invite.max_uses and invite.uses >= invite.max_uses:
        raise HTTPException(status_code=400, detail="Invite code has reached maximum uses")

    existing = db.query(WorkspaceMember).filter(
        WorkspaceMember.workspace_id == invite.workspace_id,
        WorkspaceMember.user_id == user.id,
    ).first()

    if existing:
        raise HTTPException(status_code=400, detail="Already a member of this workspace")

    new_member = WorkspaceMember(
        workspace_id=invite.workspace_id,
        user_id=user.id,
        role="pending",
    )
    db.add(new_member)

    invite.uses += 1
    db.commit()

    ws = db.query(Workspace).filter(Workspace.id == invite.workspace_id).first()
    return {
        "workspace_id": invite.workspace_id,
        "workspace_name": ws.name,
        "role": "pending",
        "detail": "Joined successfully. Waiting for owner to grant access."
    }