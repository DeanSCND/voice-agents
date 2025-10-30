# Archer Implementation Plan

**Version:** 1.0
**Date:** October 30, 2024
**Status:** Planning
**Strategy:** Phased Derisking - Validate Core → Build Features → Innovate

---

## Executive Summary

This implementation plan prioritizes **derisking** by validating Cartesia Line SDK quality with a real phone call first, then systematically building toward feature parity with ai-banking-voice-agent, and finally adding innovative capabilities.

### Phased Approach

```
Phase 0: Proof of Concept (1 week)
  ↓ Validate Cartesia quality with real calls
Phase 1: Core Voice Agent (2 weeks)
  ↓ Basic tools + database foundation
Phase 2: Feature Parity (3 weeks)
  ↓ Match ai-banking-voice-agent capabilities
Phase 3: Admin Dashboard (2 weeks)
  ↓ Configuration + monitoring UI
Phase 4: Innovation (3 weeks)
  ↓ Archer voice-first UI
Phase 5: Production Ready (2 weeks)
  ↓ Security, performance, deployment
```

**Total Timeline:** 13 weeks (3.25 months)
**Critical Path:** Phase 0 → Phase 1 → Phase 2
**Innovation Track:** Can start Phase 4 in parallel with Phase 3

---

## Phase 0: Proof of Concept - Cartesia Quality Validation

**Duration:** 1 week
**Priority:** 🔴 CRITICAL - Derisking
**Objective:** Place real phone call using Cartesia Line SDK and validate voice quality meets requirements

### Goals

1. Prove Cartesia can handle real phone calls via Twilio
2. Validate voice quality (latency, clarity, naturalness)
3. Confirm Line SDK integration works as expected
4. Make GO/NO-GO decision on Cartesia vs staying with ElevenLabs

### Tasks

#### Day 1: Environment Setup
```bash
✅ Create Line SDK account
✅ Obtain Cartesia API keys
✅ Set up Twilio account + phone number
✅ Configure development environment
✅ Install Line SDK CLI tools
```

#### Day 2-3: Minimal Agent Implementation
```python
# backend/src/poc/simple_agent.py
from line import Agent, Context

class SimpleGreetingAgent(Agent):
    """Minimal agent for quality validation"""

    def __init__(self):
        super().__init__(
            name="Simple Greeting Agent",
            voice_config={
                "model": "sonic-english",
                "voice_id": "professional-friendly-male",
                "speed": 1.0
            }
        )

    def get_system_prompt(self, context: Context) -> str:
        return """
        You are a friendly AI assistant testing voice quality.

        When the call starts, greet the caller and ask them a few questions
        to test conversation quality:
        1. Can they hear you clearly?
        2. How natural does your voice sound?
        3. Is there any noticeable latency?

        Keep the conversation natural and brief (2-3 minutes max).
        """
```

**Tasks:**
- ✅ Implement minimal Line SDK agent
- ✅ Configure Cartesia voice settings
- ✅ Set up Twilio → Line SDK connection
- ✅ Deploy to development environment

#### Day 4-5: Testing & Validation
```bash
# Test scenarios
✅ Outbound call to your phone number
✅ Inbound call from your phone
✅ Multi-turn conversation (5+ exchanges)
✅ Background noise handling
✅ Interruption handling (barge-in)
✅ Different voice speeds/emotions
```

**Quality Checklist:**

**Component-Specific Latency** (measured via Line SDK events):
- [ ] Cartesia TTS first-byte <100ms (P90, internal metric)
- [ ] STT processing <200ms (P90)
- [ ] LLM first-token <500ms (P90, simple responses)

**End-to-End User Experience** (measured via call recordings):
- [ ] Simple greeting response <600ms (median, user speaks → hears response)
- [ ] Multi-turn responses <800ms (median)
- [ ] Tool-based responses <2000ms (median, verification/payment lookups)

**Subjective Quality** (validated by 3+ testers):
- [ ] Voice sounds natural (7+/10 rating)
- [ ] Latency feels natural (7+/10 rating, conversation flows smoothly)
- [ ] Transcription accuracy >90%
- [ ] No audio dropouts or glitches
- [ ] Barge-in works smoothly
- [ ] Background noise doesn't break agent

**Baseline Comparison** (vs existing ai-banking-voice-agent):
- [ ] Cartesia is measurably faster than ElevenLabs (any improvement counts)
- [ ] Voice quality is equal or better than ElevenLabs

### Deliverables

1. **Working POC agent:** Can call your phone number and have natural conversation
2. **Comprehensive quality report:**
   - Component latency breakdown (TTS, STT, LLM with P90/P95 percentiles)
   - End-to-end latency measurements from multiple locations
   - Comparison to ElevenLabs baseline (existing ai-banking-voice-agent)
   - Subjective quality ratings from 3+ testers
3. **Call recording samples:** 10+ test calls recorded with timestamp analysis
4. **Latency instrumentation code:** Line SDK event hooks and analysis scripts
5. **Technical validation:** Confirms Line SDK works as advertised
6. **GO/NO-GO decision:** Data-driven recommendation with confidence level

### Success Criteria

