# Backend API Specification for Line Agent Tools

The Line agent needs these API endpoints in the Twilio backend (`../archer/backend/`) to execute tools without database access.

## Architecture

```
┌──────────────────┐                    ┌──────────────────┐
│   Line Agent     │  HTTPS Requests    │ Twilio Backend   │
│   (Cartesia)     │ ─────────────────► │ (Your Server)    │
│                  │                    │                  │
│  API Tools:      │                    │  API Endpoints:  │
│  - verify        │                    │  - /api/v1/tools/│
│  - get_options   │                    │    verify-account│
│  - process       │                    │    get-options   │
│                  │                    │    process-payment│
│                  │                    │                  │
│  (No database!)  │                    │  (Has database)  │
└──────────────────┘                    └──────────────────┘
                                                  │
                                                  ▼
                                        ┌──────────────────┐
                                        │   PostgreSQL     │
                                        │   Database       │
                                        └──────────────────┘
```

## Required API Endpoints

### 1. Verify Account

**Endpoint**: `POST /api/v1/tools/verify-account`

**Purpose**: Verify customer identity

**Request Body**:
```json
{
  "account_last_4": "1234",
  "postal_code": "T2P1J9",
  "phone_number": "+14036193821"  // optional
}
```

**Success Response (200)**:
```json
{
  "verified": true,
  "customer_id": "92b7caea-1b60-4a71-9c59-f025935cf4d9",
  "customer_name": "Dean Skelton",
  "balance": 350.00,
  "days_overdue": 15,
  "segment": "standard"
}
```

**Failure Response (404)**:
```json
{
  "verified": false,
  "error": "Account not found or verification failed"
}
```

**Implementation Notes**:
- Look up customer by phone_number (if provided)
- Verify account_last_4 and postal_code match
- Return customer details if verified
- Never return details if verification fails (security!)

---

### 2. Get Payment Options

**Endpoint**: `POST /api/v1/tools/get-options`

**Purpose**: Calculate available payment options

**Request Body**:
```json
{
  "customer_id": "92b7caea-1b60-4a71-9c59-f025935cf4d9",  // optional
  "balance": 350.00,        // optional
  "days_overdue": 15        // optional
}
```

**Success Response (200)**:
```json
{
  "full_payment": {
    "amount": 350.00,
    "description": "Pay the full balance today"
  },
  "settlement_offer": {
    "amount": 280.00,
    "discount_percent": 20,
    "description": "One-time settlement (20% discount)"
  },
  "payment_plans": [
    {
      "months": 3,
      "monthly_payment": 120.00,
      "total": 360.00,
      "description": "3 monthly payments of $120"
    },
    {
      "months": 6,
      "monthly_payment": 60.00,
      "total": 360.00,
      "description": "6 monthly payments of $60"
    }
  ]
}
```

**Implementation Notes**:
- If customer_id provided, look up balance and days_overdue
- Calculate settlement based on days_overdue (more overdue = bigger discount)
- Generate 2-3 payment plan options
- Add small interest for payment plans if applicable

---

### 3. Process Payment

**Endpoint**: `POST /api/v1/tools/process-payment`

**Purpose**: Record customer's payment arrangement

**Request Body**:
```json
{
  "customer_id": "92b7caea-1b60-4a71-9c59-f025935cf4d9",
  "call_sid": "CA5405b85ea222c20a55e0ef626da3afe6",
  "payment_type": "payment_plan",  // "full", "settlement", "payment_plan"
  "amount": 60.00,
  "schedule": {                     // for payment_plan only
    "months": 6,
    "start_date": "2025-11-30"
  }
}
```

**Success Response (200)**:
```json
{
  "success": true,
  "confirmation_number": "CONF-20251030-12345",
  "payment_type": "payment_plan",
  "amount": 60.00,
  "next_due_date": "2025-11-30",
  "message": "Payment arrangement confirmed. First payment of $60 due on 2025-11-30."
}
```

**Failure Response (400)**:
```json
{
  "success": false,
  "error": "Invalid payment type or amount"
}
```

**Implementation Notes**:
- Create record in database (payment_arrangements table)
- Update call record with outcome
- Generate unique confirmation number
- Calculate next due date
- Send confirmation email/SMS (future enhancement)

---

## Security Considerations

### Authentication
Line agent will call these endpoints from Cartesia's platform. Options:

**Option 1: API Key (Simple)**
```python
# In Line agent
headers = {"X-API-Key": os.getenv("BACKEND_API_KEY")}
response = await client.post(url, json=data, headers=headers)

# In Twilio backend
@app.middleware("http")
async def verify_api_key(request: Request, call_next):
    api_key = request.headers.get("X-API-Key")
    if api_key != os.getenv("BACKEND_API_KEY"):
        return JSONResponse({"error": "Unauthorized"}, status_code=401)
    return await call_next(request)
```

**Option 2: Call SID Verification**
```python
# Use Twilio's call SID as authentication
# Only accept requests for active calls
```

### Rate Limiting
- Limit requests per IP/API key
- Prevent abuse from malicious actors

### Input Validation
- Validate all inputs before database queries
- Prevent SQL injection
- Sanitize phone numbers, postal codes

---

## Example Implementation

Create file: `archer/backend/src/api/tools.py`

```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from ..models.database import get_session
from ..repositories.customer_repo import CustomerRepository
from ..repositories.call_repo import CallRepository

router = APIRouter(prefix="/api/v1/tools", tags=["tools"])

class VerifyAccountRequest(BaseModel):
    account_last_4: str
    postal_code: str
    phone_number: str | None = None

@router.post("/verify-account")
async def verify_account(
    request: VerifyAccountRequest,
    session: AsyncSession = Depends(get_session)
):
    """Verify customer account."""
    customer_repo = CustomerRepository(session)

    # Find customer by phone if provided
    if request.phone_number:
        customer = await customer_repo.get_by_phone(request.phone_number)
    else:
        # Search by account_last_4 and postal_code
        customer = await customer_repo.find_by_verification(
            request.account_last_4,
            request.postal_code
        )

    if not customer:
        raise HTTPException(status_code=404, detail="Account not found")

    # Verify credentials match
    if (customer.account_last_4 != request.account_last_4 or
        customer.postal_code.upper() != request.postal_code.upper()):
        raise HTTPException(status_code=404, detail="Verification failed")

    return {
        "verified": True,
        "customer_id": str(customer.id),
        "customer_name": customer.name,
        "balance": float(customer.balance),
        "days_overdue": customer.days_overdue,
        "segment": customer.segment
    }

# Implement get-options and process-payment similarly...
```

---

## Testing the APIs

### Using curl

```bash
# Test verify-account
curl -X POST http://localhost:8000/api/v1/tools/verify-account \
  -H "Content-Type: application/json" \
  -d '{
    "account_last_4": "1234",
    "postal_code": "T2P1J9",
    "phone_number": "+14036193821"
  }'

# Test get-options
curl -X POST http://localhost:8000/api/v1/tools/get-options \
  -H "Content-Type: application/json" \
  -d '{
    "customer_id": "92b7caea-1b60-4a71-9c59-f025935cf4d9",
    "balance": 350.00,
    "days_overdue": 15
  }'

# Test process-payment
curl -X POST http://localhost:8000/api/v1/tools/process-payment \
  -H "Content-Type: application/json" \
  -d '{
    "customer_id": "92b7caea-1b60-4a71-9c59-f025935cf4d9",
    "call_sid": "CA123...",
    "payment_type": "payment_plan",
    "amount": 60.00,
    "schedule": {"months": 6}
  }'
```

---

## Deployment Checklist

Before deploying Line agent:
- [ ] Implement all 3 API endpoints in Twilio backend
- [ ] Test endpoints with curl
- [ ] Ensure backend is accessible via HTTPS (ngrok for dev)
- [ ] Set BACKEND_API_URL in Line agent environment
- [ ] Add API key authentication (optional but recommended)
- [ ] Test end-to-end: Line agent → API → Database → Response

---

## Benefits of This Architecture

✅ **No database exposure** - Database stays private
✅ **Low latency** - Single HTTP request per tool
✅ **Stateless agent** - Line agent has no dependencies
✅ **Easy deployment** - No database credentials in Cartesia
✅ **Reusable APIs** - Could use for web dashboard, mobile app, etc.
✅ **Better security** - API layer for auth/validation
✅ **Scalability** - Backend can cache, rate-limit, optimize

---

## Next Steps

1. **Implement API endpoints** in `archer/backend/src/api/tools.py`
2. **Register router** in `archer/backend/src/main.py`
3. **Test locally** with curl
4. **Deploy backend** with ngrok (or production URL)
5. **Configure Line agent** with `BACKEND_API_URL`
6. **Deploy Line agent** to Cartesia
7. **Test end-to-end** conversation with tool execution
