# Persistence Strategy: PostgreSQL vs Azure Tables + Blob Storage

**Decision Date:** October 30, 2024
**Status:** Approved
**Decision:** PostgreSQL + JSONB for all persistence

---

## Executive Summary

Archer replaces the ai-banking-voice-agent's split persistence model (Azure Tables + Blob Storage) with a unified **PostgreSQL + JSONB** approach. This provides a single source of truth, proper relational data modeling, rich query capabilities, and significantly improved developer experience with minimal cost increase (+$15/mo).

**Key Benefits:**
- ✅ Single source of truth (unified data model)
- ✅ Proper SQL with JOINs, foreign keys, transactions
- ✅ JSONB for flexible config storage with query capabilities
- ✅ Easy local development (`docker-compose up`, no Azure)
- ✅ Standard tooling (SQLAlchemy ORM, Alembic migrations)

---

## Current System Problems (ai-banking-voice-agent)

### Architecture Overview

```
┌─────────────────────────────────────────────┐
│       Current Persistence Architecture      │
│                                              │
│  ┌──────────────┐         ┌──────────────┐ │
│  │ Azure Tables │         │ Blob Storage │ │
│  ├──────────────┤         ├──────────────┤ │
│  │ CallHistory  │         │  Prompts/    │ │
│  │ Transcripts  │         │  Behavioral  │ │
│  │ Customers    │         │  Configs     │ │
│  │ Organizations│         │  (15 JSON)   │ │
│  └──────────────┘         └──────────────┘ │
│         ▲                        ▲          │
│         └────────────┬───────────┘          │
│                      │                      │
│              ┌───────▼────────┐             │
│              │  Application   │             │
│              │  (FastAPI)     │             │
│              └────────────────┘             │
└─────────────────────────────────────────────┘
```

### Data Split Issues

**Azure Tables stores:**
- `CallHistory` table - call metadata (partitioned by customer_id)
- `CallTranscripts` table - transcripts, tool executions (partitioned by call_sid)
- `CustomerData` table - customer information
- `OrganizationData` table - organization settings

**Azure Blob Storage stores:**
- `prompts/system_prompt.txt` - agent system prompts
- `behavioral-configs/*.json` - 15 behavioral tactic configurations

### Specific Problems

| Problem | Impact | Example |
|---------|--------|---------|
| **Data Split** | Can't query across Tables + Blob | "Show all calls using aggressive_anchor tactic" requires fetching from Blob, then filtering Tables |
| **NoSQL Limitations** | Weak query capabilities | Can't do JOINs; line 302-309 in call_history_service.py shows inefficient query when partition key unknown |
| **Deployment Scripts** | Manual config upload process | `deploy_prompt.py`, `upload_behavioral_configs.py` needed to sync configs |
| **Local Dev Complexity** | Azure Storage Emulator or real Azure | Developers can't work offline; setup is complex |
| **No Relationships** | No foreign keys | Orphaned data possible; referential integrity manual |
| **Partition Key Pain** | Must know partition key for efficiency | Querying without partition key scans entire table |
| **Cache Delay** | 5-minute TTL on prompts | Prompt updates take 5 min to propagate to backend |
| **Cost Complexity** | Two Azure services to manage | Tables + Blob billing, monitoring, configuration |

### Code Example: Current Inefficiency

```python
# From ai-banking-voice-agent/api/services/call_history_service.py:302-309
async def record_call_end(cls, call_sid: str, customer_id: Optional[str] = None):
    # If customer_id not provided, we need to query for the record
    if customer_id is None:
        # Query all partitions for this call_sid (inefficient but necessary)
        filter_query = f"RowKey eq '{call_sid}'"
        entities = list(cls._history_table.query_entities(query_filter=filter_query))
        if not entities:
            logger.warning(f"Could not find call record for {call_sid}")
            return
        customer_id = entities[0]["PartitionKey"]
```

**Issue:** Without the partition key (customer_id), must scan entire table. This doesn't scale.

---

## Proposed Solution: PostgreSQL + JSONB

### Architecture Overview

```
┌─────────────────────────────────────────────┐
│       Proposed PostgreSQL Architecture       │
│                                              │
│  ┌────────────────────────────────────────┐ │
│  │         PostgreSQL Database            │ │
│  ├────────────────────────────────────────┤ │
│  │  Relational Tables:                    │ │
│  │  - customers                           │ │
│  │  - organizations                       │ │
│  │  - calls (FK → customers)              │ │
│  │  - call_transcript_entries (FK→calls)  │ │
│  │                                         │ │
│  │  Config Tables (JSONB):                │ │
│  │  - behavioral_tactics (JSONB config)   │ │
│  │  - system_prompts (TEXT + JSONB vars)  │ │
│  │  - agent_configs (JSONB settings)      │ │
│  └────────────────────────────────────────┘ │
│                      ▲                      │
│              ┌───────┴────────┐             │
│              │  Application   │             │
│              │  (FastAPI +    │             │
│              │  SQLAlchemy)   │             │
│              └────────────────┘             │
└─────────────────────────────────────────────┘
```

