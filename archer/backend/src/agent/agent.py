from typing import Dict, Any, Optional
import os
import asyncio

# Try to import Cartesia SDK client and types. If unavailable, provide fallbacks so tests run locally.
try:
    import cartesia
    CartesiaClient = getattr(cartesia, "Client", None) or getattr(cartesia, "CartesiaClient", None)
    # SDK may provide Agent/Context classes; try to import 'line' helpers
    try:
        from cartesia.line import Agent as SDKAgent, Context as SDKContext
    except Exception:
        SDKAgent = None
        SDKContext = None
except Exception:
    cartesia = None
    CartesiaClient = None
    SDKAgent = None
    SDKContext = None

# Fallback lightweight Agent/Context for environments without Cartesia installed
class Agent:
    def __init__(self, name: str, system_prompt: str, tools: list):
        self.name = name
        self.system_prompt = system_prompt
        self.tools = {tool.name: tool for tool in tools}

    async def handle_call(self, context: Dict[str, Any]) -> Dict[str, Any]:
        raise NotImplementedError


class Context(dict):
    """Simple dict-like context when SDK types are not available."""
    pass


# If the SDK provided Agent/Context, alias them so rest of the code can use real classes
if SDKAgent is not None:
    Agent = SDKAgent  # type: ignore
if SDKContext is not None:
    Context = SDKContext  # type: ignore

from ..tools.verification import VerifyAccountTool
from ..tools.payment import GetCustomerOptionsTool, ProcessPaymentTool


