from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, func
from sqlalchemy.orm import selectinload
from datetime import datetime

from ..models.database import Call, CallTranscriptEntry


class CallRepository:
    """Repository for call data access."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_call(self, call_data: dict) -> Call:
        """Create a new call record."""
        call = Call(**call_data)
        self.session.add(call)
        await self.session.commit()
        await self.session.refresh(call)
        return call

    async def get_call_by_sid(self, call_sid: str) -> Optional[Call]:
        """Get call by Twilio call SID."""
        result = await self.session.execute(
            select(Call).where(Call.call_sid == call_sid)
        )
        return result.scalar_one_or_none()

    async def get_call_with_transcript(self, call_sid: str) -> Optional[Call]:
        """Get call with all transcript entries eagerly loaded."""
        result = await self.session.execute(
            select(Call)
            .options(
                selectinload(Call.transcript_entries),
                selectinload(Call.customer)
            )
            .where(Call.call_sid == call_sid)
        )
        return result.scalar_one_or_none()

    async def get_customer_calls(
        self,
        customer_id: str,
        status: Optional[str] = None,
        limit: int = 50
    ) -> List[Call]:
        """Get all calls for a customer, ordered by most recent."""
        query = (
            select(Call)
            .where(Call.customer_id == customer_id)
            .order_by(desc(Call.start_time))
            .limit(limit)
        )

        if status:
            query = query.where(Call.status == status)

        result = await self.session.execute(query)
        return result.scalars().all()

    async def add_transcript_entry(
        self,
        call_id: str,
        entry_data: dict
    ) -> CallTranscriptEntry:
        """Add a transcript entry to a call."""
        # Get next sequence number
        result = await self.session.execute(
            select(func.max(CallTranscriptEntry.sequence_number))
            .where(CallTranscriptEntry.call_id == call_id)
        )
        max_seq = result.scalar() or 0

        entry = CallTranscriptEntry(
            call_id=call_id,
            sequence_number=max_seq + 1,
            **entry_data
        )
        self.session.add(entry)
        await self.session.commit()
        await self.session.refresh(entry)
        return entry

    async def update_call_extra_data(
        self,
        call_sid: str,
        extra_data: dict
    ) -> Optional[Call]:
        """Update call extra_data (for payment arrangements, etc.)."""
        call = await self.get_call_by_sid(call_sid)
        if call:
            # Merge with existing extra_data
            call.extra_data = {**(call.extra_data or {}), **extra_data}
            await self.session.commit()
            await self.session.refresh(call)
        return call

    async def update_call_end(
        self,
        call_sid: str,
        end_time: datetime,
        duration: int,
        outcome: Optional[str] = None
    ) -> Optional[Call]:
        """Update call with end time, duration, and outcome."""
        call = await self.get_call_by_sid(call_sid)
        if call:
            call.end_time = end_time
            call.duration_seconds = duration
            call.status = "completed"
            if outcome:
                call.outcome = outcome
            await self.session.commit()
            await self.session.refresh(call)
        return call
