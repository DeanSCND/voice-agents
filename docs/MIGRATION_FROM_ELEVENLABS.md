# Migration from ElevenLabs to Cartesia Line SDK

**Document Version:** 1.0
**Date:** October 30, 2024
**Status:** Planning Phase

---

## Executive Summary

This document captures lessons learned from the `ai-banking-voice-agent` (ElevenLabs) implementation and provides guidance for migrating to Archer (Cartesia Line SDK). The migration offers significant architectural simplification while preserving all critical business features.

### Migration Value Proposition

| Metric | ElevenLabs (Current) | Archer (Cartesia) | Improvement |
|--------|---------------------|-------------------|-------------|
| **First-byte Latency** | 150-200ms | 40-90ms | 62% faster |
| **Infrastructure Code** | ~30 service modules | ~10 modules | 67% reduction |
| **Tool Integration** | Webhook registration | Native Python functions | 75% simpler |
| **Deployment Time** | 15-20 min manual | <5 min automated | 90% faster |
| **WebSocket Management** | 1000+ lines custom | Managed by platform | 100% elimination |

---

## Current System Analysis

### ai-banking-voice-agent Architecture

```
┌─────────────────────────────────────────────────────┐
│           Current ElevenLabs System                  │
│                                                      │
│  ┌──────────┐     ┌──────────┐     ┌────────────┐ │
│  │  Twilio  │────▶│ WebSocket│────▶│ ElevenLabs │ │
│  │  Phone   │◀────│  Handler │◀────│   Agent    │ │
│  └──────────┘     └─────┬────┘     └──────┬─────┘ │
│                          │                  │       │
│                    ┌─────▼─────┐     ┌─────▼─────┐ │
│                    │   Redis   │     │  Webhook  │ │
│                    │  Session  │     │ Endpoints │ │
│                    └───────────┘     └─────┬─────┘ │
│                                            │       │
│                                     ┌──────▼─────┐ │
│                                     │  Tool APIs │ │
│                                     │ (8 tools)  │ │
│                                     └────────────┘ │
└─────────────────────────────────────────────────────┘
```

### Complexity Points

#### 1. Webhook Tool Registration
**Current Implementation:**
- JSON configuration files per environment (dev/prod)
- Dynamic URL substitution for different environments
- Manual webhook registration via ElevenLabs API
- Tool name prefixes (`dev_`, `prod_`) in configurations

**Example:**
```json
// api/config/tools/api/dev/verify_account.json
{
  "name": "dev_verify_account",
  "description": "Verify customer identity",
  "url": "https://ngrok-url.app/api/v1/tools/verify_account",
  "parameters": {
    "account_last_4": { "type": "string", "required": true },
    "postal_code": { "type": "string", "required": true }
  }
}
```

**Pain Points:**
- 🔴 16+ JSON configuration files to maintain
- 🔴 Environment-specific webhook URLs
- 🔴 Manual synchronization between ElevenLabs and backend
- 🔴 Difficult to test locally

#### 2. Prompt Management
**Current Implementation:**
- Compositional prompt system
- Azure Blob Storage for dynamic loading
- Template substitution for tool names
- Organization-specific prompt variations

**Flow:**
```python
# 1. Load template from local file
template = read_file("api/config/prompts/agent_prompt_template.txt")

# 2. Substitute tool names for environment
prompt = template.replace("{{verify_account}}", "`dev_verify_account`")

# 3. Upload to Azure Blob Storage
azure_blob.upload("prompts/dev/agent_prompt.txt", prompt)

# 4. Backend fetches from Azure Blob (cached 5min)
cached_prompt = azure_blob.download("prompts/dev/agent_prompt.txt")
```

**Pain Points:**
- 🔴 Complex deployment process (local → Azure Blob)
- 🔴 5-minute cache delay for prompt updates
- 🔴 Tool name substitution fragile
- 🔴 Requires Azure Blob Storage infrastructure

#### 3. Agent Configuration
**Current Implementation:**
- Separate ElevenLabs agents for dev and prod
- Agent tracking in `.elevenlabs/agents.json`
- Manual agent creation and tool linking