### Why PostgreSQL?

| Benefit | Explanation |
|---------|-------------|
| **Single Source of Truth** | All data in one place - no split between Tables and Blob |
| **Proper Relational Model** | Foreign keys, JOIN, transactions - data integrity enforced |
| **JSONB for Flexibility** | Store configs as JSON but with query capabilities (e.g., `WHERE config->>'urgency_level' = '5'`) |
| **Easy Local Dev** | `docker-compose up` → instant local database |
| **Production Ready** | Azure Database for PostgreSQL (managed, HA, backups) |
| **Mature Tooling** | SQLAlchemy ORM, Alembic migrations, pgAdmin, great ecosystem |
| **Cost Effective** | $30-50/mo for small instance vs Tables + Blob combo (~$15) |
| **Full SQL Power** | Complex queries, analytics, reporting all possible |
| **Version Control** | Database migrations in git vs deployment scripts |

---

## Complete Schema Design

### Core Relational Tables

```sql
-- Customers (primary entity)
CREATE TABLE customers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    phone_number VARCHAR(20) UNIQUE NOT NULL,
    name VARCHAR(100) NOT NULL,
    account_last_4 VARCHAR(4) NOT NULL,
    postal_code VARCHAR(10) NOT NULL,
    balance DECIMAL(10, 2) NOT NULL,
    days_overdue INTEGER DEFAULT 0,
    segment VARCHAR(20) NOT NULL,  -- 'premium', 'standard'
    language VARCHAR(5) DEFAULT 'en',  -- 'en', 'fr'
    metadata JSONB DEFAULT '{}',  -- Flexible additional data
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Organizations (multi-tenant support)
CREATE TABLE organizations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) NOT NULL,
    domain VARCHAR(100),
    settings JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Organization memberships (many-to-many)
CREATE TABLE organization_members (
    organization_id UUID REFERENCES organizations(id) ON DELETE CASCADE,
    customer_id UUID REFERENCES customers(id) ON DELETE CASCADE,
    role VARCHAR(50) DEFAULT 'member',
    PRIMARY KEY (organization_id, customer_id)
);

-- Call Records (main call entity)
CREATE TABLE calls (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    call_sid VARCHAR(100) UNIQUE NOT NULL,
    customer_id UUID REFERENCES customers(id) ON DELETE CASCADE,
    organization_id UUID REFERENCES organizations(id) ON DELETE SET NULL,
    call_type VARCHAR(20) NOT NULL,  -- 'real_call', 'simulator', 'test'
    direction VARCHAR(10) NOT NULL,  -- 'inbound', 'outbound'
    status VARCHAR(20) NOT NULL,  -- 'in_progress', 'completed', 'failed', 'no_answer'
    start_time TIMESTAMP NOT NULL,
    end_time TIMESTAMP,
    duration_seconds INTEGER,
    conversation_id VARCHAR(100),  -- ElevenLabs/Line SDK conversation ID
    behavioral_tactic_id UUID REFERENCES behavioral_tactics(id) ON DELETE SET NULL,
    outcome VARCHAR(50),  -- 'payment_arranged', 'callback_scheduled', 'transfer', etc.
    metadata JSONB DEFAULT '{}',  -- Additional call-specific data
    created_at TIMESTAMP DEFAULT NOW()
);

-- Call Transcript Entries (one-to-many with calls)
CREATE TABLE call_transcript_entries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    call_id UUID REFERENCES calls(id) ON DELETE CASCADE,
    timestamp TIMESTAMP NOT NULL,
    entry_type VARCHAR(20) NOT NULL,  -- 'transcript', 'tool', 'event'
    sequence_number INTEGER NOT NULL,  -- For deterministic ordering

    -- Transcript fields (when entry_type = 'transcript')
    speaker VARCHAR(20),  -- 'agent', 'customer'
    text TEXT,

    -- Tool execution fields (when entry_type = 'tool')
    tool_name VARCHAR(50),
    tool_request JSONB,
    tool_response JSONB,
    tool_success BOOLEAN,
    tool_duration_ms INTEGER,

    -- Event fields (when entry_type = 'event')
    event_type VARCHAR(50),  -- 'call_connected', 'call_ended', 'error', etc.
    event_data JSONB,

    created_at TIMESTAMP DEFAULT NOW()
);

-- Performance indexes
CREATE INDEX idx_customers_phone ON customers(phone_number);
CREATE INDEX idx_calls_customer_id ON calls(customer_id);
CREATE INDEX idx_calls_start_time ON calls(start_time DESC);
CREATE INDEX idx_calls_status ON calls(status);
CREATE INDEX idx_calls_outcome ON calls(outcome);
CREATE INDEX idx_transcript_call_id ON call_transcript_entries(call_id);
CREATE INDEX idx_transcript_timestamp ON call_transcript_entries(timestamp);
CREATE INDEX idx_transcript_sequence ON call_transcript_entries(call_id, sequence_number);

-- Composite indexes for common queries
CREATE INDEX idx_calls_customer_status ON calls(customer_id, status);
CREATE INDEX idx_calls_org_status ON calls(organization_id, status) WHERE organization_id IS NOT NULL;
```

