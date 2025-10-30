# Archer Scripts

Utility scripts for development, deployment, and testing.

## Development Scripts

### start_dev.py - Unified Development Stack

**One-command startup for the complete Archer development environment.**

```bash
# Start everything (PostgreSQL, Redis, Backend, Ngrok)
python scripts/start_dev.py

# Or make executable and run directly
chmod +x scripts/start_dev.py
./scripts/start_dev.py
```

**What it does**:
1. ✅ Checks for `.env` file (warns if missing)
2. 🐳 Starts PostgreSQL + Redis via docker-compose
3. 🔄 Runs database migrations (Alembic)
4. 🚀 Starts FastAPI backend on port 8000
5. 🌐 Starts Ngrok tunnel for Twilio webhooks
6. 📊 Displays status panel with all URLs

**Services started**:
- **PostgreSQL**: localhost:5432 (database: archer_dev)
- **Redis**: localhost:6379 (cache/sessions)
- **Backend**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health
- **Ngrok**: https://xxxx.ngrok.io (public webhook URL)

**Graceful shutdown**:
- Press `Ctrl+C` to stop all services
- Cleans up processes, ports, and Docker containers

---

## Requirements

### System Dependencies

```bash
# macOS (Homebrew)
brew install python@3.11
brew install poetry
brew install docker
brew install ngrok

# Ubuntu/Debian
sudo apt install python3.11 python3-pip
pip install poetry
# Install Docker: https://docs.docker.com/engine/install/ubuntu/
# Install Ngrok: https://ngrok.com/download
```

### Python Dependencies

The startup script uses these optional libraries for better UX:
- `rich` - Beautiful terminal output (highly recommended)
- `requests` - HTTP client for Ngrok API

```bash
# Install globally or in your base environment
pip install rich requests
```

---

## Usage Examples

### First Time Setup

```bash
# 1. Clone repository
cd voice-agents

# 2. Configure environment
cp .env.example .env
# Edit .env with your credentials:
#   - CARTESIA_API_KEY
#   - TWILIO_ACCOUNT_SID
#   - TWILIO_AUTH_TOKEN

# 3. Install backend dependencies
cd archer/backend
poetry install

# 4. Start everything
cd ../..
python scripts/start_dev.py
```

### Daily Development

```bash
# Start the stack
python scripts/start_dev.py

# Backend auto-reloads on code changes
# Ngrok URL is displayed - update Twilio webhook

# Stop with Ctrl+C
```

### Manual Service Control

If you need to run services individually:

```bash
# Just PostgreSQL + Redis
docker-compose up -d postgres redis

# Just backend (requires DB running)
cd archer/backend
poetry run uvicorn src.main:app --reload --port 8000

# Just ngrok
ngrok http 8000
```

---

## Troubleshooting

### "Docker not found"
```bash
# Install Docker Desktop
# macOS: https://docs.docker.com/desktop/install/mac-install/
# Windows: https://docs.docker.com/desktop/install/windows-install/
```

### "Port 8000 already in use"
```bash
# Find and kill the process
lsof -ti :8000 | xargs kill -9

# Or let start_dev.py handle it (it auto-kills)
```

### "Poetry not found"
```bash
# Install Poetry
curl -sSL https://install.python-poetry.org | python3 -

# Or via Homebrew (macOS)
brew install poetry
```

### "Ngrok not found" (Optional)
```bash
# Install Ngrok
brew install ngrok

# Or download from https://ngrok.com/download

# Authenticate (first time)
ngrok config add-authtoken YOUR_TOKEN
```

### "Database migration failed"
```bash
# Run migrations manually
cd archer/backend
poetry run alembic upgrade head

# Check database connection
poetry run python -c "from src.models.database import engine; import asyncio; asyncio.run(engine.connect())"
```

### "Cannot connect to database"
```bash
# Check if PostgreSQL is running
docker-compose ps postgres

# Check logs
docker-compose logs postgres

# Restart PostgreSQL
docker-compose restart postgres
```

---

## Environment Variables

See `.env.example` for complete list. Key variables:

```bash
# Required for Phase 1
DATABASE_URL=postgresql+asyncpg://archer:archer_dev_pass@localhost:5432/archer_dev
REDIS_URL=redis://localhost:6379
CARTESIA_API_KEY=your_cartesia_api_key
TWILIO_ACCOUNT_SID=your_twilio_account_sid
TWILIO_AUTH_TOKEN=your_twilio_auth_token
TWILIO_PHONE_NUMBER=+1234567890

# Optional
LOG_LEVEL=info
ENVIRONMENT=development
```

---

## Development Workflow

### Typical Development Session

```bash
# 1. Start services
python scripts/start_dev.py

# 2. Wait for startup (5-10 seconds)
# You'll see:
#   ✓ PostgreSQL started
#   ✓ Redis started
#   ✓ Backend starting
#   ✓ Ngrok tunnel ready

# 3. Update Twilio webhook to Ngrok URL
# Copy the webhook URL from console output

# 4. Make code changes
# Backend auto-reloads on save

# 5. Test via API docs
# Open: http://localhost:8000/docs

# 6. Place test call to your Twilio number

# 7. Stop when done (Ctrl+C)
```

### Running Tests

```bash
# In a separate terminal (while services are running)
cd archer/backend
poetry run pytest --cov

# Or stop services and run tests standalone
docker-compose up -d postgres redis
poetry run pytest --cov
```

---

## Script Architecture

**Based on**: `ai-banking-voice-agent/scripts/start_dev_full.py`

**Key features**:
- ✅ Process group management for clean shutdown
- ✅ Port conflict detection and resolution
- ✅ Health checks for all services
- ✅ Graceful signal handling (SIGINT, SIGTERM)
- ✅ Cross-platform support (macOS, Linux, Windows)
- ✅ Rich terminal output (if available)
- ✅ Automatic cleanup on exit

**Process tree**:
```
start_dev.py (PID 1234)
├── docker-compose (postgres + redis)
├── uvicorn (PID 1235) - Backend
│   └── watchgod (auto-reload)
└── ngrok (PID 1236) - Tunnel
```

---

## Future Scripts (Coming in Phase 2+)

- `seed_test_data.py` - Create test customers and call records
- `deploy_prod.py` - Deploy to Azure (Phase 5)
- `test_call.py` - Simulate test calls (Phase 2)
- `sync_tools.py` - Sync tools with Cartesia (Phase 2)

---

## Support

- **Issues**: Report bugs in GitHub Issues
- **Documentation**: See main [README.md](../README.md)
- **Architecture**: See [ARCHITECTURE.md](../ARCHITECTURE.md)

---

**Built for Archer Voice Agent Phase 1**