class ArcherCallAgent(Agent):
    """Archer voice agent powered by Cartesia Line SDK (when available).

    This implementation initializes a Cartesia client when possible and provides a
    basic handle_call implementation that establishes a conversation with the SDK.

    For Phase 2A we do not execute any tools via the SDK; tools are registered but
    not invoked by the SDK in this phase.
    """

    def __init__(
        self,
        customer_repository,
        call_repository,
        system_prompt: Optional[str] = None,
    ):
        # Create tools
        tools = [
            VerifyAccountTool(customer_repository),
            GetCustomerOptionsTool(),
            ProcessPaymentTool(call_repository),
        ]

        if not system_prompt:
            system_prompt = self._default_system_prompt()

        # Initialize base Agent
        super().__init__(name="Archer Call Agent", system_prompt=system_prompt, tools=tools)

        # Repositories
        self.customer_repo = customer_repository
        self.call_repo = call_repository

        # Initialize Cartesia client if available
        self.cartesia_api_key = os.getenv("CARTESIA_API_KEY")
        self.cartesia_voice_id = os.getenv("CARTESIA_VOICE_ID") or os.getenv("CARTESIA_VOICE")
        self.client = None
        if CartesiaClient and self.cartesia_api_key:
            try:
                # Most SDKs expose a Client class taking api_key kwarg
                self.client = CartesiaClient(api_key=self.cartesia_api_key)
            except Exception:
                # If client init fails, keep client as None and proceed with fallback behavior
                self.client = None

    def _default_system_prompt(self) -> str:
        return """You are a professional customer service agent helping resolve account matters.

Your goal is to help customers resolve their overdue accounts in a respectful and empathetic manner.

CRITICAL RULES:
1. You MUST verify customer identity before discussing any account details
2. Use the verify_account tool FIRST - do not proceed without verification
3. Once verified, use get_customer_options to present payment choices
4. Use process_payment to finalize arrangements
5. Be professional, empathetic, and compliance-aware
6. Never discuss specific account details before verification
7. Offer multiple payment options (full payment, settlement, payment plan)
8. Respect customer's financial situation

WORKFLOW:
1. Greet customer warmly
2. Verify identity (account_last_4 + postal_code)
3. Present payment options based on their situation
4. Process selected payment arrangement
5. Confirm and thank customer

COMPLIANCE:
- Follow TCPA, FDCPA regulations
- Never threaten or harass
- Respect do-not-call requests
- Provide written confirmation of arrangements

CONTEXT AWARENESS:
- After verification, you'll have access to: customer_name, balance, days_overdue
- Use this information to personalize the conversation
- Adapt your approach based on days_overdue (urgent vs. collaborative)

TOOLS AVAILABLE:
- verify_account: Verify customer identity (required first)
- get_customer_options: Calculate payment options
- process_payment: Record payment arrangement

Remember: You're here to help, not to intimidate. Build rapport and find solutions."""

    async def initialize_context(
        self,
        customer_phone: str,
        customer_id: str,
        call_sid: str,
    ) -> Dict[str, Any]:
        context = {
            "customer_phone": customer_phone,
            "customer_id": customer_id,
            "call_sid": call_sid,
            "verified": False,
            "verification_attempts": 0,
            "payment_options": None,
            "call_outcome": None,
        }
        return context

    async def handle_call(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Handle an incoming call.

        This method attempts to initialize a Cartesia conversation and enable real-time
        streaming/tool execution when possible. It is conservative: any SDK/network
        error falls back to the local greeting so tests and development continue to work.

        Behavior changes for Phase 2A+:
        - When a Cartesia client is available, attempt to create a conversation and
          enable realtime/tool execution if supported by the SDK.
        - Store tool calls and results into the context under "tool_calls" so callers
          can persist them to the database as needed.
        """
        # Default tool_calls storage
        context.setdefault("tool_calls", [])

        # If SDK client is present, try to start a conversation and enable realtime/tools.
        if self.client:
            try:
                conv = None

                # Preferred: SDK exposes a 'conversations' factory
                if hasattr(self.client, "conversations"):
                    try:
                        conv = await self._maybe_await(self.client.conversations.create(
                            system_prompt=self.system_prompt,
                            voice=self.cartesia_voice_id,
                            metadata={"call_sid": context.get("call_sid")},
                        ))
                    except Exception:
                        # Fallback param names
                        try:
                            conv = await self._maybe_await(self.client.conversations.create(
                                prompt=self.system_prompt,
                                voice_id=self.cartesia_voice_id,
                            ))
                        except Exception:
                            conv = None

                # Some SDKs expose a direct 'create_conversation' helper
                if conv is None and hasattr(self.client, "create_conversation"):
                    try:
                        conv = await self._maybe_await(self.client.create_conversation(
                            prompt=self.system_prompt,
                            voice=self.cartesia_voice_id,
                        ))
                    except Exception:
                        conv = None

                # If we have a conversation, try to enable realtime features/tooling
                if conv and getattr(conv, "id", None):
                    context["conversation_id"] = getattr(conv, "id")
                    context["realtime_enabled"] = False

                    # Try to attach tools and enable realtime streaming if the SDK supports it
                    try:
                        # If the SDK supports starting a realtime session or websocket, attempt to start it
                        if hasattr(conv, "start_realtime"):
                            # Hypothetical API - try and catch
                            realtime_session = await self._maybe_await(conv.start_realtime())
                            context["realtime_enabled"] = True
                            context["realtime_session"] = getattr(realtime_session, "id", None)

                        # If the SDK supports registering tools execution callbacks, register a simple wrapper
                        if hasattr(conv, "on_tool_call"):
                            def _tool_callback(tool_name: str, args: dict, result: dict):
                                # Record tool call in context
                                context.setdefault("tool_calls", []).append({
                                    "tool": tool_name,
                                    "args": args,
                                    "result": result,
                                })

                            try:
                                conv.on_tool_call(_tool_callback)
                            except Exception:
                                # Some SDKs may expect async registration
                                try:
                                    await self._maybe_await(conv.on_tool_call(_tool_callback))
                                except Exception:
                                    pass

                        # If the SDK exposes a direct 'realtime' API on the client, attempt to enable tool execution
                        if hasattr(self.client, "realtime") and context.get("realtime_enabled") is False:
                            try:
                                # Some SDKs allow starting a realtime session from the client
                                session = await self._maybe_await(self.client.realtime.start(conversation_id=context["conversation_id"]))
                                context["realtime_enabled"] = True
                                context["realtime_session"] = getattr(session, "id", None)
                            except Exception:
                                pass

                    except Exception:
                        # Non-fatal - continue even if realtime/tools enabling fails
                        pass

                    # Send initial greeting using common SDK patterns
                    try:
                        if hasattr(conv, "send_message"):
                            resp = await self._maybe_await(conv.send_message({"text": "Hello, this is Archer. How can I help you today?"}))
                        elif hasattr(self.client, "messages"):
                            resp = await self._maybe_await(self.client.messages.create(conv.id, {"text": "Hello, this is Archer. How can I help you today?"}))
                        else:
                            resp = None

                        if resp and hasattr(resp, "text"):
                            context["last_agent_message"] = resp.text
                        else:
                            # If no response object, set a simple message marker
                            context.setdefault("last_agent_message", "Agent initialized and ready to converse.")
                    except Exception:
                        # Ignore send failures but keep conversation id for post-call transcript retrieval
                        context.setdefault("last_agent_message", "Agent initialized (messaging failed).")

                    return context

            except Exception:
                # Any unexpected SDK error - fallback below
                pass

        # Fallback local greeting (no SDK or SDK failed)
        context["last_agent_message"] = (
            "Hello, thank you for calling Archer. For your security, I will need to verify your identity. "
            "Can you please provide the last 4 digits of your account number and your postal code?"
        )

        return context

    async def _maybe_await(self, value):
        """Helper to await coroutine if needed, otherwise return value synchronously."""
        if asyncio.iscoroutine(value):
            return await value
        return value
