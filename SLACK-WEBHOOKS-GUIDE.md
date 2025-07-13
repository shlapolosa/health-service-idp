# Slack Webhook Notifications for Argo Workflows

This guide documents the comprehensive step-by-step Slack notification system implemented for VCluster and AppContainer workflows, based on the existing GitHub Actions notification patterns.

## 🎯 Overview

The Slack webhook system provides real-time status updates at every step of the VCluster and AppContainer creation processes, mirroring the rich notification experience from the GitHub Actions workflows.

### Key Features

- **Step-by-step notifications** for all workflow phases
- **Rich Slack block formatting** with emojis, fields, and action buttons
- **Success/failure notifications** with detailed error information
- **Progress updates** for long-running operations
- **Reusable notification templates** across different workflow types
- **Secure webhook URL management** via Kubernetes secrets
- **Configurable notification settings** via ConfigMaps

## 📋 Notification Flow

### VCluster Creation Flow

1. **🚀 Starting**: Initial notification with request details
2. **✅ Validated**: Parameters validated successfully
3. **⏳ Provisioning**: VCluster claim created, provisioning started
4. **📊 Progress**: Updates every 5 minutes during long operations
5. **🎉 Success**: Complete with capabilities, endpoints, and access instructions
6. **❌ Failure**: Detailed error information with logs link

### AppContainer Creation Flow

1. **📦 Starting**: Initial notification with AppContainer details
2. **✅ Validated**: Request parameters validated
3. **🔧 VCluster Setup**: Creating or validating VCluster environment
4. **✅ VCluster Ready**: VCluster available for deployment
5. **📚 Repositories**: Creating source and GitOps repositories
6. **🚀 Microservices**: Creating default microservice template
7. **🌐 Service Mesh**: Configuring Istio and exposing endpoints
8. **🎉 Success**: Complete with repository links and service endpoints
9. **❌ Failure**: Detailed error information with specific failed step

## 🔧 Architecture

### Components

```
argo-workflows/
├── slack-notification-template.yaml     # Reusable notification templates
├── vcluster-template.yaml              # Enhanced VCluster workflow
├── appcontainer-template.yaml          # Enhanced AppContainer workflow
├── setup-slack-webhook-secret.yaml     # Secret and ConfigMap setup
└── deploy-slack-notifications.sh       # Deployment script
```

### Template Structure

#### Core Templates
- `send-slack-notification` - Basic notification sender
- `send-slack-progress` - Progress update formatter  
- `send-slack-success` - Success notification with rich blocks
- `send-slack-failure` - Failure notification with error details

#### Workflow-Specific Templates
- `notify-vcluster-*` - VCluster notification variants
- `notify-appcontainer-*` - AppContainer notification variants

### Configuration Management

#### Secrets (slack-webhook)
```yaml
stringData:
  webhook-url: "https://hooks.slack.com/services/..."
```

#### ConfigMap (slack-notification-config)
```yaml
data:
  argo-workflows-base-url: "https://argo-workflows.example.com"
  progress-interval: "300"    # 5 minutes
  timeout-warning: "600"      # 10 minutes
  max-timeout: "1800"         # 30 minutes
```

## 🚀 Deployment

### Quick Setup

```bash
# Deploy all components
./deploy-slack-notifications.sh
```

### Manual Setup

1. **Deploy secrets and configuration:**
   ```bash
   kubectl apply -f argo-workflows/setup-slack-webhook-secret.yaml
   ```

2. **Deploy notification templates:**
   ```bash
   kubectl apply -f argo-workflows/slack-notification-template.yaml
   ```

3. **Deploy enhanced workflow templates:**
   ```bash
   kubectl apply -f argo-workflows/vcluster-template.yaml
   kubectl apply -f argo-workflows/appcontainer-template.yaml
   ```

### Configuration Updates

#### Update Slack Webhook URL
```bash
# Encode your webhook URL
WEBHOOK_URL_B64=$(echo -n "https://hooks.slack.com/services/YOUR/WEBHOOK/URL" | base64)

# Update the secret
kubectl patch secret slack-webhook -n argo --type='json' \
  -p="[{\"op\": \"replace\", \"path\": \"/data/webhook-url\", \"value\":\"$WEBHOOK_URL_B64\"}]"
```

#### Update Argo Workflows UI URL
```bash
kubectl patch configmap slack-notification-config -n argo --type='json' \
  -p='[{"op": "replace", "path": "/data/argo-workflows-base-url", "value":"https://your-argo-ui.com"}]'
```

## 📱 Notification Examples

