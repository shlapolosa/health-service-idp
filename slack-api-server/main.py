"""
Main Entry Point - Slack API Server
Follows Onion Architecture with FastAPI
"""

import os
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

# Add src to Python path
import sys
src_path = Path(__file__).parent / 'src'
sys.path.insert(0, str(src_path))

from src.interface.controllers import create_slack_app

# Create FastAPI application
app = create_slack_app()

# Add startup event
@app.on_event("startup")
async def startup_event():
    """Application startup event."""
    logger.info("🚀 Slack API Server starting up...")
    logger.info(f"📁 Working directory: {os.getcwd()}")
    logger.info(f"🔧 Environment: {os.getenv('ENVIRONMENT', 'development')}")
    
    # Log configuration
    github_token = os.getenv('GITHUB_TOKEN')
    slack_secret = os.getenv('SLACK_SIGNING_SECRET')
    
    logger.info(f"🔑 GitHub token configured: {'✅' if github_token else '❌'}")
    logger.info(f"🔐 Slack signing secret configured: {'✅' if slack_secret else '❌'}")
    logger.info("✅ Slack API Server ready!")


@app.on_event("shutdown")
async def shutdown_event():
    """Application shutdown event."""
    logger.info("👋 Slack API Server shutting down...")


if __name__ == "__main__":
    import uvicorn
    
    # Get configuration from environment
    host = os.getenv('HOST', '0.0.0.0')
    port = int(os.getenv('PORT', '8080'))
    
    logger.info(f"🌐 Starting server on {host}:{port}")
    
    uvicorn.run(
        "main:app",
        host=host,
        port=port,
        reload=True,
        log_level="info"
    )