### Configuration Tables (JSONB)

```sql
-- Behavioral Tactics (replaces JSON files in Blob Storage)
CREATE TABLE behavioral_tactics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(50) UNIQUE NOT NULL,  -- 'aggressive_anchor', 'empathetic_gradual', etc.
    archetype VARCHAR(50) NOT NULL,  -- 'Aggressive Anchor', 'Empathetic Gradual', etc.
    description TEXT,
    config JSONB NOT NULL,  -- Full tactic configuration as JSON
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Example row:
INSERT INTO behavioral_tactics (name, archetype, config) VALUES (
    'aggressive_anchor',
    'Aggressive Anchor',
    '{
        "urgency_level": 5,
        "empathy_index": 2,
        "persistence_level": 4,
        "authority_level": 5,
        "opening_strategy": "direct_assertive",
        "tactics": [
            {
                "name": "High Anchor",
                "description": "Start with full balance to establish ceiling",
                "timing": "early"
            },
            {
                "name": "Deadline Pressure",
                "description": "Emphasize time-sensitive consequences",
                "timing": "mid"
            }
        ]
    }'::jsonb
);

-- JSONB query examples:
-- Get all tactics with urgency_level > 3
SELECT name, config->>'urgency_level' as urgency
FROM behavioral_tactics
WHERE (config->>'urgency_level')::int > 3;

-- Get tactics containing specific tactic name
SELECT name, archetype
FROM behavioral_tactics
WHERE config @> '{"tactics": [{"name": "High Anchor"}]}';


-- System Prompts (replaces Blob Storage)
CREATE TABLE system_prompts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(50) UNIQUE NOT NULL,  -- 'default', 'premium_customer', 'overdue_30_days', etc.
    environment VARCHAR(20) NOT NULL,  -- 'development', 'staging', 'production'
    prompt_template TEXT NOT NULL,  -- Template with {{variables}}
    variables JSONB DEFAULT '{}',  -- Default variable values
    version INTEGER DEFAULT 1,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Prompt versioning (keep history)
CREATE INDEX idx_prompts_name_version ON system_prompts(name, version DESC);
CREATE INDEX idx_prompts_active ON system_prompts(is_active) WHERE is_active = true;

-- Example row:
INSERT INTO system_prompts (name, environment, prompt_template, variables) VALUES (
    'default',
    'production',
    'You are Alex from TD Bank calling about account management.

Current Context:
- Customer: {{customer_name}}
- Balance: ${{balance}}
- Days Overdue: {{days_overdue}}

Instructions:
1. Verify identity before discussing account
2. Use tools for all operations
3. Follow compliance requirements',
    '{"customer_name": "Unknown", "balance": "0.00", "days_overdue": 0}'::jsonb
);


-- Agent Configurations (voice, behavior, tools)
CREATE TABLE agent_configs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID REFERENCES organizations(id) ON DELETE CASCADE,
    name VARCHAR(100) NOT NULL,
    voice_config JSONB NOT NULL,  -- Voice model, speed, emotion, etc.
    behavior_config JSONB NOT NULL,  -- Urgency, empathy, persistence levels
    tool_config JSONB NOT NULL,  -- Which tools are enabled, tool-specific settings
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Example row:
INSERT INTO agent_configs (name, voice_config, behavior_config, tool_config) VALUES (
    'default_banking_agent',
    '{
        "tts_model": "sonic-english",
        "tts_voice": "professional-banking-male",
        "tts_speed": 1.0,
        "stt_model": "ink-whisper"
    }'::jsonb,
    '{
        "default_tactic": "balanced_progression",
        "max_call_duration": 600,
        "allow_interruptions": true
    }'::jsonb,
    '{
        "enabled_tools": ["verify_account", "get_customer_options", "process_payment"],
        "verification": {"max_attempts": 2},
        "payment": {"allow_sms_link": true}
    }'::jsonb
);
```

---

## SQLAlchemy Implementation

### Models

```python
# backend/src/models/base.py
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

Base = declarative_base()

# Async engine
engine = create_async_engine(
    DATABASE_URL,
    echo=True,  # Log SQL queries in development
    future=True
)

# Async session factory
async_session = sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)

async def get_session() -> AsyncSession:
    """Dependency for FastAPI route handlers."""
    async with async_session() as session:
        yield session
```