✅ **GO Decision (proceed to Phase 1 if ALL met):**
- Cartesia TTS latency <100ms (P90) - validates advertised performance
- End-to-end simple responses <600ms (median) - competitive with industry
- Subjective latency rating 7+/10 from 3+ testers - feels natural
- Measurably faster than ElevenLabs baseline - any improvement justifies migration
- No critical Line SDK bugs discovered - technically viable

❌ **NO-GO Decision (pivot back to ElevenLabs if ANY met):**
- Cartesia TTS latency >150ms (P90) - significantly worse than advertised
- End-to-end latency >800ms simple responses - worse than ElevenLabs (~950ms)
- Subjective rating <6/10 - users find it frustrating
- Critical bugs block core functionality - not production-ready
- Zero improvement over ElevenLabs - no justification for migration

### Exit Criteria

**Must achieve before Phase 1:**
- Successfully placed 20+ test calls from multiple locations (US East, West, mobile)
- Voice quality validated by 3+ people (you + team members)
- Latency measurements documented with percentiles (median, P90, P95)
- Component-specific latency meets targets (TTS <100ms, end-to-end <600ms)
- Comparison to ElevenLabs baseline shows measurable improvement
- Comprehensive quality report generated
- No critical technical issues discovered
- Confidence level >8/10 in Cartesia choice

### Measurement Methodology

**See `docs/LATENCY_ANALYSIS.md` for comprehensive measurement strategy.**

#### Quick Reference: How to Measure Latency

**Level 1: Cartesia Internal Metrics** (validates TTS <100ms target)
```python
# Instrument POC agent with Line SDK event hooks
from line import Agent, Context
import time

class LatencyTrackingAgent(Agent):
    async def on_tts_start(self, context: Context):
        context.metrics['tts_start'] = time.time()

    async def on_first_audio_chunk(self, context: Context):
        tts_latency_ms = (time.time() - context.metrics['tts_start']) * 1000
        # This should be <100ms per Cartesia spec
        log_metric('tts_first_byte_ms', tts_latency_ms)
```

**Level 2: End-to-End User Experience** (validates <600ms target)
```markdown
Test Protocol:
1. Record all test calls (Twilio recording + local)
2. Analyze recordings with timestamp detection scripts
3. Measure: User finishes speaking → Agent first word heard
4. Repeat 20+ times from different locations
5. Calculate: median, P90, P95 percentiles
```

**Level 3: ElevenLabs Baseline Comparison**
```bash
# Before Phase 0, measure current ai-banking-voice-agent
# Make 5-10 calls, measure end-to-end latency
# Expected: ~950ms for simple responses with ElevenLabs

# During Phase 0, compare Cartesia POC to baseline
# Target: Any measurable improvement justifies migration
```

**Geographic Testing:**
- US East Coast (home/office): Baseline regional overhead
- US West Coast (home/office): +100-180ms expected
- Mobile networks (LTE/5G): +80-150ms expected

**Deliverable:** Structured quality report with component breakdown, end-to-end measurements, baseline comparison, and GO/NO-GO recommendation.

### Risks & Mitigation

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Voice quality below expectations | Medium | High | Test multiple voices/speeds, compare to ElevenLabs recordings |
| End-to-end latency exceeds targets | Medium | High | Use component-specific measurement (TTS vs full chain), compare to ElevenLabs baseline, test from multiple regions. See `docs/LATENCY_ANALYSIS.md` for realistic targets. |
| Cartesia TTS >150ms (not as advertised) | Low | High | Measure via Line SDK events, engage Cartesia support if above spec, NO-GO trigger |
| Line SDK bugs/missing features | Low | High | Engage Cartesia support early, document workarounds |
| Twilio integration issues | Low | Medium | Use Cartesia's Twilio integration guide, test thoroughly |
| Geographic latency variance too high | Low | Medium | Test from US East/West/mobile, consider multi-region deployment for Phase 2+ |

### Budget

- **Development time:** 40 hours (1 developer, 1 week)
- **Cartesia costs:** ~$50 (test calls)
- **Twilio costs:** ~$20 (phone number + calls)
- **Total:** ~$70 + developer time

---

## Phase 1: Core Voice Agent - Foundation

**Duration:** 2 weeks
**Priority:** 🟠 HIGH
**Objective:** Build functional voice agent with core tools and database foundation

**Prerequisites:** Phase 0 complete, GO decision made

### Goals

1. Implement 3 core tools (verification, options, payment)
2. Set up PostgreSQL database with initial schema
3. Working backend API for tool execution
4. Basic call history tracking

### Week 1: Database & Infrastructure

#### Tasks
```bash
✅ Set up mono-repo structure (backend/ + frontend/)
✅ Initialize Poetry for backend (Python 3.11+)
✅ Create docker-compose.yml (PostgreSQL + Redis)
✅ Set up Alembic for database migrations
✅ Implement SQLAlchemy models (Customer, Call, BehavioralTactic)
✅ Create initial migration (schema from PERSISTENCE_STRATEGY.md)
✅ Implement Repository pattern for data access
✅ Set up FastAPI application structure
✅ Configure environment variables (.env.example)
```

