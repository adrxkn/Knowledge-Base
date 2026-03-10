from dotenv import load_dotenv
import os

load_dotenv()

from datetime import datetime, timezone
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import sessionmaker, relationship, declarative_base
from pgvector.sqlalchemy import Vector

SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL")
if not SQLALCHEMY_DATABASE_URL:
    raise RuntimeError("DATABASE_URL environment variable is not set")

engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
Base = declarative_base()


def now_utc():
    """Timezone-aware UTC timestamp. datetime.utcnow() is deprecated in Python 3.12+."""
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, nullable=False, index=True)
    email = Column(String, unique=True, nullable=False, index=True)
    hashed_password = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), default=now_utc)

    workspaces = relationship(
        "Workspace", back_populates="owner",
        cascade="all, delete", lazy="selectin"
    )
    documents = relationship(
        "Document", back_populates="owner",
        cascade="all, delete", lazy="selectin"
    )
    chat_messages = relationship(
        "ChatMessage", back_populates="user",
        cascade="all, delete", lazy="selectin"
    )


class Workspace(Base):
    __tablename__ = "workspaces"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    created_at = Column(DateTime(timezone=True), default=now_utc)

    owner = relationship("User", back_populates="workspaces")
    documents = relationship(
        "Document", back_populates="workspace",
        cascade="all, delete", lazy="selectin"
    )
    chunks = relationship(
        "Chunk", back_populates="workspace",
        cascade="all, delete", lazy="selectin"
    )
    chat_messages = relationship(
        "ChatMessage", back_populates="workspace",
        cascade="all, delete", lazy="selectin"
    )


class Document(Base):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    workspace_id = Column(Integer, ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False)
    filename = Column(String, nullable=False)
    file_path = Column(String, nullable=False)
    file_size = Column(Integer)
    status = Column(String, default="pending")          
    status_message = Column(Text, nullable=True)      
    upload_date = Column(DateTime(timezone=True), default=now_utc)
    content_text = Column(Text)

    owner = relationship("User", back_populates="documents")
    workspace = relationship("Workspace", back_populates="documents")
    chunks = relationship(
        "Chunk", back_populates="document",
        cascade="all, delete", lazy="selectin"
    )


class Chunk(Base):
    __tablename__ = "chunks"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    workspace_id = Column(Integer, ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False)
    content = Column(Text, nullable=False)
    # 384 dimensions for all-MiniLM-L6-v2
    embedding = Column(Vector(384))
    created_at = Column(DateTime(timezone=True), default=now_utc)

    document = relationship("Document", back_populates="chunks")
    workspace = relationship("Workspace", back_populates="chunks")


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id = Column(Integer, primary_key=True, index=True)
    workspace_id = Column(Integer, ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    question = Column(Text, nullable=False)
    answer = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), default=now_utc)

    workspace = relationship("Workspace", back_populates="chat_messages")
    user = relationship("User", back_populates="chat_messages")


Base.metadata.create_all(bind=engine)