```python
# backend/src/models/customer.py
from sqlalchemy import Column, String, Integer, DECIMAL, TIMESTAMP
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from .base import Base

class Customer(Base):
    __tablename__ = 'customers'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    phone_number = Column(String(20), unique=True, nullable=False, index=True)
    name = Column(String(100), nullable=False)
    account_last_4 = Column(String(4), nullable=False)
    postal_code = Column(String(10), nullable=False)
    balance = Column(DECIMAL(10, 2), nullable=False)
    days_overdue = Column(Integer, default=0)
    segment = Column(String(20), nullable=False)
    language = Column(String(5), default='en')
    metadata = Column(JSONB, default={})
    created_at = Column(TIMESTAMP, default=datetime.utcnow)
    updated_at = Column(TIMESTAMP, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    calls = relationship("Call", back_populates="customer", cascade="all, delete-orphan")
```

```python
# backend/src/models/call.py
from sqlalchemy import Column, String, Integer, TIMESTAMP, ForeignKey, Boolean
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from .base import Base

class Call(Base):
    __tablename__ = 'calls'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    call_sid = Column(String(100), unique=True, nullable=False, index=True)
    customer_id = Column(UUID(as_uuid=True), ForeignKey('customers.id', ondelete='CASCADE'), nullable=False)
    organization_id = Column(UUID(as_uuid=True), ForeignKey('organizations.id', ondelete='SET NULL'))
    call_type = Column(String(20), nullable=False)
    direction = Column(String(10), nullable=False)
    status = Column(String(20), nullable=False, index=True)
    start_time = Column(TIMESTAMP, nullable=False, index=True)
    end_time = Column(TIMESTAMP)
    duration_seconds = Column(Integer)
    conversation_id = Column(String(100))
    behavioral_tactic_id = Column(UUID(as_uuid=True), ForeignKey('behavioral_tactics.id', ondelete='SET NULL'))
    outcome = Column(String(50))
    metadata = Column(JSONB, default={})
    created_at = Column(TIMESTAMP, default=datetime.utcnow)

    # Relationships
    customer = relationship("Customer", back_populates="calls")
    transcript_entries = relationship("CallTranscriptEntry", back_populates="call", cascade="all, delete-orphan", order_by="CallTranscriptEntry.sequence_number")
    behavioral_tactic = relationship("BehavioralTactic")

class CallTranscriptEntry(Base):
    __tablename__ = 'call_transcript_entries'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    call_id = Column(UUID(as_uuid=True), ForeignKey('calls.id', ondelete='CASCADE'), nullable=False, index=True)
    timestamp = Column(TIMESTAMP, nullable=False, index=True)
    entry_type = Column(String(20), nullable=False)
    sequence_number = Column(Integer, nullable=False)

    # Transcript fields
    speaker = Column(String(20))
    text = Column(String)

    # Tool execution fields
    tool_name = Column(String(50))
    tool_request = Column(JSONB)
    tool_response = Column(JSONB)
    tool_success = Column(Boolean)
    tool_duration_ms = Column(Integer)

    # Event fields
    event_type = Column(String(50))
    event_data = Column(JSONB)

    created_at = Column(TIMESTAMP, default=datetime.utcnow)

    # Relationships
    call = relationship("Call", back_populates="transcript_entries")
```

```python
# backend/src/models/behavioral_tactic.py
from sqlalchemy import Column, String, Boolean, Integer, TIMESTAMP
from sqlalchemy.dialects.postgresql import UUID, JSONB
from datetime import datetime
import uuid

from .base import Base

class BehavioralTactic(Base):
    __tablename__ = 'behavioral_tactics'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(50), unique=True, nullable=False)
    archetype = Column(String(50), nullable=False)
    description = Column(String)
    config = Column(JSONB, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(TIMESTAMP, default=datetime.utcnow)
    updated_at = Column(TIMESTAMP, default=datetime.utcnow, onupdate=datetime.utcnow)
```

### Repository Pattern

