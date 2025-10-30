# Archer Project Architecture

**Version:** 1.0
**Date:** October 30, 2024
**Status:** Active

---

## Executive Summary

Archer is a rebuilt voice agent system using **Cartesia Line SDK** and **Twilio**, designed to replace the existing ElevenLabs-based implementation. The project uses a **mono-repo architecture** with automated API contract synchronization between backend (Python) and frontend (TypeScript).

### Key Architectural Decisions

1. ✅ **Mono-repo structure** with independent backend/frontend directories
2. ✅ **Automated type generation** from Pydantic models → TypeScript types
3. ✅ **Parallel CI/CD builds** with path-based optimization
4. ✅ **Dual Azure Web Apps** deployment (backend + frontend independence)
5. ✅ **Line SDK managed infrastructure** (vs. self-managed ElevenLabs WebSockets)

---

## System Overview

```
┌─────────────────────────────────────────────────────────┐
│                     Archer System                        │
│                                                          │
│  ┌──────────────────┐         ┌──────────────────┐     │
│  │   Frontend UI    │◀───────▶│  Backend Service │     │
│  │  (React/TS)     │   REST   │  (FastAPI/Line)  │     │
│  │  - Config Mgmt   │   API    │  - Agent Logic   │     │
│  │  - Call Testing  │          │  - Tool Impls    │     │
│  │  - Demo          │          │  - Line SDK      │     │
│  └──────────────────┘         └─────────┬────────┘     │
│                                          │              │
│                        ┌─────────────────┴──────┐       │
│                        │                        │       │
│                  ┌─────▼──────┐         ┌──────▼─────┐ │
│                  │  Cartesia  │         │   Twilio   │ │
│                  │  Line SDK  │         │   Voice    │ │
│                  └────────────┘         └────────────┘ │
└─────────────────────────────────────────────────────────┘
```

---

## Repository Strategy: Mono-repo

### Decision Rationale

After analyzing the existing `ai-banking-voice-agent` implementation and considering Archer's requirements, we selected a **mono-repo architecture**.

#### Why Mono-repo?

| Factor | Benefit |
|--------|---------|
| **API Contract Sync** | Automated TypeScript generation from Pydantic models |
| **Atomic Changes** | Backend API + Frontend types in single PR |
| **Simplified CI/CD** | Single workflow with parallel builds |
| **Development Velocity** | Single clone, unified tooling, shared docs |
| **Code Reuse** | Easy migration from ai-banking-voice-agent |

#### Trade-offs Considered

✅ **Accepted Trade-offs:**
- Shared GitHub issue/PR space (acceptable with good labels)
- Unified git history (benefit for feature tracing)
- Root-level tooling configs (simplified maintenance)

❌ **Rejected Multi-repo Concerns:**
- Separate team autonomy (unnecessary - teams collaborate)
- Independent versioning (achievable via directory tags)
- Access control (not needed - same security boundary)

### Repository Structure

