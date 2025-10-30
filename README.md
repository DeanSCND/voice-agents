# Archer - AI Voice Agent Platform

**Next-generation voice agent system powered by Cartesia Line SDK and Twilio**

[![Architecture](https://img.shields.io/badge/Architecture-Mono--repo-blue)](ARCHITECTURE.md)
[![Backend](https://img.shields.io/badge/Backend-Python%20%2F%20FastAPI-green)](archer/backend/)
[![Phase](https://img.shields.io/badge/Phase-1%20Foundation-orange)](docs/IMPLEMENTATION_PLAN.md)

---

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- Docker & Docker Compose
- Poetry (Python package manager)
- Cartesia API key
- Twilio account

### Local Development Setup

```bash
# 1. Clone repository
cd voice-agents

# 2. Copy environment template
cp .env.example .env
# Edit .env with your credentials (Cartesia, Twilio, etc.)

# 3. Start services (PostgreSQL + Redis + Backend)
docker-compose up -d

# 4. Run database migrations
docker-compose exec backend poetry run alembic upgrade head

# 5. Verify services
curl http://localhost:8000/health
# Should return: {"status": "healthy"}

# 6. Access API documentation
open http://localhost:8000/docs
```

### Backend Development (Without Docker)

```bash
cd archer/backend

# Install dependencies
poetry install

# Configure environment
cp .env.example .env
# Edit with your values

# Start PostgreSQL and Redis
docker-compose up -d postgres redis

# Run migrations
poetry run alembic upgrade head

# Start development server
poetry run uvicorn src.main:app --reload --port 8000

# Run tests
poetry run pytest --cov

# Access API at http://localhost:8000
```

---

## 📋 Phase 1 Status: Core Voice Agent Foundation

**Current Implementation** (2 weeks, Phase 1):

✅ **Backend Infrastructure**:
- Mono-repo structure (archer/backend/)
- Poetry dependency management
- FastAPI REST API
- PostgreSQL database with SQLAlchemy 2.0 async
- Alembic migrations
- Repository pattern

✅ **Database Models**:
- Customer (phone, account_last_4, postal_code, balance, days_overdue)
- Call (call_sid, customer FK, status, metadata JSONB)
- CallTranscriptEntry (call FK, transcript/tool/event data)

✅ **Three Core Tools** (Cartesia Line SDK):
1. **VerifyAccountTool** - Two-factor auth (account_last_4 + postal_code), max 2 attempts
2. **GetCustomerOptionsTool** - Calculate payment options (full, settlement, payment plan)
3. **ProcessPaymentTool** - Record arrangements (SMS link, bank transfer, payment plan)

✅ **BankingVoiceAgent**:
- Cartesia Line SDK agent with 3 tools
- Professional system prompt (TCPA/FDCPA compliant)
- Context-aware conversation
- Verification-first workflow

✅ **API Endpoints**:
- POST `/api/v1/calls/initiate` - Initiate outbound call
- GET `/api/v1/calls/{call_sid}` - Get call details
- GET `/health` - Health check

✅ **Test Coverage**:
- test_verification_tool.py - 4 test cases
- test_payment_tools.py - 7 test cases
- test_repositories.py - 8 test cases
- >70% coverage target

---

## 🗂️ Project Structure

```
voice-agents/
├── archer/backend/           # Python backend (Poetry)
│   ├── src/
│   │   ├── agent/           # BankingVoiceAgent (Line SDK)
│   │   ├── tools/           # Verification, payment tools
│   │   ├── models/          # SQLAlchemy models + Pydantic schemas
│   │   ├── repositories/    # Data access layer
│   │   ├── api/             # FastAPI endpoints
│   │   └── main.py          # FastAPI app
│   ├── alembic/             # Database migrations
│   ├── tests/               # Pytest test suite
│   └── pyproject.toml       # Poetry config
│
├── docs/                    # Documentation
│   ├── IMPLEMENTATION_PLAN.md      # Phased rollout (Phases 0-5)
│   ├── LATENCY_ANALYSIS.md         # Latency measurement strategy
│   ├── PERSISTENCE_STRATEGY.md     # PostgreSQL architecture
│   └── MIGRATION_FROM_ELEVENLABS.md
│
├── docker-compose.yml       # PostgreSQL + Redis + Backend
├── .env.example             # Environment template
├── ARCHITECTURE.md          # System architecture
└── README.md                # This file
```

---

## 📊 API Documentation

Interactive API documentation available when backend is running:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

### Key Endpoints

```bash
# Health check
GET /health

# Initiate outbound call
POST /api/v1/calls/initiate
{
  "customer_phone": "+15555551234",
  "customer_id": "uuid-here"
}

# Get call details
GET /api/v1/calls/{call_sid}

# Get customer calls
GET /api/v1/calls/customer/{customer_id}
```

---

## 🧪 Testing

```bash
cd archer/backend

# Run all tests with coverage
poetry run pytest --cov

# Run specific test file
poetry run pytest tests/test_verification_tool.py -v

# Run with coverage report
poetry run pytest --cov --cov-report=html
open htmlcov/index.html
```

---

## 🛠️ Development Workflow

### Database Migrations

```bash
# Create new migration
poetry run alembic revision --autogenerate -m "Description"

# Apply migrations
poetry run alembic upgrade head

# Rollback migration
poetry run alembic downgrade -1

# View migration history
poetry run alembic history
```

### Code Quality

```bash
# Format code
poetry run black src/ tests/

# Type checking
poetry run mypy src/

# Linting
poetry run ruff check src/
```

---

## 🎯 Phase 1 Exit Criteria

Before proceeding to Phase 2, verify:

- [ ] Can initiate call programmatically via API
- [ ] Agent successfully verifies test customer (2FA)
- [ ] Agent presents payment options from database
- [ ] Agent records payment arrangements
- [ ] Call history + transcripts stored in database
- [ ] All tests passing (>70% coverage)
- [ ] Docker Compose brings up full stack
- [ ] Can complete end-to-end call flow

---

## 📚 Documentation

- **[ARCHITECTURE.md](ARCHITECTURE.md)** - System architecture and design decisions
- **[IMPLEMENTATION_PLAN.md](docs/IMPLEMENTATION_PLAN.md)** - 5-phase implementation plan
- **[LATENCY_ANALYSIS.md](docs/LATENCY_ANALYSIS.md)** - Latency measurement methodology
- **[PERSISTENCE_STRATEGY.md](docs/PERSISTENCE_STRATEGY.md)** - PostgreSQL + JSONB strategy
- **[MIGRATION_FROM_ELEVENLABS.md](docs/MIGRATION_FROM_ELEVENLABS.md)** - ElevenLabs → Cartesia

---

## 🚧 Roadmap

### Phase 0: Proof of Concept (1 week) ⏳ Pending
- Minimal agent to validate Cartesia quality
- Real phone call testing
- Latency measurement
- GO/NO-GO decision

### Phase 1: Core Voice Agent (2 weeks) ✅ **CURRENT**
- 3 core tools (verification, options, payment)
- PostgreSQL database foundation
- FastAPI REST API
- Basic call history tracking

### Phase 2: Feature Parity (3 weeks) 📋 Next
- Complete tool suite (7-8 tools)
- Behavioral tactics system
- OpenAI negotiation guidance
- Socket.IO real-time events

### Phase 3: Admin Dashboard (2 weeks)
- React UI with TypeScript
- Live call monitoring
- Configuration management
- Dark/light theme system

### Phase 4: Innovation (3 weeks)
- Archer voice-first UI (optional)
- Demo-focused experience

### Phase 5: Production Ready (2 weeks)
- Security hardening
- Performance optimization
- Azure deployment
- Monitoring and alerts

---

## 🔒 Environment Variables

See [.env.example](.env.example) for complete list. Key variables:

```bash
# Required for Phase 1
DATABASE_URL=postgresql+asyncpg://...
CARTESIA_API_KEY=your_key
TWILIO_ACCOUNT_SID=your_sid
TWILIO_AUTH_TOKEN=your_token
```

---

## 🤝 Contributing

### Development Guidelines

1. **Branch naming**: `feature/description`, `fix/description`
2. **Commit messages**: Conventional commits format
3. **PR requirements**: Tests passing, >70% coverage, approved review
4. **Code style**: Black (Python)

---

## 📞 Support

- **Issues**: GitHub Issues
- **Documentation**: [docs/](docs/)
- **Architecture Questions**: See [ARCHITECTURE.md](ARCHITECTURE.md)

---

**Built with ❤️ by the Symend Team**

**Phase 1 Foundation Complete** - Ready for Phase 2 feature development.
