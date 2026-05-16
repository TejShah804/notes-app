import uuid

from sqlalchemy import Column, DateTime, ForeignKey, String, Table, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


def generate_uuid() -> str:
    return str(uuid.uuid4())


shared_notes = Table(
    "shared_notes",
    Base.metadata,
    Column(
        "user_id",
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "note_id",
        String(36),
        ForeignKey("notes.id", ondelete="CASCADE"),
        primary_key=True,
    ),
)


class User(Base):
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    created_at = Column(DateTime, server_default=func.now())

    notes = relationship(
        "Note",
        back_populates="owner",
        cascade="all, delete",
    )
    shared_notes = relationship(
        "Note",
        secondary=shared_notes,
        back_populates="shared_with",
    )


class Note(Base):
    __tablename__ = "notes"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    title = Column(String(255), nullable=False)
    content = Column(Text, nullable=False)
    is_pinned = Column(String(5), default="false")
    owner_id = Column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(
        DateTime,
        server_default=func.now(),
        onupdate=func.now(),
    )

    owner = relationship("User", back_populates="notes")
    shared_with = relationship(
        "User",
        secondary=shared_notes,
        back_populates="shared_notes",
    )