```
archer/
├── .github/
│   └── workflows/
│       └── deploy.yml              # Single workflow, parallel jobs
│
├── backend/                         # Python service (Poetry)
│   ├── pyproject.toml
│   ├── poetry.lock
│   ├── Dockerfile
│   ├── src/
│   │   ├── main.py                # FastAPI app
│   │   ├── agent/                 # Line SDK agent
│   │   │   ├── agent.py          # BankingVoiceAgent class
│   │   │   ├── config.py         # Voice/behavior config
│   │   │   └── prompts.py        # System prompt generation
│   │   ├── tools/                 # Agent tools
│   │   │   ├── verification.py
│   │   │   ├── payment.py
│   │   │   ├── negotiation.py
│   │   │   └── transfer.py
│   │   ├── api/                   # REST API routes
│   │   │   ├── calls.py
│   │   │   ├── config.py
│   │   │   └── admin.py
│   │   ├── models/                # Pydantic models (SOURCE OF TRUTH)
│   │   │   ├── call.py
│   │   │   ├── customer.py
│   │   │   ├── config.py
│   │   │   └── behavioral.py
│   │   ├── services/              # Business logic
│   │   └── clients/               # External clients
│   └── tests/
│
├── frontend/                       # React UI (npm/pnpm)
│   ├── package.json
│   ├── Dockerfile
│   ├── src/
│   │   ├── types/
│   │   │   └── api.ts            # GENERATED from backend/src/models
│   │   ├── components/
│   │   │   ├── config/           # Configuration management
│   │   │   ├── testing/          # Call testing interface
│   │   │   └── demo/             # Demo capabilities
│   │   ├── pages/
│   │   ├── services/
│   │   │   ├── api.ts            # REST API client
│   │   │   └── websocket.ts      # Real-time updates
│   │   └── hooks/
│   └── tests/
│
├── shared/                         # Shared tooling
│   ├── scripts/
│   │   ├── generate-types.py     # Pydantic → TypeScript
│   │   └── dev-setup.sh          # Local dev setup
│   └── docs/                      # Architecture docs
│
├── docs/                          # Project documentation
│   ├── REPOSITORY_STRATEGY.md    # Mono-repo rationale
│   ├── MIGRATION_FROM_ELEVENLABS.md
│   └── API.md
│
├── README.md                      # Main project README
├── docker-compose.yml             # Local development
└── .gitignore
```

---

## API Contract Synchronization

### Problem: Type Drift

Without synchronization, backend and frontend types diverge:
- Backend adds new field → Frontend doesn't know
- Frontend expects field → Backend removed it
- Runtime errors instead of compile-time safety

### Solution: Automated Type Generation

**Source of Truth:** Backend Pydantic models
**Generated Output:** Frontend TypeScript types
**Trigger:** Pre-commit hook + CI validation

#### Implementation

```bash
# shared/scripts/generate-types.py
python -m pydantic_to_typescript \
    --input backend/src/models \
    --output frontend/src/types/api.ts \
    --json2ts-cmd json2ts
```

#### Example: Backend Model

```python
# backend/src/models/customer.py
from pydantic import BaseModel

class CustomerProfile(BaseModel):
    phone_number: str
    name: str
    account_last_4: str
    postal_code: str
    balance: float
    days_overdue: int
    segment: str
    language: str = "en"
```

#### Generated TypeScript

```typescript
// frontend/src/types/api.ts (GENERATED - DO NOT EDIT)
export interface CustomerProfile {
  phone_number: string;
  name: string;
  account_last_4: string;
  postal_code: string;
  balance: number;
  days_overdue: number;
  segment: string;
  language: string;
}
```

#### Workflow

1. Developer updates `backend/src/models/customer.py`
2. Pre-commit hook runs `generate-types.py`
3. `frontend/src/types/api.ts` automatically updated
4. TypeScript compiler catches frontend issues immediately
5. Single PR contains backend change + frontend type update

---

## Technology Stack

### Backend (Archer Service)

| Layer | Technology | Version | Purpose |
|-------|------------|---------|---------|
| **Language** | Python | 3.11+ | Backend logic |
| **Framework** | FastAPI | 0.104+ | REST API |
| **Server** | Uvicorn | 0.24+ | ASGI server |
| **Voice Agent** | Cartesia Line SDK | Latest | Voice AI platform |
| **Telephony** | Twilio Voice API | - | Phone connectivity |
| **LLM** | OpenAI GPT-4 | - | Negotiation guidance |
| **Cache** | Redis | 7.0+ | Session state |
| **Package Mgmt** | Poetry | 1.7+ | Dependency management |
| **Container** | Docker | 24+ | Deployment |

### Frontend (Configuration UI)

| Layer | Technology | Version | Purpose |
|-------|------------|---------|---------|
| **Framework** | React | 18.3+ | UI library |
| **Language** | TypeScript | 5.3+ | Type safety |
| **Build Tool** | Vite | 4.5+ | Fast dev server |
| **Routing** | React Router | 6+ | SPA routing |
| **State** | TanStack Query | 5+ | Server state |
| **Real-time** | Socket.IO Client | 4.8+ | Live updates |
| **Styling** | Tailwind CSS | 4+ | Utility-first CSS |
| **Package Mgmt** | npm/pnpm | - | Dependency management |