**Database Schema (Initial):**
```sql
-- Core tables for Phase 1
customers (id, phone_number, name, account_last_4, postal_code, balance, days_overdue)
calls (id, call_sid, customer_id, call_type, status, start_time, end_time, duration)
call_transcript_entries (id, call_id, timestamp, speaker, text, metadata)
```

**Directory Structure:**
```
archer/
├── backend/
│   ├── src/
│   │   ├── main.py                    # FastAPI app
│   │   ├── agent/
│   │   │   └── agent.py              # BankingVoiceAgent
│   │   ├── tools/
│   │   │   ├── verification.py
│   │   │   ├── payment.py
│   │   │   └── negotiation.py
│   │   ├── models/
│   │   │   ├── database.py           # SQLAlchemy models
│   │   │   └── schemas.py            # Pydantic schemas
│   │   ├── repositories/
│   │   │   ├── customer_repo.py
│   │   │   └── call_repo.py
│   │   └── api/
│   │       └── calls.py
│   ├── alembic/
│   │   └── versions/
│   ├── tests/
│   ├── pyproject.toml
│   └── Dockerfile
├── docker-compose.yml
└── .env.example
```

### Week 2: Core Tools Implementation

#### Tool 1: Account Verification
```python
# backend/src/tools/verification.py
from line import Tool, ToolResult, Context

class VerifyAccountTool(Tool):
    """Two-factor verification: last 4 + postal code"""

    async def execute(
        self,
        context: Context,
        account_last_4: str,
        postal_code: str
    ) -> ToolResult:
        """Verify against database"""
        customer_id = context.get("customer_id")

        # Query database
        customer = await self.customer_repo.get_by_id(customer_id)

        # Check match
        verified = (
            customer.account_last_4 == account_last_4 and
            customer.postal_code == postal_code
        )

        if verified:
            context.set("verified", True)
            return ToolResult(
                success=True,
                message="Thank you! Your identity has been verified."
            )
        else:
            attempts = context.get("verification_attempts", 0) + 1
            context.set("verification_attempts", attempts)

            if attempts >= 2:
                return ToolResult(
                    success=False,
                    message="I'm unable to verify your account. Please call customer service.",
                    should_end_call=True
                )

            return ToolResult(
                success=False,
                message=f"That doesn't match our records. You have {2-attempts} attempt(s) remaining."
            )
```

#### Tool 2: Get Customer Options
```python
# backend/src/tools/payment.py
class GetCustomerOptionsTool(Tool):
    """Retrieve payment options from database/business logic"""

    async def execute(self, context: Context) -> ToolResult:
        """Get options based on customer profile"""
        if not context.get("verified"):
            return ToolResult(
                success=False,
                message="Please verify your identity first."
            )

        customer_id = context.get("customer_id")
        customer = await self.customer_repo.get_by_id(customer_id)

        # Business logic for available options
        options = self._calculate_options(customer)

        # Store in context
        context.set("payment_options", options)

        return ToolResult(
            success=True,
            message=self._format_options_speech(options),
            data=options
        )
```

#### Tool 3: Process Payment
```python
class ProcessPaymentTool(Tool):
    """Process payment arrangement"""

    async def execute(
        self,
        context: Context,
        amount: float,
        payment_method: str  # 'sms_link' or 'bank_transfer'
    ) -> ToolResult:
        """Record payment arrangement"""
        customer_id = context.get("customer_id")
        call_id = context.get("call_id")

        # Record in database
        await self.call_repo.record_payment_arrangement(
            call_id=call_id,
            customer_id=customer_id,
            amount=amount,
            method=payment_method
        )

        # Send SMS if needed
        if payment_method == "sms_link":
            await self.sms_service.send_payment_link(customer_id, amount)

        return ToolResult(
            success=True,
            message=f"Perfect! I've arranged ${amount:,.2f} payment via {payment_method}."
        )
```

### Deliverables

1. **Database:** PostgreSQL running with initial schema
2. **Core agent:** BankingVoiceAgent with 3 tools registered
3. **API endpoints:** POST /api/v1/calls/initiate
4. **Test coverage:** >70% for tools and repositories
5. **Docker setup:** docker-compose brings up full stack

### Success Criteria

- [ ] Can initiate call programmatically via API
- [ ] Agent successfully verifies test customer
- [ ] Agent presents payment options from database
- [ ] Agent records payment arrangements
- [ ] Call history stored in database
- [ ] All tests passing

### Testing Plan

```bash
# Integration test flow
1. Create test customer in database
2. Initiate call via API
3. Agent calls test number
4. Walk through verification flow
5. Request payment options
6. Confirm payment arrangement
7. Verify data stored in database
8. Check call transcript recorded
```

### Exit Criteria

- 3 core tools fully functional
- Database stores call data correctly
- Can complete end-to-end call with verification + payment
- Ready to add more tools and complexity

---

## Phase 2: Feature Parity - Match ai-banking-voice-agent

**Duration:** 3 weeks
**Priority:** 🟡 MEDIUM
**Objective:** Achieve functional parity with existing ElevenLabs implementation

**Prerequisites:** Phase 1 complete

### Goals

1. Complete all 7-8 tools from ai-banking-voice-agent
2. Implement behavioral tactics system
3. Add negotiation guidance LLM integration
4. Real-time event streaming (Socket.IO)
5. Advanced call flow handling

