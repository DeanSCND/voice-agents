"""Customer repository using async SQLAlchemy 2.0 patterns."""

from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from ..models.database import Customer


class CustomerRepository:
    """Repository for customer data access."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, customer_id: str) -> Optional[Customer]:
        """Get customer by UUID."""
        result = await self.session.execute(
            select(Customer).where(Customer.id == customer_id)
        )
        return result.scalar_one_or_none()

    async def get_by_phone(self, phone_number: str) -> Optional[Customer]:
        """Get customer by phone number."""
        result = await self.session.execute(
            select(Customer).where(Customer.phone_number == phone_number)
        )
        return result.scalar_one_or_none()

    async def verify_identity(
        self, 
        phone_number: str, 
        account_last_4: str, 
        postal_code: str
    ) -> Optional[Customer]:
        """Verify customer identity with two-factor auth (account_last_4 + postal_code).

        Returns Customer if verification succeeds, None otherwise.
        """
        result = await self.session.execute(
            select(Customer).where(
                Customer.phone_number == phone_number,
                Customer.account_last_4 == account_last_4,
                Customer.postal_code == postal_code,
            )
        )
        return result.scalar_one_or_none()

    async def create_customer(self, customer_data: dict) -> Customer:
        """Create a new customer record."""
        customer = Customer(**customer_data)
        self.session.add(customer)
        await self.session.commit()
        await self.session.refresh(customer)
        return customer

    async def update_balance(
        self, 
        customer_id: str, 
        new_balance: float, 
        days_overdue: int,
    ) -> Optional[Customer]:
        """Update customer balance and days overdue."""
        customer = await self.get_by_id(customer_id)
        if customer:
            customer.balance = new_balance
            customer.days_overdue = days_overdue
            await self.session.commit()
            await self.session.refresh(customer)
        return customer
