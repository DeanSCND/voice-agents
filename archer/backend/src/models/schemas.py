"""Pydantic v2 schemas for request/response validation.

These schemas are intended to mirror the SQLAlchemy models for API
validation and use Pydantic v2 patterns (ConfigDict(from_attributes=True)).
"""

from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, Dict, Any
from datetime import datetime
from decimal import Decimal
from uuid import UUID

# Customer Schemas
class CustomerBase(BaseModel):
    phone_number: str = Field(..., max_length=20)
    name: str = Field(..., max_length=100)
    account_last_4: str = Field(..., max_length=4)
    postal_code: str = Field(..., max_length=10)
    balance: Decimal = Field(..., decimal_places=2)
    days_overdue: int = Field(default=0)
    segment: str = Field(default='standard', max_length=20)
    language: str = Field(default='en', max_length=5)
    extra_data: Dict[str, Any] = Field(default_factory=dict)


class CustomerCreate(CustomerBase):
    pass


class CustomerResponse(CustomerBase):
    id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# Call Schemas
class CallBase(BaseModel):
    call_sid: str = Field(..., max_length=100)
    customer_id: UUID
    call_type: str = Field(..., max_length=20)  # 'real_call', 'simulator', 'test'
    direction: str = Field(default='outbound', max_length=10)
    status: str = Field(..., max_length=20)  # 'in_progress', 'completed', 'failed'
    start_time: datetime
    end_time: Optional[datetime] = None
    duration_seconds: Optional[int] = None
    conversation_id: Optional[str] = Field(None, max_length=100)
    outcome: Optional[str] = Field(None, max_length=50)
    extra_data: Dict[str, Any] = Field(default_factory=dict)


class CallCreate(BaseModel):
    call_sid: str
    customer_id: UUID
    call_type: str = 'real_call'
    direction: str = 'outbound'
    status: str = 'in_progress'
    start_time: datetime
    conversation_id: Optional[str] = None
    extra_data: Dict[str, Any] = Field(default_factory=dict)


class CallResponse(CallBase):
    id: UUID
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# Transcript Entry Schemas
class TranscriptEntryBase(BaseModel):
    call_id: UUID
    timestamp: datetime
    entry_type: str = Field(..., max_length=20)  # 'transcript', 'tool', 'event'
    sequence_number: int

    # Transcript fields
    speaker: Optional[str] = Field(None, max_length=20)
    text: Optional[str] = None

    # Tool execution fields
    tool_name: Optional[str] = Field(None, max_length=50)
    tool_request: Optional[Dict[str, Any]] = None
    tool_response: Optional[Dict[str, Any]] = None
    tool_success: Optional[bool] = None
    tool_duration_ms: Optional[int] = None

    # Event fields
    event_type: Optional[str] = Field(None, max_length=50)
    event_data: Optional[Dict[str, Any]] = None


class TranscriptEntryCreate(BaseModel):
    timestamp: datetime
    entry_type: str
    speaker: Optional[str] = None
    text: Optional[str] = None
    tool_name: Optional[str] = None
    tool_request: Optional[Dict[str, Any]] = None
    tool_response: Optional[Dict[str, Any]] = None
    tool_success: Optional[bool] = None
    tool_duration_ms: Optional[int] = None
    event_type: Optional[str] = None
    event_data: Optional[Dict[str, Any]] = None


class TranscriptEntryResponse(TranscriptEntryBase):
    id: UUID
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# API Request/Response Schemas
class InitiateCallRequest(BaseModel):
    customer_phone: Optional[str] = Field(None, description="Customer phone number")
    customer_id: Optional[UUID] = Field(None, description="Customer UUID")


class InitiateCallResponse(BaseModel):
    call_id: UUID
    call_sid: str
    status: str
    message: str