### Week 1: Complete Tool Suite

#### Remaining Tools to Implement

**Tool 4: Calculate Payment Plan**
```python
class CalculatePaymentPlanTool(Tool):
    """Calculate monthly payment options"""
    async def execute(self, context, months: int, down_payment: float):
        # Business logic for payment plan calculation
        pass
```

**Tool 5: Negotiation Guidance** (OpenAI integration)
```python
class NegotiationGuidanceTool(Tool):
    """AI-powered settlement recommendations"""
    async def execute(self, context, customer_offer: float):
        # Call OpenAI GPT-4 for guidance
        guidance = await self.openai_client.get_negotiation_guidance(
            balance=context.get("balance"),
            customer_offer=customer_offer,
            conversation_context=self._get_recent_transcript(context)
        )
        return guidance
```

**Tool 6: Schedule Callback**
```python
class ScheduleCallbackTool(Tool):
    """Schedule follow-up call"""
    async def execute(self, context, datetime: str, reason: str):
        # Store callback in database
        pass
```

**Tool 7: Transfer to Agent**
```python
class TransferToAgentTool(Tool):
    """Transfer to human agent"""
    async def execute(self, context, reason: str):
        # Twilio transfer logic
        pass
```

**Tasks:**
```bash
✅ Implement calculate_payment_plan tool
✅ Integrate OpenAI for negotiation guidance
✅ Implement schedule_callback tool
✅ Implement transfer_to_agent tool
✅ Add tool execution logging
✅ Implement tool retry logic
✅ Add tool execution metrics
```

### Week 2: Behavioral Tactics System

**Objective:** Port behavioral tactics from ai-banking-voice-agent

**Tasks:**
```bash
✅ Migrate behavioral configs from Azure Blob → PostgreSQL JSONB
✅ Create BehavioralTactic model and repository
✅ Implement tactic selection logic
✅ Update agent prompt generation with tactic parameters
✅ Add tactic tracking in call records
✅ Test all 4 archetypes (aggressive_anchor, empathetic_gradual, balanced_progression, stern)
```

**Database Schema:**
```sql
CREATE TABLE behavioral_tactics (
    id UUID PRIMARY KEY,
    name VARCHAR(50) UNIQUE NOT NULL,
    archetype VARCHAR(50) NOT NULL,
    config JSONB NOT NULL,  -- urgency, empathy, persistence, authority
    created_at TIMESTAMP DEFAULT NOW()
);

-- Seed with 4 base tactics
INSERT INTO behavioral_tactics (name, archetype, config) VALUES
('aggressive_anchor', 'aggressive', '{"urgency": 8, "empathy": 2, "persistence": 9, "authority": 7}'),
('empathetic_gradual', 'empathetic', '{"urgency": 3, "empathy": 9, "persistence": 5, "authority": 4}'),
('balanced_progression', 'balanced', '{"urgency": 5, "empathy": 6, "persistence": 7, "authority": 6}'),
('stern', 'stern', '{"urgency": 7, "empathy": 3, "persistence": 6, "authority": 9}');
```

**Prompt Generation:**
```python
def get_system_prompt(self, context: Context) -> str:
    tactic = context.get("behavioral_tactic")
    config = tactic.config

    urgency_instructions = self._get_urgency_instructions(config["urgency"])
    empathy_instructions = self._get_empathy_instructions(config["empathy"])

    return f"""
    You are Alex from TD Bank calling about account management.

    Conversation Style (Tactic: {tactic.name}):
    - Urgency: {urgency_instructions}
    - Empathy: {empathy_instructions}
    - Persistence: {self._get_persistence_instructions(config["persistence"])}
    - Authority: {self._get_authority_instructions(config["authority"])}

    ...
    """
```

### Week 3: Real-time Events & Advanced Features

**Objective:** Socket.IO integration and production features

**Tasks:**
```bash
✅ Set up Socket.IO server with Redis adapter
✅ Implement event emitters in agent (tool_executed, call_status_update)
✅ Add call recording (optional)
✅ Implement compliance checks (TCPA, FDCPA keywords)
✅ Add error recovery and retry logic
✅ Implement call quality monitoring
✅ Add detailed logging and observability
```

**Socket.IO Events:**
```python
# Emit events during call
@agent.on_event(Event.TOOL_EXECUTED)
async def on_tool_executed(context, tool_name, result):
    await sio.emit('call_tool_execution', {
        'call_id': context.get('call_sid'),
        'tool': tool_name,
        'result': result,
        'timestamp': datetime.now().isoformat()
    }, room=f"call_{context.get('call_sid')}")
```

### Deliverables

1. **Complete tool suite:** All 7-8 tools functional
2. **Behavioral tactics:** 4 archetypes working with dynamic prompt generation
3. **OpenAI integration:** Negotiation guidance operational
4. **Real-time events:** Socket.IO streaming call events
5. **Database:** All tables populated with reference data
6. **Tests:** >80% coverage

### Success Criteria

- [ ] Feature parity checklist 100% complete (compare to ai-banking-voice-agent)
- [ ] All behavioral tactics tested with real calls
- [ ] Negotiation guidance provides useful recommendations
- [ ] Real-time events stream correctly to frontend (when built)
- [ ] No functional regressions vs ai-banking-voice-agent

