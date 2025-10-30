from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime
import uuid

from ..models.database import get_session
from ..models.schemas import InitiateCallRequest, InitiateCallResponse, CallResponse
from ..repositories.customer_repo import CustomerRepository
from ..repositories.call_repo import CallRepository
from ..agent.agent import ArcherCallAgent

router = APIRouter(prefix="/api/v1/calls", tags=["calls"])

@router.post("/initiate", response_model=InitiateCallResponse)
async def initiate_call(
    request: InitiateCallRequest,
    session: AsyncSession = Depends(get_session)
):
    """Initiate an outbound call to a customer.
    
    This endpoint:
    1. Creates a call record in the database
    2. Initializes the BankingVoiceAgent with context
    3. Returns call_id and call_sid for tracking
    
    In production, this would trigger actual Twilio call via Line SDK.
    """
    # Initialize repositories
    customer_repo = CustomerRepository(session)
    call_repo = CallRepository(session)
    
    # Get customer by phone or ID
    customer = await customer_repo.get_by_phone(request.customer_phone)
    if not customer:
        # Try by id (UUID)
        try:
            customer = await customer_repo.get_by_id(str(request.customer_id))
        except Exception:
            customer = None
    
    if not customer:
        raise HTTPException(
            status_code=404, 
            detail=f"Customer not found: {request.customer_phone}"
        )
    
    # Generate call SID (in production, this comes from Twilio)
    call_sid = f"CA{uuid.uuid4().hex[:32]}"
    
    # Create call record
    call = await call_repo.create_call({
        "call_sid": call_sid,
        "customer_id": customer.id,
        "call_type": "real_call",
        "direction": "outbound",
        "status": "in_progress",
        "start_time": datetime.utcnow(),
        "extra_data": {}
    })
    
    # Initialize agent
    agent = ArcherCallAgent(customer_repo, call_repo)
    context = await agent.initialize_context(
        customer_phone=customer.phone_number,
        customer_id=str(customer.id),
        call_sid=call_sid
    )
    
    # In production: trigger Line SDK call here
    # For now, just return the call info
    
    return InitiateCallResponse(
        call_id=call.id,
        call_sid=call_sid,
        status="initiated",
        message=f"Call initiated to {customer.name} at {customer.phone_number}"
    )

@router.get("/{call_sid}", response_model=CallResponse)
async def get_call(
    call_sid: str,
    session: AsyncSession = Depends(get_session)
):
    """Get call details by call SID."""
    call_repo = CallRepository(session)
    call = await call_repo.get_call_by_sid(call_sid)
    
    if not call:
        raise HTTPException(status_code=404, detail="Call not found")
    
    return call

@router.get("/customer/{customer_id}")
async def get_customer_calls(
    customer_id: str,
    session: AsyncSession = Depends(get_session)
):
    """Get all calls for a customer."""
    call_repo = CallRepository(session)
    calls = await call_repo.get_customer_calls(customer_id)
    return {"calls": calls, "count": len(calls)}
