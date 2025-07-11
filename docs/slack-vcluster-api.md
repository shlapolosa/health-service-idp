# Slack VCluster Creation API

This document describes the GitHub API integration for creating VClusters from Slack commands.

## Overview

The Slack integration works through GitHub's repository dispatch API to trigger VCluster creation workflows. Your Slack API server should send a POST request to the GitHub API with the appropriate payload.

## API Endpoint

```
POST https://api.github.com/repos/shlapolosa/health-service-idp/dispatches
```

## Authentication

Include your GitHub Personal Access Token in the Authorization header:

```
Authorization: token YOUR_GITHUB_TOKEN
```

## Payload Structure

### Required Fields

```json
{
  "event_type": "slack_create_vcluster",
  "client_payload": {
    "vcluster_name": "string",     // Required: lowercase alphanumeric with hyphens, max 20 chars
    "namespace": "string",         // Required: lowercase alphanumeric with hyphens, max 15 chars  
    "user": "string"              // Required: Slack username who requested the VCluster
  }
}
```

### Optional Fields

```json
{
  "event_type": "slack_create_vcluster",
  "client_payload": {
    "vcluster_name": "demo-cluster",
    "namespace": "development",
    "user": "john.doe",
    
    // Optional: Repository to create alongside VCluster
    "repository": "my-app",        // lowercase alphanumeric with hyphens
    
    // Optional: Slack context
    "slack_channel": "C1234567890",
    "slack_user_id": "U1234567890",
    
    // Optional: VCluster capabilities (defaults to true for most)
    "capabilities": {
      "observability": true,       // Enable Grafana, Prometheus, Jaeger
      "security": true,           // Enable security policies and RBAC
      "gitops": true,             // Enable ArgoCD
      "monitoring": true,         // Enable monitoring stack
      "logging": true,            // Enable logging stack  
      "networking": true,         // Enable service mesh and network policies
      "autoscaling": true,        // Enable HPA and VPA
      "backup": false             // Enable backup solutions (default: false)
    },
    
    // Optional: Resource specifications
    "resources": {
      "cpu_limit": "2000m",       // CPU limit (default: 2000m)
      "memory_limit": "4Gi",      // Memory limit (default: 4Gi)
      "storage_size": "10Gi",     // Storage size (default: 10Gi)
      "node_count": 3             // Number of nodes (default: 3)
    }
  }
}
```

## Example Payloads

### Basic VCluster

```json
{
  "event_type": "slack_create_vcluster",
  "client_payload": {
    "vcluster_name": "my-cluster",
    "namespace": "development",
    "user": "developer"
  }
}
```

### VCluster with Repository

```json
{
  "event_type": "slack_create_vcluster", 
  "client_payload": {
    "vcluster_name": "api-cluster",
    "namespace": "backend",
    "repository": "user-api",
    "user": "backend-dev"
  }
}
```

### Production Configuration

```json
{
  "event_type": "slack_create_vcluster",
  "client_payload": {
    "vcluster_name": "prod-cluster",
    "namespace": "production",
    "repository": "microservices",
    "user": "devops-engineer",
    "capabilities": {
      "observability": true,
      "security": true,
      "gitops": true,
      "monitoring": true,
      "logging": true,
      "networking": true,
      "autoscaling": true,
      "backup": true
    },
    "resources": {
      "cpu_limit": "8000m",
      "memory_limit": "16Gi",
      "storage_size": "100Gi",
      "node_count": 10
    },
    "slack_channel": "C9876543210",
    "slack_user_id": "U9876543210"
  }
}
```

### Minimal Configuration (Security Only)

```json
{
  "event_type": "slack_create_vcluster",
  "client_payload": {
    "vcluster_name": "secure-cluster",
    "namespace": "security",
    "user": "security-admin",
    "capabilities": {
      "observability": false,
      "security": true,
      "gitops": false,
      "monitoring": false,
      "logging": false,
      "networking": false,
      "autoscaling": false,
      "backup": false
    },
    "resources": {
      "cpu_limit": "1000m",
      "memory_limit": "2Gi",
      "storage_size": "5Gi",
      "node_count": 1
    }
  }
}
```

