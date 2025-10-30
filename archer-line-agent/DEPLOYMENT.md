# Archer Line Agent - Deployment Guide

## Quick Start

This guide walks you through deploying the Archer voice agent to Cartesia's Line platform.

## Prerequisites

✅ **Cartesia Account** - Sign up at https://play.cartesia.ai/
✅ **GitHub Repository** - Code must be in a Git repository
✅ **PostgreSQL Database** - Shared database accessible from Cartesia
✅ **Environment Variables** - Cartesia API key and database URL

## Step 1: Prepare Environment

### 1.1 Create `.env` file

```bash
cd archer-line-agent
cp .env.example .env
```

Edit `.env` with your actual credentials:
```env
CARTESIA_API_KEY=sk_car_your_actual_key_here
DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/database
```

### 1.2 Install Dependencies (Optional - for local testing)

```bash
poetry install
```

## Step 2: Deploy to Cartesia

### Option A: GitHub Integration (Recommended)

#### 2.1 Push Code to GitHub

```bash
git add .
git commit -m "Add Archer Line agent"
git push origin main
```

#### 2.2 Connect in Cartesia Platform

1. Go to https://play.cartesia.ai/
2. Click "Create Agent" or select existing agent
3. Navigate to "Deployments" section
4. Click "Connect GitHub"
5. Authorize Cartesia to access your repository
6. Select your repository: `voice-agents`
7. **Important**: If using monorepo structure, specify subdirectory:
   - Path: `archer-line-agent/`
8. Save configuration

#### 2.3 Trigger Deployment

Any push to `main` branch will automatically deploy. Or manually trigger:
- In Cartesia dashboard, click "Deploy Now"
- Wait for build to complete (usually 1-2 minutes)
- Status should change to "ready"

### Option B: CLI Deployment

#### 2.4 Install Line CLI

```bash
pip install cartesia-line
```

#### 2.5 Authenticate

```bash
line login
# Follow prompts to authenticate with Cartesia
```

#### 2.6 Deploy

```bash
cd archer-line-agent
line deploy
```

## Step 3: Configure Environment Variables in Cartesia

### 3.1 Set Environment Variables

In Cartesia dashboard:
1. Go to your agent settings
2. Navigate to "Environment Variables"
3. Add the following:

```
CARTESIA_API_KEY=sk_car_...
DATABASE_URL=postgresql+asyncpg://...
ENVIRONMENT=production
DEBUG=false
```

**Important**: These override the `.env` file during deployment.

### 3.2 Database Access

Ensure your PostgreSQL database is accessible from Cartesia's platform:
- If using external database, whitelist Cartesia's IP ranges
- Consider using connection pooling for production
- Test connection before deploying

## Step 4: Test Deployment

### 4.1 Check Deployment Status

In Cartesia dashboard:
- View deployment logs
- Confirm status is "ready"
- Check health endpoint: `GET /health`

### 4.2 Test Call in Playground

1. In Cartesia dashboard, find "Test Call" button
2. Click to initiate test call
3. Follow voice prompts
4. Verify agent responses correctly

### 4.3 Test with Twilio Integration

1. Update Twilio backend configuration (in `../archer/backend/`)
2. Configure webhook to point to deployed agent
3. Call your Twilio number
4. Verify end-to-end conversation flow

## Step 5: Monitor and Maintain

### 5.1 View Logs

- Access logs in Cartesia dashboard
- Monitor call metrics and analytics
- Review conversation transcripts

### 5.2 Update Deployment

Any push to `main` branch will automatically redeploy:
```bash
git add .
git commit -m "Update agent behavior"
git push
```

### 5.3 Rollback if Needed

In Cartesia dashboard:
- View deployment history
- Select previous deployment
- Click "Activate" to rollback

## Troubleshooting

### Deployment fails with "Invalid main.py"

**Solution**: Ensure `main.py` is at root of deployment directory
```bash
ls archer-line-agent/
# Should show: main.py, pyproject.toml, etc.
```

### "Health check failed"

**Solution**: Check `/health` endpoint is responding
```python
# In main.py, verify:
@app.get("/health")
async def health_check():
    return {"status": "healthy"}
```

### Database connection errors

**Solutions**:
1. Verify DATABASE_URL format: `postgresql+asyncpg://user:pass@host:port/db`
2. Check database is accessible from Cartesia platform
3. Verify credentials are correct
4. Test connection locally first

### Agent not responding to calls

**Solutions**:
1. Check deployment status is "ready"
2. Verify `handle_new_call` function exists in main.py
3. Review deployment logs for errors
4. Ensure Cartesia API key is valid

### Tools not executing

**Solutions**:
1. Verify tools are properly imported in main.py
2. Check database has required tables
3. Review tool implementation for errors
4. Check logs for tool execution failures

## Production Checklist

Before going to production:

- [ ] Environment variables set in Cartesia dashboard
- [ ] Database is production-ready (not localhost)
- [ ] Connection pooling configured
- [ ] Monitoring and logging enabled
- [ ] Agent tested with various scenarios
- [ ] Compliance requirements verified (TCPA, FDCPA)
- [ ] Backup and disaster recovery plan
- [ ] Rate limiting and scaling configured
- [ ] Security review completed

## Next Steps

1. **Test thoroughly** - Try various customer scenarios
2. **Monitor metrics** - Watch call duration, success rate
3. **Iterate** - Improve prompts based on real conversations
4. **Scale** - Adjust Cartesia plan as call volume grows

## Support

- **Cartesia Docs**: https://docs.cartesia.ai/line
- **Discord**: https://discord.gg/cartesia
- **Email**: support@cartesia.ai

## Appendix: Monorepo Structure

If using monorepo with both Twilio backend and Line agent:

```
voice-agents/
├── archer/
│   └── backend/          # Twilio orchestrator
└── archer-line-agent/    # Line agent (this deployment)
    ├── main.py           # Deploy this directory
    ├── pyproject.toml
    └── ...
```

In Cartesia GitHub integration, specify:
- Repository: `your-org/voice-agents`
- Path: `archer-line-agent/`

This tells Cartesia to only deploy the `archer-line-agent/` subdirectory.