**Example:**
```json
// .elevenlabs/agents.json
{
  "dev": {
    "agent_id": "agent_dev123...",
    "name": "AI Collections Agent - Development",
    "source_agent": "agent_prod456..."
  },
  "prod": {
    "agent_id": "agent_prod456...",
    "name": "AI Collections Agent - Production"
  }
}
```

**Pain Points:**
- 🔴 Maintain two separate agents
- 🔴 Ensure tools linked to correct agent
- 🔴 Manual synchronization of agent settings
- 🔴 Different agent IDs across environments

#### 4. WebSocket Handler
**Current Implementation:**
- Custom 1000+ line WebSocket handler
- Twilio stream protocol translation
- ElevenLabs protocol handling
- Audio format conversion (PCM ↔ μ-law)
- Session state management
- Error recovery logic

**Example:**
```python
# api/services/websocket_handler.py (simplified)
class WebSocketHandler:
    async def handle_twilio_stream(self, websocket):
        # Decode Twilio audio (μ-law)
        audio_data = decode_mulaw(twilio_message)

        # Convert to ElevenLabs format (PCM)
        pcm_audio = convert_to_pcm(audio_data)

        # Send to ElevenLabs via WebSocket
        await elevenlabs_ws.send(pcm_audio)

        # Receive ElevenLabs audio
        response_audio = await elevenlabs_ws.receive()

        # Convert back to μ-law
        mulaw_audio = convert_to_mulaw(response_audio)

        # Send to Twilio
        await twilio_ws.send(mulaw_audio)
```

**Pain Points:**
- 🔴 Complex audio transcoding
- 🔴 Multiple network hops (Twilio → Backend → ElevenLabs)
- 🔴 Manual session state management
- 🔴 Error recovery logic duplicated
- 🔴 Difficult to test and debug

#### 5. Multi-Worker Coordination
**Current Implementation:**
- 4 Uvicorn workers for backend
- Redis-backed Socket.IO for real-time dashboard
- Room membership synchronization across workers
- Event broadcasting coordination

**Pain Points:**
- 🔴 Requires Redis for Socket.IO coordination
- 🔴 Worker-to-worker communication complexity
- 🔴 Events can be lost if Redis not configured correctly
- 🔴 Debugging multi-worker issues challenging

---

## What to Preserve

### ✅ Critical Features to Migrate

#### 1. Behavioral Tactics System
**Description:** 15 research-backed conversation tactics organized into 4 archetypes.

**Current Implementation:**
```python
# Azure Blob Storage: behavioral-configs/
aggressive_anchor.json
empathetic_gradual.json
balanced_progression.json
stern.json
```

**Archer Migration:**
```python
# backend/src/agent/behavioral.py
from pydantic import BaseModel

class BehavioralTactic(BaseModel):
    name: str
    archetype: str
    urgency: int
    empathy: int
    persistence: int
    authority: int

# Load from config files or database
TACTICS = load_behavioral_configs()
```

**Status:** ✅ **Fully Preservable** - Reuse same configs, port to Line SDK system prompt generation

#### 2. Real-time Dashboard with Socket.IO
**Description:** Live call monitoring, event streaming, configuration management.

**Current Implementation:**
```typescript
// web/src/services/websocket.ts
const socket = io(API_URL);
socket.on('call_tool_execution', handleToolExecution);
socket.on('call_status_update', handleStatusUpdate);
```

**Archer Migration Strategy:**
```python
# backend/src/api/websocket.py
# Preserve existing Socket.IO infrastructure
# Bridge Line SDK events to Socket.IO

@agent.on_event(Event.TOOL_EXECUTED)
async def on_tool_executed(context, tool_name, result):
    # Emit to Socket.IO room
    await sio.emit('call_tool_execution', {
        'call_id': context.get('call_sid'),
        'tool': tool_name,
        'result': result
    }, room=f"call_{context.get('call_sid')}")
```

**Status:** ✅ **Fully Preservable** - Bridge Line SDK events to existing Socket.IO system

#### 3. Two-Factor Verification Flow
**Description:** Last 4 digits + postal code verification with retry logic.

