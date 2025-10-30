"""
Archer Voice Agent - Simple Conversational MVP

Minimal Line SDK implementation to test basic conversation flow.
No tools, no database, no API calls - just conversation.
"""
import os
from fastapi import FastAPI
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Line SDK imports
try:
    from line import LineSystem, CallRequest
    from line.nodes import TalkingNode
    from line.bridges import Bridge
    from line.events import UserTranscriptionReceived, UserStoppedSpeaking, UserStartedSpeaking
except ImportError:
    print("Warning: Line SDK not installed. Install with: pip install cartesia-line")
    LineSystem = None

# FastAPI app for Line deployment
app = FastAPI(
    title="Archer Line Agent - MVP",
    description="Simple conversational voice agent (no tools)",
    version="0.1.0"
)

# Simple system prompt for testing
SYSTEM_PROMPT = """You are Archer, a friendly and professional banking customer service agent.

Keep the conversation simple and natural. You're here to have a pleasant conversation with the customer.

Guidelines:
- Be warm and professional
- Listen to what the customer says
- Respond naturally
- Keep responses concise (1-2 sentences)
- If they ask about account details, politely explain this is a test call

Example conversation:
Customer: "Hello"
You: "Hello! Thanks for calling. How can I help you today?"

Customer: "I wanted to check my account balance"
You: "I'd be happy to help with that. This is currently a test call to verify our system is working correctly. Is there anything else I can assist you with?"
"""

# Initialize Line system
if LineSystem:
    system = LineSystem()

    @system.handle("new_call")
    async def handle_new_call(call_request: CallRequest):
        """Handle incoming call - simple conversation."""

        # Create conversation node
        conversation_node = TalkingNode(
            system_prompt=SYSTEM_PROMPT,
        )

        # Set up bridge for event routing
        conversation_bridge = Bridge(conversation_node)
        system.with_speaking_node(conversation_node, bridge=conversation_bridge)

        # Route user speech to conversation
        conversation_bridge.on(UserTranscriptionReceived).map(conversation_node.add_event)

        # Handle conversation flow with interruption support
        (
            conversation_bridge.on(UserStoppedSpeaking)
            .interrupt_on(UserStartedSpeaking, handler=conversation_node.on_interrupt_generate)
            .stream(conversation_node.generate)
            .broadcast()
        )

        # Start the system
        await system.start()

        # Send initial greeting
        await system.send_initial_message(
            "Hello! Thanks for calling Archer. This is a test call. How are you doing today?"
        )

        # Wait for conversation to complete
        await system.wait_for_shutdown()


@app.get("/health")
async def health_check():
    """Health check endpoint for Line platform."""
    return {
        "status": "healthy",
        "agent": "archer-mvp",
        "version": "0.1.0"
    }


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "agent": "Archer MVP",
        "description": "Simple conversational agent (no tools)",
        "status": "ready"
    }


def main():
    """Start the Line agent system."""
    if LineSystem:
        system.start()
    else:
        print("Line SDK not available. Install: pip install cartesia-line")


if __name__ == "__main__":
    main()