```python
# backend/src/repositories/call_repository.py
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, func
from sqlalchemy.orm import selectinload
from datetime import datetime

from ..models.call import Call, CallTranscriptEntry

class CallRepository:
    """Repository for call data access."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_call(self, call_data: dict) -> Call:
        """Create a new call record."""
        call = Call(**call_data)
        self.session.add(call)
        await self.session.commit()
        await self.session.refresh(call)
        return call

    async def get_call_by_sid(self, call_sid: str) -> Optional[Call]:
        """Get call by Twilio call SID."""
        result = await self.session.execute(
            select(Call).where(Call.call_sid == call_sid)
        )
        return result.scalar_one_or_none()

    async def get_call_with_transcript(self, call_sid: str) -> Optional[Call]:
        """Get call with all transcript entries eagerly loaded."""
        result = await self.session.execute(
            select(Call)
            .options(
                selectinload(Call.transcript_entries),
                selectinload(Call.customer),
                selectinload(Call.behavioral_tactic)
            )
            .where(Call.call_sid == call_sid)
        )
        return result.scalar_one_or_none()

    async def get_customer_calls(
        self,
        customer_id: str,
        status: Optional[str] = None,
        limit: int = 50
    ) -> List[Call]:
        """Get all calls for a customer, ordered by most recent."""
        query = (
            select(Call)
            .where(Call.customer_id == customer_id)
            .order_by(desc(Call.start_time))
            .limit(limit)
        )

        if status:
            query = query.where(Call.status == status)

        result = await self.session.execute(query)
        return result.scalars().all()

    async def add_transcript_entry(
        self,
        call_id: str,
        entry_data: dict
    ) -> CallTranscriptEntry:
        """Add a transcript entry to a call."""
        # Get next sequence number
        result = await self.session.execute(
            select(func.max(CallTranscriptEntry.sequence_number))
            .where(CallTranscriptEntry.call_id == call_id)
        )
        max_seq = result.scalar() or 0

        entry = CallTranscriptEntry(
            call_id=call_id,
            sequence_number=max_seq + 1,
            **entry_data
        )
        self.session.add(entry)
        await self.session.commit()
        return entry

    async def update_call_end(
        self,
        call_sid: str,
        end_time: datetime,
        duration: int,
        outcome: Optional[str] = None
    ) -> Call:
        """Update call with end time, duration, and outcome."""
        call = await self.get_call_by_sid(call_sid)
        if call:
            call.end_time = end_time
            call.duration_seconds = duration
            call.status = "completed"
            if outcome:
                call.outcome = outcome
            await self.session.commit()
            await self.session.refresh(call)
        return call

    async def get_calls_by_tactic(
        self,
        tactic_id: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[Call]:
        """Get all calls using a specific behavioral tactic."""
        query = select(Call).where(Call.behavioral_tactic_id == tactic_id)

        if start_date:
            query = query.where(Call.start_time >= start_date)
        if end_date:
            query = query.where(Call.start_time <= end_date)

        result = await self.session.execute(query)
        return result.scalars().all()
```

```python
# backend/src/repositories/behavioral_repository.py
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from ..models.behavioral_tactic import BehavioralTactic

class BehavioralRepository:
    """Repository for behavioral tactics."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_tactic_by_name(self, name: str) -> Optional[BehavioralTactic]:
        """Get tactic by name (e.g., 'aggressive_anchor')."""
        result = await self.session.execute(
            select(BehavioralTactic).where(BehavioralTactic.name == name)
        )
        return result.scalar_one_or_none()

    async def get_all_tactics(self, active_only: bool = True) -> List[BehavioralTactic]:
        """Get all behavioral tactics."""
        query = select(BehavioralTactic)
        if active_only:
            query = query.where(BehavioralTactic.is_active == True)

        result = await self.session.execute(query)
        return result.scalars().all()

    async def upsert_tactic(self, tactic_data: dict) -> BehavioralTactic:
        """Create or update a behavioral tactic."""
        existing = await self.get_tactic_by_name(tactic_data['name'])

        if existing:
            # Update existing
            for key, value in tactic_data.items():
                setattr(existing, key, value)
            await self.session.commit()
            await self.session.refresh(existing)
            return existing
        else:
            # Create new
            tactic = BehavioralTactic(**tactic_data)
            self.session.add(tactic)
            await self.session.commit()
            await self.session.refresh(tactic)
            return tactic

    async def query_tactics_by_urgency(self, min_urgency: int) -> List[BehavioralTactic]:
        """Query tactics by urgency level using JSONB."""
        from sqlalchemy import cast, Integer

        result = await self.session.execute(
            select(BehavioralTactic)
            .where(
                cast(BehavioralTactic.config['urgency_level'].astext, Integer) >= min_urgency
            )
        )
        return result.scalars().all()
```

### FastAPI Integration

```python
# backend/src/api/routes/calls.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from ...models.base import get_session
from ...repositories.call_repository import CallRepository
from ...schemas.call import CallCreate, CallResponse

router = APIRouter(prefix="/api/v1/calls", tags=["calls"])

@router.post("/", response_model=CallResponse)
async def create_call(
    call_data: CallCreate,
    session: AsyncSession = Depends(get_session)
):
    """Create a new call record."""
    repo = CallRepository(session)
    call = await repo.create_call(call_data.dict())
    return call

@router.get("/{call_sid}", response_model=CallResponse)
async def get_call(
    call_sid: str,
    session: AsyncSession = Depends(get_session)
):
    """Get call details with transcript."""
    repo = CallRepository(session)
    call = await repo.get_call_with_transcript(call_sid)
    if not call:
        raise HTTPException(status_code=404, detail="Call not found")
    return call

@router.get("/customer/{customer_id}")
async def get_customer_calls(
    customer_id: str,
    status: Optional[str] = None,
    limit: int = 50,
    session: AsyncSession = Depends(get_session)
):
    """Get all calls for a customer."""
    repo = CallRepository(session)
    calls = await repo.get_customer_calls(customer_id, status, limit)
    return calls
```

