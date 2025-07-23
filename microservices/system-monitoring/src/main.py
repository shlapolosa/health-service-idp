"""Main application entry point following 12-factor principles"""
import os
import uvicorn
from interface.api import app

if __name__ == "__main__":
    # 12-Factor: Port binding
    port = int(os.getenv("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)
