# GitHub Secrets Setup for VCluster Creation Action

The following secrets need to be configured in your GitHub repository before the VCluster creation action can work.

## Required Secrets

### 1. AWS_ROLE_ARN
**Description**: AWS IAM Role ARN for GitHub Actions to assume
**Value**: `arn:aws:iam::YOUR_AWS_ACCOUNT_ID:role/GitHubActionsRole`
**Example**: `arn:aws:iam::123456789012:role/GitHubActionsRole`

### 2. EKS_CLUSTER_NAME
**Description**: EKS cluster name for direct AWS authentication
**How to get**: Use your EKS cluster name
**Value**: `socrateshlapolosa-karpenter-demo`

### 3. SLACK_WEBHOOK_URL
**Description**: Slack webhook URL for sending notifications
**How to get**: Create an incoming webhook in your Slack workspace
**Value**: `https://hooks.slack.com/services/T00000000/B00000000/XXXXXXXXXXXXXXXXXXXXXXXX`

## Environment Variables (Already Set)
- `AWS_REGION`: us-west-2 (configured in workflow)
- `PERSONAL_ACCESS_TOKEN`: Available as environment variable

## Manual Setup Required

Since these involve sensitive credentials, you'll need to set them up manually in GitHub:

1. Go to: https://github.com/shlapolosa/health-service-idp/settings/secrets/actions
2. Click "New repository secret"
3. Add each secret with the values below

## Detailed Setup Instructions

### AWS_ROLE_ARN Setup
```bash
# 1. Get your AWS Account ID
aws sts get-caller-identity --query Account --output text

# 2. Create IAM role (if not exists) with trust policy for GitHub Actions
aws iam create-role --role-name GitHubActionsRole \
  --assume-role-policy-document '{
    "Version": "2012-10-17",
    "Statement": [
      {
        "Effect": "Allow",
        "Principal": {
          "Federated": "arn:aws:iam::YOUR_ACCOUNT_ID:oidc-provider/token.actions.githubusercontent.com"
        },
        "Action": "sts:AssumeRoleWithWebIdentity",
        "Condition": {
          "StringEquals": {
            "token.actions.githubusercontent.com:aud": "sts.amazonaws.com",
            "token.actions.githubusercontent.com:sub": "repo:shlapolosa/health-service-idp:ref:refs/heads/main"
          }
        }
      }
    ]
  }'

# 3. Attach necessary policies
aws iam attach-role-policy --role-name GitHubActionsRole \
  --policy-arn arn:aws:iam::aws:policy/AmazonEKSClusterPolicy

# 4. Get the role ARN
aws iam get-role --role-name GitHubActionsRole --query Role.Arn --output text
```

### EKS_CLUSTER_NAME Setup
```bash
# 1. Verify EKS cluster exists and is accessible
aws eks describe-cluster --region us-west-2 --name socrateshlapolosa-karpenter-demo

# 2. Test cluster access (optional)
aws eks update-kubeconfig --region us-west-2 --name socrateshlapolosa-karpenter-demo
kubectl cluster-info

# 3. Use cluster name as GitHub secret value
echo "socrateshlapolosa-karpenter-demo"
```

### SLACK_WEBHOOK_URL Setup
1. Go to your Slack workspace
2. Visit: https://api.slack.com/apps
3. Create a new app or use existing
4. Enable "Incoming Webhooks"
5. Create a webhook for your desired channel
6. Copy the webhook URL to GitHub secret

## Testing Configuration

After setting up secrets, test with:
```bash
./test-slack-vcluster.sh basic
```

## Current Secret Status
- ✅ AWS_ROLE_ARN: `arn:aws:iam::263350857079:role/GitHubActionsRole`
- ✅ EKS_CLUSTER_NAME: `socrateshlapolosa-karpenter-demo`
- ✅ SLACK_WEBHOOK_URL: `https://hooks.slack.com/services/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`