---

## Local vs Production Setup

### Local Development (Docker Compose)

```yaml
# docker-compose.yml
version: '3.8'

services:
  postgres:
    image: postgres:15-alpine
    environment:
      POSTGRES_DB: archer_dev
      POSTGRES_USER: archer
      POSTGRES_PASSWORD: archer_dev_pass
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./backend/migrations/init.sql:/docker-entrypoint-initdb.d/init.sql
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U archer"]
      interval: 10s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5

  backend:
    build: ./backend
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    environment:
      DATABASE_URL: postgresql+asyncpg://archer:archer_dev_pass@postgres:5432/archer_dev
      REDIS_URL: redis://redis:6379
      LINE_API_KEY: ${LINE_API_KEY}
      TWILIO_ACCOUNT_SID: ${TWILIO_ACCOUNT_SID}
      TWILIO_AUTH_TOKEN: ${TWILIO_AUTH_TOKEN}
    ports:
      - "8000:8000"
    volumes:
      - ./backend:/app
    command: uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload

  frontend:
    build: ./frontend
    depends_on:
      - backend
    environment:
      VITE_API_URL: http://localhost:8000
      VITE_WS_URL: ws://localhost:8000
    ports:
      - "3000:3000"
    volumes:
      - ./frontend:/app
      - /app/node_modules
    command: npm run dev -- --host 0.0.0.0

volumes:
  postgres_data:
  redis_data:
```

**Developer Experience:**
```bash
# Start everything
docker-compose up

# Backend: http://localhost:8000
# Frontend: http://localhost:3000
# PostgreSQL: localhost:5432
# Redis: localhost:6379
# API Docs: http://localhost:8000/docs

# Run migrations
docker-compose exec backend alembic upgrade head

# Seed data
docker-compose exec backend python scripts/seed_data.py

# No Azure dependencies for local development!
```

### Production (Azure)

```bash
# 1. Create Azure Database for PostgreSQL
az postgres flexible-server create \
  --name archer-postgres-prod \
  --resource-group archer-rg \
  --location eastus \
  --admin-user archer_admin \
  --admin-password <secure-password> \
  --sku-name Standard_B2s \
  --tier Burstable \
  --storage-size 32 \
  --version 15

# 2. Configure firewall for Azure services
az postgres flexible-server firewall-rule create \
  --name archer-postgres-prod \
  --resource-group archer-rg \
  --rule-name allow-azure-services \
  --start-ip-address 0.0.0.0 \
  --end-ip-address 0.0.0.0

# 3. Connection string
postgresql://archer_admin@archer-postgres-prod:<password>@archer-postgres-prod.postgres.database.azure.com:5432/archer?sslmode=require

# 4. Run migrations
DATABASE_URL=<connection-string> alembic upgrade head

# 5. Deploy backend and frontend (same as current)
```

---

## Migration Strategy from Azure Tables + Blob

### Phase 1: Set Up PostgreSQL (Week 1)

**Objectives:**
- Create Azure PostgreSQL instance
- Set up database schema
- Verify connectivity

**Tasks:**
```bash
# 1. Create Azure PostgreSQL
az postgres flexible-server create...

# 2. Configure environment
export DATABASE_URL="postgresql://..."

# 3. Run Alembic migrations
cd backend
poetry run alembic upgrade head

# 4. Verify tables created
psql $DATABASE_URL -c "\dt"

# Expected output:
# - customers
# - organizations
# - calls
# - call_transcript_entries
# - behavioral_tactics
# - system_prompts
# - agent_configs
```

**Deliverables:**
- ✅ Azure PostgreSQL instance provisioned
- ✅ Schema created via migrations
- ✅ Connection from backend verified

---

### Phase 2: Migrate Behavioral Configs (Week 2)

**Objectives:**
- Download JSON files from Azure Blob Storage
- Insert into `behavioral_tactics` table
- Test config loading from PostgreSQL

**Migration Script:**
```python
# backend/scripts/migrate_behavioral_configs.py
import asyncio
import json
from pathlib import Path
from azure.storage.blob import BlobServiceClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.base import async_session
from src.repositories.behavioral_repository import BehavioralRepository

async def migrate_behavioral_configs():
    """Migrate behavioral configs from Azure Blob → PostgreSQL."""

    # 1. Download from Azure Blob Storage
    print("Downloading configs from Azure Blob...")
    blob_client = BlobServiceClient.from_connection_string(AZURE_CONN_STR)
    container = blob_client.get_container_client("behavioral-configs")

    configs = []
    for blob in container.list_blobs():
        blob_data = container.download_blob(blob.name).readall()
        config = json.loads(blob_data)

        # Extract name from filename
        name = Path(blob.name).stem

        configs.append({
            "name": name,
            "archetype": config.get("archetype", name.replace("_", " ").title()),
            "description": config.get("description"),
            "config": config
        })

    print(f"Downloaded {len(configs)} configs")

    # 2. Insert into PostgreSQL
    print("Inserting into PostgreSQL...")
    async with async_session() as session:
        repo = BehavioralRepository(session)

        for config in configs:
            tactic = await repo.upsert_tactic(config)
            print(f"  ✅ Migrated: {tactic.name}")

    print(f"✅ Migration complete: {len(configs)} configs migrated")

if __name__ == "__main__":
    asyncio.run(migrate_behavioral_configs())
```

