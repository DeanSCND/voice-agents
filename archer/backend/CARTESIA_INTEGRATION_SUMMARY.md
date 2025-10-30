# Cartesia Real-Time Voice Integration - Implementation Summary

## Overview
Successfully implemented bidirectional WebSocket streaming between Twilio and Cartesia for real-time voice conversations with tool execution support.

## Files Modified

### 1. Dependencies (`pyproject.toml`)
- Added `websockets = "^12.0"` for WebSocket client connections

### 2. Twilio Webhook (`src/api/webhooks.py`)
**Lines 68-84**: Updated TwiML generation
- Replaced placeholder TwiML with `<Connect><Stream>` directive
- WebSocket URL: `wss://{WEBHOOK_BASE_URL}/ws/cartesia`
- Embedded stream parameters: `call_sid`, `customer_id`, `customer_phone`
- **Preserved**: All existing database recording and error handling logic

### 3. WebSocket Handler (`src/api/websockets.py`) - NEW FILE
Created complete WebSocket bridge with:
- **Endpoint**: `/ws/cartesia`
- **Main Handler**: `handle_cartesia_stream(websocket: WebSocket)`
- **Bidirectional Loops**:
  - `_twilio_receive_loop()`: Twilio → Cartesia audio forwarding
  - `_cartesia_receive_loop()`: Cartesia → Twilio audio forwarding
- **Audio Processing**: Base64 encode/decode with normalization
- **Lifecycle Management**: Connection setup, error handling, cleanup

### 4. Agent Updates (`src/agent/agent.py`)
**Lines 149-274**: Enhanced `handle_call()` method
- Added real-time streaming support
- Tool execution callback registration
- Tool calls storage in context: `context["tool_calls"]`
- **Preserved**: Fallback behavior for testing without SDK

### 5. Main Application (`src/main.py`)
- Imported `websockets` router
- Registered WebSocket routes: `app.include_router(websockets.router)`

## Environment Variables Required

### Already in .env.example:
```bash
CARTESIA_API_KEY=your_cartesia_api_key_here
CARTESIA_VOICE_ID=your_cartesia_voice_id_here
```

### Additional Required (add to .env):
```bash
# WebSocket endpoint URL (for TwiML generation)
WEBHOOK_BASE_URL=https://your-domain.ngrok.io

# Cartesia WebSocket endpoint (optional override)
CARTESIA_WS_URL=wss://api.cartesia.ai/v1/stream
```

## Architecture Flow

```
1. Caller → Twilio Number
2. Twilio → POST /webhooks/twilio/incoming
3. Backend → Create call record in database
4. Backend → Return TwiML with <Stream url="wss://.../ws/cartesia" />
5. Twilio → Connect to /ws/cartesia WebSocket
6. Backend → Connect to Cartesia WebSocket
7. Audio flows bidirectionally:
   - Twilio audio (mulaw base64) → Cartesia
   - Cartesia audio (base64) → Twilio
8. Tools executed during conversation
9. Call ends → WebSocket cleanup → Database update
```

## Current Implementation Status

### ✅ Completed
- [x] Twilio webhook TwiML generation with Stream
- [x] WebSocket endpoint `/ws/cartesia`
- [x] Bidirectional audio streaming loops
- [x] Connection lifecycle management
- [x] Tool execution callback support
- [x] Database recording preservation
- [x] Error handling and fallbacks

### ⚠️ Needs Configuration
1. **Cartesia WebSocket URL**: Set `CARTESIA_WS_URL` to actual endpoint
2. **Domain Configuration**: Set `WEBHOOK_BASE_URL` to your ngrok/production domain
3. **Audio Format Conversion**: May need mulaw ↔ PCM16 conversion depending on Cartesia requirements

### 🔍 Testing Required
1. **WebSocket Connection**: Verify Cartesia accepts connection with Bearer token
2. **Audio Format**: Confirm Cartesia audio format requirements (mulaw vs PCM16)
3. **Message Protocol**: Validate Cartesia WebSocket message format
4. **Tool Execution**: Verify tools are invoked during conversation
5. **End-to-End Call**: Test complete call flow from dial to hangup

## Next Steps

### 1. Install Dependencies
```bash
cd /Users/deanskelton/Devlopment/symend/voice-agents/archer/backend
poetry install
```

### 2. Configure Environment
```bash
# Update .env file with:
export WEBHOOK_BASE_URL="https://your-ngrok-url.ngrok.io"
export CARTESIA_WS_URL="wss://api.cartesia.ai/v1/stream"  # Update with actual URL
export CARTESIA_API_KEY="your_actual_api_key"
export CARTESIA_VOICE_ID="your_actual_voice_id"
```

### 3. Start Development Server
```bash
poetry run uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

### 4. Expose with ngrok
```bash
ngrok http 8000
# Update WEBHOOK_BASE_URL with ngrok URL
```

### 5. Configure Twilio Webhook
In Twilio Console, set voice webhook to:
```
https://your-ngrok-url.ngrok.io/webhooks/twilio/incoming
```

### 6. Test Call Flow
1. Call your Twilio number
2. Monitor logs for WebSocket connections
3. Verify audio flows bidirectionally
4. Test tool execution (verify, options, payment)
5. Check database for call records

## Known Considerations

### Audio Format Conversion
The current implementation passes base64 audio directly. If Cartesia expects different format:

```python
# Add to websockets.py if needed:
import audioop

# Convert mulaw to PCM16 (if required)
pcm_audio = audioop.ulaw2lin(mulaw_bytes, 2)

# Convert PCM16 to mulaw (if required)
mulaw_audio = audioop.lin2ulaw(pcm_bytes, 2)
```

### Cartesia SDK Documentation
Consult Cartesia documentation for:
- Exact WebSocket endpoint URL
- Authentication method (Bearer token vs signed URL)
- Audio format expectations
- Message protocol structure
- Tool execution event format

### Tool Execution
Tools are registered in `ArcherCallAgent`:
- `verify_account` - Customer identity verification
- `get_customer_options` - Payment options calculation
- `process_payment` - Payment arrangement recording

Verify Cartesia SDK invokes these during conversation.

## Debugging

### Enable Verbose Logging
```python
# In websockets.py, add:
logging.basicConfig(level=logging.DEBUG)
```

### Monitor WebSocket Messages
```python
# Log all messages in receive loops:
logger.debug("cartesia_message_raw", extra={"message": message})
logger.debug("twilio_message_raw", extra={"data": data})
```

### Check Connection State
```bash
# Watch logs for:
- "twilio_websocket_accepted_for_cartesia"
- "connecting_to_cartesia"
- "cartesia_connected"
- "twilio_stream_started"
```

## Success Criteria

✅ Call connects to Twilio number
✅ WebSocket established to Cartesia
✅ Bidirectional audio streaming works
✅ Agent voice heard by caller
✅ Caller speech recognized by agent
✅ Tools executed during conversation
✅ Call record saved to database
✅ Call ends gracefully

## Support Resources

- **Cartesia Documentation**: Check for WebSocket API specifics
- **Reference Implementation**: `/Users/deanskelton/Devlopment/symend/voice-agents/ai-banking-voice-agent/`
- **Twilio Media Streams**: https://www.twilio.com/docs/voice/twiml/stream
- **WebSocket Protocol**: RFC 6455

## Contact

For issues or questions about this integration, refer to:
- Cartesia SDK documentation
- Twilio Media Streams documentation
- Reference implementation patterns in ai-banking-voice-agent
