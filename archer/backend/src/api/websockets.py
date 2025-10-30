import asyncio
import json
import base64
import os
import logging
from typing import Optional
from fastapi import WebSocket, APIRouter
import websockets
from websockets.exceptions import ConnectionClosed

from ..models.database import get_session
from ..repositories.call_repo import CallRepository
from ..repositories.customer_repo import CustomerRepository
from ..agent.agent import ArcherCallAgent

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ws", tags=["websockets"])


async def _cartesia_receive_loop(cartesia_ws: websockets.WebSocketClientProtocol, twilio_ws: WebSocket, stream_state: dict) -> None:
    """Receive audio/events from Cartesia and forward to Twilio."""
    logger.info("cartesia_receive_loop_started")
    try:
        async for message in cartesia_ws:
            # Cartesia may send JSON messages with audio base64 payloads
            try:
                if isinstance(message, bytes):
                    # If binary, assume raw audio chunk - encode to base64 for Twilio
                    audio_b64 = base64.b64encode(message).decode("utf-8")
                    if stream_state.get("stream_sid"):
                        tw_msg = {"event": "media", "streamSid": stream_state["stream_sid"], "media": {"payload": audio_b64}}
                        await twilio_ws.send_json(tw_msg)
                else:
                    data = json.loads(message)
                    # Handle known Cartesia message types (best-effort)
                    if data.get("type") == "audio":
                        audio_b64 = data.get("audio_base64") or data.get("audio")
                        if audio_b64 and stream_state.get("stream_sid"):
                            tw_msg = {"event": "media", "streamSid": stream_state["stream_sid"], "media": {"payload": audio_b64}}
                            await twilio_ws.send_json(tw_msg)
                    elif data.get("type") == "pong":
                        # ignore
                        pass
                    elif data.get("type") == "conversation_ack":
                        conv_id = data.get("conversation_id")
                        stream_state["conversation_id"] = conv_id
                    else:
                        logger.debug("cartesia_event", extra={"data": data})
            except json.JSONDecodeError:
                logger.warning("received_non_json_from_cartesia")
            except Exception as e:
                logger.exception("error_processing_cartesia_message: %s", str(e))
    except ConnectionClosed as e:
        logger.info("cartesia_ws_closed", extra={"code": e.code, "reason": e.reason})
    except Exception as e:
        logger.exception("cartesia_receive_loop_error", exc_info=e)
    finally:
        logger.info("cartesia_receive_loop_ended")


async def _twilio_receive_loop(twilio_ws: WebSocket, cartesia_ws: websockets.WebSocketClientProtocol, stream_state: dict) -> None:
    """Receive audio from Twilio and forward to Cartesia SDK WebSocket."""
    logger.info("twilio_receive_loop_started")
    try:
        while True:
            data = await twilio_ws.receive_json()
            event = data.get("event")

            if event == "connected":
                logger.info("twilio_connected_event")
            elif event == "start":
                start_payload = data.get("start", {})
                stream_sid = start_payload.get("streamSid")
                stream_state["stream_sid"] = stream_sid

                # Extract call_sid from stream params if provided
                call_sid = (
                    start_payload.get("callSid")
                    or start_payload.get("call_sid")
                    or start_payload.get("customParameters", {}).get("call_sid")
                )
                stream_state["call_sid"] = call_sid

                # Optionally register call mapping or load context
                logger.info("twilio_stream_started", extra={"stream_sid": stream_sid, "call_sid": call_sid})

            elif event == "media":
                media = data.get("media", {})
                payload = media.get("payload")
                if payload:
                    # Twilio sends base64 mulaw; Cartesia may expect PCM16 or other - for now pass through
                    try:
                        # Normalize by decoding then re-encoding
                        audio_bytes = base64.b64decode(payload)
                        normalized = base64.b64encode(audio_bytes).decode("utf-8")
                        msg = {"user_audio_chunk": normalized}
                        await cartesia_ws.send(json.dumps(msg))
                    except ConnectionClosed as e:
                        logger.info("cartesia_ws_closed_during_send", extra={"code": e.code})
                        break
                    except Exception as e:
                        logger.exception("error_sending_audio_to_cartesia", exc_info=e)

            elif event == "stop":
                logger.info("twilio_stream_stopped", extra={"call_sid": stream_state.get("call_sid")})
                # Close cartesia ws to signal end of stream
                try:
                    await cartesia_ws.close()
                except Exception:
                    pass
                break
            else:
                logger.debug("unknown_twilio_event", extra={"event": event})
    except Exception as e:
        logger.exception("twilio_receive_loop_error", exc_info=e)
    finally:
        logger.info("twilio_receive_loop_ended")


async def handle_cartesia_stream(websocket: WebSocket) -> None:
    """Main handler for /ws/cartesia endpoint. Accepts Twilio WebSocket and bridges to Cartesia SDK."""
    await websocket.accept()
    logger.info("twilio_websocket_accepted_for_cartesia")

    # Initialize Cartesia SDK client
    cartesia_api_key = os.getenv("CARTESIA_API_KEY")
    cartesia_voice_id = os.getenv("CARTESIA_VOICE_ID", "a0e99841-438c-4a64-b679-ae501e7d6091")

    # Import Cartesia SDK
    try:
        from cartesia import Cartesia
    except ImportError:
        logger.error("Cartesia SDK not installed")
        await websocket.close()
        return

    cartesia_client = None
    cartesia_ws = None

    try:
        # Create Cartesia client and TTS WebSocket connection
        logger.info("initializing_cartesia_client")
        cartesia_client = Cartesia(api_key=cartesia_api_key)

        # Create TTS WebSocket for real-time streaming
        logger.info("creating_cartesia_tts_websocket")
        cartesia_ws = cartesia_client.tts.websocket()

        stream_state = {
            "stream_sid": None,
            "call_sid": None,
            "conversation_id": None,
        }

        # Create receive loops
        cartesia_task = asyncio.create_task(_cartesia_receive_loop(cartesia_ws, websocket, stream_state))
        twilio_task = asyncio.create_task(_twilio_receive_loop(websocket, cartesia_ws, stream_state))

        done, pending = await asyncio.wait([cartesia_task, twilio_task], return_when=asyncio.FIRST_COMPLETED)

        for task in pending:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

        for task in done:
            if task.exception():
                logger.error("stream_task_exception", exc_info=task.exception())

    except ConnectionClosed as e:
        logger.info("cartesia_connection_closed_unexpectedly", extra={"code": e.code, "reason": e.reason})
    except Exception as e:
        logger.exception("handle_cartesia_stream_error", exc_info=e)
    finally:
        logger.info("cleaning_up_cartesia_handler")
        try:
            if cartesia_ws and cartesia_ws.state.name == 'OPEN':
                await cartesia_ws.close()
        except Exception:
            pass
        try:
            await websocket.close()
        except Exception:
            pass


# Expose route for FastAPI to include
@router.websocket("/cartesia")
async def cartesia_ws_endpoint(ws: WebSocket):
    await handle_cartesia_stream(ws)