### Feature Parity Checklist

| Feature | ai-banking-voice-agent | Archer | Status |
|---------|----------------------|--------|--------|
| Account verification | ✅ | ✅ | Complete |
| Payment options | ✅ | ✅ | Complete |
| Payment processing | ✅ | ✅ | Complete |
| Payment plans | ✅ | ⏳ | Week 1 |
| Negotiation guidance | ✅ | ⏳ | Week 1 |
| Callback scheduling | ✅ | ⏳ | Week 1 |
| Agent transfer | ✅ | ⏳ | Week 1 |
| Behavioral tactics | ✅ | ⏳ | Week 2 |
| Real-time events | ✅ | ⏳ | Week 3 |
| Call recording | ✅ | ⏳ | Week 3 |
| Compliance checks | ✅ | ⏳ | Week 3 |

### Exit Criteria

- All features from ai-banking-voice-agent replicated
- Backend fully functional and tested
- Ready for frontend development
- No known critical bugs

---

## Phase 3: Admin Dashboard - Configuration UI

**Duration:** 2 weeks
**Priority:** 🟡 MEDIUM
**Objective:** Build React admin interface for configuration and monitoring

**Prerequisites:** Phase 2 complete

### Goals

1. Basic UI with left nav + top nav (from ai-banking-voice-agent)
2. Dark/light theme system (dark default)
3. Call monitoring dashboard
4. Behavioral tactics configuration
5. Test call interface

### Week 1: Foundation & Theme

**Tasks:**
```bash
✅ Initialize React app with Vite + TypeScript
✅ Set up Tailwind CSS
✅ Implement dark theme (default: #0a0e1a, cyan #00d9ff)
✅ Implement light theme
✅ Add theme toggle in user menu
✅ Persist theme in localStorage
✅ Copy left nav + top nav from ai-banking-voice-agent
✅ Set up React Router for navigation
✅ Generate TypeScript types from Pydantic models
✅ Set up TanStack Query for API state
```

**Directory Structure:**
```
frontend/
├── src/
│   ├── components/
│   │   ├── layout/
│   │   │   ├── LeftNav.tsx
│   │   │   ├── TopNav.tsx
│   │   │   └── ThemeToggle.tsx
│   │   └── shared/
│   ├── pages/
│   │   ├── Dashboard.tsx
│   │   ├── Calls.tsx
│   │   ├── Tactics.tsx
│   │   └── TestCall.tsx
│   ├── services/
│   │   ├── api.ts              # REST API client
│   │   └── websocket.ts        # Socket.IO client
│   ├── types/
│   │   └── api.ts              # Generated from backend
│   ├── hooks/
│   │   ├── useTheme.ts
│   │   └── useCalls.ts
│   ├── App.tsx
│   └── main.tsx
├── package.json
└── Dockerfile
```

### Week 2: Core Pages

**Page 1: Dashboard**
- Today's call metrics (count, duration, success rate)
- Recent calls list
- Active calls counter
- Behavioral tactic performance chart

**Page 2: Call History**
- Searchable/filterable call list
- Call detail view with transcript
- Export functionality

**Page 3: Behavioral Tactics Configuration**
- List of tactics
- Edit tactic parameters (urgency, empathy, persistence, authority)
- Create new custom tactics
- Tactic performance analytics

**Page 4: Test Call Interface**
- Phone number input
- Tactic selector
- Customer context (balance, overdue days)
- Start call button
- Live call monitoring (when active)

**Socket.IO Integration:**
```typescript
// Real-time call updates
socket.on('call_started', (data) => {
  // Update UI
});

socket.on('call_tool_execution', (data) => {
  // Show tool execution in real-time
});

socket.on('call_ended', (data) => {
  // Update call history
});
```

### Deliverables

1. **Working UI:** All core pages functional
2. **Theme system:** Dark (default) + light mode toggle
3. **API integration:** Frontend calls backend successfully
4. **Real-time updates:** Socket.IO events displayed
5. **Type safety:** Generated types prevent API mismatches

### Success Criteria

- [ ] Can view call history
- [ ] Can configure behavioral tactics
- [ ] Can initiate test calls
- [ ] Real-time updates work
- [ ] Theme toggle persists preference
- [ ] Responsive design (desktop + tablet)

### Exit Criteria

- Feature parity with ai-banking-voice-agent UI achieved
- All pages functional and tested
- Ready for innovation features (Archer voice UI)

---

## Phase 4: Innovation - Archer Voice-First UI

**Duration:** 3 weeks
**Priority:** 🟢 LOW (Can be deprioritized if needed)
**Objective:** Implement Archer voice-first admin interface

**Prerequisites:** Phase 3 complete (can start in parallel)

### Week 1: Foundation

**Tasks:**
```bash
✅ Create backend/src/archer/ agent structure
✅ Implement ArcherUIAgent with Line SDK
✅ Create frontend/src/components/archer/ components
✅ Integrate Cartesia voice client (STT + TTS)
✅ Implement ArcherAvatar with animations
✅ Build VoiceWaveform visualization
✅ Add push-to-talk (spacebar)
✅ Implement auto-greet on page load
```

### Week 2: Demo Flows

