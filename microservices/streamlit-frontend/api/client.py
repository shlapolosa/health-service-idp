import httpx
import asyncio
import websockets
import json
import streamlit as st
import os
from typing import Dict, List, Any, Optional, Callable
from urllib.parse import urljoin
from datetime import datetime
import logging
from contextlib import asynccontextmanager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class APIError(Exception):
    """Custom exception for API errors"""
    def __init__(self, message: str, status_code: Optional[int] = None):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)

class APIClient:
    """Enhanced HTTP client for backend API communication with retry logic and connection management"""
    
    def __init__(self, base_url: str = None):
        self.base_url = base_url or os.getenv("ORCHESTRATION_SERVICE_URL", "http://localhost:8080")
        self.api_prefix = ""
        self.headers = {"Content-Type": "application/json"}
        self.token = None
        self.timeout = 30.0
        self.max_retries = 3
        self.retry_delay = 1.0
        
        # Connection health tracking
        self.last_health_check = None
        self.is_healthy = False
    
    def set_auth_token(self, token: str):
        """Set authentication token for API requests"""
        self.token = token
        self.headers["Authorization"] = f"Bearer {token}"
    
    def _make_url(self, endpoint: str) -> str:
        """Construct full API URL"""
        return urljoin(self.base_url, f"{self.api_prefix}{endpoint}")
    
    async def _make_request(self, method: str, endpoint: str, **kwargs) -> httpx.Response:
        """Make HTTP request with retry logic and error handling"""
        url = self._make_url(endpoint)
        
        for attempt in range(self.max_retries):
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    response = await client.request(
                        method,
                        url,
                        headers=self.headers,
                        **kwargs
                    )
                    
                    # Update health status
                    self.is_healthy = True
                    self.last_health_check = datetime.now()
                    
                    # Handle HTTP errors
                    if response.status_code >= 400:
                        error_msg = f"HTTP {response.status_code}: {response.text}"
                        logger.error(f"API error for {method} {url}: {error_msg}")
                        raise APIError(error_msg, response.status_code)
                    
                    return response
                    
            except httpx.TimeoutException:
                logger.warning(f"Timeout on attempt {attempt + 1} for {method} {url}")
                if attempt == self.max_retries - 1:
                    self.is_healthy = False
                    raise APIError(f"Request timeout after {self.max_retries} attempts")
                await asyncio.sleep(self.retry_delay * (attempt + 1))
                
            except httpx.ConnectError:
                logger.warning(f"Connection error on attempt {attempt + 1} for {method} {url}")
                if attempt == self.max_retries - 1:
                    self.is_healthy = False
                    raise APIError("Unable to connect to backend service")
                await asyncio.sleep(self.retry_delay * (attempt + 1))
                
            except Exception as e:
                logger.error(f"Unexpected error on attempt {attempt + 1} for {method} {url}: {e}")
                if attempt == self.max_retries - 1:
                    self.is_healthy = False
                    raise APIError(f"Request failed: {str(e)}")
                await asyncio.sleep(self.retry_delay * (attempt + 1))
    
    async def health_check(self) -> bool:
        """Check if the backend API is healthy"""
        try:
            response = await self._make_request("GET", "/health")
            health_data = response.json()
            self.is_healthy = health_data.get("status") == "healthy"
            return self.is_healthy
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            self.is_healthy = False
            return False
    
    # Architecture endpoints
    async def get_architectures(self) -> List[Dict[str, Any]]:
        """Get all architectures"""
        try:
            response = await self._make_request("GET", "/architectures")
            return response.json()
        except APIError as e:
            logger.error(f"Error fetching architectures: {e.message}")
            return []
    
    async def get_architecture(self, arch_id: int) -> Optional[Dict[str, Any]]:
        """Get specific architecture by ID"""
        try:
            response = await self._make_request("GET", f"/architectures/{arch_id}")
            return response.json()
        except APIError as e:
            logger.error(f"Error fetching architecture {arch_id}: {e.message}")
            return None
    
    async def create_architecture(self, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Create new architecture"""
        try:
            response = await self._make_request("POST", "/architectures", json=data)
            return response.json()
        except APIError as e:
            logger.error(f"Error creating architecture: {e.message}")
            return None
    
    async def update_architecture(self, arch_id: int, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Update existing architecture"""
        try:
            response = await self._make_request("PUT", f"/architectures/{arch_id}", json=data)
            return response.json()
        except APIError as e:
            logger.error(f"Error updating architecture {arch_id}: {e.message}")
            return None
    
    async def delete_architecture(self, arch_id: int) -> bool:
        """Delete architecture"""
        try:
            await self._make_request("DELETE", f"/architectures/{arch_id}")
            return True
        except APIError as e:
            logger.error(f"Error deleting architecture {arch_id}: {e.message}")
            return False
    
    # Chat and Agent Orchestration endpoints
    async def send_chat_message(self, message: str, context: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        """Send chat message to agent orchestration system"""
        try:
            data = {
                "query": message,
                "parameters": {"workflow_type": "requirements_analysis"},
                "context": context or {}
            }
            response = await self._make_request("POST", "/workflows", json=data)
            return response.json()
        except APIError as e:
            logger.error(f"Error sending chat message: {e.message}")
            return None
    
    async def get_agent_status(self) -> Optional[Dict[str, Any]]:
        """Get status of all agents"""
        try:
            response = await self._make_request("GET", "/agents")
            return response.json()
        except APIError as e:
            logger.error(f"Error fetching agent status: {e.message}")
            return None
    
    async def start_workflow(self, workflow_type: str, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Start an agent workflow"""
        try:
            payload = {
                "query": data.get("query", ""),
                "parameters": {"workflow_type": workflow_type},
                "context": data.get("context", {})
            }
            response = await self._make_request("POST", "/workflows", json=payload)
            return response.json()
        except APIError as e:
            logger.error(f"Error starting workflow: {e.message}")
            return None
    
    async def get_workflow_status(self, workflow_id: str) -> Optional[Dict[str, Any]]:
        """Get workflow status"""
        try:
            response = await self._make_request("GET", f"/workflows/{workflow_id}")
            return response.json()
        except APIError as e:
            logger.error(f"Error fetching workflow status {workflow_id}: {e.message}")
            return None
    
    # Authentication endpoints
    async def authenticate(self, email: str, password: str) -> Optional[str]:
        """Authenticate user and return token"""
        try:
            response = await self._make_request(
                "POST", 
                "/auth/login",
                data={"username": email, "password": password},
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )
            token_data = response.json()
            return token_data.get("access_token")
        except APIError as e:
            logger.error(f"Error authenticating: {e.message}")
            return None
    
    # Agent endpoints
    async def get_agent_metrics(self) -> Dict[str, Any]:
        """Get agent metrics and status"""
        try:
            response = await self._make_request("GET", "/metrics")
            return response.json()
        except APIError as e:
            logger.error(f"Error fetching agent metrics: {e.message}")
            return {"agents": [], "online": 0, "total": 0}
    
    async def trigger_agent_workflow(self, workflow_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Trigger an agent workflow"""
        try:
            payload = {
                "query": workflow_data.get("query", ""),
                "parameters": workflow_data.get("parameters", {}),
                "context": workflow_data.get("context", {})
            }
            response = await self._make_request("POST", "/workflows", json=payload)
            return response.json()
        except APIError as e:
            logger.error(f"Error triggering workflow: {e.message}")
            return None
    
    # Change request endpoints
    async def get_change_requests(self) -> List[Dict[str, Any]]:
        """Get all change requests"""
        try:
            response = await self._make_request("GET", "/change-requests")
            return response.json()
        except APIError as e:
            logger.error(f"Error fetching change requests: {e.message}")
            return []
    
    async def create_change_request(self, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Create new change request"""
        try:
            response = await self._make_request("POST", "/change-requests", json=data)
            return response.json()
        except APIError as e:
            logger.error(f"Error creating change request: {e.message}")
            return None

class WebSocketManager:
    """Manages WebSocket connections for real-time updates"""
    
    def __init__(self, base_url: str = None):
        self.base_url = base_url or os.getenv("ORCHESTRATION_WS_URL", "ws://localhost:8080") 
        self.ws_url = f"{self.base_url}/ws"
        self.connection = None
        self.is_connected = False
        self.message_handlers = {}
        self.reconnect_attempts = 0
        self.max_reconnect_attempts = 5
        self.reconnect_delay = 2.0
        
    def register_handler(self, message_type: str, handler: Callable):
        """Register a message handler for specific message types"""
        self.message_handlers[message_type] = handler
    
    async def connect(self) -> bool:
        """Establish WebSocket connection"""
        try:
            self.connection = await websockets.connect(
                self.ws_url,
                timeout=10,
                ping_interval=30,
                ping_timeout=10
            )
            self.is_connected = True
            self.reconnect_attempts = 0
            logger.info("WebSocket connected successfully")
            return True
            
        except Exception as e:
            logger.error(f"WebSocket connection failed: {e}")
            self.is_connected = False
            return False
    
    async def disconnect(self):
        """Disconnect WebSocket"""
        if self.connection:
            await self.connection.close()
            self.connection = None
            self.is_connected = False
            logger.info("WebSocket disconnected")
    
    async def send_message(self, message: Dict[str, Any]) -> bool:
        """Send message through WebSocket"""
        if not self.is_connected or not self.connection:
            logger.warning("WebSocket not connected, cannot send message")
            return False
        
        try:
            await self.connection.send(json.dumps(message))
            return True
        except Exception as e:
            logger.error(f"Error sending WebSocket message: {e}")
            self.is_connected = False
            return False
    
    async def listen_for_messages(self):
        """Listen for incoming WebSocket messages"""
        while self.is_connected and self.connection:
            try:
                message = await self.connection.recv()
                data = json.loads(message)
                
                # Handle message based on type
                message_type = data.get("type", "unknown")
                if message_type in self.message_handlers:
                    await self.message_handlers[message_type](data)
                else:
                    logger.warning(f"No handler for message type: {message_type}")
                    
            except websockets.exceptions.ConnectionClosed:
                logger.warning("WebSocket connection closed")
                self.is_connected = False
                await self._attempt_reconnect()
                break
                
            except Exception as e:
                logger.error(f"Error receiving WebSocket message: {e}")
                await asyncio.sleep(1)
    
    async def _attempt_reconnect(self):
        """Attempt to reconnect WebSocket"""
        if self.reconnect_attempts >= self.max_reconnect_attempts:
            logger.error("Max reconnection attempts reached")
            return
        
        self.reconnect_attempts += 1
        logger.info(f"Attempting WebSocket reconnection {self.reconnect_attempts}/{self.max_reconnect_attempts}")
        
        await asyncio.sleep(self.reconnect_delay * self.reconnect_attempts)
        
        if await self.connect():
            # Restart message listening
            asyncio.create_task(self.listen_for_messages())

class APIIntegration:
    """Main integration class that combines API client and WebSocket manager"""
    
    def __init__(self, api_base_url: str = None, ws_base_url: str = None):
        self.api_client = APIClient(api_base_url)
        self.websocket = WebSocketManager(ws_base_url)
        self.is_initialized = False
        
        # Register WebSocket message handlers
        self._setup_websocket_handlers()
    
    def _setup_websocket_handlers(self):
        """Setup WebSocket message handlers"""
        
        async def handle_architecture_update(data):
            """Handle architecture update messages"""
            if 'architectures' in st.session_state:
                arch_data = data.get('architecture')
                if arch_data:
                    # Update architecture in session state
                    architectures = st.session_state.architectures
                    for i, arch in enumerate(architectures):
                        if arch['id'] == arch_data['id']:
                            architectures[i] = arch_data
                            break
                    else:
                        architectures.append(arch_data)
                    
                    st.session_state.architectures = architectures
                    st.rerun()
        
        async def handle_agent_status_update(data):
            """Handle agent status update messages"""
            logger.info(f"Agent status update: {data}")
            # Trigger UI update if needed
            st.rerun()
        
        async def handle_notification(data):
            """Handle notification messages"""
            message = data.get('message', 'New notification')
            level = data.get('level', 'info')
            
            if level == 'error':
                st.error(message)
            elif level == 'warning':
                st.warning(message)
            elif level == 'success':
                st.success(message)
            else:
                st.info(message)
        
        # Register handlers
        self.websocket.register_handler('architecture_update', handle_architecture_update)
        self.websocket.register_handler('agent_status', handle_agent_status_update)
        self.websocket.register_handler('notification', handle_notification)
    
    async def initialize(self) -> bool:
        """Initialize the API integration"""
        try:
            # Check API health
            api_healthy = await self.api_client.health_check()
            
            # Attempt WebSocket connection
            ws_connected = await self.websocket.connect()
            
            if ws_connected:
                # Start listening for messages
                asyncio.create_task(self.websocket.listen_for_messages())
            
            self.is_initialized = api_healthy or ws_connected
            
            logger.info(f"API Integration initialized - API: {api_healthy}, WebSocket: {ws_connected}")
            return self.is_initialized
            
        except Exception as e:
            logger.error(f"Failed to initialize API integration: {e}")
            return False
    
    async def cleanup(self):
        """Cleanup connections"""
        await self.websocket.disconnect()
    
    def get_connection_status(self) -> Dict[str, Any]:
        """Get connection status information"""
        return {
            'api_healthy': self.api_client.is_healthy,
            'api_last_check': self.api_client.last_health_check,
            'websocket_connected': self.websocket.is_connected,
            'websocket_reconnect_attempts': self.websocket.reconnect_attempts,
            'initialized': self.is_initialized
        }

# Global instances
api_client = APIClient()
websocket_manager = WebSocketManager()
api_integration = APIIntegration()