## Response Codes

| Code | Meaning |
|------|---------|
| 204  | Success - Workflow triggered |
| 401  | Unauthorized - Invalid GitHub token |
| 404  | Not Found - Repository doesn't exist |
| 422  | Validation Error - Invalid payload |

## Workflow Behavior

### Success Flow
1. GitHub Action validates input parameters
2. Checks if VCluster name already exists
3. Creates Kubernetes namespace
4. Creates VClusterEnvironmentClaim with specified capabilities
5. Creates AppContainerClaim (if repository specified)
6. Waits for VCluster to be ready (up to 15 minutes)
7. Extracts connection information
8. Sends success notification to Slack

### Failure Scenarios
- **Validation Errors**: Invalid names, boolean values, etc.
- **Existing VCluster**: VCluster with same name already exists
- **Kubernetes Errors**: Unable to connect to cluster
- **Provisioning Failures**: VCluster fails to start
- **Timeout**: VCluster takes longer than 15 minutes to be ready

## Slack Notifications

The workflow will send rich Slack notifications with:

### Success Notification
- ✅ VCluster creation complete
- 📊 Enabled capabilities 
- 🔗 Connection endpoints
- 📋 Access instructions
- 🔗 Link to GitHub Action logs

### Failure Notification  
- ❌ Error details
- 🔍 Link to logs for troubleshooting
- 💡 Suggested fixes

### Existing VCluster Notification
- ⚠️ VCluster already exists
- 💡 Suggestion to use different name

## Natural Language Parsing

Your Slack API server can parse natural language commands like:

```
"create vcluster with name demo in namespace development and repository called user-api"
```

Extract parameters:
- `vcluster_name`: "demo"
- `namespace`: "development" 
- `repository`: "user-api"

Then construct the appropriate JSON payload for the GitHub API.

## Curl Example

```bash
curl -X POST \
  -H "Authorization: token YOUR_GITHUB_TOKEN" \
  -H "Accept: application/vnd.github.v3+json" \
  -H "Content-Type: application/json" \
  https://api.github.com/repos/shlapolosa/health-service-idp/dispatches \
  -d '{
    "event_type": "slack_create_vcluster",
    "client_payload": {
      "vcluster_name": "demo",
      "namespace": "development",
      "repository": "my-app",
      "user": "developer",
      "capabilities": {
        "observability": true,
        "security": true
      }
    }
  }'
```

## Monitoring

After triggering the workflow, you can monitor progress at:
- GitHub Actions: https://github.com/shlapolosa/health-service-idp/actions
- Workflow will send updates to Slack automatically

## Validation Rules

### VCluster Name
- Lowercase letters, numbers, and hyphens only
- Maximum 20 characters
- Cannot start or end with hyphen

### Namespace
- Lowercase letters, numbers, and hyphens only  
- Maximum 15 characters
- Cannot start or end with hyphen

### Repository Name
- Lowercase letters, numbers, and hyphens only
- No length limit (but keep reasonable)
- Optional field

### Capabilities
- All values must be boolean (true/false)
- Invalid boolean values will cause validation errors

### Resources
- CPU: Standard Kubernetes CPU format (e.g., "1000m", "2")
- Memory: Standard Kubernetes memory format (e.g., "1Gi", "512Mi")
- Storage: Standard Kubernetes storage format (e.g., "10Gi", "500Mi")
- Node Count: Positive integer

## Error Handling

The GitHub Action includes comprehensive error handling:

1. **Input Validation**: Validates all parameters before processing
2. **Kubernetes Connectivity**: Tests cluster connection
3. **Resource Conflicts**: Checks for existing VClusters
4. **Timeout Handling**: 15-minute timeout with progress updates
5. **Slack Notifications**: Detailed error messages sent to Slack

## Security Considerations

- GitHub token should have `repo` scope
- VCluster creation requires appropriate Kubernetes RBAC
- All secrets are managed through GitHub Secrets
- Workflow runs with minimal required permissions

## Testing

Use the included test script to validate the integration:

```bash
./test-slack-vcluster.sh
```

This will trigger test workflows with various configurations to verify the implementation works correctly.