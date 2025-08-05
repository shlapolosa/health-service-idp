#!/bin/bash

echo "🔍 Reproducing the SERVICE_SELECTOR extra brace issue"
echo "====================================================="

# Test the exact environment variable that the Kubernetes pod receives
export SERVICE_SELECTOR='{"app.kubernetes.io/managed-by":"kubevela"}'
export NAMESPACE="default"
export GATEWAY_NAME="api-gateway"
export AUTO_DISCOVERY="true"
export DISCOVERY_INTERVAL="5m"

echo "Original environment variables:"
echo "SERVICE_SELECTOR='$SERVICE_SELECTOR'"
echo "NAMESPACE='$NAMESPACE'"
echo "GATEWAY_NAME='$GATEWAY_NAME'"
echo "AUTO_DISCOVERY='$AUTO_DISCOVERY'"
echo "DISCOVERY_INTERVAL='$DISCOVERY_INTERVAL'"
echo ""

# Test the start.sh default assignment behavior
echo "Testing start.sh default assignment:"
TEST_SELECTOR_1="${SERVICE_SELECTOR:-{\"app.kubernetes.io/managed-by\":\"kubevela\"}}"
echo "Result: '$TEST_SELECTOR_1'"
echo ""

# Test the generate-mesh-config.sh default assignment behavior  
echo "Testing generate-mesh-config.sh default assignment:"
TEST_SELECTOR_2="${SERVICE_SELECTOR:-{\"app.kubernetes.io/managed-by\":\"kubevela\"}}"
echo "Result: '$TEST_SELECTOR_2'"
echo ""

# Test what happens when we echo without quotes vs with quotes
echo "Testing echo behavior:"
echo "Without quotes: SERVICE_SELECTOR=$SERVICE_SELECTOR"
echo "With quotes: SERVICE_SELECTOR=\"$SERVICE_SELECTOR\""
echo ""

# Test jq parsing
echo "Testing jq parsing:"
echo "Input: $SERVICE_SELECTOR"
echo "jq result:"
echo "$SERVICE_SELECTOR" | jq -r 'to_entries | map("\(.key)=\(.value)") | join(",")' 2>&1
echo ""

# Test what happens if SERVICE_SELECTOR gets corrupted somehow
echo "Testing potential corruption scenarios:"

# Scenario 1: Double default assignment
unset SERVICE_SELECTOR_TEST
SERVICE_SELECTOR_TEST="${SERVICE_SELECTOR_TEST:-{\"app.kubernetes.io/managed-by\":\"kubevela\"}}"
SERVICE_SELECTOR_TEST="${SERVICE_SELECTOR_TEST:-{\"app.kubernetes.io/managed-by\":\"kubevela\"}}"
echo "Double default assignment: '$SERVICE_SELECTOR_TEST'"

# Scenario 2: String concatenation error
SERVICE_SELECTOR_TEST="$SERVICE_SELECTOR"
SERVICE_SELECTOR_TEST="$SERVICE_SELECTOR_TEST}"  # Simulate accidental extra brace
echo "Accidental concatenation: '$SERVICE_SELECTOR_TEST'"

# Scenario 3: Variable substitution in complex context
echo "Complex context test:"
SELECTOR_TEMP="$SERVICE_SELECTOR"
echo "Selector: $SELECTOR_TEMP" 
echo "Selector with braces: ${SELECTOR_TEMP}"
echo ""

# Test the exact commands from generate-mesh-config.sh
echo "Testing exact generate-mesh-config.sh commands:"
echo "📊 Discovering Knative services"
echo "Selector: \"$SERVICE_SELECTOR\""
echo "Namespace: ${NAMESPACE}"

# Parse service selector JSON to kubectl label selector format
label_selector=$(echo "$SERVICE_SELECTOR" | jq -r 'to_entries | map("\(.key)=\(.value)") | join(",")')
echo "Label selector: ${label_selector}"