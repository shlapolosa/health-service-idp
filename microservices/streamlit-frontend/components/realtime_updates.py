import streamlit as st
from typing import Dict, Any, List, Callable
import json
from datetime import datetime
from api.client import api_integration, websocket_manager
from utils.async_utils import run_async_in_streamlit, task_manager

class RealtimeUpdateManager:
    """Manages real-time updates from backend via WebSocket"""
    
    def __init__(self):
        self.update_handlers = {}
        self.notification_queue = []
        self.max_notifications = 50
        
    def register_update_handler(self, update_type: str, handler: Callable):
        """Register handler for specific update types"""
        self.update_handlers[update_type] = handler
    
    def handle_architecture_update(self, data: Dict[str, Any]):
        """Handle real-time architecture updates"""
        try:
            architecture = data.get('architecture')
            if not architecture:
                return
            
            # Update session state
            if 'architectures' in st.session_state:
                architectures = st.session_state.architectures
                updated = False
                
                # Find and update existing architecture
                for i, arch in enumerate(architectures):
                    if arch['id'] == architecture['id']:
                        architectures[i] = architecture
                        updated = True
                        break
                
                # Add new architecture if not found
                if not updated:
                    architectures.append(architecture)
                
                st.session_state.architectures = architectures
                
                # Add notification
                self.add_notification({
                    'type': 'architecture_update',
                    'message': f"Architecture '{architecture.get('name', 'Unknown')}' was updated",
                    'level': 'info',
                    'timestamp': datetime.now().isoformat()
                })
                
                # Trigger UI refresh
                st.rerun()
                
        except Exception as e:
            st.error(f"Error handling architecture update: {e}")
    
    def handle_agent_status_update(self, data: Dict[str, Any]):
        """Handle real-time agent status updates"""
        try:
            agent_data = data.get('agent')
            if not agent_data:
                return
            
            # Update agent status in session state
            if 'agent_status' not in st.session_state:
                st.session_state.agent_status = {}
            
            agent_name = agent_data.get('name')
            if agent_name:
                st.session_state.agent_status[agent_name] = agent_data
                
                # Add notification for status changes
                status = agent_data.get('status', 'unknown')
                self.add_notification({
                    'type': 'agent_status',
                    'message': f"Agent '{agent_name}' is now {status}",
                    'level': 'info' if status == 'online' else 'warning',
                    'timestamp': datetime.now().isoformat()
                })
                
        except Exception as e:
            st.error(f"Error handling agent status update: {e}")
    
    def handle_workflow_update(self, data: Dict[str, Any]):
        """Handle workflow execution updates"""
        try:
            workflow = data.get('workflow')
            if not workflow:
                return
            
            workflow_id = workflow.get('id')
            status = workflow.get('status')
            
            # Update workflow status in session state
            if 'active_workflows' not in st.session_state:
                st.session_state.active_workflows = {}
            
            st.session_state.active_workflows[workflow_id] = workflow
            
            # Add notification
            self.add_notification({
                'type': 'workflow_update',
                'message': f"Workflow {workflow_id} status: {status}",
                'level': 'success' if status == 'completed' else 'info',
                'timestamp': datetime.now().isoformat()
            })
            
        except Exception as e:
            st.error(f"Error handling workflow update: {e}")
    
    def handle_change_request_update(self, data: Dict[str, Any]):
        """Handle change request updates"""
        try:
            change_request = data.get('change_request')
            if not change_request:
                return
            
            # Update change requests in session state
            if 'change_requests' not in st.session_state:
                st.session_state.change_requests = []
            
            change_requests = st.session_state.change_requests
            cr_id = change_request.get('id')
            
            # Update existing or add new
            updated = False
            for i, cr in enumerate(change_requests):
                if cr['id'] == cr_id:
                    change_requests[i] = change_request
                    updated = True
                    break
            
            if not updated:
                change_requests.append(change_request)
            
            st.session_state.change_requests = change_requests
            
            # Add notification
            status = change_request.get('status', 'unknown')
            self.add_notification({
                'type': 'change_request',
                'message': f"Change request {cr_id} is now {status}",
                'level': 'success' if status == 'approved' else 'info',
                'timestamp': datetime.now().isoformat()
            })
            
        except Exception as e:
            st.error(f"Error handling change request update: {e}")
    
    def add_notification(self, notification: Dict[str, Any]):
        """Add notification to queue"""
        self.notification_queue.append(notification)
        
        # Keep only recent notifications
        if len(self.notification_queue) > self.max_notifications:
            self.notification_queue = self.notification_queue[-self.max_notifications:]
        
        # Store in session state for persistence
        st.session_state.notification_queue = self.notification_queue
    
    def get_recent_notifications(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent notifications"""
        return self.notification_queue[-limit:] if self.notification_queue else []
    
    def clear_notifications(self):
        """Clear all notifications"""
        self.notification_queue.clear()
        if 'notification_queue' in st.session_state:
            del st.session_state.notification_queue
    
    def send_realtime_update(self, update_type: str, data: Dict[str, Any]):
        """Send update to backend via WebSocket"""
        if not websocket_manager.is_connected:
            st.warning("WebSocket not connected - update not sent")
            return False
        
        message = {
            'type': update_type,
            'data': data,
            'timestamp': datetime.now().isoformat(),
            'source': 'frontend'
        }
        
        try:
            success = run_async_in_streamlit(websocket_manager.send_message(message))
            if success:
                st.success(f"Update sent: {update_type}")
            else:
                st.error("Failed to send update")
            return success
        except Exception as e:
            st.error(f"Error sending update: {e}")
            return False
    
    def render_notification_panel(self):
        """Render notification panel"""
        notifications = self.get_recent_notifications()
        
        if not notifications:
            st.info("No recent notifications")
            return
        
        st.markdown("### 🔔 Recent Notifications")
        
        for notification in reversed(notifications):  # Show newest first
            timestamp = datetime.fromisoformat(notification['timestamp'])
            time_str = timestamp.strftime("%H:%M:%S")
            
            level = notification.get('level', 'info')
            icon = {
                'info': '🔵',
                'success': '🟢', 
                'warning': '🟡',
                'error': '🔴'
            }.get(level, '⚪')
            
            with st.expander(f"{icon} {time_str} - {notification['type']}"):
                st.write(notification['message'])
                if 'data' in notification:
                    st.json(notification['data'])
        
        # Clear notifications button
        if st.button("🗑️ Clear Notifications"):
            self.clear_notifications()
            st.rerun()
    
    def setup_websocket_handlers(self):
        """Setup WebSocket message handlers"""
        websocket_manager.register_handler('architecture_update', self.handle_architecture_update)
        websocket_manager.register_handler('agent_status', self.handle_agent_status_update)
        websocket_manager.register_handler('workflow_update', self.handle_workflow_update)
        websocket_manager.register_handler('change_request', self.handle_change_request_update)

class RealtimeMetrics:
    """Tracks and displays real-time metrics"""
    
    def __init__(self):
        self.metrics = {
            'active_users': 0,
            'architectures_count': 0,
            'agents_online': 0,
            'pending_changes': 0,
            'system_health': 'unknown'
        }
    
    def update_metrics(self, new_metrics: Dict[str, Any]):
        """Update metrics from backend"""
        self.metrics.update(new_metrics)
        
        # Store in session state
        st.session_state.realtime_metrics = self.metrics
    
    def get_metric(self, metric_name: str, default=0):
        """Get specific metric value"""
        return self.metrics.get(metric_name, default)
    
    def render_metrics_dashboard(self):
        """Render real-time metrics dashboard"""
        st.markdown("### 📊 Real-time Metrics")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric(
                "Active Users",
                self.get_metric('active_users'),
                delta=self.get_metric('active_users_delta')
            )
        
        with col2:
            st.metric(
                "Architectures",
                self.get_metric('architectures_count'),
                delta=self.get_metric('architectures_delta')
            )
        
        with col3:
            st.metric(
                "Agents Online",
                f"{self.get_metric('agents_online')}/{self.get_metric('total_agents', 8)}",
                delta=self.get_metric('agents_delta')
            )
        
        with col4:
            health = self.get_metric('system_health', 'unknown')
            health_color = {
                'healthy': '🟢',
                'warning': '🟡', 
                'critical': '🔴',
                'unknown': '⚪'
            }.get(health, '⚪')
            
            st.metric(
                "System Health",
                f"{health_color} {health.title()}"
            )

# Global instances
realtime_manager = RealtimeUpdateManager()
realtime_metrics = RealtimeMetrics()

# Setup WebSocket handlers
realtime_manager.setup_websocket_handlers()