**Tasks:**
```bash
✅ Implement RunDemoFlow tool with "quick_tour"
✅ Create LaunchTestCall tool
✅ Implement QueryAnalytics tool
✅ Build overlay integration (login, test call, analytics)
✅ Implement context synchronization
✅ Add pause/resume on overlay interactions
✅ Pre-record demo call audio
```

### Week 3: Polish

**Tasks:**
```bash
✅ Error handling & fallbacks
✅ Text chat fallback
✅ Mobile responsive design
✅ Performance optimization (<400ms latency)
✅ User acceptance testing
✅ Accessibility audit
```

### Deliverables

1. **Archer UI agent:** Working voice-first interface
2. **Demo flows:** 90-second "quick tour" perfected
3. **Polish:** Dark theme optimized, smooth animations
4. **Fallbacks:** Text chat, dismissible UI

### Success Criteria

- [ ] 90-second demo completes successfully
- [ ] Voice latency <400ms
- [ ] Sales team can demo confidently
- [ ] Zero demo failures in demo mode

**Note:** This phase can be deferred if timeline is tight. Core functionality complete after Phase 3.

---

## Phase 5: Production Ready - Security & Deployment

**Duration:** 2 weeks
**Priority:** 🔴 CRITICAL (before production)
**Objective:** Security hardening, performance optimization, production deployment

### Week 1: Security & Compliance

**Tasks:**
```bash
✅ Security audit
  - SQL injection prevention (use parameterized queries)
  - XSS protection (sanitize inputs)
  - CSRF protection (tokens)
  - API authentication (JWT)
  - PII masking in logs
✅ Compliance review
  - TCPA compliance (consent, DNC list)
  - FDCPA compliance (threat keywords blocked)
  - GDPR considerations (data retention)
✅ Penetration testing
✅ Secrets management (Azure Key Vault)
✅ Rate limiting (prevent abuse)
✅ Input validation (all endpoints)
```

### Week 2: Performance & Deployment

**Performance Optimization:**
```bash
✅ Database query optimization
  - Add indexes on frequently queried columns
  - Optimize N+1 queries
  - Connection pooling
✅ Caching strategy
  - Redis for session state
  - Cache behavioral tactics (rarely change)
✅ Frontend optimization
  - Code splitting
  - Lazy loading
  - Image optimization
✅ Load testing (simulate 100 concurrent calls)
```

**Deployment:**
```bash
✅ Create GitHub Actions workflow
  - Parallel backend + frontend builds
  - Run tests
  - Push to Azure Container Registry
  - Deploy to Azure Web Apps
✅ Set up Azure resources
  - 2 Web Apps (backend + frontend)
  - Azure Database for PostgreSQL
  - Redis Cache
  - Application Insights (monitoring)
✅ Configure environment variables
✅ Set up monitoring & alerts
✅ Document deployment process
✅ Create rollback procedure
```

### Deliverables

1. **Security:** All vulnerabilities addressed
2. **Performance:** Load tested, optimized
3. **Deployment:** Automated CI/CD pipeline
4. **Monitoring:** Application Insights configured
5. **Documentation:** Deployment guide, runbooks

### Success Criteria

- [ ] Security audit passed
- [ ] Load test handles 100 concurrent calls
- [ ] Deployment automated and documented
- [ ] Monitoring dashboards operational
- [ ] Ready for production traffic

---

## Timeline Summary

```
┌────────────────────────────────────────────────────────┐
│                    Gantt Chart                          │
└────────────────────────────────────────────────────────┘

Week 1:   [Phase 0: POC - Cartesia Validation]
            ↓ GO/NO-GO Decision
Week 2-3: [Phase 1: Core Voice Agent]
Week 4-6: [Phase 2: Feature Parity]
Week 7-8: [Phase 3: Admin Dashboard]
Week 9-11:[Phase 4: Archer Voice UI] ← Optional/Parallel
Week 12-13:[Phase 5: Production Ready]

Critical Path: Phase 0 → 1 → 2 → 5
Innovation Track: Phase 4 (can run parallel to Phase 5)
```

### Milestone Dates (Starting Today: Oct 30, 2024)

| Phase | Start Date | End Date | Duration | Milestone |
|-------|-----------|----------|----------|-----------|
| **Phase 0** | Oct 30 | Nov 6 | 1 week | ✅ Cartesia validated |
| **Phase 1** | Nov 7 | Nov 20 | 2 weeks | ✅ Core agent working |
| **Phase 2** | Nov 21 | Dec 11 | 3 weeks | ✅ Feature parity |
| **Phase 3** | Dec 12 | Dec 25 | 2 weeks | ✅ Admin dashboard |
| **Phase 4** | Dec 12* | Jan 1 | 3 weeks | ✅ Innovation complete |
| **Phase 5** | Dec 26 | Jan 8 | 2 weeks | 🚀 Production launch |

*Phase 4 can start parallel to Phase 3

**Target Launch Date:** January 8, 2025 (13 weeks from now)

---

## Resource Requirements

### Team Composition

**Minimum Viable Team:**
- 1 Full-stack Developer (Backend + Frontend)
- 1 Product Manager (part-time, for decisions)
- You (for testing, validation, feedback)

