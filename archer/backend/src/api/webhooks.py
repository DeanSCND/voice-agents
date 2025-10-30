from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime
import os

from ..models.database import get_session
from ..repositories.customer_repo import CustomerRepository
from ..repositories.call_repo import CallRepository

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


@router.post("/twilio/incoming")
async def twilio_incoming(request: Request, session: AsyncSession = Depends(get_session)):
    """Handle incoming Twilio call webhook.

    Expected form parameters: CallSid, From, To
    Creates a Call record and returns TwiML to connect caller to Cartesia/agent.
    """
    import logging
    logger = logging.getLogger(__name__)

    form = await request.form()
    call_sid = form.get("CallSid")
    from_number = form.get("From")
    to_number = form.get("To")

    logger.info(f"[WEBHOOK] Incoming call: CallSid={call_sid}, From={from_number}, To={to_number}")

    if not call_sid or not from_number:
        # Bad request from Twilio
        raise HTTPException(status_code=400, detail="Missing CallSid or From in webhook")

    customer_repo = CustomerRepository(session)
    call_repo = CallRepository(session)

    # Try to find customer by phone
    customer = await customer_repo.get_by_phone(from_number)

    # Create call record only if customer exists
    if not customer:
        # Create a lightweight TwiML response informing caller
        twiml = """<?xml version=\"1.0\" encoding=\"UTF-8\"?>
<Response>
  <Say voice=\"alice\">Thank you for calling. We couldn't match your phone number to an account. Please contact support for assistance.</Say>
  <Hangup/>
</Response>"""
        return Response(content=twiml, media_type="application/xml")

    # Create call record
    call_data = {
        "call_sid": call_sid,
        "customer_id": customer.id,
        "call_type": "real_call",
        "direction": "inbound",
        "status": "in_progress",
        "start_time": datetime.utcnow(),
        "extra_data": {"from": from_number, "to": to_number},
    }

    try:
        call = await call_repo.create_call(call_data)
        logger.info(f"[WEBHOOK] Call record created: {call.id}")
    except Exception as e:
        # If DB write fails, still return TwiML but mark failure
        logger.error(f"[WEBHOOK] Failed to create call record: {e}")
        twiml = """<?xml version=\"1.0\" encoding=\"UTF-8\"?>
<Response>
  <Say voice=\"alice\">We're experiencing temporary issues. Please try again later.</Say>
  <Hangup/>
</Response>"""
        return Response(content=twiml, media_type="application/xml")

    # Build WebSocket URL for media streaming
    # In production, use actual domain from environment variable
    base_url = os.getenv("WEBHOOK_BASE_URL", "your-domain.ngrok.io")
    websocket_url = f"wss://{base_url.replace('https://', '')}/ws/cartesia"

    # DEBUG: Log the WebSocket URL being generated
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"Generating TwiML with WebSocket URL: {websocket_url}")
    logger.info(f"Call SID: {call_sid}, Customer: {customer.name}")

    # Generate TwiML to connect call to WebSocket
    from twilio.twiml.voice_response import VoiceResponse
    resp = VoiceResponse()
    connect = resp.connect()
    stream = connect.stream(url=websocket_url)
    stream.parameter(name="call_sid", value=call_sid)
    stream.parameter(name="customer_id", value=str(customer.id))
    stream.parameter(name="customer_phone", value=from_number)

    twiml = resp.to_xml()
    logger.info(f"TwiML response: {twiml}")

    return Response(content=twiml, media_type="application/xml")


@router.post("/twilio/status")
async def twilio_status(request: Request, session: AsyncSession = Depends(get_session)):
    """Handle Twilio call status callbacks.

    Expected form parameters: CallSid, CallStatus, CallDuration (optional)
    Updates call status in database and sets end time/duration on completion.
    """
    form = await request.form()
    call_sid = form.get("CallSid")
    call_status = form.get("CallStatus")
    call_duration = form.get("CallDuration")

    if not call_sid or not call_status:
        raise HTTPException(status_code=400, detail="Missing CallSid or CallStatus")

    call_repo = CallRepository(session)

    # Map Twilio statuses to our internal statuses
    status_map = {
        "completed": "completed",
        "in-progress": "in_progress",
        "ringing": "ringing",
        "busy": "failed",
        "failed": "failed",
        "no-answer": "failed",
    }

    internal_status = status_map.get(call_status.lower(), call_status.lower())

    try:
        call = await call_repo.get_call_by_sid(call_sid)
        if not call:
            # Nothing to update
            return {"status": "not_found"}

        # If completed, update end time and duration
        if internal_status == "completed":
            try:
                duration = int(call_duration) if call_duration else None
            except Exception:
                duration = None
            end_time = datetime.utcnow()
            if duration is None and call.start_time:
                # compute approximate duration
                try:
                    duration = int((end_time - call.start_time).total_seconds())
                except Exception:
                    duration = None

            await call_repo.update_call_end(call_sid, end_time, duration or 0, outcome=call.outcome)
        else:
            # Update status field
            await call_repo.update_call_extra_data(call_sid, {"status": internal_status})
    except Exception:
        # Be tolerant of DB errors
        return {"status": "error"}

    return {"status": "updated"}
