"""SQLAlchemy 2.0 async models and engine setup.

Models implemented according to PERSISTENCE_STRATEGY.md.
"""
import os
import uuid
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import declarative_base, relationship, sessionmaker
from sqlalchemy import (
    Column,
    String,
    Integer,
    DECIMAL,
    TIMESTAMP,
    ForeignKey,
    Boolean,
    Index,
    JSON,
)
from sqlalchemy.dialects.postgresql import UUID

# Base declarative class
Base = declarative_base()

# Database URL from environment
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://archer:archer_dev_pass@localhost:5432/archer_dev",
)

# Async engine
engine = create_async_engine(
    DATABASE_URL,
    echo=True,  # Log SQL in development
    future=True,
)

# Async session factory
async_session = sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)


async def get_session() -> AsyncSession:
    """Dependency for FastAPI route handlers."""
    async with async_session() as session:
        yield session


# Models
class Customer(Base):
    __tablename__ = "customers"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    phone_number = Column(String(20), unique=True, nullable=False, index=True)
    name = Column(String(100), nullable=False)
    account_last_4 = Column(String(4), nullable=False)
    postal_code = Column(String(10), nullable=False)
    balance = Column(DECIMAL(10, 2), nullable=False)
    days_overdue = Column(Integer, default=0)
    segment = Column(String(20), nullable=False, default="standard")
    language = Column(String(5), default="en")
    extra_data = Column(JSON, default={})  # Renamed from 'metadata' (reserved by SQLAlchemy)
    created_at = Column(TIMESTAMP, default=datetime.utcnow)
    updated_at = Column(TIMESTAMP, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    calls = relationship("Call", back_populates="customer", cascade="all, delete-orphan")


class Call(Base):
    __tablename__ = "calls"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    call_sid = Column(String(100), unique=True, nullable=False, index=True)
    customer_id = Column(
        UUID(as_uuid=True), ForeignKey("customers.id", ondelete="CASCADE"), nullable=False, index=True
    )
    call_type = Column(String(20), nullable=False)  # 'real_call', 'simulator', 'test'
    direction = Column(String(10), nullable=False, default="outbound")
    status = Column(String(20), nullable=False, index=True)  # 'in_progress', 'completed', 'failed'
    start_time = Column(TIMESTAMP, nullable=False, index=True)
    end_time = Column(TIMESTAMP)
    duration_seconds = Column(Integer)
    conversation_id = Column(String(100))
    outcome = Column(String(50))  # 'payment_arranged', 'callback_scheduled', 'transfer'
    extra_data = Column(JSON, default={})  # Renamed from 'metadata' (reserved by SQLAlchemy)
    created_at = Column(TIMESTAMP, default=datetime.utcnow)

    # Relationships
    customer = relationship("Customer", back_populates="calls")
    transcript_entries = relationship(
        "CallTranscriptEntry",
        back_populates="call",
        cascade="all, delete-orphan",
        order_by="CallTranscriptEntry.sequence_number",
    )


class CallTranscriptEntry(Base):
    __tablename__ = "call_transcript_entries"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    call_id = Column(UUID(as_uuid=True), ForeignKey("calls.id", ondelete="CASCADE"), nullable=False, index=True)
    timestamp = Column(TIMESTAMP, nullable=False, index=True)
    entry_type = Column(String(20), nullable=False)  # 'transcript', 'tool', 'event'
    sequence_number = Column(Integer, nullable=False)

    # Transcript fields (when entry_type = 'transcript')
    speaker = Column(String(20))  # 'agent', 'customer'
    text = Column(String)

    # Tool execution fields (when entry_type = 'tool')
    tool_name = Column(String(50))
    tool_request = Column(JSON)
    tool_response = Column(JSON)
    tool_success = Column(Boolean)
    tool_duration_ms = Column(Integer)

    # Event fields (when entry_type = 'event')
    event_type = Column(String(50))
    event_data = Column(JSON)

    created_at = Column(TIMESTAMP, default=datetime.utcnow)

    # Relationships
    call = relationship("Call", back_populates="transcript_entries")


# Performance indexes
Index("idx_transcript_call_sequence", CallTranscriptEntry.call_id, CallTranscriptEntry.sequence_number)
