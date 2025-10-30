from typing import Dict, Any, Optional
from pydantic import BaseModel, Field

# Attempt to import Cartesia SDK Tool base classes; fall back to local implementations for tests.
try:
    from cartesia.line import Tool as CartesiaTool, ToolResult as CartesiaToolResult, Context as CartesiaContext
except Exception:
    CartesiaTool = None
    CartesiaToolResult = None
    CartesiaContext = None


# For now, create compatible base classes if SDK is not available
class ToolResult:
    """ToolResult compatible with Cartesia/Line SDK."""

    def __init__(self, success: bool, message: str, should_end_call: bool = False, data: Optional[Dict] = None):
        self.success = success
        self.message = message
        self.should_end_call = should_end_call
        self.data = data or {}


class Context(dict):
    """Context compatible with Cartesia/Line SDK."""

    pass


class Tool:
    """Base Tool class compatible with Cartesia/Line SDK."""

    name: str
    description: str

    async def execute(self, context: Context, **kwargs) -> ToolResult:
        raise NotImplementedError


# If SDK classes exist, alias them for compatibility
if CartesiaTool is not None:
    Tool = CartesiaTool  # type: ignore
if CartesiaToolResult is not None:
    ToolResult = CartesiaToolResult  # type: ignore
if CartesiaContext is not None:
    Context = CartesiaContext  # type: ignore


# Tool Parameters Schema
class VerifyAccountParams(BaseModel):
    account_last_4: str = Field(..., description="Last 4 digits of account number", max_length=4)
    postal_code: str = Field(..., description="Postal code for verification", max_length=10)


class VerifyAccountTool(Tool):
    """Two-factor authentication tool: account_last_4 + postal_code.

    Tracks failed attempts and ends call after max failures.
    Sets context["verified"] = True on success.
    """

    name = "verify_account"
    description = "Verify customer identity using account last 4 digits and postal code"

    def __init__(self, customer_repository):
        """Initialize with customer repository for database lookups."""
        self.customer_repo = customer_repository
        self.max_attempts = 2

    async def execute(self, context: Context, account_last_4: str, postal_code: str) -> ToolResult:
        """Execute verification.

        Args:
            context: Line SDK context with customer_phone
            account_last_4: Last 4 digits of account
            postal_code: Customer postal code

        Returns:
            ToolResult with success/failure and should_end_call flag
        """
        # Get customer phone from context
        customer_phone = context.get("customer_phone")
        if not customer_phone:
            return ToolResult(
                success=False,
                message="Customer phone number not available in context",
                should_end_call=True,
            )

        # Track failed attempts
        failed_attempts = context.get("verification_attempts", 0)

        # Verify identity via repository
        try:
            customer = await self.customer_repo.verify_identity(
                phone_number=customer_phone,
                account_last_4=account_last_4,
                postal_code=postal_code,
            )
        except Exception:
            # On unexpected errors, end the call for safety
            return ToolResult(
                success=False,
                message="An error occurred while verifying your identity. For security, I need to end this call. Please try again later.",
                should_end_call=True,
            )

        if customer:
            # Verification successful
            context["verified"] = True
            context["customer_id"] = str(getattr(customer, "id", ""))
            context["customer_name"] = getattr(customer, "name", "")
            # Ensure numeric types are serializable
            try:
                context["balance"] = float(getattr(customer, "balance", 0.0))
            except Exception:
                context["balance"] = 0.0
            context["days_overdue"] = getattr(customer, "days_overdue", 0)

            return ToolResult(
                success=True,
                message=f"Identity verified. Welcome back, {context['customer_name']}.",
                data={
                    "customer_id": context["customer_id"],
                    "balance": context["balance"],
                    "days_overdue": context["days_overdue"],
                },
            )
        else:
            # Verification failed
            failed_attempts += 1
            context["verification_attempts"] = failed_attempts

            if failed_attempts >= self.max_attempts:
                return ToolResult(
                    success=False,
                    message=(
                        "I'm sorry, I couldn't verify your identity. For security, I need to end this call. "
                        "Please call back with your account information ready."
                    ),
                    should_end_call=True,
                )
            else:
                remaining = self.max_attempts - failed_attempts
                plural = "s" if remaining > 1 else ""
                return ToolResult(
                    success=False,
                    message=(
                        f"The information provided doesn't match our records. You have {remaining} attempt{plural} remaining. "
                        "Please try again."
                    ),
                    data={"attempts_remaining": remaining},
                )


# Backwards-compatible simple verifier
def verify_customer(account_last_4: str, postal_code: str) -> bool:
    """Basic placeholder verification logic.

    Returns True if account_last_4 looks like 4 digits and postal_code is non-empty.
    """
    if not account_last_4 or len(account_last_4) != 4:
        return False
    if not postal_code:
        return False
    return True
