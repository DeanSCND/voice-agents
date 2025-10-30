import pytest
from types import SimpleNamespace
from unittest.mock import AsyncMock

from src.tools.verification import VerifyAccountTool, Context


@pytest.mark.asyncio
async def test_verify_account_success_sets_context_and_returns_data():
    # Arrange
    customer = SimpleNamespace(id=123, name="Jane Doe", balance=250.75, days_overdue=3)
    customer_repo = SimpleNamespace(verify_identity=AsyncMock(return_value=customer))

    tool = VerifyAccountTool(customer_repository=customer_repo)
    context = Context({"customer_phone": "+15551234"})

    # Act
    result = await tool.execute(context, account_last_4="1234", postal_code="90210")

    # Assert
    assert result.success is True
    assert "Welcome back" in result.message
    assert context.get("verified") is True
    assert context.get("customer_id") == "123"
    assert context.get("customer_name") == "Jane Doe"
    assert isinstance(context.get("balance"), float)
    assert context.get("balance") == 250.75
    assert context.get("days_overdue") == 3
    assert result.data == {
        "customer_id": "123",
        "balance": 250.75,
        "days_overdue": 3,
    }
    # verify repository called with expected params
    customer_repo.verify_identity.assert_awaited_once()
    customer_repo.verify_identity.assert_awaited_with(
        phone_number="+15551234", account_last_4="1234", postal_code="90210"
    )


@pytest.mark.asyncio
async def test_verify_account_failed_first_attempt_increments_attempts_and_allows_retry():
    # Arrange
    customer_repo = SimpleNamespace(verify_identity=AsyncMock(return_value=None))
    tool = VerifyAccountTool(customer_repository=customer_repo)
    context = Context({"customer_phone": "+15551234"})

    # Act
    result = await tool.execute(context, account_last_4="0000", postal_code="00000")

    # Assert
    assert result.success is False
    assert result.should_end_call is False
    assert context.get("verification_attempts") == 1
    # attempts_remaining should be 1 (max 2 - 1)
    assert result.data.get("attempts_remaining") == 1
    assert "remaining" in result.message
    customer_repo.verify_identity.assert_awaited_once()


@pytest.mark.asyncio
async def test_verify_account_failed_max_attempts_ends_call():
    # Arrange
    customer_repo = SimpleNamespace(verify_identity=AsyncMock(return_value=None))
    tool = VerifyAccountTool(customer_repository=customer_repo)
    # Simulate one prior failed attempt
    context = Context({"customer_phone": "+15551234", "verification_attempts": 1})

    # Act
    result = await tool.execute(context, account_last_4="0000", postal_code="00000")

    # Assert
    assert result.success is False
    assert result.should_end_call is True
    # verification_attempts should be incremented to max (2)
    assert context.get("verification_attempts") == 2
    assert "end this call" in result.message
    customer_repo.verify_identity.assert_awaited_once()


@pytest.mark.asyncio
async def test_verify_account_missing_customer_phone_fails_gracefully_and_does_not_call_repo():
    # Arrange
    # Repo that would raise if called; we assert it is not awaited
    verify_mock = AsyncMock()
    customer_repo = SimpleNamespace(verify_identity=verify_mock)
    tool = VerifyAccountTool(customer_repository=customer_repo)
    context = Context({})  # no customer_phone

    # Act
    result = await tool.execute(context, account_last_4="1234", postal_code="90210")

    # Assert
    assert result.success is False
    assert result.should_end_call is True
    assert "phone number not available" in result.message.lower()
    # ensure repository was not called
    verify_mock.assert_not_called()
    assert context.get("verified") is None
