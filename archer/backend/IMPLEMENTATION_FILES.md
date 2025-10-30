# Cartesia Integration - Implementation Files Reference

## Files Modified

### 1. `/pyproject.toml`
**What changed**: Added websockets dependency
```toml
websockets = "^12.0"
```
**Why**: WebSocket client library for connecting to Cartesia

### 2. `/src/api/webhooks.py`
**Lines modified**: 68-84
**What changed**: TwiML generation updated to include `<Stream>` directive
```python
# OLD (lines 68-74):
twiml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
  <Say voice="alice">Connecting you to your Archer agent. Please hold.</Say>
  <!-- In production: connect to Cartesia voice connector -->
</Response>"""

# NEW (lines 68-84):
base_url = os.getenv("WEBHOOK_BASE_URL", "your-domain.ngrok.io")
websocket_url = f"wss://{base_url.replace('https://', '')}/ws/cartesia"

from twilio.twiml.voice_response import VoiceResponse
resp = VoiceResponse()
connect = resp.connect()
stream = connect.stream(url=websocket_url)
stream.parameter(name="call_sid", value=call_sid)
stream.parameter(name="customer_id", value=str(customer.id))
stream.parameter(name="customer_phone", value=from_number)

twiml = resp.to_xml()
```
**Why**: Instructs Twilio to stream audio to WebSocket endpoint

### 3. `/src/api/websockets.py` (NEW FILE)
**What it does**: WebSocket bridge between Twilio and Cartesia
**Key components**:
- `handle_cartesia_stream()` - Main WebSocket handler
- `_twilio_receive_loop()` - Receives from Twilio, forwards to Cartesia
- `_cartesia_receive_loop()` - Receives from Cartesia, forwards to Twilio
- Router registered at `/ws/cartesia`

**Audio flow**:
```
Twilio → Base64 mulaw → Normalize → Cartesia
Cartesia → Base64 audio → Twilio
```

### 4. `/src/agent/agent.py`
**Lines modified**: 149-274
**What changed**: Enhanced `handle_call()` method
```python
# NEW capabilities added:
- Real-time streaming support
- Tool execution callback registration
- context["tool_calls"] storage
- Conversation ID tracking
- Realtime session management
```
**Why**: Enables tool execution during live conversations

### 5. `/src/main.py`
**Lines modified**: 5, 26
**What changed**: WebSocket router registration
```python
# Line 5: Import added
from .api import calls, webhooks, websockets

# Line 26: Router included
app.include_router(websockets.router)
```
**Why**: Makes `/ws/cartesia` endpoint available

### 6. `/.env.example`
**Lines added**: 30-32
**What changed**: Added WebSocket configuration
```bash
WEBHOOK_BASE_URL=https://your-domain.ngrok.io
CARTESIA_WS_URL=wss://api.cartesia.ai/v1/stream
```
**Why**: Configuration for TwiML generation and Cartesia connection

## Files Created

### Documentation Files

1. **`/CARTESIA_INTEGRATION_SUMMARY.md`**
   - Complete implementation overview
   - Architecture flow diagram
   - Environment variables guide
   - Testing requirements
   - Known considerations

2. **`/TESTING_CHECKLIST.md`**
   - Step-by-step testing guide
   - Pre-testing setup instructions
   - 6 testing scenarios
   - Debugging guide
   - Common issues and solutions

3. **`/IMPLEMENTATION_FILES.md`** (this file)
   - Quick reference for all changes
   - File-by-file breakdown
   - Code snippets for key changes

## Environment Variables Required

Update your `.env` file with these values:

```bash
# Already exists in .env.example:
CARTESIA_API_KEY=your_actual_api_key
CARTESIA_VOICE_ID=your_actual_voice_id

# NEW - Add these:
WEBHOOK_BASE_URL=https://your-ngrok-url.ngrok.io
CARTESIA_WS_URL=wss://api.cartesia.ai/v1/stream
```

## Quick Start Commands

```bash
# 1. Install dependencies
poetry install

# 2. Start database
docker-compose up -d postgres

# 3. Run migrations
poetry run alembic upgrade head

# 4. Start application
poetry run uvicorn src.main:app --reload --host 0.0.0.0 --port 8000

# 5. In another terminal, start ngrok
ngrok http 8000

# 6. Update .env with ngrok URL and restart app
```

## Architecture Overview

```
┌─────────┐     ┌─────────┐     ┌──────────┐     ┌──────────┐
│ Caller  │────▶│ Twilio  │────▶│ Webhook  │────▶│ Database │
└─────────┘     └─────────┘     └──────────┘     └──────────┘
                     │                │
                     │ WebSocket      │ TwiML with
                     │ Stream         │ <Stream> URL
                     ▼                ▼
                ┌─────────────────────────┐
                │  /ws/cartesia handler   │
                │  (websockets.py)        │
                └─────────────────────────┘
                     │              │
          Twilio ◀───┤              ├───▶ Cartesia
          audio      │              │     WebSocket
                     │              │
                     ▼              ▼
                ┌────────────────────────┐
                │  Bidirectional Audio   │
                │  Twilio ⇄ Cartesia     │
                └────────────────────────┘
```

## Testing Status

- [ ] Dependencies installed (`poetry install`)
- [ ] Environment variables configured (`.env`)
- [ ] Database running and migrated
- [ ] Application starts without errors
- [ ] ngrok exposing application
- [ ] Twilio webhook configured
- [ ] Test call placed
- [ ] WebSocket connection established
- [ ] Audio streaming working
- [ ] Tools executing during conversation
- [ ] Call records saved to database

## Next Actions

1. **Configure Cartesia WebSocket URL**
   - Consult Cartesia documentation for actual endpoint
   - May need to call API to get signed URL
   - Update `CARTESIA_WS_URL` in `.env`

2. **Test Audio Format**
   - Verify Cartesia accepts mulaw format
   - If not, implement conversion in `websockets.py`
   - Add `audioop.ulaw2lin()` and `audioop.lin2ulaw()`

3. **Verify Tool Execution**
   - Check Cartesia SDK tool callback format
   - Update `agent.py` if needed for SDK-specific patterns
   - Monitor logs during test calls

4. **Production Hardening**
   - Add structured logging (structlog)
   - Implement reconnection logic
   - Add performance metrics
   - Set up monitoring/alerting

## Reference Files

- **ElevenLabs reference**: `/Users/deanskelton/Devlopment/symend/voice-agents/ai-banking-voice-agent/`
- **Twilio Media Streams docs**: https://www.twilio.com/docs/voice/twiml/stream
- **WebSocket RFC**: https://tools.ietf.org/html/rfc6455

## Support

For implementation questions:
1. Review `CARTESIA_INTEGRATION_SUMMARY.md`
2. Follow `TESTING_CHECKLIST.md`
3. Check application logs
4. Consult Cartesia documentation
5. Reference ElevenLabs implementation patterns