### Starting Notification
```json
{
  "text": "🔧 VCluster Progress",
  "blocks": [
    {
      "type": "section",
      "text": {
        "type": "mrkdwn",
        "text": "🔧 *VCluster Progress*\n\n*Resource:* `my-vcluster`\n*Namespace:* `development`\n*User:* @john.doe\n\n*Status:* Validating parameters and setting up infrastructure..."
      }
    }
  ]
}
```

### Success Notification
```json
{
  "text": "🎉 VCluster Created Successfully!",
  "blocks": [
    {
      "type": "header",
      "text": {
        "type": "plain_text",
        "text": "🎉 VCluster Creation Complete"
      }
    },
    {
      "type": "section",
      "fields": [
        {
          "type": "mrkdwn", 
          "text": "*Name:*\n`my-vcluster`"
        },
        {
          "type": "mrkdwn",
          "text": "*Namespace:*\n`development`"
        }
      ]
    },
    {
      "type": "actions",
      "elements": [
        {
          "type": "button",
          "text": {
            "type": "plain_text",
            "text": "📋 View Workflow"
          },
          "url": "https://argo-workflows.example.com/workflows/argo/vcluster-creation-abc123"
        }
      ]
    }
  ]
}
```

## 🔍 Monitoring and Troubleshooting

### View Workflow Logs
```bash
# List workflows
kubectl get workflows -n argo

# Get logs for specific workflow
kubectl logs -n argo -l workflows.argoproj.io/workflow=<workflow-name>

# Watch workflow progress
kubectl get workflow <workflow-name> -n argo -w
```

### Check Notification Components
```bash
# Verify secret exists
kubectl get secret slack-webhook -n argo

# Check configmap
kubectl get configmap slack-notification-config -n argo -o yaml

# List workflow templates
kubectl get workflowtemplate -n argo
```

### Test Notifications
```bash
# Test with a simple workflow
kubectl create -f - <<EOF
apiVersion: argoproj.io/v1alpha1
kind: Workflow
metadata:
  generateName: test-slack-
  namespace: argo
spec:
  entrypoint: test-notification
  templates:
  - name: test-notification
    steps:
    - - name: send-test
        templateRef:
          name: slack-notifications
          template: send-slack-notification
        arguments:
          parameters:
          - name: message
            value: "Test notification from Argo Workflows"
          - name: emoji
            value: "🧪"
EOF
```

## 🛠️ Customization

### Adding New Notification Types

1. **Create new template in `slack-notification-template.yaml`:**
   ```yaml
   - name: notify-custom-workflow
     inputs:
       parameters:
       - name: custom-parameter
     templateRef:
       name: slack-notifications
       template: send-slack-progress
     arguments:
       parameters:
       - name: workflow-type
         value: "custom"
       - name: step-name
         value: "Custom workflow step..."
   ```

2. **Reference in your workflow:**
   ```yaml
   - - name: notify-custom
       templateRef:
         name: slack-notifications
         template: notify-custom-workflow
   ```

### Customizing Message Format

Edit the notification templates in `slack-notification-template.yaml` to modify:
- Message text and formatting
- Slack block structure
- Button actions and URLs
- Progress update frequency

### Channel-Specific Notifications

Update the ConfigMap to include channel mappings:
```yaml
data:
  vcluster-channel: "#infrastructure"
  appcontainer-channel: "#deployments"
  error-channel: "#alerts"
```

## 🔗 Integration Points

### Slack API Server Integration

The Slack API server triggers workflows that automatically include notifications:

1. **VCluster creation** via `/vcluster create` command
2. **AppContainer creation** via `/appcontainer create` command

### GitHub Actions Compatibility

The notification format maintains compatibility with the existing GitHub Actions patterns, ensuring consistent user experience across both platforms.

## 📊 Performance Considerations

- **Notification frequency**: Limited to every 5 minutes for progress updates
- **Timeout handling**: Workflows timeout after 30 minutes with appropriate notifications
- **Error handling**: All notification failures are logged but don't block workflow execution
- **Resource usage**: Minimal overhead using lightweight curl containers

## 🔒 Security

- **Webhook URL**: Stored securely in Kubernetes secrets
- **Access control**: Uses Argo Workflows RBAC for template access
- **Network security**: Notifications sent over HTTPS to Slack
- **Audit trail**: All notification attempts logged in workflow logs

## 🎯 Best Practices

1. **Always test notifications** in a development environment first
2. **Monitor webhook rate limits** to avoid Slack API throttling
3. **Use appropriate channels** for different notification types
4. **Keep webhook URLs secure** and rotate them regularly
5. **Include relevant context** in notifications for better debugging
6. **Set up alerting** for notification failures

---

This comprehensive notification system ensures that users receive timely, informative updates throughout the entire VCluster and AppContainer creation process, matching the rich experience provided by the GitHub Actions workflows.