# Slack App Setup Guide

This guide walks through creating a Slack app and bot for VCluster management.

## Step 1: Create Slack App

1. Go to [https://api.slack.com/apps](https://api.slack.com/apps)
2. Click **"Create New App"**
3. Choose **"From scratch"**
4. App Name: `VCluster Manager`
5. Workspace: Select your workspace
6. Click **"Create App"**

## Step 2: Configure Bot

### OAuth & Permissions
1. Go to **"OAuth & Permissions"** in the sidebar
2. Add Bot Token Scopes:
   - `chat:write` - Send messages
   - `chat:write.public` - Send messages to channels the bot isn't in
   - `commands` - Add slash commands
   - `users:read` - Read user information

3. Click **"Install to Workspace"**
4. Copy the **Bot User OAuth Token** (starts with `xoxb-`)

### Slash Commands
1. Go to **"Slash Commands"** in the sidebar
2. Click **"Create New Command"**
3. Configure:
   - **Command**: `/vcluster`
   - **Request URL**: `https://your-server.com/slack/commands`
   - **Short Description**: `Manage VClusters`
   - **Usage Hint**: `create [name] [options] | list | delete [name] | status [name]`
4. Click **"Save"**

### App Credentials
1. Go to **"Basic Information"** in the sidebar
2. Copy the **Signing Secret** from "App Credentials"

## Step 3: Configure Server Environment

Create `.env` file with your credentials:

```bash
# Copy from .env.example
cp .env.example .env

# Edit with your values
nano .env
```

Required environment variables:
```bash
SLACK_SIGNING_SECRET=your_signing_secret_from_basic_information
SLACK_BOT_TOKEN=xoxb-your-bot-token-from-oauth
GITHUB_TOKEN=your_github_personal_access_token
GITHUB_REPO=shlapolosa/health-service-idp
```

## Step 4: Start Server

### Local Development
```bash
# Install dependencies
pip install -r requirements.txt

# Start server
python app.py
```

### Using Docker
```bash
# Build and run
docker-compose up --build

# Or run detached
docker-compose up -d
```

### Production (with ngrok for testing)
```bash
# Install ngrok if you don't have it
# brew install ngrok  # macOS
# Download from https://ngrok.com

# Start your server
python app.py

# In another terminal, expose it
ngrok http 5000

# Copy the HTTPS URL (e.g., https://abc123.ngrok.io)
# Update Slack slash command URL to: https://abc123.ngrok.io/slack/commands
```

## Step 5: Test Integration

### Test Slash Command
In your Slack workspace:
```
/vcluster help
/vcluster create test-cluster with observability
/vcluster create my-app in namespace production with security and monitoring
```

### Test Natural Language Examples
```
/vcluster create development with all capabilities
/vcluster create large vcluster called prod-cluster with observability and security
/vcluster create vcluster with monitoring but without backup in namespace dev
```

## Step 6: Verify GitHub Integration

1. Check GitHub Actions: https://github.com/shlapolosa/health-service-idp/actions
2. Look for triggered workflows after slash commands
3. Check server logs for GitHub API calls

## Troubleshooting

### Common Issues

**"dispatch_failed" error:**
- Check GITHUB_TOKEN has correct permissions
- Verify GITHUB_REPO format: `owner/repo`
- Check GitHub repository exists and is accessible

**Slack signature verification failed:**
- Ensure SLACK_SIGNING_SECRET is correct
- Check request timestamp (must be within 5 minutes)
- Verify server clock is synchronized

**Command not responding:**
- Check slash command URL is correct and accessible
- Verify server is running and healthy: `curl localhost:5000/health`
- Check Slack app permissions

### Debug Mode
Enable debug logging:
```bash
export DEBUG=true
python app.py
```

### Check Server Health
```bash
curl http://localhost:5000/health
```

### Test Natural Language Parsing
```bash
python test_server.py
```

## Security Notes

1. **Keep secrets secure**: Never commit `.env` file to git
2. **Use HTTPS**: Slack requires HTTPS endpoints in production
3. **Verify requests**: Server validates Slack request signatures
4. **Minimal permissions**: Bot only has necessary Slack scopes

## Next Steps

1. ✅ Create Slack app and bot
2. ✅ Configure slash commands  
3. ✅ Set up environment variables
4. ✅ Test server locally
5. ⏳ Deploy to production (optional)
6. ⏳ Test end-to-end VCluster creation
7. ⏳ Set up monitoring and alerting