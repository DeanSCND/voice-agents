# Cartesia Integration Testing Checklist

## Pre-Testing Setup

### 1. Install Dependencies
```bash
cd /Users/deanskelton/Devlopment/symend/voice-agents/archer/backend
poetry install
```

### 2. Configure Environment Variables
Copy and update `.env` file:
```bash
cp .env.example .env
# Then edit .env with your actual values:
```

**Required values:**
- `CARTESIA_API_KEY` - Your Cartesia API key
- `CARTESIA_VOICE_ID` - Voice ID for conversations
- `CARTESIA_WS_URL` - WebSocket endpoint (consult Cartesia docs)
- `WEBHOOK_BASE_URL` - Your ngrok URL (set after starting ngrok)
- `TWILIO_ACCOUNT_SID` - Your Twilio account SID
- `TWILIO_AUTH_TOKEN` - Your Twilio auth token
- `TWILIO_PHONE_NUMBER` - Your Twilio phone number
- `DATABASE_URL` - PostgreSQL connection string

### 3. Start Database
```bash
# If using Docker:
docker-compose up -d postgres

# Or start PostgreSQL locally
```

### 4. Run Database Migrations
```bash
poetry run alembic upgrade head
```

### 5. Start Application
```bash
poetry run uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

### 6. Expose with ngrok
```bash
ngrok http 8000
# Copy the HTTPS URL (e.g., https://abc123.ngrok.io)
```

### 7. Update Environment
```bash
# Update .env with ngrok URL:
WEBHOOK_BASE_URL=https://abc123.ngrok.io
# Restart the application
```

### 8. Configure Twilio Webhook
1. Go to Twilio Console
2. Navigate to Phone Numbers → Active Numbers
3. Click your phone number
4. Under "Voice & Fax", set:
   - **A CALL COMES IN**: Webhook
   - **URL**: `https://abc123.ngrok.io/webhooks/twilio/incoming`
   - **HTTP**: POST
5. Save

## Testing Scenarios

### Test 1: Basic Webhook Response
**Goal**: Verify Twilio webhook receives correct TwiML

```bash
# Make a test call to your Twilio number
# Check application logs for:
```

**Expected logs:**
```
INFO: Received Twilio webhook: CallSid=... From=... To=...
INFO: Created call record: call_id=...
INFO: Returning TwiML with Stream connection
```

**Verify TwiML includes:**
```xml
<Response>
  <Connect>
    <Stream url="wss://abc123.ngrok.io/ws/cartesia">
      <Parameter name="call_sid" value="CA..." />
      <Parameter name="customer_id" value="..." />
      <Parameter name="customer_phone" value="..." />
    </Stream>
  </Connect>
</Response>
```

### Test 2: WebSocket Connection
**Goal**: Verify Twilio connects to WebSocket endpoint

**Expected logs:**
```
INFO: twilio_websocket_accepted_for_cartesia
INFO: connecting_to_cartesia url=wss://api.cartesia.ai/v1/stream
INFO: cartesia_connected
INFO: twilio_stream_started stream_sid=MZ... call_sid=CA...
```

**Failure scenarios:**
- `ConnectionRefused`: Check `CARTESIA_WS_URL` is correct
- `401 Unauthorized`: Check `CARTESIA_API_KEY` is valid
- `Timeout`: Check network connectivity to Cartesia

### Test 3: Audio Streaming
**Goal**: Verify bidirectional audio flow

**Test steps:**
1. Call Twilio number
2. Listen for agent voice
3. Speak into phone
4. Verify agent responds

**Expected logs:**
```
DEBUG: Received media event from Twilio
DEBUG: Forwarding audio to Cartesia: user_audio_chunk
DEBUG: Received audio from Cartesia
DEBUG: Forwarding audio to Twilio: media event
```

**Failure scenarios:**
- No audio heard: Check audio format compatibility
- One-way audio: Check both receive loops are running
- Garbled audio: May need format conversion (mulaw ↔ PCM16)

### Test 4: Tool Execution
**Goal**: Verify tools are invoked during conversation

**Test conversation:**
```
Agent: "Hello, this is Archer. Can I help you today?"
Caller: "Yes, I need to verify my account."
Agent: "I can help with that. What's the last 4 digits of your account?"
Caller: "1234"
Agent: "And your postal code?"
Caller: "12345"
[Tool: verify_account should be called here]
```

**Expected logs:**
```
INFO: Tool called: verify_account
DEBUG: Tool args: {"account_last_4": "1234", "postal_code": "12345"}
DEBUG: Tool result: {"verified": true, "customer_name": "..."}
```

