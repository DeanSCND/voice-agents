# Archer Line Agent

Banking collections voice agent powered by Cartesia Line SDK.

## Overview

This is the Cartesia Line SDK implementation of the Archer voice agent. It handles voice conversations for banking collections with account verification, payment options, and payment processing capabilities.

## Features

- 🎯 **Account Verification** - Secure customer identity verification before discussing account details
- 💰 **Payment Options** - Calculate and present payment plans, settlements, and full payment options
- 📞 **Payment Processing** - Record and process payment arrangements
- 🔒 **Compliance** - TCPA and FDCPA compliant conversation flows
- 🤝 **Empathetic Communication** - Professional and respectful customer interactions

## Architecture

This Line agent works in tandem with the Twilio backend (in `../archer/backend/`):

- **Twilio Backend** - Handles call initiation, phone number management, and webhooks
- **Line Agent** (this project) - Handles AI conversation logic deployed to Cartesia

## Project Structure

```
archer-line-agent/
├── main.py              # Line agent entry point with FastAPI app
├── config.py            # Configuration and environment variables
├── pyproject.toml       # Poetry dependencies
├── tools/               # Agent tools (verification, payment)
├── repositories/        # Database repositories
└── models/             # Database models
```

## Setup

### Prerequisites

- Python 3.11+
- Poetry
- Cartesia account and API key
- PostgreSQL database (shared with Twilio backend)

### Installation

```bash
# Install dependencies
poetry install

# Copy environment template
cp .env.example .env

# Edit .env with your credentials
# - CARTESIA_API_KEY
# - DATABASE_URL
```

### Local Development

```bash
# Run the agent locally
poetry run python main.py

# Or run with uvicorn for FastAPI endpoints
poetry run uvicorn main:app --reload
```

## Deployment to Cartesia

### Via GitHub Integration

1. **Push to GitHub**:
   ```bash
   git add .
   git commit -m "Initial Archer Line agent"
   git push
   ```

2. **Link in Cartesia Platform**:
   - Go to https://play.cartesia.ai/
   - Create new agent or select existing
   - Connect GitHub repository
   - Select `archer-line-agent` directory (or configure monorepo path)
   - Every push to `main` branch will auto-deploy

### Via CLI

```bash
# Install Line CLI
pip install cartesia-line

# Deploy
line deploy
```

## Conversation Flow

1. **Greeting** - Agent introduces itself
2. **Verification** - Collect account_last_4 and postal_code
3. **Options** - Present payment options based on account status
4. **Processing** - Record selected payment arrangement
5. **Confirmation** - Thank customer and confirm next steps

## Tools Available to Agent

### `verify_account`
Verify customer identity using account number and postal code.

**Parameters**:
- `account_last_4` (str): Last 4 digits of account number
- `postal_code` (str): Customer's postal code

### `get_customer_options`
Calculate available payment options for verified customer.

**Returns**: Payment plans, settlement offers, full payment option

### `process_payment`
Record customer's selected payment arrangement.

**Parameters**:
- `payment_type` (str): 'full', 'settlement', or 'payment_plan'
- `amount` (float): Payment amount
- `schedule` (dict, optional): Payment plan schedule

## Integration with Twilio Backend

The Line agent shares the same PostgreSQL database as the Twilio backend:

- **Customer records** - Shared `customers` table
- **Call records** - `calls` table tracks all interactions
- **Tool execution** - Results saved to `tool_calls` table

## Environment Variables

```env
CARTESIA_API_KEY=sk_car_...           # Your Cartesia API key
CARTESIA_VOICE_ID=a0e99841...         # Voice ID for agent
DATABASE_URL=postgresql+asyncpg://... # Shared database
ENVIRONMENT=development|production
DEBUG=true|false
```

## Testing

### Test Locally
```bash
# Run the agent
poetry run python main.py

# Make a test call using Cartesia playground
# https://play.cartesia.ai/
```

### Test with Twilio
Once deployed to Cartesia:
1. Configure Twilio backend to connect to deployed agent
2. Call your Twilio number
3. Conversation handled by Line agent

## Troubleshooting

### Agent not receiving calls
- Check Line deployment status in Cartesia dashboard
- Verify webhook configuration in Twilio backend
- Check logs in Cartesia platform

### Database connection issues
- Verify DATABASE_URL is correct
- Ensure PostgreSQL is accessible from Cartesia platform
- Check firewall rules if using external database

### Tool execution failures
- Check database schema matches models
- Verify customer data exists for testing
- Review tool implementation in `tools/` directory

## Development Workflow

1. Make changes to `main.py`, tools, or configuration
2. Test locally with `poetry run python main.py`
3. Commit and push to GitHub
4. Auto-deployment triggers on Cartesia
5. Test via Cartesia playground or Twilio integration

## Support

- [Cartesia Line Documentation](https://docs.cartesia.ai/line)
- [Cartesia Discord](https://discord.gg/cartesia)
- [GitHub Issues](https://github.com/your-org/voice-agents/issues)

## License

Proprietary - Internal use only
