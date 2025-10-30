import pytest
import pytest_asyncio
from datetime import datetime
from decimal import Decimal

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from src.models.database import Base
from src.repositories.customer_repo import CustomerRepository
from src.repositories.call_repo import CallRepository


DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest_asyncio.fixture(scope="module")
async def async_engine():
    engine = create_async_engine(DATABASE_URL, future=True)
    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def session(async_engine):
    async_session = sessionmaker(async_engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as session:
        yield session


@pytest.fixture
def customer_repo(session):
    return CustomerRepository(session)


@pytest.fixture
def call_repo(session):
    return CallRepository(session)


@pytest.mark.asyncio
async def test_create_and_get_customer(customer_repo):
    data = {
        "phone_number": "+15551234567",
        "name": "John Doe",
        "account_last_4": "1234",
        "postal_code": "A1B2C3",
        "balance": Decimal("150.75"),
        "days_overdue": 5,
        "segment": "premium",
        "language": "en",
        "extra_data": {"source": "test"},
    }

    customer = await customer_repo.create_customer(data)
    assert customer is not None
    assert customer.phone_number == data["phone_number"]
    assert customer.name == data["name"]
    # balance is stored as Decimal
    assert Decimal(customer.balance) == Decimal("150.75")

    fetched = await customer_repo.get_by_phone(data["phone_number"])
    assert fetched is not None
    assert fetched.id == customer.id


@pytest.mark.asyncio
async def test_verify_identity_success_and_failure(customer_repo):
    data = {
        "phone_number": "+15557654321",
        "name": "Jane Smith",
        "account_last_4": "9876",
        "postal_code": "99999",
        "balance": Decimal("0.00"),
        "days_overdue": 0,
        "segment": "standard",
        "language": "en",
        "extra_data": {},
    }

    customer = await customer_repo.create_customer(data)
    assert customer is not None

    verified = await customer_repo.verify_identity(
        data["phone_number"], data["account_last_4"], data["postal_code"]
    )
    assert verified is not None
    assert verified.id == customer.id

    wrong = await customer_repo.verify_identity(
        data["phone_number"], "0000", data["postal_code"]
    )
    assert wrong is None


@pytest.mark.asyncio
async def test_call_repository_create_get_and_transcript(call_repo, customer_repo):
    # create a customer to link the call to
    cust_data = {
        "phone_number": "+15559876543",
        "name": "Call Customer",
        "account_last_4": "5555",
        "postal_code": "11111",
        "balance": Decimal("10.00"),
        "days_overdue": 0,
        "segment": "standard",
        "language": "en",
        "extra_data": {},
    }
    customer = await customer_repo.create_customer(cust_data)

    call_data = {
        "call_sid": "SID123",
        "customer_id": customer.id,
        "call_type": "real_call",
        "direction": "outbound",
        "status": "in_progress",
        "start_time": datetime.utcnow(),
        "extra_data": {"initial": True},
    }

    call = await call_repo.create_call(call_data)
    assert call is not None
    assert call.call_sid == call_data["call_sid"]
    assert call.customer_id == customer.id

    fetched = await call_repo.get_call_by_sid(call_data["call_sid"])
    assert fetched is not None
    assert fetched.id == call.id

    # Add transcript entries and ensure sequence increments
    entry1 = await call_repo.add_transcript_entry(
        call.id,
        {
            "timestamp": datetime.utcnow(),
            "entry_type": "transcript",
            "speaker": "customer",
            "text": "Hello",
        },
    )
    assert entry1.sequence_number == 1

    entry2 = await call_repo.add_transcript_entry(
        call.id,
        {
            "timestamp": datetime.utcnow(),
            "entry_type": "transcript",
            "speaker": "agent",
            "text": "Hi there",
        },
    )
    assert entry2.sequence_number == 2


@pytest.mark.asyncio
async def test_update_call_extra_data_merges(call_repo, customer_repo):
    cust_data = {
        "phone_number": "+15550123456",
        "name": "Meta Customer",
        "account_last_4": "2222",
        "postal_code": "22222",
        "balance": Decimal("5.00"),
        "days_overdue": 0,
        "segment": "standard",
        "language": "en",
        "extra_data": {},
    }
    customer = await customer_repo.create_customer(cust_data)

    call_data = {
        "call_sid": "SID_META",
        "customer_id": customer.id,
        "call_type": "real_call",
        "direction": "outbound",
        "status": "in_progress",
        "start_time": datetime.utcnow(),
        "extra_data": {"keep": "old", "a": 1},
    }

    call = await call_repo.create_call(call_data)
    assert call.extra_data.get("keep") == "old"
    assert call.extra_data.get("a") == 1

    updated = await call_repo.update_call_extra_data(call.call_sid, {"a": 2, "new": "b"})
    assert updated is not None
    # Merged: 'a' overridden, 'keep' preserved, 'new' added
    assert updated.extra_data.get("a") == 2
    assert updated.extra_data.get("keep") == "old"
    assert updated.extra_data.get("new") == "b"