**Check database:**
```sql
SELECT * FROM calls WHERE call_sid = 'CA...';
-- Should see call record with outcome
```

### Test 5: Error Handling
**Goal**: Verify graceful error handling

**Test scenarios:**
1. **Invalid customer phone**: Call from unregistered number
   - Expected: Polite message, no crash
   
2. **Cartesia connection fails**: Stop Cartesia or use invalid URL
   - Expected: Error logged, WebSocket closed gracefully
   
3. **Mid-call disconnect**: Hang up during conversation
   - Expected: Cleanup logs, database updated

### Test 6: Database Recording
**Goal**: Verify call records are saved

**After test call:**
```sql
SELECT 
    call_sid,
    customer_id,
    direction,
    status,
    start_time,
    end_time,
    duration
FROM calls 
ORDER BY start_time DESC 
LIMIT 1;
```

**Expected:**
- Call record exists
- `call_sid` matches Twilio call
- `customer_id` links to customer
- `status` = 'completed' or 'in_progress'
- `start_time` and `end_time` recorded

## Debugging Guide

### Check Application Status
```bash
# Health check
curl http://localhost:8000/health

# API documentation
open http://localhost:8000/docs
```

### Monitor Logs in Real-Time
```bash
# Application logs
tail -f /path/to/logs/app.log

# Or watch console output with uvicorn
```

### Enable Debug Logging
Edit `src/api/websockets.py`:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Test WebSocket Manually
```python
import asyncio
import websockets

async def test_ws():
    uri = "ws://localhost:8000/ws/cartesia"
    async with websockets.connect(uri) as ws:
        print("Connected!")
        await ws.send('{"event": "test"}')
        response = await ws.recv()
        print(f"Response: {response}")

asyncio.run(test_ws())
```

### Check Twilio Debugger
1. Go to Twilio Console
2. Navigate to Monitor → Logs → Debugger
3. Find your recent call
4. Check for errors or warnings

### Verify Cartesia API
```bash
# Test Cartesia API key
curl -H "Authorization: Bearer $CARTESIA_API_KEY" \
     https://api.cartesia.ai/v1/voices

# Should return list of voices
```

## Common Issues & Solutions

### Issue: "No module named 'websockets'"
**Solution:**
```bash
poetry add websockets
poetry install
```

### Issue: "WEBHOOK_BASE_URL not set"
**Solution:**
```bash
# Add to .env
WEBHOOK_BASE_URL=https://your-ngrok-url.ngrok.io
```

### Issue: "Customer not found"
**Solution:**
```sql
-- Add test customer
INSERT INTO customers (phone_number, first_name, last_name, account_number, postal_code)
VALUES ('+1234567890', 'Test', 'Customer', '1234', '12345');
```

### Issue: "Cartesia connection refused"
**Solution:**
- Verify `CARTESIA_WS_URL` is correct
- Check Cartesia documentation for actual WebSocket endpoint
- May need signed URL from Cartesia API first

### Issue: "Audio not streaming"
**Solution:**
- Check audio format (may need mulaw ↔ PCM16 conversion)
- Verify Cartesia WebSocket message format
- Enable debug logging to see raw messages

### Issue: "Tools not executing"
**Solution:**
- Verify Cartesia SDK supports tool callbacks
- Check tool registration in `agent.py`
- Enable debug logging for tool execution

## Success Indicators

- [ ] Application starts without errors
- [ ] Webhook receives Twilio POST requests
- [ ] TwiML with `<Stream>` is returned
- [ ] WebSocket connection established
- [ ] Twilio connects to `/ws/cartesia`
- [ ] Cartesia WebSocket connection succeeds
- [ ] Audio flows Twilio → Cartesia
- [ ] Audio flows Cartesia → Twilio
- [ ] Agent voice is heard
- [ ] Caller speech is recognized
- [ ] Tools are executed
- [ ] Call records saved to database
- [ ] Call ends gracefully

## Next Steps After Testing

Once basic flow works:

1. **Optimize Audio Format**: Add mulaw ↔ PCM16 conversion if needed
2. **Enhanced Logging**: Add structured logging with context
3. **Error Recovery**: Implement reconnection logic
4. **Performance Monitoring**: Add metrics for latency and quality
5. **Production Hardening**: Add rate limiting, auth, monitoring
6. **Integration Tests**: Write automated tests for call flows
7. **Documentation**: Update with actual Cartesia endpoints used

## Support

If you encounter issues:
1. Check application logs
2. Review Twilio Debugger
3. Consult Cartesia documentation
4. Reference implementation: `ai-banking-voice-agent`
5. Review this checklist for common issues
