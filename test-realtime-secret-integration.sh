#!/bin/bash

# Test realtime platform secret integration and discovery
set -e

CONTEXT="platform_user@socrateshlapolosa-karpenter-demo.us-west-2.eksctl.io"
NAMESPACE="test-realtime-integration"

echo "=== Testing Realtime Platform Secret Integration ==="
echo "Context: $CONTEXT"
echo "Namespace: $NAMESPACE"

kubectl config use-context $CONTEXT

# Create test namespace
echo "Creating test namespace..."
kubectl create namespace $NAMESPACE --dry-run=client -o yaml | kubectl apply -f -

# Create mock realtime platform secrets
echo "Creating mock realtime platform secrets..."
REALTIME_PLATFORM="health-streaming"

kubectl create secret generic "${REALTIME_PLATFORM}-kafka-secret" \
    --from-literal=KAFKA_BOOTSTRAP_SERVERS="kafka.${REALTIME_PLATFORM}.svc.cluster.local:9092" \
    --from-literal=KAFKA_USERNAME="stream-user" \
    --from-literal=KAFKA_PASSWORD="stream-password" \
    -n $NAMESPACE --dry-run=client -o yaml | kubectl apply -f -

kubectl create secret generic "${REALTIME_PLATFORM}-mqtt-secret" \
    --from-literal=MQTT_HOST="mqtt.${REALTIME_PLATFORM}.svc.cluster.local" \
    --from-literal=MQTT_PORT="1883" \
    --from-literal=MQTT_USERNAME="iot-user" \
    --from-literal=MQTT_PASSWORD="iot-password" \
    -n $NAMESPACE --dry-run=client -o yaml | kubectl apply -f -

kubectl create secret generic "${REALTIME_PLATFORM}-db-secret" \
    --from-literal=DB_HOST="postgres.${REALTIME_PLATFORM}.svc.cluster.local" \
    --from-literal=DB_PORT="5432" \
    --from-literal=DB_NAME="streaming_db" \
    --from-literal=DB_USERNAME="stream_user" \
    --from-literal=DB_PASSWORD="stream_password" \
    -n $NAMESPACE --dry-run=client -o yaml | kubectl apply -f -

echo "✅ Mock secrets created"

# Test basic webservice (no realtime)
echo -e "\n=== Test 1: Basic Webservice (No Realtime) ==="
cat > /tmp/basic-webservice.yaml <<EOF
apiVersion: core.oam.dev/v1beta1
kind: Application
metadata:
  name: basic-webservice
  namespace: $NAMESPACE
spec:
  components:
  - name: basic-webservice
    type: webservice
    properties:
      image: nginx:alpine
      port: 8080
      language: python
      framework: fastapi
EOF

kubectl apply -f /tmp/basic-webservice.yaml
echo "Basic webservice application created"

# Test realtime webservice
echo -e "\n=== Test 2: Realtime Webservice ==="
cat > /tmp/realtime-webservice.yaml <<EOF
apiVersion: core.oam.dev/v1beta1
kind: Application
metadata:
  name: realtime-webservice
  namespace: $NAMESPACE
spec:
  components:
  - name: realtime-webservice
    type: webservice
    properties:
      image: nginx:alpine
      port: 8080
      language: python
      framework: fastapi
      realtime: $REALTIME_PLATFORM
EOF

kubectl apply -f /tmp/realtime-webservice.yaml
echo "Realtime webservice application created"

# Wait and check results
echo -e "\n=== Waiting for applications to process... ==="
sleep 30

echo -e "\n=== Test Results ==="
echo "Applications:"
kubectl get applications.core.oam.dev -n $NAMESPACE

echo -e "\nKnative Services:"
kubectl get ksvc -n $NAMESPACE || echo "No Knative services found"

echo -e "\nDeployments:"
kubectl get deployments -n $NAMESPACE || echo "No deployments found"

echo -e "\nSecrets:"
kubectl get secrets -n $NAMESPACE

echo -e "\n=== Application Details ==="
echo "Basic Webservice:"
kubectl describe applications.core.oam.dev basic-webservice -n $NAMESPACE | tail -10

echo -e "\nRealtime Webservice:"
kubectl describe applications.core.oam.dev realtime-webservice -n $NAMESPACE | tail -10

echo -e "\n=== Secret Integration Test ==="
# Check if realtime webservice has the expected secret references
echo "Checking for secret injection in realtime webservice..."

# Check if any pods/deployments exist and have the secret references
DEPLOYMENT=$(kubectl get deployment -n $NAMESPACE -l app.oam.dev/name=realtime-webservice -o name 2>/dev/null | head -1)
if [ -n "$DEPLOYMENT" ]; then
    echo "Found deployment: $DEPLOYMENT"
    kubectl get $DEPLOYMENT -n $NAMESPACE -o jsonpath='{.spec.template.spec.containers[0].envFrom}' | jq . || echo "No envFrom found"
else
    echo "No deployment found for realtime-webservice"
fi

# Check Knative Service for secret references
KSVC=$(kubectl get ksvc -n $NAMESPACE -l app.oam.dev/name=realtime-webservice -o name 2>/dev/null | head -1)
if [ -n "$KSVC" ]; then
    echo "Found Knative Service: $KSVC"
    kubectl get $KSVC -n $NAMESPACE -o yaml | grep -A20 envFrom || echo "No envFrom found in Knative Service"
else
    echo "No Knative Service found for realtime-webservice"
fi

echo -e "\n=== Cleanup ==="
kubectl delete namespace $NAMESPACE
echo "Test completed!"