**Current Implementation:**
```python
# api/api/v1/endpoints/tools.py
@router.post("/tools/verify_account")
async def verify_account(request: VerifyAccountRequest):
    # Webhook-based implementation
    attempts = redis.get(f"verify_attempts:{call_sid}")
    if attempts >= 2:
        return {"success": False, "message": "Max attempts"}
    # ... verification logic
```

**Archer Migration:**
```python
# backend/src/tools/verification.py
from line import Tool, ToolResult

class VerifyAccountTool(Tool):
    async def execute(self, context: Context, **params) -> ToolResult:
        # Native function implementation
        attempts = context.get("verification_attempts", 0)
        if attempts >= 2:
            return ToolResult(
                success=False,
                message="Max attempts reached",
                should_end_call=True
            )
        # ... verification logic
```

**Status:** ✅ **Fully Preservable** - Convert webhook to native function, preserve logic

#### 4. Payment Arrangement Logic
**Description:** Extensions, payment plans, due date adjustments.

**Current Implementation:**
```python
# Business logic in webhook endpoints
@router.post("/tools/process_payment")
async def process_payment(request: PaymentRequest):
    # Determine payment type
    if request.payment_type == "sms_link":
        # Send SMS payment link
    elif request.payment_type == "bank_transfer":
        # Process transfer
```

**Archer Migration:**
```python
# backend/src/tools/payment.py
class ProcessPaymentTool(Tool):
    async def execute(self, context: Context, **params) -> ToolResult:
        # Reuse existing business logic
        # Convert from webhook to native function
```

**Status:** ✅ **Fully Preservable** - Reuse business logic, simplify integration

#### 5. Negotiation Guidance LLM
**Description:** OpenAI GPT-4 powered settlement recommendations.

**Current Implementation:**
```python
# api/services/negotiation_llm.py
async def get_negotiation_guidance(
    customer_offer: float,
    balance: float,
    conversation_context: str
) -> NegotiationGuidance:
    # OpenAI API call
    response = await openai_client.chat.completions.create(...)
    return parse_guidance(response)
```

**Archer Migration:**
```python
# backend/src/tools/negotiation.py
class NegotiationGuidanceTool(Tool):
    def __init__(self, openai_client):
        self.openai_client = openai_client

    async def execute(self, context: Context, **params) -> ToolResult:
        # Reuse existing OpenAI integration
        guidance = await self.openai_client.get_guidance(...)
        return ToolResult(success=True, data=guidance)
```

**Status:** ✅ **Fully Preservable** - Copy existing OpenAI integration

---

## What to Improve

### 🔧 Architectural Simplifications

#### 1. Tool Registration: Webhooks → Native Functions

**Before (ElevenLabs):**
```
1. Define tool in JSON config
2. Deploy JSON to ElevenLabs
3. Implement webhook endpoint
4. Register webhook URL with ElevenLabs
5. Handle webhook signature validation
6. Parse tool parameters from JSON
```

**After (Archer/Line SDK):**
```python
# backend/src/tools/verification.py
class VerifyAccountTool(Tool):
    """Native Python function - no webhooks!"""

    def __init__(self, backend_client):
        super().__init__(
            name="verify_account",
            description="Verify customer identity",
            parameters={
                "account_last_4": {
                    "type": "string",
                    "required": True
                },
                "postal_code": {
                    "type": "string",
                    "required": True
                }
            }
        )
        self.backend = backend_client

    async def execute(self, context: Context, **params) -> ToolResult:
        # Direct function call - no HTTP overhead
        result = await self.backend.verify(
            params["account_last_4"],
            params["postal_code"]
        )
        return ToolResult(success=result["verified"])
```

**Benefits:**
- ✅ 75% less configuration code
- ✅ No webhook endpoint registration
- ✅ Direct function calls (no HTTP overhead)
- ✅ Type-safe parameters
- ✅ Easier to test locally

#### 2. Prompt Management: Azure Blob → In-Code

**Before (ElevenLabs):**
```
1. Edit template file
2. Run deployment script
3. Substitute tool names
4. Upload to Azure Blob Storage
5. Wait 5 minutes for cache expiry
6. Backend fetches from Azure Blob
```