#### Theme System

**Default:** Dark mode with deep navy background (#0a0e1a) and cyan accents (#00d9ff)

The frontend implements a complete light/dark theme system:

**Features:**
- **Dark mode default:** Optimized for voice waveform visualization and reduced eye strain
- **Light mode option:** Clean white background for bright environments
- **Theme toggle:** Accessible switch in user menu
- **Persistence:** User preference saved in localStorage
- **System-aware:** Respects OS theme preference on first visit
- **Smooth transitions:** CSS transitions for theme switching

**Color Palette:**
```css
/* Dark Theme (Default) */
--bg-primary: #0a0e1a;        /* Deep navy */
--bg-secondary: #141b2d;      /* Panel backgrounds */
--accent-primary: #00d9ff;    /* Cyan accents */
--text-primary: #e8edf5;      /* Soft white text */

/* Light Theme */
--bg-primary: #ffffff;        /* White */
--bg-secondary: #f5f7fa;      /* Light gray */
--accent-primary: #00d9ff;    /* Same cyan */
--text-primary: #1e2739;      /* Dark gray text */
```

**Implementation:**
- CSS custom properties for theme values
- React context for theme state
- Tailwind dark mode classes
- Prefers-color-scheme media query support

**Rationale:**
- Dark mode reduces eye strain during extended monitoring sessions
- Voice waveforms and glowing accents "pop" better on dark backgrounds
- Modern SaaS standard (Vercel, Linear, etc.) sets user expectations
- Accessibility: Both themes tested for WCAG AA contrast compliance

### Infrastructure

| Service | Technology | Purpose |
|---------|------------|---------|
| **Cloud Platform** | Azure | Hosting |
| **Backend Host** | Azure Web App | Backend service |
| **Frontend Host** | Azure Web App | Static SPA |
| **Container Registry** | Azure ACR | Docker images |
| **CI/CD** | GitHub Actions | Build & deploy |
| **Monitoring** | Azure App Insights | Observability |

---

## Deployment Architecture

### Dual Azure Web App Strategy

```
┌─────────────────────────────────────────────────────┐
│              GitHub Repository                       │
│                 (mono-repo)                         │
└──────────────┬──────────────────┬───────────────────┘
               │                  │
        ┌──────▼──────┐    ┌─────▼──────┐
        │   Backend   │    │  Frontend  │
        │   Build     │    │   Build    │
        │   Job       │    │   Job      │
        └──────┬──────┘    └─────┬──────┘
               │                  │
        ┌──────▼──────┐    ┌─────▼──────┐
        │   Docker    │    │   Docker   │
        │   Image     │    │   Image    │
        └──────┬──────┘    └─────┬──────┘
               │                  │
        ┌──────▼──────────────────▼──────┐
        │     Azure Container Registry    │
        └──────┬──────────────────┬───────┘
               │                  │
        ┌──────▼──────┐    ┌─────▼──────┐
        │   Backend   │    │  Frontend  │
        │   Web App   │    │   Web App  │
        │   :8000     │    │   :80      │
        └─────────────┘    └────────────┘
```

### Deployment Benefits

1. **Independent Scaling:** Backend and frontend scale separately
2. **Isolated Failures:** Frontend outage doesn't affect backend
3. **Parallel Deployments:** Both deploy simultaneously via GitHub Actions
4. **Cost Optimization:** Scale each tier based on load
5. **Security Boundaries:** Separate app service plans if needed

### GitHub Actions Workflow

```yaml
# .github/workflows/deploy.yml
jobs:
  build-backend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: docker/build-push-action@v5
        with:
          context: ./backend
          file: ./backend/Dockerfile
          push: true

  build-frontend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: docker/build-push-action@v5
        with:
          context: ./frontend
          file: ./frontend/Dockerfile
          push: true

  deploy:
    needs: [build-backend, build-frontend]
    runs-on: ubuntu-latest
    steps:
      - name: Deploy backend
        uses: azure/webapps-deploy@v2
      - name: Deploy frontend
        uses: azure/webapps-deploy@v2
```

---

## Path-Based CI Optimization

### Problem: Unnecessary Builds

In a mono-repo, changes to backend shouldn't rebuild frontend and vice versa.

### Solution: Path-Based Triggers

```yaml
# .github/workflows/deploy.yml
build-backend:
  if: |
    contains(github.event.head_commit.modified, 'backend/') ||
    contains(github.event.head_commit.modified, 'shared/')

build-frontend:
  if: |
    contains(github.event.head_commit.modified, 'frontend/') ||
    contains(github.event.head_commit.modified, 'shared/')
```

### Benefits

- ✅ 50% faster CI when only one side changes
- ✅ Reduced ACR storage costs
- ✅ Faster developer feedback
- ✅ Lower Azure build minutes usage

---

## Data Persistence Strategy

### Decision: PostgreSQL + JSONB

**Archer uses PostgreSQL as the single source of truth for all persistence needs**, replacing the Azure Tables + Blob Storage combination used in ai-banking-voice-agent.

### Rationale

| Factor | Azure Tables + Blob (Old) | PostgreSQL + JSONB (New) | Decision |
|--------|-------------------------|------------------------|----------|
| **Data Model** | Split across Tables + Blob | Unified relational + JSONB | PostgreSQL ✅ |
| **Query Power** | Limited NoSQL queries | Full SQL with JOINs | PostgreSQL ✅ |
| **Local Dev** | Azure Emulator required | `docker-compose up` | PostgreSQL ✅ |
| **Data Integrity** | Manual consistency | Foreign keys, transactions | PostgreSQL ✅ |
| **Config Management** | Deployment scripts | Database migrations | PostgreSQL ✅ |
| **Cost** | ~$45/mo | ~$60/mo (+$15) | PostgreSQL ✅ (worth it) |
| **Developer Experience** | Complex, Azure-dependent | Simple, standard tooling | PostgreSQL ✅ |

### Problems with ai-banking-voice-agent Approach

The current system splits persistence across:
- **Azure Tables:** Call history, transcripts, customer data
- **Azure Blob Storage:** Prompts, behavioral configs (JSON files)

**Issues:**
- 🔴 Can't query across Tables + Blob (e.g., "all calls using tactic X")
- 🔴 NoSQL limitations (no JOINs, weak filtering)
- 🔴 Requires deployment scripts to upload configs
- 🔴 Local development needs Azure Storage Emulator
- 🔴 No foreign keys = manual referential integrity
- 🔴 Partition key requirements = inefficient queries
- 🔴 5-minute cache TTL for prompt updates

### PostgreSQL Schema Design

#### Core Relational Tables

```sql
-- Customers
CREATE TABLE customers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    phone_number VARCHAR(20) UNIQUE NOT NULL,
    name VARCHAR(100) NOT NULL,
    account_last_4 VARCHAR(4) NOT NULL,
    postal_code VARCHAR(10) NOT NULL,
    balance DECIMAL(10, 2) NOT NULL,
    days_overdue INTEGER DEFAULT 0,
    segment VARCHAR(20) NOT NULL,
    language VARCHAR(5) DEFAULT 'en',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Organizations (multi-tenant)
CREATE TABLE organizations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) NOT NULL,
    settings JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT NOW()
);

-- Call Records
CREATE TABLE calls (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    call_sid VARCHAR(100) UNIQUE NOT NULL,
    customer_id UUID REFERENCES customers(id) ON DELETE CASCADE,
    organization_id UUID REFERENCES organizations(id),
    call_type VARCHAR(20) NOT NULL,
    direction VARCHAR(10) NOT NULL,
    status VARCHAR(20) NOT NULL,
    start_time TIMESTAMP NOT NULL,
    end_time TIMESTAMP,
    duration_seconds INTEGER,
    behavioral_tactic_id UUID REFERENCES behavioral_tactics(id),
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT NOW()
);

-- Transcript Entries (one-to-many)
CREATE TABLE call_transcript_entries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    call_id UUID REFERENCES calls(id) ON DELETE CASCADE,
    timestamp TIMESTAMP NOT NULL,
    entry_type VARCHAR(20) NOT NULL,  -- 'transcript', 'tool', 'event'
    speaker VARCHAR(20),               -- 'agent', 'customer'
    text TEXT,
    tool_name VARCHAR(50),
    tool_request JSONB,
    tool_response JSONB,
    event_type VARCHAR(50),
    created_at TIMESTAMP DEFAULT NOW()
);

-- Indexes for performance
CREATE INDEX idx_calls_customer_id ON calls(customer_id);
CREATE INDEX idx_calls_start_time ON calls(start_time DESC);
CREATE INDEX idx_transcript_call_id ON call_transcript_entries(call_id);
```

#### Configuration Tables (JSONB for Flexibility)

```sql
-- Behavioral Tactics (replaces JSON files in Blob Storage)
CREATE TABLE behavioral_tactics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(50) UNIQUE NOT NULL,
    archetype VARCHAR(50) NOT NULL,
    config JSONB NOT NULL,  -- Full tactic configuration
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- System Prompts (replaces Blob Storage)
CREATE TABLE system_prompts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(50) UNIQUE NOT NULL,
    environment VARCHAR(20) NOT NULL,
    prompt_template TEXT NOT NULL,
    variables JSONB DEFAULT '{}',
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT NOW()
);
```

**Example Behavioral Tactic Row:**
```json
{
  "name": "aggressive_anchor",
  "archetype": "Aggressive Anchor",
  "config": {
    "urgency_level": 5,
    "empathy_index": 2,
    "persistence_level": 4,
    "tactics": [
      {"name": "High Anchor", "description": "Start with full balance..."}
    ]
  }
}
```

### Redis Usage (Transient Data Only)

**Keep Redis for:**
- ✅ Active call session state (TTL: 10 minutes)
- ✅ Socket.IO coordination (multi-worker)
- ✅ Rate limiting caches
- ❌ **Never for**: Long-term storage, configs, call history

### Local vs Production Setup

#### Local Development
```yaml
# docker-compose.yml
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

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
```

**Developer Experience:**
```bash
docker-compose up  # ← Single command
# PostgreSQL + Redis + Backend + Frontend all running
# No Azure dependencies!
```

#### Production (Azure)
```bash
# Azure Database for PostgreSQL
az postgres flexible-server create \
  --name archer-postgres-prod \
  --sku-name Standard_B2s \
  --tier Burstable

# Connection string
DATABASE_URL=postgresql://user@host:5432/archer?sslmode=require
```

### SQLAlchemy Implementation

```python
# backend/src/models/call.py
from sqlalchemy import Column, String, Integer, TIMESTAMP, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

class Call(Base):
    __tablename__ = 'calls'

    id = Column(UUID(as_uuid=True), primary_key=True)
    call_sid = Column(String(100), unique=True, nullable=False)
    customer_id = Column(UUID(as_uuid=True), ForeignKey('customers.id'))
    status = Column(String(20), nullable=False)
    start_time = Column(TIMESTAMP, nullable=False)
    metadata = Column(JSONB, default={})

    # Relationships
    customer = relationship("Customer", back_populates="calls")
    transcript_entries = relationship("CallTranscriptEntry")
```

**Repository Pattern:**
```python
# backend/src/repositories/call_repository.py
class CallRepository:
    async def get_call_with_transcript(self, call_sid: str) -> Call:
        result = await self.session.execute(
            select(Call)
            .options(selectinload(Call.transcript_entries))
            .where(Call.call_sid == call_sid)
        )
        return result.scalar_one_or_none()
```

### Migration Strategy

**Phase 1:** Set up PostgreSQL (Week 1)
- Create Azure PostgreSQL instance
- Run Alembic migrations
- Verify schema

**Phase 2:** Migrate Behavioral Configs (Week 2)
- Download JSON files from Blob Storage
- Insert into `behavioral_tactics` table
- Test config loading

**Phase 3:** Migrate Call History (Week 3)
- Stream data from Azure Tables
- Insert into PostgreSQL with proper relationships
- Verify data integrity

**Phase 4:** Dual-Write Period (Week 4)
- Write to both systems temporarily
- Verify consistency
- Monitor performance

**Phase 5:** Cut Over (Week 5)
- Switch reads to PostgreSQL
- Stop writing to Azure Tables
- Decommission Azure storage

### Benefits Summary

**Archer's PostgreSQL approach provides:**
- ✅ **Single source of truth** - all data in one place
- ✅ **Proper relational model** - foreign keys, transactions, JOINs
- ✅ **JSONB flexibility** - store configs as JSON but query them
- ✅ **Easy local development** - `docker-compose up`, no Azure
- ✅ **Rich query capabilities** - full SQL power vs NoSQL limitations
- ✅ **Data integrity** - referential integrity enforced
- ✅ **Standard tooling** - SQLAlchemy ORM, Alembic migrations
- ✅ **Version control configs** - migrations vs deployment scripts

**Cost Impact:** +$15/mo ($45 → $60) for significantly better developer experience and maintainability.

See [docs/PERSISTENCE_STRATEGY.md](docs/PERSISTENCE_STRATEGY.md) for detailed schema design and migration guide.

---

## Line SDK Integration Architecture

### Cartesia Line SDK vs ElevenLabs

| Aspect | ElevenLabs (Old) | Cartesia Line SDK (New) |
|--------|------------------|------------------------|
| **Tool Integration** | Webhook registration | Native Python functions |
| **Prompt Management** | Azure Blob Storage | In-code with config files |
| **Agent Configuration** | Separate dev/prod agents | Single codebase + env vars |
| **WebSocket Handling** | Custom implementation | Managed by platform |
| **Audio Processing** | Transcoding required | Native μ-law support |
| **Deployment** | Self-managed infra | Managed platform |
| **First-byte Latency** | 150-200ms | 40-90ms |
| **Infrastructure Code** | ~30 service modules | ~10 modules |

### Line SDK Architecture

```python
# backend/src/agent/agent.py
from line import Agent, Tool, Context

class BankingVoiceAgent(Agent):
    def __init__(self):
        super().__init__(
            name="Archer Banking Agent",
            voice_config=AudioConfig(
                tts_model="sonic-english",
                tts_voice="professional-banking",
                stt_model="ink-whisper"
            )
        )
        self.register_tools()

    def register_tools(self):
        """Register tools as native Python functions."""
        self.add_tool(VerifyAccountTool(self.backend))
        self.add_tool(ProcessPaymentTool(self.backend))
        self.add_tool(NegotiationGuidanceTool(self.backend))
```

### Benefits

1. **67% Reduction** in infrastructure code
2. **100% Elimination** of webhook management
3. **62% Faster** first-byte latency
4. **75% Simpler** tool integration
5. **90% Faster** deployment process

---

## Development Workflow

### Local Development Setup

```bash
# 1. Clone repository
git clone <repo-url>
cd archer

# 2. Start backend
cd backend
poetry install
poetry run uvicorn src.main:app --reload

# 3. Start frontend (separate terminal)
cd frontend
npm install
npm run dev

# 4. Docker Compose (alternative)
docker-compose up
```

### Type Generation Workflow

```bash
# Manual generation
cd shared/scripts
python generate-types.py

# Automatic via pre-commit hook
git add backend/src/models/customer.py
git commit -m "Add customer field"
# → Hook runs generate-types.py automatically
# → frontend/src/types/api.ts updated
```

### Testing Strategy

```bash
# Backend tests (isolated)
cd backend
poetry run pytest

# Frontend tests (isolated)
cd frontend
npm run test

# Integration tests (both)
docker-compose up -d
pytest tests/integration/
```

---

## Security Architecture

### Authentication & Authorization

- **API Key Authentication:** Backend API secured with keys
- **Twilio Signature Validation:** Webhook requests verified
- **Azure AD Integration:** Future SSO for admin UI

### Data Protection

- **TLS 1.3:** All communications encrypted
- **WSS:** Secure WebSocket connections
- **Azure SSE:** Encrypted storage at rest
- **PII Masking:** Logs sanitized of sensitive data

### Compliance

- **TCPA/FDCPA:** Call time restrictions, consent recording
- **GDPR:** Data retention policies
- **PCI DSS:** Payment data handling
- **Audit Logging:** Comprehensive activity tracking

---

## Performance Architecture

### Optimization Strategies

| Layer | Strategy | Target |
|-------|----------|--------|
| **API** | Async FastAPI, connection pooling | <50ms |
| **Voice** | Line SDK managed infrastructure | <100ms |
| **Database** | Redis caching, read replicas | <20ms |
| **Frontend** | Code splitting, lazy loading | <1s load |

### Caching Strategy

```python
# Multi-level caching
L1: In-memory cache (LRU, 1000 items)
L2: Redis (5min TTL)
L3: Database (source of truth)
```

### Monitoring

- **Application Insights:** Request tracing, dependency tracking
- **Custom Metrics:** Call success rate, tool execution time
- **Real-time Dashboard:** Socket.IO events for live monitoring
- **Alerts:** Error rate, latency thresholds

---

## Migration Strategy

### Lessons from ai-banking-voice-agent

**Preserve:**
- ✅ Behavioral tactics system (15 tactics, 4 archetypes)
- ✅ Real-time dashboard with Socket.IO
- ✅ Two-factor verification flow
- ✅ Payment arrangement logic
- ✅ Multi-worker Redis coordination

**Improve:**
- 🔧 Eliminate webhook tool registration → Native functions
- 🔧 Remove Azure Blob prompt management → In-code prompts
- 🔧 Simplify agent configuration → Single codebase
- 🔧 Reduce WebSocket complexity → Line SDK managed

**Reuse:**
- ♻️ FastAPI API structure
- ♻️ React dashboard components
- ♻️ Socket.IO real-time patterns
- ♻️ Docker deployment configs
- ♻️ GitHub Actions workflows

---

## Versioning Strategy

### Independent Component Versioning

```
backend/VERSION     → v1.2.3
frontend/VERSION    → v2.0.1
```

### Git Tagging

```bash
# Backend release
git tag backend-v1.2.3

# Frontend release
git tag frontend-v2.0.1

# Full release (both)
git tag v1.2.3
```

---

## Innovative Features

### Archer Voice-First UI Agent

**Status:** Planning Phase | **Priority:** Demo-Focused Innovation

#### Concept Overview

Archer features an **optional voice-first admin interface** where users interact with an AI assistant (also called "Archer") to navigate, configure, and test the platform. This meta-agent approach demonstrates our voice technology while making the admin interface more intuitive.

#### Key Innovation Points

| Aspect | Traditional Admin | Archer Voice-First |
|--------|------------------|-------------------|
| **Primary Interface** | Mouse + keyboard navigation | Voice conversation with Archer |
| **Feature Discovery** | Browse menus and documentation | Ask "What can you do?" |
| **Test Calls** | Click through 5+ form fields | "Hey Archer, test a call to myself" |
| **Analytics** | Navigate dashboard filters | "Show me today's failed calls" |
| **Troubleshooting** | Read logs manually | "Why did call ABC123 fail?" |

#### Strategic Value

1. **Dogfooding Excellence:** Continuous internal testing of Cartesia Line SDK
2. **Market Differentiation:** No competitor has voice-first admin interface
3. **Demo Impact:** "Our admin panel IS a voice agent" closes deals
4. **Accessibility:** Natural interface for vision-impaired and hands-free scenarios
5. **Customer Confidence:** Shows we believe in our own technology

#### Architecture

```
┌─────────────────────────────────────────────┐
│         Archer Voice-First UI                │
│                                              │
│  ┌────────────────────────────────────────┐ │
│  │    Archer Avatar & Waveform            │ │
│  │    "Hey there! I'm Archer..."          │ │
│  └────────────────────────────────────────┘ │
│                                              │
│  ┌────────────────────────────────────────┐ │
│  │    Overlays (triggered by Archer)      │ │
│  │    • Login                             │ │
│  │    • Test Call                         │ │
│  │    • Analytics                         │ │
│  └────────────────────────────────────────┘ │
│                                              │
│  [Dismiss → Traditional UI]                  │
└─────────────────────────────────────────────┘
```

**Separate Agent Instance:**
```python
# backend/src/archer/agent.py
class ArcherUIAgent(Agent):
    """Meta-agent for admin interface"""
    tools = [
        ShowLoginOverlay(),
        LaunchTestCall(),
        QueryAnalytics(),
        NavigateToPage(),
        ExplainFeature(),
        RunDemoFlow()  # Pre-programmed demos
    ]
```

#### Core Capabilities

- **Auto-greet on page load:** Immediate voice introduction
- **Natural language navigation:** Voice commands replace clicking
- **Pre-programmed demo flows:** 90-second "quick tour" that never fails
- **Context-aware suggestions:** Archer knows what user is doing
- **Text chat fallback:** Full functionality via text input
- **Microphone-safe:** Auto-pauses during test calls (no conflicts)
- **Dismissible:** Users can switch to traditional left nav + top nav UI

#### Demo-Focused Design

**Target Experience (90 seconds):**
1. User lands → Archer greets immediately (0:01)
2. User: "Show me the demo" (0:05)
3. Archer auto-logs in with demo account (0:08)
4. Archer launches pre-configured test call (0:15)
5. Call demonstrates aggressive_anchor tactic (0:20-1:05)
6. Archer shows analytics dashboard (1:10)
7. Archer asks "Anything else?" (1:30)

**Result:** Prospect impressed, remembers demo, tells colleagues → deals close

#### Implementation Timeline

- **Week 1-3:** Core Archer infrastructure (avatar, voice, demo flows)
- **Week 4-6:** Polish (theme integration, error handling, UAT)
- **Week 7-8:** Production deployment with limited release

#### Risk Mitigation

| Risk | Mitigation |
|------|-----------|
| **Voice discoverability** | Quick action buttons, "What can you do?" command |
| **Privacy concerns** | Text chat mode, push-to-talk, easy dismissal |
| **Latency expectations** | Target <400ms, optimistic UI updates |
| **Error handling** | Show transcription, confirm destructive actions |
| **Microphone conflicts** | Auto-pause protocol when test calls start |

#### Success Metrics

- **Adoption:** >40% of users interact with Archer
- **Demo Impact:** +30% conversion rate with Archer demos
- **Latency:** <400ms p95 voice response time
- **Reliability:** 100% demo flow success rate
- **Satisfaction:** >8/10 user NPS

#### Documentation

See [docs/INNOVATION_ARCHER_UI_AGENT.md](docs/INNOVATION_ARCHER_UI_AGENT.md) for comprehensive planning, technical architecture, demo flows, visual design specifications, and implementation details.

---

## Future Considerations

### When to Reconsider Multi-repo

Monitor these signals:
- Backend/frontend teams stop collaborating
- Significantly different release cadences emerge
- Security boundaries require separate repos
- Repo size becomes unwieldy (>10GB)

### Scalability Plans

- **Micro-frontends:** If UI becomes complex
- **Service decomposition:** If backend grows beyond voice agent
- **Polyrepo migration:** If independence becomes critical

---

## References

- [Repository Strategy Details](docs/REPOSITORY_STRATEGY.md)
- [Migration from ElevenLabs](docs/MIGRATION_FROM_ELEVENLABS.md)
- [Archer Voice-First UI Innovation](docs/INNOVATION_ARCHER_UI_AGENT.md)
- [Data Persistence Strategy](docs/PERSISTENCE_STRATEGY.md)
- [Line SDK Design Document](DESIGN-CARTESIA-LINE-SYSTEM.md)
- [API Documentation](docs/API.md)

---

**Last Updated:** October 30, 2024
**Maintained By:** Architecture Team
