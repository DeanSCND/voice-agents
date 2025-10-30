"""
Archer Voice Agent - Simple Conversational MVP

Minimal Line SDK implementation to test basic conversation flow.
Echo-style implementation without LLM for initial testing.
"""
from typing import AsyncGenerator
from dotenv import load_dotenv

from line import (
    Bridge,
    CallRequest,
    ConversationContext,
    ReasoningNode,
    VoiceAgentApp,
    VoiceAgentSystem,
)
from line.events import AgentResponse, UserStoppedSpeaking, UserTranscriptionReceived

# Load environment variables
load_dotenv()

# Simple system prompt for testing
SYSTEM_PROMPT = """You are Archer, a friendly and professional banking customer service agent.

Keep the conversation simple and natural. You're here to have a pleasant conversation with the customer.

Guidelines:
- Be warm and professional
- Listen to what the customer says
- Respond naturally
- Keep responses concise (1-2 sentences)
- If they ask about account details, politely explain this is a test call
"""


class ArcherNode(ReasoningNode):
    """Simple conversational node for testing."""

    def __init__(self):
        super().__init__(
            system_prompt=SYSTEM_PROMPT,
            node_id="archer"
        )

    async def process_context(self, context: ConversationContext) -> AsyncGenerator[AgentResponse, None]:
        """Process conversation context and generate response."""
        latest_message = context.get_latest_user_transcript_message()

        # Simple canned responses for testing
        response = "Thank you for calling Archer. I'm here to help you with your banking needs. How can I assist you today?"

        if latest_message:
            message_lower = latest_message.lower()
            if "balance" in message_lower or "account" in message_lower:
                response = "I'd be happy to help with your account information. This is currently a test call to verify our system is working correctly."
            elif "hello" in message_lower or "hi" in message_lower:
                response = "Hello! Thanks for calling Archer. How can I help you today?"
            elif "help" in message_lower:
                response = "I can assist you with account information, payments, and general banking questions. What would you like help with?"
            elif "bye" in message_lower or "goodbye" in message_lower:
                response = "Thank you for calling Archer. Have a great day!"
            else:
                response = f"I understand you're asking about: {latest_message}. This is a test call to verify our voice system. Is there anything else I can help you with?"

        yield AgentResponse(content=response)


async def handle_new_call(system: VoiceAgentSystem, call_request: CallRequest):
    """Handle incoming call - simple conversation."""

    # Create conversation node
    node = ArcherNode()
    bridge = Bridge(node)
    system.with_speaking_node(node, bridge)

    # Route user speech to conversation
    bridge.on(UserTranscriptionReceived).map(node.add_event)

    # Handle conversation flow
    bridge.on(UserStoppedSpeaking).stream(node.generate).broadcast()

    # Start the system
    await system.start()

    # Send initial greeting
    await system.send_initial_message(
        "Hello! Thanks for calling Archer. This is a test call. How are you doing today?"
    )

    # Wait for conversation to complete
    await system.wait_for_shutdown()


# Create VoiceAgentApp
app = VoiceAgentApp(handle_new_call)

if __name__ == "__main__":
    app.run()
