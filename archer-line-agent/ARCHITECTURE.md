# Archer Line Agent - Architecture

## System Overview

The Archer voice agent system is split into two components:

```
┌─────────────────────────────────────────────────────────────┐
│                     Voice Agent System                       │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────────┐              ┌──────────────────┐    │
│  │  Twilio Backend  │◄────────────►│  Line Agent      │    │
│  │  (Orchestrator)  │              │  (AI Brain)      │    │
│  └──────────────────┘              └──────────────────┘    │
│         │                                   │               │
│         │                                   │               │
│         ▼                                   ▼               │
│  ┌──────────────────────────────────────────────────┐      │
│  │           Shared PostgreSQL Database              │      │
│  │  (customers, calls, tool_calls tables)           │      │
│  └──────────────────────────────────────────────────┘      │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

## Component Responsibilities

### Twilio Backend (`../archer/backend/`)

**Purpose**: Call orchestration and telephony management

**Responsibilities**:
- Receive incoming calls via Twilio webhooks
- Manage phone numbers and routing
- Create call records in database
- Generate TwiML to connect caller to Line agent
- Handle call status updates
- Provide REST API for call management

**Technology Stack**:
- FastAPI
- SQLAlchemy 2.0 (async)
- Twilio SDK
- PostgreSQL

### Line Agent (`./` - this directory)

**Purpose**: Conversational AI and business logic

**Responsibilities**:
- Handle voice conversation flow
- Execute account verification
- Calculate and present payment options
- Process payment arrangements
- Maintain compliance with regulations
- Log tool executions to database

**Technology Stack**:
- Cartesia Line SDK
- FastAPI (for health checks)
- SQLAlchemy 2.0 (shared models)
- PostgreSQL (shared database)

## Data Flow

### Inbound Call Flow

```
1. Customer Calls Twilio Number
   │
   ▼
2. Twilio sends POST to /webhooks/twilio/incoming
   │
   ▼
3. Twilio Backend:
   - Looks up customer by phone number
   - Creates call record in database
   - Returns TwiML with <Connect><Stream> to Line agent
   │
   ▼
4. Twilio establishes WebSocket to Line agent
   │
   ▼
5. Line Agent:
   - Receives call_request event
   - Initializes conversation with greeting
   - Begins verification flow
   │
   ▼
6. Customer Conversation:
   - Line agent listens (STT via Cartesia Ink)
   - Processes conversation logic
   - Responds (TTS via Cartesia Sonic)
   - Executes tools as needed
   │
   ▼
7. Tool Execution:
   - verify_account → checks database
   - get_customer_options → calculates offers
   - process_payment → records arrangement
   │
   ▼
8. Call Completion:
   - Line agent confirms arrangements
   - Thanks customer
   - Ends call
   │
   ▼
9. Twilio sends status callback
   │
   ▼
10. Twilio Backend:
    - Updates call record with duration
    - Sets call outcome
    - Stores final status
```

## Database Schema

### Shared Tables

Both components access the same PostgreSQL database:

#### `customers`
```sql
- id (UUID, primary key)
- phone_number (varchar, unique)
- name (varchar)
- account_last_4 (varchar)
- postal_code (varchar)
- balance (decimal)
- days_overdue (integer)
- segment (varchar)
- language (varchar)
- extra_data (jsonb)
- created_at, updated_at (timestamp)
```

#### `calls`
```sql
- id (UUID, primary key)
- call_sid (varchar, unique) - Twilio identifier
- customer_id (UUID, foreign key)
- call_type (varchar) - 'real_call', 'test'
- direction (varchar) - 'inbound', 'outbound'
- status (varchar) - 'in_progress', 'completed', 'failed'
- start_time, end_time (timestamp)
- duration_seconds (integer)
- conversation_id (varchar) - Line conversation ID
- outcome (varchar) - 'payment_scheduled', 'refused', etc.
- extra_data (jsonb)
- created_at (timestamp)
```

#### `tool_calls` (future)
```sql
- id (UUID, primary key)
- call_id (UUID, foreign key)
- tool_name (varchar)
- input_args (jsonb)
- result (jsonb)
- executed_at (timestamp)
```

## Tools Architecture

### Tool Pattern

All tools inherit from base `Tool` class:

```python
class Tool:
    name: str
    description: str

    async def execute(self, **kwargs) -> Dict[str, Any]:
        # Implementation
        pass
