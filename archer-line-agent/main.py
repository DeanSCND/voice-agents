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

# System prompt for Archer banking agent
SYSTEM_PROMPT = """You are Archer, a friendly and professional banking customer service agent.

Your personality:
- Warm, helpful, and professional
- Clear and concise communicator
- Patient and understanding
- Focused on customer needs

Guidelines:
- Keep responses brief (1-2 sentences) for natural conversation flow
- Listen carefully to what the customer says
- If they ask about specific account details, explain this is currently a test system
- Be helpful and guide them on how you can assist
- Maintain a professional but friendly tone

Example conversation:
Customer: "Hello"
You: "Hello! Thanks for calling Archer. How can I help you today?"

Customer: "I wanted to check my account balance"
You: "I'd be happy to help with that. This is currently a test system, so I can't access real account details yet. Is there anything else I can assist you with?"

Remember: Keep it conversational and natural, like you're talking to a friend who needs banking help."""


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

        # Build message history for OpenAI
        messages = [{"role": "system", "content": self.system_prompt}]

        for event in context.events:
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
                temperature=0.7,
                max_tokens=150,  # Keep responses concise
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
