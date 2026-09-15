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
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(100), unique=True, nullable=False, index=True)
    display_name = Column(String(100), nullable=False)
    password_hash = Column(String(300), nullable=False)


class RedactionRecord(Base):
    __tablename__ = "redaction_records"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False, index=True)
    redacted_text = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
