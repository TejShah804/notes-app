from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app import models, schemas
from app.auth import get_current_user
from app.database import get_db

router = APIRouter(prefix="/notes", tags=["Notes"])


def get_accessible_note(
    note_id: str, user: models.User, db: Session
) -> models.Note:
    note = db.query(models.Note).filter(models.Note.id == note_id).first()
    if not note:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Note not found",
        )

    is_owner = note.owner_id == user.id
    is_shared = any(shared_user.id == user.id for shared_user in note.shared_with)

    if not is_owner and not is_shared:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )

    return note


@router.get("", response_model=List[schemas.NoteResponse])
def list_notes(
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    q: Optional[str] = Query(None),
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = db.query(models.Note).filter(
        or_(
            models.Note.owner_id == current_user.id,
            models.Note.shared_with.any(models.User.id == current_user.id),
        )
    )

    if q:
        query = query.filter(
            or_(
                models.Note.title.ilike(f"%{q}%"),
                models.Note.content.ilike(f"%{q}%"),
            )
        )

    query = query.order_by(
        models.Note.is_pinned.desc(),
        models.Note.updated_at.desc(),
    )

    offset = (page - 1) * limit
    notes = query.offset(offset).limit(limit).all()
    return notes


@router.get("/{note_id}", response_model=schemas.NoteResponse)
def get_note(
    note_id: str,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return get_accessible_note(note_id, current_user, db)


@router.post("", response_model=schemas.NoteResponse, status_code=status.HTTP_201_CREATED)
def create_note(
    payload: schemas.NoteCreate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not payload.title.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Title cannot be empty",
        )
    if not payload.content.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Content cannot be empty",
        )

    note = models.Note(
        title=payload.title.strip(),
        content=payload.content.strip(),
        owner_id=current_user.id,
    )
    db.add(note)
    db.commit()
    db.refresh(note)
    return note


@router.put("/{note_id}", response_model=schemas.NoteResponse)
def update_note(
    note_id: str,
    payload: schemas.NoteUpdate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    note = (
        db.query(models.Note)
        .filter(
            models.Note.id == note_id,
            models.Note.owner_id == current_user.id,
        )
        .first()
    )

    if not note:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Note not found or access denied",
        )

    if payload.title is not None:
        if not payload.title.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Title cannot be empty",
            )
        note.title = payload.title.strip()

    if payload.content is not None:
        if not payload.content.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Content cannot be empty",
            )
        note.content = payload.content.strip()

    db.commit()
    db.refresh(note)
    return note


@router.delete("/{note_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_note(
    note_id: str,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    note = (
        db.query(models.Note)
        .filter(
            models.Note.id == note_id,
            models.Note.owner_id == current_user.id,
        )
        .first()
    )

    if not note:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Note not found or access denied",
        )

    db.delete(note)
    db.commit()


@router.post("/{note_id}/share")
def share_note(
    note_id: str,
    payload: schemas.ShareNote,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    note = (
        db.query(models.Note)
        .filter(
            models.Note.id == note_id,
            models.Note.owner_id == current_user.id,
        )
        .first()
    )

    if not note:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Note not found or access denied",
        )

    if payload.share_with_email == current_user.email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot share a note with yourself",
        )

    target_user = (
        db.query(models.User)
        .filter(models.User.email == payload.share_with_email)
        .first()
    )

    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User with that email not found",
        )

    already_shared = any(
        shared_user.id == target_user.id for shared_user in note.shared_with
    )
    if already_shared:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Note already shared with this user",
        )

    note.shared_with.append(target_user)
    db.commit()

    return {
        "message": f"Note shared successfully with {payload.share_with_email}"
    }


@router.post("/{note_id}/pin")
def toggle_pin(
    note_id: str,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    note = (
        db.query(models.Note)
        .filter(
            models.Note.id == note_id,
            models.Note.owner_id == current_user.id,
        )
        .first()
    )

    if not note:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Note not found or access denied",
        )

    if note.is_pinned == "true":
        note.is_pinned = "false"
        message = "Note unpinned successfully"
    else:
        note.is_pinned = "true"
        message = "Note pinned successfully"

    db.commit()
    db.refresh(note)

    return {"message": message, "is_pinned": note.is_pinned}
