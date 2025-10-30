"""Payment tools for Line SDK - customer payment options and processing."""

from typing import Dict, Any, Optional
from pydantic import BaseModel, Field
from decimal import Decimal

# Line SDK imports (use same base classes as verification.py)
from .verification import Tool, ToolResult, Context

# If Cartesia SDK provides Tool/ToolResult/Context, they're aliased in verification.py so imports stay compatible


# Simple helper retained for backward compatibility/tests
def calculate_payment_options(balance: float) -> Dict[str, float]:
    """Return simple payment option calculations as placeholders.

    - full: pay full balance
    - settlement: 90% of balance
    - plan_monthly: simple 6-month plan
    """
    if balance <= 0:
        return {"full": 0.0, "settlement": 0.0, "plan_monthly": 0.0}

    full = round(balance, 2)
    settlement = round(balance * 0.9, 2)
    plan_monthly = round(balance / 6, 2)
    return {"full": full, "settlement": settlement, "plan_monthly": plan_monthly}


# Tool 1: Get Customer Payment Options
class GetCustomerOptionsParams(BaseModel):
    """Parameters for getting payment options.

    No external parameters are required; the tool uses values stored in the context.
    """
    pass


class GetCustomerOptionsTool(Tool):
    """Calculate and present payment options based on customer's balance and overdue status.

    Requires verification first. Calculates: full_payment, settlement (if >90 days overdue), payment_plan
    """

    name = "get_customer_options"
    description = "Get available payment options for the customer"

    async def execute(self, context: Context) -> ToolResult:
        """Execute option calculation.

        Args:
            context: Line SDK context with customer data

        Returns:
            ToolResult with payment options
        """
        # Check verification first
        if not context.get("verified"):
            return ToolResult(
                success=False,
                message="I need to verify your identity first before discussing payment options.",
            )

        # Get customer data from context
        balance = context.get("balance")
        days_overdue = context.get("days_overdue", 0)
        customer_name = context.get("customer_name", "there")

        if balance is None:
            return ToolResult(
                success=False,
                message="I'm having trouble accessing your account information. Please try again.",
            )

        # Ensure numeric
        try:
            balance_val = float(balance)
        except Exception:
            balance_val = 0.0

        # Calculate options
        options: Dict[str, Any] = {
            "full_payment": {
                "amount": round(balance_val, 2),
                "description": "Pay the full balance",
            }
        }

        # Settlement option if >90 days overdue
        if days_overdue and days_overdue > 90:
            settlement_amount = round(balance_val * 0.7, 2)  # 30% discount -> pay 70%
            options["settlement"] = {
                "amount": settlement_amount,
                "description": f"Settlement offer: Pay ${settlement_amount:.2f} (30% discount)",
                "discount_percentage": 30,
            }

        # Payment plan option (6 months)
        payment_plan_monthly = round(balance_val / 6, 2) if balance_val > 0 else 0.0
        options["payment_plan"] = {
            "amount": payment_plan_monthly,
            "description": f"Payment plan: ${payment_plan_monthly:.2f} per month for 6 months",
            "months": 6,
        }

        # Store in context for later use
        context["payment_options"] = options

        # Format natural speech response
        message = f"{customer_name}, here are your payment options: "
        message += f"You can pay the full balance of ${options['full_payment']['amount']:.2f}. "

        if "settlement" in options:
            message += (
                f"Since your account is {days_overdue} days overdue, we can offer a settlement of "
                f"${options['settlement']['amount']:.2f}, saving you 30%. "
            )

        message += (
            f"Or you can set up a payment plan of ${options['payment_plan']['amount']:.2f} per month for 6 months. "
        )
        message += "Which option works best for you?"

        return ToolResult(
            success=True,
            message=message,
            data=options,
        )


# Tool 2: Process Payment Arrangement
class ProcessPaymentParams(BaseModel):
    payment_type: str = Field(..., description="Type: 'sms_link', 'bank_transfer', or 'payment_plan'")
    option: str = Field(..., description="Option chosen: 'full_payment', 'settlement', or 'payment_plan'")


class ProcessPaymentTool(Tool):
    """Process payment arrangement and record in call metadata.

    Supports: sms_link, bank_transfer, payment_plan
    Records arrangement in call metadata via repository
    """

    name = "process_payment"
    description = "Process a payment arrangement for the customer"

    def __init__(self, call_repository):
        """Initialize with call repository for recording arrangements."""
        self.call_repo = call_repository

    async def execute(self, context: Context, payment_type: str, option: str) -> ToolResult:
        """Execute payment processing.

        Args:
            context: Line SDK context
            payment_type: 'sms_link', 'bank_transfer', 'payment_plan'
            option: 'full_payment', 'settlement', 'payment_plan'

        Returns:
            ToolResult with confirmation
        """
        # Check verification
        if not context.get("verified"):
            return ToolResult(
                success=False,
                message="I need to verify your identity first.",
            )

        # Get payment options from context
        options = context.get("payment_options")
        if not options or option not in options:
            return ToolResult(
                success=False,
                message="Please let me get your payment options first.",
            )

        # Get selected option details
        selected_option = options[option]
        try:
            amount = float(selected_option.get("amount", 0.0))
        except Exception:
            amount = 0.0

        # Record in call metadata
        call_sid = context.get("call_sid")
        recorded = False
        if call_sid:
            metadata = {
                "payment_arrangement": {
                    "payment_type": payment_type,
                    "option": option,
                    "amount": amount,
                    "timestamp": context.get("current_time", ""),
                    "customer_id": context.get("customer_id"),
                }
            }

            try:
                # call_repo expected to have async update_call_metadata
                await self.call_repo.update_call_metadata(call_sid, metadata)
                recorded = True
            except Exception:
                # Do not fail the tool if recording fails
                recorded = False

        # Generate confirmation message
        if payment_type == "sms_link":
            message = (
                f"Perfect! I'll send you a text message with a secure payment link for ${amount:.2f}. "
                "You'll receive it within the next few minutes. Is there anything else I can help you with?"
            )
        elif payment_type == "bank_transfer":
            message = (
                f"Great! I'll set up a bank transfer for ${amount:.2f}. "
                "You'll receive the transfer details via email shortly. Is there anything else?"
            )
        elif payment_type == "payment_plan":
            months = selected_option.get("months", 6)
            message = (
                f"Excellent! I've set up your payment plan of ${amount:.2f} per month for {months} months. "
                "You'll receive a confirmation email with all the details. Is there anything else I can help you with today?"
            )
        else:
            message = f"I've recorded your payment arrangement for ${amount:.2f}. You'll receive confirmation shortly."

        # Store outcome in context
        context["call_outcome"] = "payment_arranged"
        context["payment_amount"] = amount

        return ToolResult(
            success=True,
            message=message,
            data={
                "payment_type": payment_type,
                "option": option,
                "amount": amount,
                "recorded": recorded,
            },
        )
