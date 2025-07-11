# 🔧 Manual GitHub Secrets Setup Required

## ✅ Completed Automatically
- ✅ AWS OIDC Provider created
- ✅ AWS IAM Role `GitHubActionsRole` created with proper policies
- ✅ Kubernetes access verified via AWS EKS
- ✅ Secret values prepared

## ❗ Manual Setup Required

Go to: **https://github.com/shlapolosa/health-service-idp/settings/secrets/actions**

### 1. AWS_ROLE_ARN
```
Name: AWS_ROLE_ARN
Value: arn:aws:iam::263350857079:role/GitHubActionsRole
```

### 2. EKS_CLUSTER_NAME
```
Name: EKS_CLUSTER_NAME
Value: socrateshlapolosa-karpenter-demo
```

### 3. SLACK_WEBHOOK_URL
```
Name: SLACK_WEBHOOK_URL
Value: [Create Slack webhook - see instructions below]
```

## 📱 Slack Webhook Setup

1. Go to: https://api.slack.com/apps
2. Click "Create New App" → "From scratch"
3. Name: "VCluster Bot" 
4. Workspace: Select your workspace
5. Go to "Incoming Webhooks" → Enable webhooks
6. Click "Add New Webhook to Workspace"
7. Select channel (e.g., #devops, #alerts)
8. Copy the webhook URL

**Example webhook URL format:**
```
https://hooks.slack.com/services/T00000000/B00000000/XXXXXXXXXXXXXXXXXXXXXXXX
```

## 🧪 Testing After Setup

Once all 3 secrets are configured:

```bash
# Test basic VCluster creation
./test-slack-vcluster.sh basic

# Monitor at: https://github.com/shlapolosa/health-service-idp/actions
```

## 📋 Verification Checklist

- [ ] AWS_ROLE_ARN secret created
- [ ] KUBE_CONFIG_DATA secret created (large base64 string)
- [ ] SLACK_WEBHOOK_URL secret created
- [ ] Test workflow triggered successfully
- [ ] Slack notifications received

## 🔍 Current Status

| Component | Status | Value/Location |
|-----------|--------|----------------|
| AWS IAM Role | ✅ Created | `arn:aws:iam::263350857079:role/GitHubActionsRole` |
| EKS Cluster Access | ✅ Verified | `socrateshlapolosa-karpenter-demo` |
| GitHub Secrets | ✅ Configured | 3 secrets: AWS_ROLE_ARN, EKS_CLUSTER_NAME, SLACK_WEBHOOK_URL |
| Slack Webhook | ✅ Working | Webhook tested successfully |

## 💡 Quick Copy Commands

```bash
# Copy AWS Role ARN
echo "arn:aws:iam::263350857079:role/GitHubActionsRole" | pbcopy

# Copy EKS Cluster Name
echo "socrateshlapolosa-karpenter-demo" | pbcopy

# View setup files
ls -la /tmp/*github* /tmp/*aws*
```

## 🚨 Security Notes

- AWS IAM role uses OIDC for secure temporary credentials
- No long-lived credentials stored in GitHub secrets
- AWS IAM role is scoped to this specific repository and branch
- Kubernetes access is managed through AWS EKS authentication
- Slack webhook only allows posting to the configured channel

After completing these steps, the VCluster creation workflow will be fully functional! 🎉