**After (Archer/Line SDK):**
```python
# backend/src/agent/prompts.py
def get_system_prompt(context: Context) -> str:
    """Generate system prompt with context."""
    return f"""
You are Alex from TD Bank calling about account management.

Current Context:
- Customer: {context.get("customer_name")}
- Balance: ${context.get("balance"):,.2f}
- Days Overdue: {context.get("days_overdue")}

Instructions:
1. Verify identity before discussing account
2. Use tools for all operations
3. Follow compliance requirements

Available Tools:
- verify_account: Verify customer identity
- get_customer_options: Retrieve payment options
- process_payment: Process payments
"""
```

**Benefits:**
- ✅ Prompts version-controlled with code
- ✅ No deployment script needed
- ✅ No Azure Blob Storage dependency
- ✅ Instant updates (no cache delay)
- ✅ Dynamic context injection easier

#### 3. Agent Configuration: Separate Agents → Single Codebase

**Before (ElevenLabs):**
```
Development:
- agent_id: agent_dev123...
- Tools: dev_verify_account, dev_get_customer_options, ...
- Webhook URLs: https://ngrok-url.app/...

Production:
- agent_id: agent_prod456...
- Tools: prod_verify_account, prod_get_customer_options, ...
- Webhook URLs: https://voice-backend.azurewebsites.net/...
```

**After (Archer/Line SDK):**
```python
# backend/src/agent/agent.py
class BankingVoiceAgent(Agent):
    def __init__(self):
        # Single agent codebase
        # Environment determined by env vars
        super().__init__(
            name=f"Archer Agent - {os.getenv('ENVIRONMENT')}",
            voice_config=get_voice_config()
        )

        # Same tools for all environments
        self.register_tools()

# Configuration via environment variables
# .env (development)
ENVIRONMENT=development
LINE_AGENT_ID=dev_agent_id

# .env (production)
ENVIRONMENT=production
LINE_AGENT_ID=prod_agent_id
```

**Benefits:**
- ✅ Single codebase for all environments
- ✅ No separate agent creation/management
- ✅ Tools don't need environment prefixes
- ✅ Configuration via standard env vars

#### 4. WebSocket Handling: Custom → Managed

**Before (ElevenLabs):**
```python
# 1000+ lines of custom WebSocket handling
- Twilio protocol decoding
- Audio transcoding (μ-law ↔ PCM)
- ElevenLabs protocol encoding
- Session state management
- Error recovery
- Keepalive pong handling
```

**After (Archer/Line SDK):**
```python
# Line SDK handles all WebSocket complexity
agent = BankingVoiceAgent()

# Twilio connects to Line SDK directly
# Native μ-law support (no transcoding)
# Managed infrastructure
```

**Benefits:**
- ✅ 100% elimination of custom WebSocket code
- ✅ Native μ-law support (no transcoding)
- ✅ Managed scaling and reliability
- ✅ Automatic error recovery
- ✅ Built-in monitoring

#### 5. Data Persistence: Azure Tables + Blob → PostgreSQL

**Before (ElevenLabs):**
```python
# Split persistence across multiple services
# 1. Azure Tables for call history
call_history_service.py → Azure Tables
  - calls (partitioned by customer_id)
  - transcripts (separate table)
  - customer_data (separate table)

# 2. Azure Blob Storage for configs
prompt_service.py → Azure Blob Storage
  - prompts/ (compositional templates)
  - behavioral-configs/ (15 tactic JSON files)

# 3. Redis for session state
redis_client.py → Redis
  - call_state:{call_sid}
  - verification_attempts:{call_sid}
```

**Pain Points:**
- 🔴 Can't query across Tables + Blob (e.g., "all calls using tactic X")
- 🔴 NoSQL limitations (no JOINs, weak filtering)
- 🔴 Manual referential integrity (no foreign keys)
- 🔴 Local development requires Azure Storage Emulator
- 🔴 5-minute cache TTL for prompt/config updates
- 🔴 Deployment scripts needed for config changes
- 🔴 Partition key required for efficient queries (without it, full table scan)