**Optimal Team:**
- 1 Backend Developer (Python/FastAPI)
- 1 Frontend Developer (React/TypeScript)
- 1 DevOps Engineer (part-time for Phase 5)
- 1 Product Manager (part-time)

### Budget Estimate

| Category | Cost | Notes |
|----------|------|-------|
| **Development** | $0 | Internal team |
| **Cartesia** | $200 | Testing + initial usage |
| **Twilio** | $100 | Phone numbers + calls |
| **Azure** | $300/month | PostgreSQL, Redis, Web Apps |
| **OpenAI** | $50 | Negotiation guidance testing |
| **Total (3 months)** | ~$1,350 | Excluding salaries |

---

## Risk Management

### Critical Risks

| Risk | Phase | Probability | Impact | Mitigation |
|------|-------|-------------|--------|------------|
| **Cartesia quality insufficient** | 0 | Medium | High | Comprehensive POC, early testing, fallback to ElevenLabs |
| **Line SDK missing features** | 1 | Low | High | Deep research in Phase 0, engage Cartesia support |
| **PostgreSQL migration issues** | 1 | Low | Medium | Test migration scripts, validate data integrity |
| **Integration complexity** | 2 | Medium | Medium | Incremental integration, thorough testing |
| **Timeline slip** | All | Medium | Medium | Buffer weeks built in, Phase 4 optional |
| **Team availability** | All | Medium | High | Cross-training, documentation, knowledge sharing |

### Contingency Plans

**If Cartesia fails Phase 0:**
- Pivot back to ElevenLabs
- Adjust architecture to accommodate ElevenLabs webhooks
- Timeline extends by 2-3 weeks

**If timeline slips:**
- Defer Phase 4 (Archer voice UI) to post-launch
- Focus on Phase 0-3 + 5 for MVP
- Launch with feature parity, add innovation later

**If team capacity constrained:**
- Extend timelines by 50%
- Prioritize Phase 0-2 (core functionality)
- Outsource frontend (Phase 3) if needed

---

## Success Metrics

### Phase 0 (Cartesia Validation)

- Voice quality rating: >7/10 (subjective)
- Latency p95: <500ms
- Successful test calls: >10
- Team confidence: >8/10 in proceeding

### Phase 1 (Core Agent)

- Core tools working: 3/3
- Database operational: 100%
- Test coverage: >70%
- End-to-end call success: 100%

### Phase 2 (Feature Parity)

- Feature parity: 100% vs ai-banking-voice-agent
- Tool suite: 7-8 tools functional
- Test coverage: >80%
- Behavioral tactics: 4/4 working

### Phase 3 (Admin Dashboard)

- UI functional: 100% of pages
- Real-time events: Working
- Theme system: Dark + light
- User testing: Positive feedback from 3+ users

### Phase 4 (Innovation)

- Demo reliability: 100% (zero failures)
- Voice latency: <400ms
- Sales team trained: 100%
- Prospect reactions: Positive from 3+ demos

### Phase 5 (Production)

- Security audit: Passed
- Load test: 100 concurrent calls
- Deployment: Automated
- Monitoring: Operational

### Post-Launch (Month 1)

- Call success rate: >95%
- Average latency: <300ms
- Uptime: >99.5%
- Customer satisfaction: >8/10

---

## Decision Points & Gates

### Phase 0 Exit Gate: GO/NO-GO on Cartesia

**Criteria for GO:**
- ✅ Voice quality acceptable (>7/10)
- ✅ Latency within range (<500ms)
- ✅ No critical technical blockers
- ✅ Team confidence >8/10

**If NO-GO:**
- Reassess with ElevenLabs
- Evaluate alternative providers
- Adjust architecture accordingly

### Phase 1 Exit Gate: Database Foundation Solid

**Criteria:**
- ✅ All migrations run successfully
- ✅ Core tables populated
- ✅ Repository pattern working
- ✅ Data integrity validated

### Phase 2 Exit Gate: Feature Parity Achieved

**Criteria:**
- ✅ All tools functional
- ✅ Behavioral tactics working
- ✅ Real-time events streaming
- ✅ No regressions vs ai-banking-voice-agent

### Phase 3 Exit Gate: UI Functional

**Criteria:**
- ✅ All pages working
- ✅ Theme system operational
- ✅ API integration complete
- ✅ User testing positive

### Phase 5 Exit Gate: Production Ready

**Criteria:**
- ✅ Security audit passed
- ✅ Performance validated
- ✅ Deployment automated
- ✅ Monitoring operational
- ✅ Team trained on operations

---

## Communication Plan

### Weekly Status Updates

**Format:**
- Completed this week
- Planned for next week
- Blockers/risks
- Decision needed

**Audience:**
- You (stakeholder)
- Development team
- Product manager

### Phase Completion Reviews

**Format:**
- Demo of completed functionality
- Metrics review (success criteria)
- Lessons learned
- Adjustments for next phase

**Timing:**
- End of each phase
- 1-hour meeting
- Documented decisions

### Daily Standups (Async)

**Format:**
- Yesterday's progress
- Today's plan
- Any blockers

**Timing:**
- Posted by 10am daily
- Slack/Teams channel

---

## Appendix A: Detailed Task Breakdown

