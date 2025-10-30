"""
Archer Voice Agent - Conversational Banking Assistant

Uses OpenAI GPT-4o mini for natural, low-latency conversations.
"""
import os
from typing import AsyncGenerator, Optional
from dotenv import load_dotenv
from loguru import logger
from openai import AsyncOpenAI

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

# Set up logging
logger.remove()
logger.add(lambda msg: print(msg, end=""), level="INFO")

# System prompt for Archer banking agent - optimized for voice
SYSTEM_PROMPT = """You are Archer, a friendly banking agent.

CRITICAL: Keep ALL responses under 20 words. This is a voice call - be extremely brief.

Guidelines:
- Maximum 1-2 short sentences per response
- No long explanations
- Get to the point immediately
- Ask one question at a time

Examples:
Customer: "Hello"
You: "Hi! How can I help you today?"

Customer: "Check my balance"
You: "This is a test system, so I can't access real accounts yet. What else can I help with?"

Customer: "What services do you offer?"
You: "We help with accounts, payments, and general banking questions. What interests you?"

Remember: SHORT responses only. Voice conversations need speed."""


class ArcherNode(ReasoningNode):
    """Conversational banking agent using OpenAI GPT-4o mini."""

    def __init__(self, openai_client: Optional[AsyncOpenAI] = None):
        super().__init__(
            system_prompt=SYSTEM_PROMPT,
            node_id="archer"
        )
        self.client = openai_client
        self.model = "gpt-4o-mini"
        logger.info(f"ArcherNode initialized with model: {self.model}")

    async def process_context(self, context: ConversationContext) -> AsyncGenerator[AgentResponse, None]:
        """Process conversation context and stream responses from OpenAI."""

        if not context.events:
            logger.info("No messages to process")
            return

        # Get the latest user message for logging
        user_message = context.get_latest_user_transcript_message()
        if user_message:
            logger.info(f'🧠 Processing user message: "{user_message}"')

        # Build message history for OpenAI (limit to last 10 turns for speed)
        messages = [{"role": "system", "content": self.system_prompt}]

        # Only keep recent conversation history to reduce latency
        recent_events = context.events[-20:] if len(context.events) > 20 else context.events

        for event in recent_events:
            if hasattr(event, 'transcript') and event.transcript:
                messages.append({
                    "role": "user",
                    "content": event.transcript
                })
            elif hasattr(event, 'content') and event.content:
                messages.append({
                    "role": "assistant",
                    "content": event.content
                })

        # Stream response from OpenAI
        if not self.client:
            # Fallback canned response if no API key
            logger.warning("No OpenAI client - using canned response")
            yield AgentResponse(content="Thank you for calling Archer. I'm here to help with your banking needs. How can I assist you today?")
            return

        try:
            stream = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.3,  # Lower for faster, more consistent responses
                max_tokens=60,    # Shorter for voice - reduce latency
                presence_penalty=0.6,  # Encourage brevity
                stream=True
            )

            full_response = ""
            async for chunk in stream:
                if chunk.choices[0].delta.content:
                    content = chunk.choices[0].delta.content
                    full_response += content
                    yield AgentResponse(content=content)

            logger.info(f'💬 Agent response: "{full_response}"')

        except Exception as e:
            logger.error(f"OpenAI API error: {e}")
            yield AgentResponse(content="I'm having trouble processing that right now. Could you please try again?")


async def handle_new_call(system: VoiceAgentSystem, call_request: CallRequest):
    """Handle incoming call with OpenAI-powered conversation."""

    logger.info(f"📞 Starting call from {call_request.from_} to {call_request.to}")

    # Initialize OpenAI client if API key is available
    openai_api_key = os.getenv("OPENAI_API_KEY")
    openai_client = AsyncOpenAI(api_key=openai_api_key) if openai_api_key else None

    if not openai_client:
        logger.warning("⚠️ OPENAI_API_KEY not set - using fallback responses")

    # Create conversation node
    node = ArcherNode(openai_client=openai_client)
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
        "Hello! Thanks for calling Archer. How can I help you today?"
    )

    logger.info("✅ Call session started")

    # Wait for conversation to complete
    await system.wait_for_shutdown()

    logger.info("📴 Call ended")


# Create VoiceAgentApp
app = VoiceAgentApp(handle_new_call)

if __name__ == "__main__":
    app.run()