**After (Archer/PostgreSQL):**
```python
# backend/src/models/database.py
from sqlalchemy import Column, String, Integer, TIMESTAMP, ForeignKey, DECIMAL
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

class Customer(Base):
    __tablename__ = 'customers'
    id = Column(UUID, primary_key=True)
    phone_number = Column(String(20), unique=True, nullable=False)
    balance = Column(DECIMAL(10, 2), nullable=False)
    # Relationships
    calls = relationship("Call", back_populates="customer")

class Call(Base):
    __tablename__ = 'calls'
    id = Column(UUID, primary_key=True)
    call_sid = Column(String(100), unique=True, nullable=False)
    customer_id = Column(UUID, ForeignKey('customers.id'))
    behavioral_tactic_id = Column(UUID, ForeignKey('behavioral_tactics.id'))
    metadata = Column(JSONB, default={})  # Flexible JSON storage
    # Relationships
    customer = relationship("Customer")
    tactic = relationship("BehavioralTactic")
    transcript_entries = relationship("CallTranscriptEntry")

class BehavioralTactic(Base):
    __tablename__ = 'behavioral_tactics'
    id = Column(UUID, primary_key=True)
    name = Column(String(50), unique=True, nullable=False)
    archetype = Column(String(50), nullable=False)
    config = Column(JSONB, nullable=False)  # JSON config storage

# Now you can query relationally!
calls_with_tactic = session.query(Call).join(BehavioralTactic).filter(
    BehavioralTactic.name == 'aggressive_anchor'
).all()
```

**Benefits:**
- ✅ Single source of truth (one database for everything)
- ✅ Proper relational model with foreign keys
- ✅ JSONB for flexible config storage (best of both worlds)
- ✅ Easy local development (docker-compose with PostgreSQL)
- ✅ Instant config updates (no cache delay)
- ✅ No deployment scripts needed for configs
- ✅ Complex queries with JOINs across all data
- ✅ ~$15/month additional cost justified by DX improvements

**Migration Path:**
```python
# Phase 1: Set up PostgreSQL + schema
# Phase 2: Migrate behavioral configs (Azure Blob → PostgreSQL JSONB)
# Phase 3: Parallel write (write to both Azure Tables + PostgreSQL)
# Phase 4: Validate data consistency
# Phase 5: Switch reads to PostgreSQL
# Phase 6: Decommission Azure Tables + Blob Storage
```

