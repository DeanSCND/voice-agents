import pytest
from types import SimpleNamespace
from unittest.mock import AsyncMock

from src.tools.payment import (
    calculate_payment_options,
    GetCustomerOptionsTool,
    ProcessPaymentTool,
)
from src.tools.verification import Context


def test_calculate_payment_options():
    opts = calculate_payment_options(600)
    assert "full" in opts and "plan_monthly" in opts
    assert opts["full"] == 600.0
    assert opts["plan_monthly"] == 100.0


@pytest.mark.asyncio
async def test_get_customer_options_requires_verification():
    tool = GetCustomerOptionsTool()
    context = Context({"verified": False})

    result = await tool.execute(context)

    assert result.success is False
    assert "verify" in result.message.lower()


@pytest.mark.asyncio
async def test_get_customer_options_standard_customer():
    tool = GetCustomerOptionsTool()
    context = Context({"verified": True, "balance": 600, "days_overdue": 30, "customer_name": "John"})

    result = await tool.execute(context)

    assert result.success is True
    assert "payment_options" in context
    data = result.data
    # settlement should NOT be offered for <= 90 days overdue
    assert "full_payment" in data and "payment_plan" in data
    assert "settlement" not in data
    assert data["full_payment"]["amount"] == 600.0
    assert data["payment_plan"]["amount"] == round(600 / 6, 2)
    assert "$600.00" in result.message


@pytest.mark.asyncio
async def test_get_customer_options_overdue_customer_includes_settlement():
    tool = GetCustomerOptionsTool()
    context = Context({"verified": True, "balance": 1000, "days_overdue": 120, "customer_name": "Alice"})

    result = await tool.execute(context)

    assert result.success is True
    data = result.data
    assert "settlement" in data
    # Settlement should be 70% of balance (30% discount)
    assert data["settlement"]["amount"] == round(1000 * 0.7, 2)
    assert data["settlement"]["discount_percentage"] == 30
    assert "30%" in data["settlement"]["description"] or "$" in data["settlement"]["description"]
    assert "settlement" in result.message.lower() or "30%" in result.message


@pytest.mark.asyncio
async def test_process_payment_requires_verification():
    call_repo = SimpleNamespace(update_call_metadata=AsyncMock())
    tool = ProcessPaymentTool(call_repo)
    # not verified
    context = Context({"payment_options": {"full_payment": {"amount": 100.0}}})

    result = await tool.execute(context, payment_type="sms_link", option="full_payment")

    assert result.success is False
    assert "verify" in result.message.lower()


@pytest.mark.asyncio
async def test_process_payment_sms_link_records_metadata_and_returns_confirmation():
    update_mock = AsyncMock(return_value=None)
    call_repo = SimpleNamespace(update_call_metadata=update_mock)
    tool = ProcessPaymentTool(call_repo)

    options = {
        "full_payment": {"amount": 200.0, "description": "Pay full"},
        "payment_plan": {"amount": round(200.0 / 6, 2), "months": 6},
    }

    ctx = Context({
        "verified": True,
        "payment_options": options,
        "call_sid": "CALL123",
        "current_time": "2025-10-30T12:00:00Z",
        "customer_id": "cust_1",
    })

    result = await tool.execute(ctx, payment_type="sms_link", option="full_payment")

    assert result.success is True
    assert "text message" in result.message.lower()
    assert "$200.00" in result.message
    # Repository should have been awaited with call_sid and metadata
    expected_metadata = {
        "payment_arrangement": {
            "payment_type": "sms_link",
            "option": "full_payment",
            "amount": 200.0,
            "timestamp": "2025-10-30T12:00:00Z",
            "customer_id": "cust_1",
        }
    }
    update_mock.assert_awaited_once()
    update_mock.assert_awaited_with("CALL123", expected_metadata)

    assert result.data["recorded"] is True
    assert ctx.get("call_outcome") == "payment_arranged"
    assert ctx.get("payment_amount") == 200.0


@pytest.mark.asyncio
async def test_process_payment_plan_includes_months_in_message():
    update_mock = AsyncMock(return_value=None)
    call_repo = SimpleNamespace(update_call_metadata=update_mock)
    tool = ProcessPaymentTool(call_repo)

    options = {
        "payment_plan": {"amount": 50.0, "months": 12},
    }

    ctx = Context({
        "verified": True,
        "payment_options": options,
        "call_sid": "CALL456",
        "current_time": "2025-10-30T13:00:00Z",
        "customer_id": "cust_2",
    })

    result = await tool.execute(ctx, payment_type="payment_plan", option="payment_plan")

    assert result.success is True
    # message should mention months
    assert "12" in result.message
    assert "$50.00" in result.message
    update_mock.assert_awaited_once()
    update_mock.assert_awaited_with(
        "CALL456",
        {
            "payment_arrangement": {
                "payment_type": "payment_plan",
                "option": "payment_plan",
                "amount": 50.0,
                "timestamp": "2025-10-30T13:00:00Z",
                "customer_id": "cust_2",
            }
        },
    )
    assert result.data["option"] == "payment_plan"


@pytest.mark.asyncio
async def test_process_payment_bank_transfer_generates_transfer_confirmation():
    update_mock = AsyncMock(return_value=None)
    call_repo = SimpleNamespace(update_call_metadata=update_mock)
    tool = ProcessPaymentTool(call_repo)

    options = {"full_payment": {"amount": 750.0}}
    ctx = Context({
        "verified": True,
        "payment_options": options,
        "call_sid": "CALL789",
        "current_time": "2025-10-30T14:00:00Z",
        "customer_id": "cust_3",
    })

    result = await tool.execute(ctx, payment_type="bank_transfer", option="full_payment")

    assert result.success is True
    assert "bank transfer" in result.message.lower()
    assert "$750.00" in result.message
    update_mock.assert_awaited_once()
    update_mock.assert_awaited_with(
        "CALL789",
        {
            "payment_arrangement": {
                "payment_type": "bank_transfer",
                "option": "full_payment",
                "amount": 750.0,
                "timestamp": "2025-10-30T14:00:00Z",
                "customer_id": "cust_3",
            }
        },
    )
    assert ctx.get("call_outcome") == "payment_arranged"
    assert ctx.get("payment_amount") == 750.0
