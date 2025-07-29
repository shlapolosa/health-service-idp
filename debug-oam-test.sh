#!/bin/bash

# Simple debug test for OAM application creation
set -e

CONTEXT="platform_user@socrateshlapolosa-karpenter-demo.us-west-2.eksctl.io"
NAMESPACE="debug-oam"

echo "Using context: $CONTEXT"
kubectl config use-context $CONTEXT

# Create namespace
echo "Creating namespace..."
kubectl create namespace $NAMESPACE --dry-run=client -o yaml | kubectl apply -f -

# Create simple OAM application
echo "Creating OAM application..."
cat > /tmp/debug-app.yaml <<EOF
apiVersion: core.oam.dev/v1beta1
kind: Application
metadata:
  name: debug-webservice
  namespace: $NAMESPACE
spec:
  components:
  - name: debug-webservice
    type: webservice
    properties:
      image: nginx:alpine
      port: 8080
      language: python
      framework: fastapi
EOF

kubectl apply -f /tmp/debug-app.yaml

echo "Waiting 30 seconds for processing..."
sleep 30

echo "Checking application status..."
kubectl get application debug-webservice -n $NAMESPACE -o yaml

echo "Checking for created resources..."
echo "Applications:"
kubectl get applications -n $NAMESPACE

echo "Knative Services:"
kubectl get ksvc -n $NAMESPACE || echo "No Knative services found"

echo "Deployments:"
kubectl get deployments -n $NAMESPACE || echo "No deployments found"

echo "Services:"
kubectl get services -n $NAMESPACE || echo "No services found"

echo "Events:"
kubectl get events -n $NAMESPACE --sort-by=.metadata.creationTimestamp

echo "Application details:"
kubectl describe application debug-webservice -n $NAMESPACE

# Cleanup
echo "Cleaning up..."
kubectl delete namespace $NAMESPACE