**Reference:** See [ARCHITECTURE.md](../ARCHITECTURE.md#data-persistence-strategy) and [PERSISTENCE_STRATEGY.md](PERSISTENCE_STRATEGY.md) for complete schema design and migration details.

---

## Code Reuse Strategy

### Directly Reusable Components

#### 1. FastAPI API Structure ♻️
```python
# Copy entire API structure
ai-banking-voice-agent/api/api/v1/endpoints/
→ archer/backend/src/api/routes/

# Endpoints to preserve:
- /config/behavioral-tactics
- /config/organizations
- /admin/calls
- /test/call
```

**Status:** 95% reusable with minor adaptations

#### 2. React Dashboard Components ♻️
```typescript
// Copy frontend components
ai-banking-voice-agent/web/src/components/
→ archer/frontend/src/components/

// Components to preserve:
- CallMonitor
- BehavioralTacticsConfig
- CallTesting
- RealTimeEvents
```

**Status:** 90% reusable (update API types)

#### 3. Socket.IO Real-time Patterns ♻️
```typescript
// Reuse WebSocket service
ai-banking-voice-agent/web/src/services/websocket.ts
→ archer/frontend/src/services/websocket.ts

// Same event types:
- call_started
- call_tool_execution
- call_completed
```

**Status:** 100% reusable

#### 4. Docker Deployment Configs ♻️
```dockerfile
# Reuse Docker configurations
ai-banking-voice-agent/Dockerfile
→ archer/backend/Dockerfile

ai-banking-voice-agent/web/Dockerfile
→ archer/frontend/Dockerfile
```

**Status:** 90% reusable (update paths)

#### 5. GitHub Actions Workflows ♻️
```yaml
# Reuse CI/CD workflow
ai-banking-voice-agent/.github/workflows/azure-deploy.yml
→ archer/.github/workflows/deploy.yml

# Same pattern:
- Parallel builds (backend + frontend)
- Azure Container Registry push
- Dual Web App deployment
```

**Status:** 95% reusable (update image names)

---

## Migration Phases

### Phase 1: Foundation (Week 1)

**Objectives:**
- Set up Archer mono-repo structure
- Implement basic Line SDK agent
- Test Twilio connection
- Validate audio quality

**Tasks:**
```bash
✅ Create mono-repo structure (backend/ + frontend/)
✅ Set up Poetry for backend
✅ Set up npm for frontend
✅ Copy docker-compose.yml from ai-banking-voice-agent
✅ Add PostgreSQL service to docker-compose.yml
✅ Create database schema with Alembic migrations
✅ Implement SQLAlchemy models (Customer, Call, BehavioralTactic)
✅ Implement basic Line SDK agent with greeting
✅ Test Twilio → Line SDK → Twilio audio path
✅ Benchmark latency vs. ElevenLabs
```

**Deliverables:**
- Working "Hello World" agent
- Twilio integration confirmed
- Audio quality validated (40-90ms latency achieved)
- PostgreSQL database initialized with schema
- Repository pattern implemented for data access

**Code to Reuse:**
- Docker configurations (90%)
- docker-compose.yml (95%)

---

### Phase 2: Core Tools (Week 2)

**Objectives:**
- Implement verify_account tool
- Implement get_customer_options tool
- Add state management
- Migrate behavioral tactics to PostgreSQL
- Connect to existing backend APIs

**Tasks:**
```bash
✅ Convert verify_account webhook → native function
✅ Convert get_customer_options webhook → native function
✅ Implement context-based state management
✅ Migrate behavioral tactics from Azure Blob → PostgreSQL JSONB
✅ Create BehavioralTacticRepository with CRUD operations
✅ Test tool execution flow
✅ Connect to existing FastAPI tool endpoints (if needed)
```

**Deliverables:**
- 2 core tools functional
- State persistence working
- Behavioral tactics stored in PostgreSQL with JSONB configs
- Backend integration tested

**Code to Reuse:**
- Verification business logic from `api/api/v1/endpoints/tools.py` (100%)
- Options calculation logic (100%)

---

### Phase 3: Complete Tool Suite (Week 3)

**Objectives:**
- Migrate remaining 5 tools
- Implement negotiation guidance
- Add payment processing
- Implement agent transfer

**Tasks:**
```bash
✅ Migrate calculate_payment_plan
✅ Migrate process_payment
✅ Migrate get_negotiation_guidance (reuse OpenAI client)
✅ Migrate schedule_callback
✅ Migrate transfer_to_agent
✅ Add error handling for all tools
```

**Deliverables:**
- All 7 tools functional
- Error handling complete
- Full conversation flow tested

**Code to Reuse:**
- Negotiation LLM service (100%)
- Payment processing logic (100%)
- Callback scheduling logic (100%)

---

### Phase 4: Behavioral Tactics & Dashboard (Week 4)

**Objectives:**
- Port behavioral tactics system
- Integrate real-time dashboard
- Bridge Line SDK events to Socket.IO
- Implement dark/light theme system

**Tasks:**
```bash
✅ Copy behavioral tactics configs
✅ Implement tactic selection in Line SDK prompts
✅ Copy React dashboard components
✅ Preserve left nav + top nav from ai-banking-voice-agent
✅ Implement dark theme (default: deep navy #0a0e1a, cyan accents #00d9ff)
✅ Implement light theme (white background, same cyan accents)
✅ Add theme toggle in user menu
✅ Persist theme preference in localStorage
✅ Bridge Line SDK events to Socket.IO
✅ Implement type generation (Pydantic → TypeScript)
✅ Test real-time event streaming
```

**Deliverables:**
- Behavioral tactics system working
- Dashboard shows live events
- Dark theme (default) + light theme toggle working
- User preference persisted across sessions
- Type generation automated

**Code to Reuse:**
- Behavioral config files (100%)
- Dashboard components (`web/src/components/`) (90%)
- Socket.IO service (`web/src/services/websocket.ts`) (100%)

---

### Phase 5: Testing & Optimization (Week 5)

**Objectives:**
- Load testing
- Latency optimization
- A/B testing setup
- Security review

**Tasks:**
```bash
✅ Load test (simulate 100 concurrent calls)
✅ Benchmark latency (confirm 40-90ms)
✅ Set up A/B testing framework
✅ Test edge cases
✅ Security audit
```

**Deliverables:**
- Performance benchmarks documented
- A/B testing framework ready
- Security audit complete

---

### Phase 6: Gradual Rollout (Week 6)

**Objectives:**
- Deploy to Azure
- Route 5% → 25% → 50% → 100% traffic
- Monitor metrics
- Rollback procedures tested

**Traffic Routing Strategy:**
```python
# Routing logic (Twilio level or application level)
routing_config = {
    "week_1": {"cartesia_percentage": 5},
    "week_2": {"cartesia_percentage": 25},
    "week_3": {"cartesia_percentage": 50},
    "week_4": {"cartesia_percentage": 100}
}
```

**Deliverables:**
- Production deployment successful
- Monitoring dashboard operational
- Rollback procedures documented

---

## Testing Strategy

### Component Testing

```bash
# Backend unit tests
cd backend
poetry run pytest tests/unit/

# Frontend unit tests
cd frontend
npm run test
```

### Integration Testing

```bash
# Full stack integration
docker-compose up -d
poetry run pytest tests/integration/

# Test scenarios:
✅ Outbound call initiation
✅ Customer verification (success/failure)
✅ Payment options presentation
✅ Payment processing
✅ Negotiation guidance
✅ Agent transfer
✅ Real-time dashboard events
```

### Parallel Running (A/B Test)

```
┌─────────────────────────────────────────┐
│           Twilio Incoming Call          │
└────────────────┬────────────────────────┘
                 │
         ┌───────▼────────┐
         │  Routing Logic │
         │  (5% / 95%)    │
         └───────┬────────┘
                 │
         ┌───────┴────────┐
         │                │
    ┌────▼─────┐    ┌────▼──────┐
    │  Archer  │    │ ElevenLabs│
    │ Line SDK │    │  (Legacy) │
    └──────────┘    └───────────┘
```

**Metrics to Monitor:**
- First-byte latency
- Tool execution success rate
- Call completion rate
- Customer satisfaction (if available)
- Error rates

**Rollback Triggers:**
- Error rate >5%
- Latency >200ms (p95)
- Tool failure rate >10%

---

## Risk Mitigation

### Risk 1: Real-time Dashboard Integration

**Risk:** Line SDK event system differs from ElevenLabs webhooks

**Mitigation:**
```python
# Bridge Line SDK events to Socket.IO
@agent.on_event(Event.TOOL_EXECUTED)
async def on_tool_executed(context, tool_name, result):
    await sio.emit('call_tool_execution', {
        'call_id': context.get('call_sid'),
        'tool': tool_name,
        'result': result
    }, room=f"call_{context.get('call_sid')}")
```

**Status:** ✅ Solvable - preserve Socket.IO infrastructure

### Risk 2: Behavioral Tactics Compatibility

**Risk:** Line SDK prompt system may not support dynamic tactics

**Mitigation:**
- Dynamic prompt generation with context
- Inject tactic parameters at call initiation
- Test all 4 archetypes during Phase 4

**Status:** ✅ Solvable - prompts are strings, full control

### Risk 3: Multi-Worker Socket.IO Coordination

**Risk:** Line SDK deployment model may differ from current 4-worker setup

**Mitigation:**
- Use Redis-backed Socket.IO (same as current)
- Line SDK managed infrastructure handles voice agent scaling
- Backend API scales independently with existing pattern

**Status:** ✅ Solvable - preserve existing Redis coordination

### Risk 4: Azure Deployment Differences

**Risk:** Line SDK may have specific Azure requirements

**Mitigation:**
- Line SDK runs in backend container (same as FastAPI)
- No special Azure configuration needed
- Same deployment pattern as current system

**Status:** ✅ Solvable - containerized deployment unchanged

---

## Migration Checklist

### Pre-Migration
- [ ] Line SDK account created
- [ ] Cartesia API keys obtained
- [ ] Archer mono-repo initialized
- [ ] Team trained on Line SDK concepts
- [ ] Migration schedule communicated

### Phase 1: Foundation
- [ ] Mono-repo structure created
- [ ] Basic Line SDK agent implemented
- [ ] Twilio integration tested
- [ ] Audio quality validated (40-90ms achieved)
- [ ] "Hello World" demo successful

### Phase 2: Core Tools
- [ ] verify_account tool migrated
- [ ] get_customer_options tool migrated
- [ ] State management implemented
- [ ] Tool execution tested
- [ ] Backend API integration working

### Phase 3: Complete Tools
- [ ] All 7 tools migrated
- [ ] Negotiation LLM integrated
- [ ] Payment processing working
- [ ] Agent transfer tested
- [ ] Error handling complete

### Phase 4: Dashboard
- [ ] Behavioral tactics migrated
- [ ] Dashboard components copied
- [ ] Line SDK events bridged to Socket.IO
- [ ] Type generation automated
- [ ] Real-time events tested

### Phase 5: Testing
- [ ] Load testing complete
- [ ] Performance benchmarks met
- [ ] A/B testing framework ready
- [ ] Security audit passed
- [ ] Edge cases tested

### Phase 6: Rollout
- [ ] Deployed to Azure
- [ ] 5% traffic routed successfully
- [ ] Monitoring operational
- [ ] 25% → 50% → 100% rollout complete
- [ ] ElevenLabs system decommissioned

---

## Rollback Plan

### Immediate Rollback Procedure

```bash
# 1. Change traffic routing to 0% Cartesia
# (Application-level or Twilio-level routing)

# 2. Verify ElevenLabs system operational
curl https://voice-backend.azurewebsites.net/health

# 3. Monitor error rates return to baseline

# 4. Investigate Archer issues in logs
az webapp log tail --name archer-backend

# 5. Fix issues and re-test in development

# 6. Resume gradual rollout when stable
```

### Rollback Triggers

Automatic rollback if:
- Error rate >5% for 5 consecutive minutes
- Latency p95 >200ms for 10 minutes
- Tool failure rate >10%
- Manual escalation from support team

---

## Success Criteria

### Technical Metrics

| Metric | Target | How to Measure |
|--------|--------|----------------|
| First-byte Latency | <100ms (p95) | Azure App Insights |
| Tool Execution Time | <50ms (p95) | Custom metrics |
| Call Setup Time | <3s | Call logs |
| Error Rate | <2% | Error tracking |
| Uptime | >99.9% | Azure monitoring |

### Business Metrics

| Metric | Target | How to Measure |
|--------|--------|----------------|
| Arrangement Rate | Maintain or improve | Call outcome tracking |
| Customer Satisfaction | ≥ baseline | Post-call surveys |
| Cost per Call | <$0.50 | Azure billing + Cartesia |
| Development Velocity | 40% faster | Feature delivery time |

### Migration Completion

✅ **Complete when:**
- All features from ElevenLabs preserved
- 100% traffic on Archer for 2 weeks
- All metrics meet/exceed targets
- Team trained and confident
- ElevenLabs infrastructure decommissioned
- Documentation updated

---

## Lessons Learned (Post-Migration)

**To be completed after migration**

### What Went Well
- TBD

### Challenges Encountered
- TBD

### Would Do Differently
- TBD

### Recommendations for Future Migrations
- TBD

---

## References

- [Archer Architecture](../ARCHITECTURE.md)
- [Line SDK Design Document](../DESIGN-CARTESIA-LINE-SYSTEM.md)
- [Repository Strategy](REPOSITORY_STRATEGY.md)
- [ai-banking-voice-agent Documentation](../ai-banking-voice-agent/docs/)

---

**Document Maintained By:** Architecture Team
**Last Updated:** October 30, 2024
**Next Review:** After Phase 1 completion
