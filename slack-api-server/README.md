# Slack API Server for VCluster Management

This server handles Slack slash commands and webhook events to trigger VCluster provisioning via GitHub Actions.

## Features

- 🤖 **Slash Commands**: `/vcluster create` with natural language processing
- 📝 **Natural Language Parsing**: "create vcluster with observability and security"  
- 🔄 **GitHub Integration**: Triggers repository dispatch events
- 📊 **Progress Updates**: Real-time Slack notifications during provisioning
- 🔐 **Security**: Slack signature verification and request validation

## Architecture

```
Slack → Slack API Server → GitHub API → GitHub Actions → AWS/Kubernetes
  ↑                                                             ↓
  └─────────── Progress Notifications ←─────────────────────────┘
```

## Setup

1. Create Slack app and bot
2. Configure slash commands
3. Set up webhook URLs  
4. Deploy server with environment variables
5. Test integration

## Commands

- `/vcluster create [name] [options]` - Create new VCluster
- `/vcluster list` - List existing VClusters  
- `/vcluster delete [name]` - Delete VCluster
- `/vcluster status [name]` - Check VCluster status