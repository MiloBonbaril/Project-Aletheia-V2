from __future__ import annotations

import enum
import uuid

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from .base import Base


class Stream(Base):
    __tablename__ = "streams"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    vtuber_name = Column(String(120), nullable=False)
    title = Column(String(200), nullable=True)
    started_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    ended_at = Column(DateTime(timezone=True), nullable=True)
    duration_seconds = Column(Integer, nullable=True)
    context = Column(JSONB, nullable=True)

    long_term_memories = relationship("LongTermMemory", back_populates="stream", cascade="all,delete-orphan")
    short_term_memories = relationship("ShortTermMemory", back_populates="stream", cascade="all,delete-orphan")
    moderation_events = relationship("ModerationEvent", back_populates="stream", cascade="all,delete-orphan")
    highlights = relationship("Highlight", back_populates="stream", cascade="all,delete-orphan")
    data_lore_entries = relationship("DataLore", back_populates="stream", cascade="all,delete-orphan")

    __table_args__ = (
        Index("ix_streams_started_at", "started_at"),
        UniqueConstraint("vtuber_name", "started_at", name="uq_streams_vtuber_start"),
    )


class LongTermMemory(Base):
    __tablename__ = "long_term_memories"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    stream_id = Column(UUID(as_uuid=True), ForeignKey("streams.id", ondelete="CASCADE"), nullable=False)
    summary = Column(Text, nullable=False)
    summary_tokens = Column(Integer, nullable=True)
    topics = Column(ARRAY(String(50)), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    stream = relationship("Stream", back_populates="long_term_memories")

    __table_args__ = (
        Index("ix_long_term_memories_stream_created", "stream_id", "created_at"),
    )


class MemoryRole(enum.StrEnum):
    user = "user"
    assistant = "assistant"
    system = "system"
    tool = "tool"


class MemoryChannel(enum.StrEnum):
    chat = "chat"
    action = "action"
    narration = "narration"


class ShortTermMemory(Base):
    __tablename__ = "short_term_memories"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    stream_id = Column(UUID(as_uuid=True), ForeignKey("streams.id", ondelete="CASCADE"), nullable=True)
    session_id = Column(UUID(as_uuid=True), nullable=False, default=uuid.uuid4)
    message_role = Column(Enum(MemoryRole, name="memory_role"), nullable=False)
    channel = Column(Enum(MemoryChannel, name="memory_channel"), nullable=False, server_default=MemoryChannel.chat.value)
    content = Column(Text, nullable=False)
    extra = Column(JSONB, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    sequence = Column(Integer, nullable=False, server_default="0")

    stream = relationship("Stream", back_populates="short_term_memories")

    __table_args__ = (
        CheckConstraint("sequence >= 0", name="ck_short_term_memories_sequence_positive"),
        Index("ix_short_term_memories_stream_seq", "stream_id", "sequence"),
        Index("ix_short_term_memories_session", "session_id", "sequence"),
        Index("ix_short_term_memories_created", "created_at"),
        {"prefixes": ["UNLOGGED"]},
    )


class UserRole(enum.StrEnum):
    admin = "admin"
    moderator = "moderator"
    operator = "operator"
    viewer = "viewer"


class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(254), nullable=False, unique=True)
    password_hash = Column(String(255), nullable=False)
    display_name = Column(String(120), nullable=True)
    role = Column(Enum(UserRole, name="user_role"), nullable=False, server_default=UserRole.operator.value)
    is_active = Column(Boolean, nullable=False, server_default="true")
    last_login_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index("ix_users_role", "role"),
    )


class SeverityLevel(enum.StrEnum):
    info = "info"
    warning = "warning"
    critical = "critical"


class ModerationEvent(Base):
    __tablename__ = "moderation_events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    stream_id = Column(UUID(as_uuid=True), ForeignKey("streams.id", ondelete="SET NULL"), nullable=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    event_type = Column(String(80), nullable=False)
    severity = Column(Enum(SeverityLevel, name="moderation_severity"), nullable=False, server_default=SeverityLevel.info.value)
    message = Column(Text, nullable=True)
    payload = Column(JSONB, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    acknowledged_at = Column(DateTime(timezone=True), nullable=True)

    stream = relationship("Stream", back_populates="moderation_events")
    user = relationship("User")

    __table_args__ = (
        Index("ix_moderation_events_stream_created", "stream_id", "created_at"),
        Index("ix_moderation_events_severity", "severity"),
    )


class Highlight(Base):
    __tablename__ = "highlights"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    stream_id = Column(UUID(as_uuid=True), ForeignKey("streams.id", ondelete="CASCADE"), nullable=False)
    title = Column(String(160), nullable=False)
    description = Column(Text, nullable=True)
    start_offset_seconds = Column(Integer, nullable=False)
    duration_seconds = Column(Integer, nullable=True)
    tags = Column(ARRAY(String(40)), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    stream = relationship("Stream", back_populates="highlights")

    __table_args__ = (
        CheckConstraint("start_offset_seconds >= 0", name="ck_highlights_start_offset_positive"),
        Index("ix_highlights_stream_start", "stream_id", "start_offset_seconds"),
    )


class LoreOrigin(enum.StrEnum):
    aletheia = "aletheia"
    viewer = "viewer"
    system = "system"


class DataLore(Base):
    __tablename__ = "data_lore"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    stream_id = Column(UUID(as_uuid=True), ForeignKey("streams.id", ondelete="SET NULL"), nullable=True)
    origin = Column(Enum(LoreOrigin, name="lore_origin"), nullable=False)
    speaker_name = Column(String(120), nullable=True)
    summary = Column(Text, nullable=False)
    tags = Column(ARRAY(String(40)), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    stream = relationship("Stream", back_populates="data_lore_entries")

    __table_args__ = (
        Index("ix_data_lore_origin_created", "origin", "created_at"),
    )


__all__ = [
    "Stream",
    "LongTermMemory",
    "ShortTermMemory",
    "User",
    "ModerationEvent",
    "Highlight",
    "DataLore",
    "MemoryRole",
    "MemoryChannel",
    "UserRole",
    "SeverityLevel",
    "LoreOrigin",
]
