# Archer Line Agent - MVP Quickstart

## Goal

Get a simple conversational agent working to verify Cartesia Line integration.

**No tools, no database, no APIs** - just a friendly conversation to test the connection.

## What This MVP Does

```
Customer calls Twilio number
    ↓
Twilio routes to Line agent (deployed on Cartesia)
    ↓
Agent says: "Hello! Thanks for calling Archer. This is a test call. How are you doing today?"
    ↓
Customer talks
    ↓
Agent responds naturally
    ↓
Simple back-and-forth conversation
```

## Quick Deploy to Cartesia

### Step 1: Prepare Environment

```bash
cd archer-line-agent

# Create .env file
cp .env.example .env

# Edit .env - only need your Cartesia API key:
CARTESIA_API_KEY=sk_car_your_actual_key_here
```

### Step 2: Commit to Git

```bash
# From voice-agents root
git add archer-line-agent/
git commit -m "Add Archer Line agent MVP - simple conversation"
git push origin main
```

### Step 3: Deploy to Cartesia

**Option A: GitHub Integration**
1. Go to https://play.cartesia.ai/
2. Click "Create Agent"
3. Connect GitHub repository
4. Select repo: `voice-agents`
5. Set path: `archer-line-agent/`
6. Push to main auto-deploys

**Option B: CLI**
```bash
pip install cartesia-line
line login
line deploy
```

### Step 4: Set Environment Variable

In Cartesia dashboard:
- Go to agent → Environment Variables
- Add: `CARTESIA_API_KEY` = your key

### Step 5: Test in Cartesia Playground

1. In Cartesia dashboard, find "Test Call" button
2. Click to make test call
3. You should hear: "Hello! Thanks for calling Archer..."
4. Talk naturally - agent will respond

## Expected Conversation

**Agent**: "Hello! Thanks for calling Archer. This is a test call. How are you doing today?"

**You**: "Hi, I'm doing well"

**Agent**: "That's great to hear! Is there anything I can help you with today?"

**You**: "I wanted to check my balance"

**Agent**: "I'd be happy to help with that. This is currently a test call to verify our system is working correctly. Is there anything else I can assist you with?"

## What's Next

Once this MVP works:

✅ **Phase 1**: Simple conversation (THIS)
🔜 **Phase 2**: Add Twilio integration
🔜 **Phase 3**: Add tools (verify account, payment options)
🔜 **Phase 4**: Add backend API calls
🔜 **Phase 5**: Production deployment

## Troubleshooting

### "Line SDK not installed"
```bash
poetry install
# Or: pip install cartesia-line
```

### Deployment fails
- Check `main.py` is at root of `archer-line-agent/`
- Verify Python 3.11+ in pyproject.toml
- Ensure FastAPI app variable is named `app`

### Agent doesn't respond
- Check deployment status is "ready" in Cartesia
- Verify CARTESIA_API_KEY is set
- Review logs in Cartesia dashboard

### Can't hear anything
- Check your microphone/speaker permissions
- Try in Cartesia web playground first
- Verify browser allows microphone access

## File Structure (Minimal)

```
archer-line-agent/
├── main.py           # 120 lines - simple conversation
├── pyproject.toml    # 3 dependencies
├── .env.example      # Just API key
└── README.md
```

## Dependencies

```toml
cartesia-line = "^0.1.3"   # Line SDK
python-dotenv = "^1.2.1"   # Environment variables
fastapi = "^0.104.0"       # Web framework
```

That's it! No database, no complex tools, just conversation.

## Success Criteria

✅ Deploy completes successfully
✅ Health check returns 200 OK
✅ Test call connects
✅ Agent greets you
✅ You can have a natural conversation
✅ Agent responds appropriately

Once this works, we can add Twilio integration and tools in v2!
