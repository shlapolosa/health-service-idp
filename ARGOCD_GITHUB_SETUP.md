# ArgoCD GitHub Integration Setup

This guide walks you through setting up ArgoCD to monitor your GitHub repository for GitOps deployment of the Visual Architecture Maintenance Tool.

## Prerequisites

1. **GitHub Personal Access Token** with `repo` permissions
2. **ArgoCD installed** and running in the vcluster
3. **Git repository** configured with remote origin

## Step 1: Create GitHub Personal Access Token

1. Go to GitHub → Settings → Developer settings → Personal access tokens → Fine-grained tokens
2. Create a new token with these permissions:
   - **Repository access**: Select your `health-service-idp` repository
   - **Repository permissions**:
     - Contents: Read
     - Metadata: Read
     - Pull requests: Read (optional)
3. Set the token as an environment variable:
   ```bash
   export GITHUB_TOKEN=your_github_token_here
   ```

## Step 2: Run the Setup Script

```bash
./setup-argocd-github.sh
```

The script will:
- Use GitHub username: `shlapolosa`
- Use GitHub token from `GITHUB_TOKEN` environment variable
- Prompt for repository URL (default: `https://github.com/shlapolosa/health-service-idp`)

## Step 3: Manual Setup (Alternative)

If you prefer manual setup:

### 3.1 Update Repository URLs

Update all ArgoCD application manifests to point to your repository:

```bash
# Replace YOUR_REPO_URL with your actual repository URL
find argocd-apps -name "*-argocd-app.yaml" -exec sed -i 's|https://github.com/your-org/health-service-idp|YOUR_REPO_URL|g' {} \;
```

### 3.2 Create Repository Secret

```bash
# Create repository secret for ArgoCD
kubectl create secret generic health-service-idp-repo \
  --from-literal=type=git \
  --from-literal=url=YOUR_REPO_URL \
  --from-literal=username=YOUR_GITHUB_USERNAME \
  --from-literal=password=YOUR_GITHUB_TOKEN \
  -n argocd

# Label the secret for ArgoCD
kubectl label secret health-service-idp-repo \
  argocd.argoproj.io/secret-type=repository \
  -n argocd
```

### 3.3 Commit and Push Manifests

```bash
# Add all manifests
git add oam-applications/ argocd-apps/ argocd-setup/ *.sh *.yaml

# Commit
git commit -m "feat: Add OAM applications and ArgoCD GitOps structure"

# Push to GitHub
git push origin main
```

### 3.4 Deploy App-of-Apps

```bash
# Deploy the ArgoCD Application of Applications
kubectl apply -f argocd-apps/app-of-apps/architecture-tool-app-of-apps.yaml
```

## Step 4: Access ArgoCD UI

1. **Get admin password**:
   ```bash
   kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath="{.data.password}" | base64 -d
   ```

2. **Port forward to ArgoCD**:
   ```bash
   kubectl port-forward svc/argocd-server -n argocd 8080:443
   ```

3. **Open ArgoCD UI**:
   - URL: https://localhost:8080
   - Username: `admin`
   - Password: (from step 1)

## Step 5: Verify Deployment

In ArgoCD UI, you should see:

1. **App-of-Apps**: `architecture-tool-app-of-apps`
2. **Individual Applications**:
   - `redis-infrastructure`
   - `orchestration-service`
   - `business-analyst-anthropic`
   - `application-architect-anthropic`
   - `infrastructure-architect-anthropic`
   - `solution-architect-anthropic`
   - `streamlit-frontend`

## Step 6: Monitor Deployment

```bash
# Watch ArgoCD applications
kubectl get applications.argoproj.io -n argocd -w

# Watch OAM applications
kubectl get applications.core.oam.dev -w

# Watch Knative services
kubectl get ksvc -w
```

## Troubleshooting

### Repository Connection Issues
- Verify GitHub token has correct permissions
- Check repository URL is correct and accessible
- Ensure repository secret is properly labeled

### Application Sync Issues
- Check application logs in ArgoCD UI
- Verify manifest syntax is correct
- Check dependency ordering in sync waves

### OAM Application Issues
- Ensure KubeVela is properly installed
- Check OAM CRDs are available
- Verify workflow dependencies

## Architecture Overview

```
GitHub Repository
    ↓ (GitOps)
ArgoCD App-of-Apps
    ↓ (manages)
Individual ArgoCD Applications
    ↓ (deploys)
OAM Applications
    ↓ (creates)
Knative Services
    ↓ (runs)
Microservice Pods
```

## Dependency Flow

```
Tier 0: Redis Infrastructure
    ↓
Tier 1: Orchestration Service
    ↓
Tier 2: Business Analyst + Application Architect
    ↓
Tier 3: Infrastructure Architect
    ↓
Tier 4: Solution Architect
    ↓
Tier 5: Streamlit Frontend
```

This setup provides a complete GitOps workflow where:
- Git commits trigger ArgoCD synchronization
- ArgoCD manages OAM applications
- OAM applications deploy Knative services
- Dependencies ensure proper startup order