**Validation:**
```sql
-- Verify configs loaded
SELECT name, archetype, config->>'urgency_level' as urgency
FROM behavioral_tactics
ORDER BY name;

-- Expected: 15 tactics
-- aggressive_anchor, empathetic_gradual, balanced_progression, stern, etc.
```

---

### Phase 3: Migrate Call History (Week 3)

**Objectives:**
- Stream call records from Azure Tables
- Insert into PostgreSQL with proper relationships
- Verify data integrity

**Migration Script:**
```python
# backend/scripts/migrate_call_history.py
import asyncio
from azure.data.tables import TableServiceClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.base import async_session
from src.repositories.call_repository import CallRepository

async def migrate_call_history():
    """Migrate call history from Azure Tables → PostgreSQL."""

    # 1. Connect to Azure Tables
    print("Connecting to Azure Tables...")
    table_client = TableServiceClient.from_connection_string(AZURE_CONN_STR)
    history_table = table_client.get_table_client("CallHistory")
    transcript_table = table_client.get_table_client("CallTranscripts")

    # 2. Stream call records
    print("Streaming call records...")
    migrated_count = 0

    async with async_session() as session:
        call_repo = CallRepository(session)

        # Stream entities to avoid loading all into memory
        for entity in history_table.list_entities():
            # Create call record
            call = await call_repo.create_call({
                "call_sid": entity["RowKey"],
                "customer_id": entity["PartitionKey"],  # Assuming partition key is customer_id
                "call_type": entity.get("call_type", "real_call"),
                "direction": "outbound",  # Default
                "status": entity.get("status", "completed"),
                "start_time": entity.get("start_time"),
                "end_time": entity.get("end_time"),
                "duration_seconds": entity.get("duration_seconds", 0),
                "conversation_id": entity.get("conversation_id")
            })

            # Migrate transcripts for this call
            transcript_filter = f"PartitionKey eq '{call.call_sid}'"
            sequence = 1

            for trans in transcript_table.query_entities(transcript_filter):
                await call_repo.add_transcript_entry(call.id, {
                    "timestamp": trans.get("timestamp"),
                    "entry_type": trans.get("entry_type", "transcript"),
                    "speaker": trans.get("speaker"),
                    "text": trans.get("text"),
                    "tool_name": trans.get("tool_name"),
                    "tool_request": json.loads(trans.get("tool_request", "{}")),
                    "tool_response": json.loads(trans.get("tool_response", "{}")),
                    "tool_success": trans.get("success") == "True",
                    "event_type": trans.get("event_type")
                })
                sequence += 1

            migrated_count += 1
            if migrated_count % 100 == 0:
                print(f"  Migrated {migrated_count} calls...")

    print(f"✅ Migration complete: {migrated_count} calls migrated")

if __name__ == "__main__":
    asyncio.run(migrate_call_history())
```

**Validation:**
```sql
-- Count calls
SELECT COUNT(*) FROM calls;

-- Count transcript entries
SELECT COUNT(*) FROM call_transcript_entries;

-- Verify data integrity
SELECT
    c.call_sid,
    c.status,
    COUNT(t.id) as transcript_count
FROM calls c
LEFT JOIN call_transcript_entries t ON t.call_id = c.id
GROUP BY c.id, c.call_sid, c.status
LIMIT 10;
```

---

### Phase 4: Dual-Write Period (Week 4)

**Objectives:**
- Write to both Azure Tables and PostgreSQL
- Verify data consistency
- Monitor performance

**Dual-Write Repository:**
```python
# backend/src/repositories/dual_write_call_repository.py
class DualWriteCallRepository:
    """Write to both Azure Tables and PostgreSQL during migration."""

    def __init__(self, postgres_repo: CallRepository, azure_service):
        self.postgres = postgres_repo
        self.azure = azure_service

    async def create_call(self, call_data: dict) -> Call:
        """Write to PostgreSQL (primary), Azure Tables (backup)."""
        # Write to PostgreSQL (synchronous, primary)
        call = await self.postgres.create_call(call_data)

        # Write to Azure Tables (fire-and-forget, for safety)
        asyncio.create_task(self._write_to_azure(call_data))

        return call

    async def _write_to_azure(self, call_data: dict):
        """Background write to Azure Tables."""
        try:
            await self.azure.record_call_start(**call_data)
        except Exception as e:
            logger.warning(f"Dual-write to Azure failed: {e}")
            # Don't raise - PostgreSQL is source of truth
```

