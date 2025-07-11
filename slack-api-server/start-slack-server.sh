#!/bin/bash

# Start Slack API Server with ngrok tunnel
# This script sets up everything needed for Slack integration testing

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

echo "🚀 Starting Slack API Server for VCluster Management"
echo "=================================================="

# Check if we're in the right directory
if [[ ! -f "app.py" ]]; then
    echo "Error: app.py not found. Run this script from the slack-api-server directory."
    exit 1
fi

# Check prerequisites
log_info "Checking prerequisites..."

# Check if ngrok is installed
if ! command -v ngrok &> /dev/null; then
    log_error "ngrok not found. Please install ngrok first:"
    echo "  • macOS: brew install ngrok"
    echo "  • Download: https://ngrok.com/download"
    exit 1
fi

# Check if Python dependencies are installed
if ! python -c "import flask, requests" &> /dev/null; then
    log_info "Installing Python dependencies..."
    pip install -r requirements.txt
fi

# Check environment variables
MISSING_VARS=()
if [[ -z "${SLACK_SIGNING_SECRET:-}" ]]; then
    MISSING_VARS+=("SLACK_SIGNING_SECRET")
fi
if [[ -z "${SLACK_BOT_TOKEN:-}" ]]; then
    MISSING_VARS+=("SLACK_BOT_TOKEN")
fi
if [[ -z "${GITHUB_TOKEN:-}" ]]; then
    MISSING_VARS+=("GITHUB_TOKEN")
fi

if [[ ${#MISSING_VARS[@]} -gt 0 ]]; then
    log_error "Missing required environment variables:"
    for var in "${MISSING_VARS[@]}"; do
        echo "  • $var"
    done
    echo ""
    echo "Please set them in your environment or create a .env file:"
    echo "  export SLACK_SIGNING_SECRET=your_signing_secret"
    echo "  export SLACK_BOT_TOKEN=xoxb-your-bot-token"
    echo "  export GITHUB_TOKEN=your_github_token"
    echo ""
    echo "Or copy .env.example to .env and fill in the values:"
    echo "  cp .env.example .env && nano .env"
    exit 1
fi

log_success "✅ Prerequisites checked"

# Start the Flask server in the background
log_info "Starting Flask server..."
export FLASK_ENV=development
export DEBUG=true
python app.py &
SERVER_PID=$!

# Wait for server to start
sleep 3

# Check if server is running
if ! curl -s http://localhost:5000/health > /dev/null; then
    log_error "Failed to start Flask server"
    kill $SERVER_PID 2>/dev/null || true
    exit 1
fi

log_success "✅ Flask server running on http://localhost:5000"

# Start ngrok tunnel
log_info "Starting ngrok tunnel..."
ngrok http 5000 --log=stdout &
NGROK_PID=$!

# Wait for ngrok to start and get the public URL
sleep 5

# Get ngrok URL
NGROK_URL=""
for i in {1..10}; do
    NGROK_URL=$(curl -s http://localhost:4040/api/tunnels | python -c "
import sys, json
try:
    data = json.load(sys.stdin)
    tunnels = data.get('tunnels', [])
    for tunnel in tunnels:
        if tunnel.get('proto') == 'https':
            print(tunnel['public_url'])
            break
except:
    pass
" 2>/dev/null)
    
    if [[ -n "$NGROK_URL" ]]; then
        break
    fi
    sleep 2
done

if [[ -z "$NGROK_URL" ]]; then
    log_error "Failed to get ngrok URL"
    kill $SERVER_PID $NGROK_PID 2>/dev/null || true
    exit 1
fi

log_success "✅ ngrok tunnel established: $NGROK_URL"

# Display setup information
echo ""
echo "🎉 Slack API Server is ready!"
echo "=============================="
echo ""
echo "📡 Server URLs:"
echo "   Local:  http://localhost:5000"
echo "   Public: $NGROK_URL"
echo ""
echo "🔗 Slack Endpoints:"
echo "   Commands: $NGROK_URL/slack/commands"
echo "   Events:   $NGROK_URL/slack/events"
echo ""
echo "⚙️ Slack App Configuration:"
echo "   1. Go to https://api.slack.com/apps"
echo "   2. Select your VCluster Manager app"
echo "   3. Go to 'Slash Commands' and update the Request URL to:"
echo "      $NGROK_URL/slack/commands"
echo ""
echo "🧪 Test Commands:"
echo "   /vcluster help"
echo "   /vcluster create test-cluster with observability"
echo "   /vcluster create large vcluster in namespace prod with security"
echo ""
echo "📊 Monitor:"
echo "   Server logs: This terminal"
echo "   ngrok web interface: http://localhost:4040"
echo "   GitHub Actions: https://github.com/${GITHUB_REPO:-shlapolosa/health-service-idp}/actions"
echo ""

# Function to cleanup on exit
cleanup() {
    echo ""
    log_info "Shutting down..."
    kill $SERVER_PID $NGROK_PID 2>/dev/null || true
    log_success "✅ Cleanup complete"
}

# Set up cleanup on script exit
trap cleanup EXIT

# Keep the script running and show logs
log_info "Press Ctrl+C to stop the server"
echo ""
echo "📝 Server Logs:"
echo "==============="

# Follow the server logs
wait $SERVER_PID