from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String, Text, func

from app.database import Base


class GameProgress(Base):
    __tablename__ = "game_progress"

    id = Column(Integer, primary_key=True, index=True)
    player_name = Column(String(100), default="Player")
    stage = Column(String(100), default="intro")
    xp = Column(Integer, default=0)
    coins = Column(Integer, default=0)
    inventory = Column(Text, default="[]")
    progress_notes = Column(Text, default="")
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class User(Base):
    """Store login identities and salted password hashes for the desktop app."""

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(100), unique=True, index=True, nullable=False)
    display_name = Column(String(100), nullable=False)
    password_hash = Column(String(256), nullable=False)
    demo_password = Column(String(100), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class RedactionRecord(Base):
    """Store a redaction request and its result for later review."""

    __tablename__ = "redactions"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(100), nullable=False)
    source_text = Column(Text, nullable=False)
    redacted_text = Column(Text, nullable=False)
    rules_applied = Column(Text, nullable=False, default="[]")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