**Monitoring:**
```python
# Compare data between systems
async def verify_consistency():
    """Verify data consistency between PostgreSQL and Azure Tables."""
    # Sample recent calls from both systems
    # Compare counts, timestamps, data
    # Report discrepancies
```

---

### Phase 5: Cut Over (Week 5)

**Objectives:**
- Switch reads to PostgreSQL
- Stop writing to Azure Tables
- Decommission Azure storage

**Tasks:**
1. **Week 5 Day 1-2:** Switch all reads to PostgreSQL
   ```python
   # Remove Azure Table reads, use PostgreSQL only
   call_repo = CallRepository(session)  # PostgreSQL only
   ```

2. **Week 5 Day 3-4:** Monitor for issues, verify performance

3. **Week 5 Day 5:** Stop dual-writes
   ```python
   # Use PostgreSQL repository directly
   # Remove DualWriteCallRepository wrapper
   ```

4. **Week 5+ (grace period):** Keep Azure Tables for 30 days as backup, then delete

---

## Cost Analysis

### Current (ai-banking-voice-agent)

| Service | Monthly Cost | Notes |
|---------|-------------|-------|
| Azure Tables | ~$10 | Per GB stored + transaction costs |
| Azure Blob Storage | ~$5 | For configs and prompts |
| Azure Cache for Redis | ~$30 | Standard tier |
| **Total** | **~$45** | |

### Proposed (Archer)

| Service | Monthly Cost | Notes |
|---------|-------------|-------|
| Azure PostgreSQL (Standard_B2s) | ~$30-35 | 2 vCPU, 4 GB RAM, 32 GB storage |
| Azure Cache for Redis | ~$30 | Same as current |
| **Total** | **~$60-65** | |

**Cost Impact:** +$15-20/mo (33% increase)

**Justification:**
- Significantly better developer experience
- Unified data model (easier to maintain)
- Proper SQL capabilities (complex queries possible)
- No deployment scripts for configs
- Local development without Azure dependencies
- **ROI:** Developer time savings far exceed $15/mo

---

## Benefits Summary

### Developer Experience

| Aspect | Before (Azure Tables + Blob) | After (PostgreSQL) | Improvement |
|--------|----------------------------|-------------------|-------------|
| **Local Setup** | Azure Storage Emulator or real Azure | `docker-compose up` | ✅ 10x simpler |
| **Query Data** | Limited NoSQL, split sources | Full SQL with JOINs | ✅ Unlimited |
| **Config Changes** | Upload scripts to Blob | Database migrations | ✅ Version controlled |
| **Testing** | Mock Azure clients | In-memory SQLite | ✅ Faster, easier |
| **Debugging** | Azure Portal + logs | pgAdmin + SQL queries | ✅ Standard tooling |

### Data Integrity

| Aspect | Before | After | Benefit |
|--------|--------|-------|---------|
| **Relationships** | Manual consistency | Foreign keys enforced | ✅ Automatic |
| **Transactions** | Not available | ACID guarantees | ✅ Data safety |
| **Orphaned Data** | Possible | Prevented by CASCADE | ✅ Clean |
| **Query Errors** | Runtime | Compile-time (SQLAlchemy) | ✅ Caught early |

### Query Capabilities

```sql
-- Example: Complex query impossible in Azure Tables
SELECT
    bt.name as tactic,
    COUNT(c.id) as call_count,
    AVG(c.duration_seconds) as avg_duration,
    SUM(CASE WHEN c.outcome = 'payment_arranged' THEN 1 ELSE 0 END) as successes
FROM calls c
JOIN behavioral_tactics bt ON c.behavioral_tactic_id = bt.id
WHERE c.start_time >= NOW() - INTERVAL '30 days'
GROUP BY bt.id, bt.name
ORDER BY successes DESC;

-- Impossible in Azure Tables (no JOIN, limited aggregation)
```

---

## Decision Summary

**Approved:** PostgreSQL + JSONB for all persistence in Archer

**Rationale:**
1. ✅ Unified data model (single source of truth)
2. ✅ Proper relational design with foreign keys
3. ✅ Rich query capabilities (full SQL)
4. ✅ Easy local development (docker-compose)
5. ✅ Standard tooling (SQLAlchemy, Alembic)
6. ✅ Version-controlled configs (migrations)
7. ✅ JSONB flexibility for configs

**Trade-off:**
- ⚠️ +$15/mo cost increase (justified by DX improvements)

**Migration:**
- 5-week phased approach
- Parallel running period for safety
- Rollback plan available

**Next Steps:**
1. Provision Azure PostgreSQL instance
2. Set up Alembic migrations
3. Begin Phase 1 of migration plan

---

**Decision Approved:** October 30, 2024
**Review Date:** Q2 2025 (after production deployment)
