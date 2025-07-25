#!/bin/bash
set -e

echo "🚀 Multi-Environment Realtime Platform Bootstrap"
echo "=================================================="

# Check if .env file exists
if [ ! -f .env ]; then
    echo "❌ .env file not found. Please create it with agent keys:"
    echo "   Format: <namespace>-agent-key=<agent_key_from_hq>"
    echo "   Example: streaming-platform-2025-realtime-agent-key=agent_key_xyz..."
    exit 1
fi

# 1. Create secrets and ConfigMap
echo "📁 Step 1: Creating secrets and agent keys ConfigMap..."
./setup-secrets.sh

# 2. Apply Crossplane composition (includes CronJob)
echo "🔧 Step 2: Applying Crossplane composition with CronJob..."
kubectl apply -f crossplane/realtime-platform-claim-composition.yaml

# 3. Verify CronJob deployment
echo "⏰ Step 3: Verifying CronJob deployment..."
sleep 5
if kubectl get cronjob multi-env-secret-sync -n default >/dev/null 2>&1; then
    echo "✅ CronJob deployed successfully"
else
    echo "⚠️  CronJob not found, may need manual deployment"
fi

# 4. Show status
echo "📊 Step 4: Current status..."
echo ""
echo "🔑 Agent Keys ConfigMap:"
kubectl get configmap env-agent-keys -n default -o yaml | grep -A 20 "data:"
echo ""
echo "⏰ CronJob Status:"
kubectl get cronjob multi-env-secret-sync -n default
echo ""
echo "🌐 Realtime Namespaces:"
kubectl get ns -l app.kubernetes.io/part-of=realtime-platform

echo ""
echo "🎉 Bootstrap complete!"
echo ""
echo "📝 Next steps:"
echo "   1. Create environment in Lenses HQ"
echo "   2. Add agent key to .env file: <namespace>-agent-key=<key>"
echo "   3. Run ./setup-secrets.sh to update ConfigMap"
echo "   4. CronJob will automatically sync secrets and restart agents"