### Phase 0: Day-by-Day Plan

**Monday (Day 1):**
- Morning: Create Line SDK account, obtain API keys
- Afternoon: Set up Twilio account, configure phone number

**Tuesday (Day 2):**
- Morning: Implement minimal Line SDK agent
- Afternoon: Configure Cartesia voice settings

**Wednesday (Day 3):**
- Morning: Set up Twilio → Line SDK connection
- Afternoon: Deploy to development environment
- Evening: First test call

**Thursday (Day 4):**
- Morning: Test various scenarios (outbound, inbound, multi-turn)
- Afternoon: Measure latency, record quality samples

**Friday (Day 5):**
- Morning: Test with team members, gather feedback
- Afternoon: Compile quality report, make GO/NO-GO recommendation

### Phase 1: Sprint Planning

**Sprint 1 (Week 1): Database Foundation**
- Story 1: Set up mono-repo structure (8 hours)
- Story 2: Configure PostgreSQL + Redis (4 hours)
- Story 3: Create SQLAlchemy models (8 hours)
- Story 4: Set up Alembic migrations (4 hours)
- Story 5: Implement repository pattern (8 hours)
- Story 6: Create FastAPI app structure (8 hours)

**Sprint 2 (Week 2): Core Tools**
- Story 1: Implement verification tool (8 hours)
- Story 2: Implement payment options tool (6 hours)
- Story 3: Implement payment processing tool (8 hours)
- Story 4: Add tool execution logging (4 hours)
- Story 5: Write integration tests (8 hours)
- Story 6: End-to-end testing (6 hours)

---

## Appendix B: Testing Strategy

### Phase 0 Testing

**Manual Testing:**
- Call your phone number 10+ times
- Test different times of day
- Test with background noise
- Test interruptions (barge-in)
- Have 2-3 team members test

**Metrics to Capture:**
- First-byte latency (ms)
- End-to-end latency (ms)
- Voice quality rating (1-10)
- Transcription accuracy (%)
- Naturalness rating (1-10)

### Phase 1 Testing

**Unit Tests:**
- Tool execution logic
- Repository CRUD operations
- Database constraints

**Integration Tests:**
- End-to-end call flow
- Database persistence
- API endpoint responses

**Performance Tests:**
- Database query speed
- API response times

### Phase 2-5 Testing

- Unit tests for all new code
- Integration tests for workflows
- Load testing (100 concurrent calls)
- Security testing (OWASP Top 10)
- User acceptance testing

---

## Appendix C: Deployment Architecture

### Development Environment

```
┌─────────────────────────────────────┐
│      Local Development               │
│                                      │
│  docker-compose up                   │
│  ├── PostgreSQL (localhost:5432)    │
│  ├── Redis (localhost:6379)         │
│  ├── Backend (localhost:8000)       │
│  └── Frontend (localhost:3000)      │
└─────────────────────────────────────┘
```

### Production Environment (Azure)

```
┌──────────────────────────────────────────────┐
│              Azure Production                 │
│                                               │
│  ┌────────────────┐  ┌────────────────┐     │
│  │  Backend       │  │  Frontend      │     │
│  │  Web App       │  │  Web App       │     │
│  │  (Python)      │  │  (React)       │     │
│  └────────┬───────┘  └────────────────┘     │
│           │                                   │
│  ┌────────▼─────────────────────────┐        │
│  │  Azure Database for PostgreSQL   │        │
│  └──────────────────────────────────┘        │
│                                               │
│  ┌──────────────────────────────────┐        │
│  │  Azure Redis Cache                │        │
│  └──────────────────────────────────┘        │
│                                               │
│  ┌──────────────────────────────────┐        │
│  │  Application Insights             │        │
│  └──────────────────────────────────┘        │
└──────────────────────────────────────────────┘
```

---

## Conclusion

This phased implementation plan prioritizes **derisking through early Cartesia validation** (Phase 0), then builds systematically toward feature parity (Phases 1-2) and innovation (Phase 4).

**Critical Success Factors:**
1. ✅ Phase 0 validation proves Cartesia quality
2. ✅ Strong database foundation in Phase 1
3. ✅ Feature parity achieved in Phase 2
4. ✅ Production-ready security and performance in Phase 5

**Flexibility:**
- Phase 4 (Archer voice UI) is optional and can be deferred
- Timeline has buffer weeks built in
- Can adjust based on Phase 0 results

**Next Steps:**
1. Review and approve this plan
2. Assemble team and assign roles
3. Schedule Phase 0 kickoff
4. Begin Cartesia POC immediately

**Ready to start Phase 0?** Let's validate Cartesia and make the GO/NO-GO decision within 1 week.

---

**Document Status:** Ready for Review
**Maintained By:** Architecture Team
**Next Review:** After Phase 0 completion
**Related Documents:**
- [ARCHITECTURE.md](../ARCHITECTURE.md)
- [INNOVATION_ARCHER_UI_AGENT.md](INNOVATION_ARCHER_UI_AGENT.md)
- [MIGRATION_FROM_ELEVENLABS.md](MIGRATION_FROM_ELEVENLABS.md)
- [PERSISTENCE_STRATEGY.md](PERSISTENCE_STRATEGY.md)
