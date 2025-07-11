# AWS Authentication Troubleshooting Summary

## Current Status: BLOCKED on GitHub Actions AWS OIDC Authentication

**Last Updated**: 2025-07-11  
**Issue**: GitHub Action consistently fails at "Setup AWS Credentials" step with OIDC authentication

---

## 🎯 Original Goal
Successfully provision VCluster and AppContainer via GitHub Actions triggered from Slack using AWS OIDC authentication.

## 🔍 Root Cause Analysis

### Key Discovery: AWS SSO Regional Mismatch
- **User's SSO Configuration**: `us-east-2` (from `~/.aws/config`)
- **EKS Cluster Location**: `us-west-2` 
- **Original Workflow Region**: `us-west-2`
- **Issue**: OIDC authentication must align with SSO region

### AWS Configuration Details
```
SSO Session: platform
SSO Start URL: https://d-9a6769cefb.awsapps.com/start/
SSO Region: us-east-2
Account ID: 263350857079
EKS Cluster: socrateshlapolosa-karpenter-demo (us-west-2)
```

---

## 🛠️ Attempted Solutions

### 1. ✅ Fixed Role Naming Issue
**Problem**: Role name "GitHubActionsRole" contains "GitHub" which causes OIDC failures  
**Solution**: Created new role `VClusterAutomationRole`  
**Result**: ✅ Completed - Role exists and policies attached  

### 2. ✅ Updated GitHub Secrets
**Problem**: GitHub secret had old role ARN  
**Solution**: Updated `AWS_ROLE_ARN` to `arn:aws:iam::263350857079:role/VClusterAutomationRole`  
**Result**: ✅ Verified via API - Secret updated at 2025-07-11T07:22:49Z  

### 3. ✅ Added Required Permissions
**Problem**: Missing `id-token: write` permission for OIDC  
**Solution**: Added permissions block to workflow  
**Result**: ✅ Workflow has correct permissions  

### 4. ✅ Fixed Trust Policy
**Problem**: Trust policy too restrictive for repository_dispatch events  
**Solution**: Updated with `StringLike` for `repo:shlapolosa/*`  
**Result**: ✅ More permissive trust policy applied  

### 5. ✅ Regional Configuration Fix
**Problem**: Workflow using `us-west-2` but SSO in `us-east-2`  
**Solution**: Split configuration:
- Auth region: `us-east-2` (for OIDC)
- EKS region: `us-west-2` (for cluster operations)  
**Result**: ✅ Workflow updated but issue persists  

### 6. ✅ OIDC Provider Enhancement
**Problem**: Might need regional STS audience  
**Solution**: Added both global and regional STS audiences:
- `sts.amazonaws.com`
- `sts.us-east-2.amazonaws.com`  
**Result**: ✅ Provider updated but issue persists  

---

## 🚫 Current Blocker

**Consistent Failure**: GitHub Action fails at "Setup AWS Credentials" step  
**Error Pattern**: "Could not assume role with OIDC"  
**Frequency**: 100% failure rate across all attempts  

### Failed Workflow Runs
- Run 16213562128: Setup AWS Credentials failure
- Run 16213637815: Setup AWS Credentials failure  
- Run 16213682499: Setup AWS Credentials failure
- Run 16214179255: Setup AWS Credentials failure
- Run 16214208634: Setup AWS Credentials failure
- Run 16214434385: Setup AWS Credentials failure (after regional fix)
- Run 16214573486: Setup AWS Credentials failure (after STS audience fix)

---

## 🔧 Current AWS Configuration

### IAM Role: `VClusterAutomationRole`
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Federated": "arn:aws:iam::263350857079:oidc-provider/token.actions.githubusercontent.com"
      },
      "Action": "sts:AssumeRoleWithWebIdentity",
      "Condition": {
        "StringEquals": {
          "token.actions.githubusercontent.com:aud": [
            "sts.amazonaws.com",
            "sts.us-east-2.amazonaws.com"
          ]
        },
        "StringLike": {
          "token.actions.githubusercontent.com:sub": "repo:shlapolosa/*"
        }
      }
    }
  ]
}
```

### OIDC Provider Configuration
- **URL**: `https://token.actions.githubusercontent.com`
- **Audiences**: `["sts.amazonaws.com", "sts.us-east-2.amazonaws.com"]`
- **Thumbprint**: `6938fd4d98bab03faadb97b34396831e3780aea1` ✅ Correct

### GitHub Secrets (Verified)
- ✅ `AWS_ROLE_ARN`: `arn:aws:iam::263350857079:role/VClusterAutomationRole`
- ✅ `EKS_CLUSTER_NAME`: `socrateshlapolosa-karpenter-demo`
- ✅ `SLACK_WEBHOOK_URL`: Configured and tested

---

## 🤔 Potential Remaining Issues

### 1. AWS SSO vs Direct IAM Conflict
- Account uses AWS SSO for identity management
- OIDC might conflict with SSO-managed identity providers
- May need specific SSO configuration for external OIDC

### 2. GitHub Repository Context
- `repository_dispatch` events might have different token context than standard workflows
- Subject claim format might differ from expected pattern

### 3. STS Regional Endpoint Issues  
- Despite regional configuration, STS calls might still route incorrectly
- AWS SSO might enforce specific STS endpoint usage

### 4. Account-Level OIDC Restrictions
- AWS account might have policies preventing external OIDC providers
- SSO configuration might override IAM OIDC settings

---

## 📋 Next Steps (When Resuming)

### Immediate Debugging
1. **Capture Exact Error**: Modify workflow to output specific OIDC error details
2. **Test Local OIDC**: Use AWS CLI to test OIDC token exchange manually
3. **Verify SSO Integration**: Check if AWS SSO allows external OIDC providers

### Alternative Approaches
1. **GitHub Secrets**: Use long-lived AWS credentials (less secure)
2. **AWS CLI Profile**: Use credential process with GitHub Actions
3. **Cross-Account Role**: Create role in different AWS account without SSO

### Advanced Troubleshooting
1. **AWS CloudTrail**: Review failed AssumeRoleWithWebIdentity calls
2. **STS Logs**: Check regional STS endpoint logs for OIDC failures
3. **SSO Admin**: Review AWS SSO configuration for OIDC conflicts

---

## 📊 Testing Scripts Created

1. **`test-full-workflow.sh`**: Comprehensive VCluster + AppContainer test
2. **`verify-provisioning.sh`**: Kubernetes resource verification  
3. **`monitor-workflow.sh`**: Real-time GitHub Action monitoring
4. **`update-github-secret.sh`**: GitHub secret management helper

---

## 💡 Lessons Learned

1. **Role Naming Matters**: Avoid "GitHub" in IAM role names for OIDC
2. **Regional Alignment**: OIDC authentication region must match SSO configuration
3. **Trust Policy Complexity**: repository_dispatch events need broader trust conditions
4. **SSO Complications**: AWS SSO adds complexity to OIDC integration

---

## 🚧 Status: PARKED

**Decision**: Moving to Slack API server setup while this authentication issue is investigated separately.

**Return Requirements**: 
- Successful OIDC authentication test
- GitHub Action completes without AWS credential errors
- Ability to provision VCluster and AppContainer resources

**Testing Readiness**: All scripts and configurations are prepared for immediate testing once authentication is resolved.