```

### Available Tools

#### 1. VerifyAccountTool
**Purpose**: Authenticate customer before discussing account details

**Input**:
```python
{
    "account_last_4": "1234",
    "postal_code": "T2P1J9"
}
```

**Output**:
```python
{
    "verified": True,
    "customer_name": "John Doe",
    "balance": 350.00,
    "days_overdue": 15
}
```

#### 2. GetCustomerOptionsTool
**Purpose**: Calculate available payment options

**Input**:
```python
{
    "balance": 350.00,
    "days_overdue": 15
}
```

**Output**:
```python
{
    "full_payment": 350.00,
    "settlement_offer": 280.00,  # 20% discount
    "payment_plans": [
        {"months": 3, "monthly": 120.00},
        {"months": 6, "monthly": 60.00}
    ]
}
```

#### 3. ProcessPaymentTool
**Purpose**: Record customer's selected payment arrangement

**Input**:
```python
{
    "call_sid": "CA123...",
    "payment_type": "payment_plan",
    "amount": 60.00,
    "schedule": {"months": 6}
}
```

**Output**:
```python
{
    "success": True,
    "confirmation_number": "CONF-12345",
    "next_due_date": "2025-11-30"
}
```

## Security & Compliance

### Data Protection
- Customer data encrypted at rest
- API keys stored in environment variables
- Database connections use SSL/TLS
- No PCI data stored (payment processing delegated)

### Regulatory Compliance
- **TCPA**: Obtain consent before automated calls
- **FDCPA**: No harassment, threats, or deception
- **Privacy**: Customer data access logged
- **Recording**: Call recordings with consent notification

### Access Control
- Twilio Backend: Internal network only
- Line Agent: Deployed on Cartesia platform
- Database: Whitelist IPs, strong credentials
- API Keys: Rotated regularly

## Deployment Architecture

```
┌─────────────────────────────────────────────────────┐
│                   Production Setup                   │
├─────────────────────────────────────────────────────┤
│                                                      │
│  Internet                                           │
│     │                                               │
│     ▼                                               │
│  ┌────────┐                                        │
│  │ Twilio │                                        │
│  │ Cloud  │                                        │
│  └────┬───┘                                        │
│       │                                            │
│       │ HTTPS Webhooks                            │
│       ▼                                            │
│  ┌─────────────────┐                              │
│  │ Twilio Backend  │  (Your server/cloud)         │
│  │ FastAPI + Nginx │                              │
│  └────────┬────────┘                              │
│           │                                        │
│           │ WebSocket                              │
│           ▼                                        │
│  ┌─────────────────┐                              │
│  │  Line Agent     │  (Cartesia Platform)         │
│  │  (Deployed)     │                              │
│  └────────┬────────┘                              │
│           │                                        │
│           │ Database Queries                       │
│           ▼                                        │
│  ┌─────────────────┐                              │
│  │   PostgreSQL    │  (Managed service)           │
│  │   Database      │                              │
│  └─────────────────┘                              │
│                                                      │
└─────────────────────────────────────────────────────┘
```

## Scaling Considerations

### Line Agent
- Auto-scales on Cartesia platform
- Handles thousands of concurrent calls
- Global distribution for low latency

### Twilio Backend
- Deploy behind load balancer
- Use horizontal scaling (multiple instances)
- Implement connection pooling for database

### Database
- Use managed PostgreSQL (AWS RDS, etc.)
- Enable read replicas for high traffic
- Implement caching layer (Redis) if needed

## Monitoring & Observability

### Metrics to Track
- **Call Volume**: Calls per hour/day
- **Success Rate**: Completed vs. failed calls
- **Average Duration**: Call length trends
- **Tool Usage**: Which tools are called most
- **Verification Rate**: % of successful verifications
- **Payment Rate**: % resulting in payment arrangements

### Logging
- Twilio Backend: Request/response logs
- Line Agent: Conversation transcripts (via Cartesia)
- Database: Audit trail of changes
- Errors: Centralized error tracking

### Alerting
- Failed deployments
- High error rates
- Database connection issues
- API rate limits exceeded

## Development Workflow

1. **Local Development**
   - Run Twilio backend locally
   - Test Line agent with Cartesia playground
   - Use shared dev database

2. **Testing**
   - Unit tests for tools
   - Integration tests for database operations
   - End-to-end tests with test phone numbers

3. **Deployment**
   - Push code to GitHub
   - Auto-deploy Line agent via GitHub integration
   - Manually deploy Twilio backend to cloud

4. **Monitoring**
   - Watch deployment logs
   - Monitor call metrics
   - Review conversation quality

## Future Enhancements

- [ ] Multi-language support
- [ ] Advanced analytics dashboard
- [ ] A/B testing for conversation flows
- [ ] Integration with payment gateways
- [ ] Automated follow-up scheduling
- [ ] Sentiment analysis
- [ ] Agent coaching based on call reviews
