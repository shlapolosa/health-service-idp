# Test Slack notifications for GitOps pipeline
import streamlit as st
from components.navigation import NavigationManager, ViewType
from components.views import ViewRenderer
from components.chat import ChatInterface, ChatMessage
from components.version_display import render_version_footer, render_detailed_version_info
from utils.session_manager import SessionManager, StateValidator
from utils.async_utils import async_runner, run_async_in_streamlit, with_loading_spinner, task_manager
from api.client import api_client, api_integration
from typing import Dict, List, Any
import asyncio

# Page configuration
st.set_page_config(
    page_title="Visual Architecture Tool",
    page_icon="🏗️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Test GitOps pipeline trigger - Fix websockets dependency

# Custom CSS for better styling
st.markdown("""
<style>
    .main-header {
        font-size: 2rem;
        font-weight: bold;
        color: #1f77b4;
        margin-bottom: 1rem;
    }
    .visualization-area {
        border: 2px solid #e0e0e0;
        border-radius: 8px;
        padding: 1rem;
        min-height: 500px;
        background-color: #f8f9fa;
    }
    .chat-area {
        border: 2px solid #e0e0e0;
        border-radius: 8px;
        padding: 1rem;
        min-height: 300px;
        max-height: 400px;
        background-color: #ffffff;
        overflow-y: auto;
    }
    .compact-chat {
        border: 1px solid #e0e0e0;
        border-radius: 6px;
        padding: 0.75rem;
        min-height: 200px;
        max-height: 300px;
        background-color: #ffffff;
        overflow-y: auto;
        margin-top: 1rem;
    }
    .full-width {
        width: 100%;
        max-width: none;
    }
    .architecture-header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 1rem;
        border-radius: 8px;
        margin-bottom: 1rem;
    }
    .quick-actions {
        background-color: #f8f9fa;
        padding: 0.5rem;
        border-radius: 6px;
        margin-bottom: 1rem;
    }
    .stButton > button {
        width: 100%;
        border-radius: 6px;
        border: 1px solid #ddd;
        background-color: white;
        color: #333;
        padding: 0.5rem 1rem;
        margin: 0.25rem 0;
    }
    .stButton > button:hover {
        background-color: #f0f0f0;
        border-color: #ccc;
    }
    .metric-container {
        background-color: white;
        padding: 1rem;
        border-radius: 8px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
</style>
""", unsafe_allow_html=True)

# Initialize session manager and validate state
session_manager = SessionManager()
validation_issues = StateValidator.validate_and_fix_state()

# Initialize sample data if needed
if not st.session_state.get('architectures'):
    st.session_state.architectures = [
        {
            "id": 1, 
            "name": "E-commerce Platform", 
            "description": "Complete e-commerce solution with microservices architecture",
            "type": "Application Architecture",
            "status": "Approved",
            "version": "2.1.0",
            "business_domain": "Retail",
            "stakeholders": ["Product Manager", "CTO", "DevOps Team"],
            "technology_stack": ["React", "Node.js", "Kubernetes", "AWS"],
            "complexity": "Complex",
            "layers": ["Business", "Application", "Technology"],
            "created_date": "2024-01-15T10:30:00Z",
            "created_recently": False
        },
        {
            "id": 2, 
            "name": "Customer Management System", 
            "description": "CRM system for managing customer relationships and data",
            "type": "Business Architecture",
            "status": "In Review",
            "version": "1.0.0",
            "business_domain": "Customer Service",
            "stakeholders": ["Sales Manager", "Customer Success"],
            "technology_stack": ["Angular", "Java", "PostgreSQL"],
            "complexity": "Moderate",
            "layers": ["Business", "Application"],
            "created_date": "2024-02-20T14:15:00Z",
            "created_recently": True
        }
    ]

@with_loading_spinner("Loading architectures...")
def load_architectures():
    """Load architectures from backend API or session state"""
    try:
        # Try to load from API first (when backend is available)
        if api_integration.is_initialized and api_client.is_healthy:
            try:
                architectures = run_async_in_streamlit(api_client.get_architectures())
                if architectures:
                    # Update session state with fresh data
                    st.session_state.architectures = architectures
                    return architectures
            except Exception as e:
                st.warning(f"Backend API unavailable, using local data: {e}")
        
        # Fallback to session state architectures
        return st.session_state.architectures
    except Exception as e:
        st.error(f"Failed to load architectures: {e}")
        return st.session_state.architectures

def initialize_api_integration():
    """Initialize API integration with status feedback"""
    if 'api_initialized' not in st.session_state:
        with st.spinner("Connecting to backend services..."):
            try:
                # Initialize API integration asynchronously
                initialized = run_async_in_streamlit(api_integration.initialize())
                st.session_state.api_initialized = initialized
                
                if initialized:
                    st.success("✅ Connected to backend services")
                else:
                    st.warning("⚠️ Backend services unavailable - running in offline mode")
                    
            except Exception as e:
                st.error(f"❌ Failed to initialize API integration: {e}")
                st.session_state.api_initialized = False

def render_chat_interface():
    """Render the enhanced chat interface"""
    st.markdown('<div class="compact-chat">', unsafe_allow_html=True)
    
    # Initialize and render chat interface
    chat_interface = ChatInterface()
    chat_interface.render_chat_interface()
    
    st.markdown('</div>', unsafe_allow_html=True)

def render_architecture_chat():
    """Render architecture-specific chat with compact styling"""
    st.markdown('<div class="compact-chat">', unsafe_allow_html=True)
    
    # Initialize and render chat interface
    chat_interface = ChatInterface()
    chat_interface.render_chat_interface()
    
    st.markdown('</div>', unsafe_allow_html=True)

def render_architecture_view_with_chat(view_renderer, selected_arch, nav_manager):
    """Render architecture view with integrated visualization and chat"""
    if not selected_arch:
        st.error("Architecture not found")
        return
    
    # Full-width layout for architecture view
    st.markdown('<div class="visualization-area full-width">', unsafe_allow_html=True)
    
    # Render breadcrumb
    nav_manager.render_breadcrumb()
    
    # Architecture header
    st.markdown(f"## 📊 {selected_arch['name']}")
    
    # Architecture details in compact form
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown(f"**Type:** {selected_arch.get('type', 'Unknown')}")
    with col2:
        status_color = {"Draft": "🟡", "In Review": "🔵", "Approved": "🟢", "Deprecated": "🔴"}.get(selected_arch.get('status', 'Draft'), "⚪")
        st.markdown(f"**Status:** {status_color} {selected_arch.get('status', 'Draft')}")
    with col3:
        st.markdown(f"**Version:** {selected_arch.get('version', '1.0.0')}")
    with col4:
        st.markdown(f"**Complexity:** {selected_arch.get('complexity', 'Moderate')}")
    
    # Full-width visualization area
    st.markdown("### 📊 Architecture Visualization")
    # Render the ArchiMate visualization directly
    view_renderer.render_view_architecture(selected_arch)
    
    # Chat component below visualization with compact height
    st.markdown("### 💬 Architecture Chat")
    st.markdown("Ask questions about this architecture or request changes:")
    
    # Enhanced chat interface with architecture context
    render_architecture_chat_interface(selected_arch)
    
    st.markdown('</div>', unsafe_allow_html=True)

def render_architecture_chat_interface(architecture):
    """Render chat interface with architecture-specific context"""
    from components.chat import ChatInterface
    from components.realtime_updates import realtime_manager
    
    # Initialize chat with architecture context
    chat_interface = ChatInterface()
    
    # Add architecture context to chat
    if 'chat_context' not in st.session_state:
        st.session_state.chat_context = {}
    
    st.session_state.chat_context['current_architecture'] = architecture
    
    # Quick action buttons for common architecture tasks
    st.markdown("#### 🚀 Quick Actions")
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🔍 Analyze Architecture", use_container_width=True):
            chat_message = f"Please analyze the '{architecture['name']}' architecture and provide insights on its design, potential issues, and recommendations for improvement."
            chat_interface.add_message("user", chat_message)
            # Trigger agent response
            handle_chat_message_with_agents(chat_message, architecture)
    
    with col2:
        if st.button("📝 Generate Documentation", use_container_width=True):
            chat_message = f"Please generate comprehensive documentation for the '{architecture['name']}' architecture including component descriptions, relationships, and usage guidelines."
            chat_interface.add_message("user", chat_message)
            handle_chat_message_with_agents(chat_message, architecture)
    
    col3, col4 = st.columns(2)
    with col3:
        if st.button("🔄 Suggest Improvements", use_container_width=True):
            chat_message = f"Based on the '{architecture['name']}' architecture, suggest specific improvements for scalability, performance, security, and maintainability."
            chat_interface.add_message("user", chat_message)
            handle_chat_message_with_agents(chat_message, architecture)
    
    with col4:
        if st.button("🧪 Create Test Plan", use_container_width=True):
            chat_message = f"Create a comprehensive test plan for the '{architecture['name']}' architecture including unit tests, integration tests, and performance tests."
            chat_interface.add_message("user", chat_message)
            handle_chat_message_with_agents(chat_message, architecture)
    
    # Render the standard chat interface with compact styling
    st.markdown("---")
    st.markdown('<div class="compact-chat">', unsafe_allow_html=True)
    chat_interface.render_chat_interface()
    st.markdown('</div>', unsafe_allow_html=True)

def handle_chat_message_with_agents(message: str, architecture: Dict[str, Any]):
    """Handle chat message by routing to appropriate agents"""
    from api.client import api_client
    from utils.async_utils import run_async_in_streamlit
    
    try:
        # Prepare architecture context for agents
        context = {
            "architecture": architecture,
            "message": message,
            "timestamp": datetime.now().isoformat(),
            "user_request": True
        }
        
        # Send to agent orchestration system
        if api_client.is_healthy:
            # Try to use the backend API
            response = run_async_in_streamlit(
                api_client.send_chat_message(message, context)
            )
            
            if response:
                st.success("Request sent to AI agents for processing")
                # The response will come back via WebSocket real-time updates
            else:
                st.warning("Backend API unavailable - using local processing")
                handle_chat_locally(message, architecture)
        else:
            # Fallback to local processing
            handle_chat_locally(message, architecture)
            
    except Exception as e:
        st.error(f"Error processing chat message: {e}")
        handle_chat_locally(message, architecture)

def handle_chat_locally(message: str, architecture: Dict[str, Any]):
    """Handle chat message locally when backend is unavailable"""
    from components.chat import ChatInterface
    
    chat_interface = ChatInterface()
    
    # Simulate agent response based on message content
    if "analyze" in message.lower():
        response = f"""🔍 **Architecture Analysis for {architecture['name']}**

**Overall Assessment:**
- Type: {architecture.get('type', 'Unknown')}
- Complexity: {architecture.get('complexity', 'Moderate')}
- Current Status: {architecture.get('status', 'Draft')}

**Key Observations:**
- The architecture follows {architecture.get('type', 'standard')} patterns
- Technology stack includes: {', '.join(architecture.get('technology_stack', ['Not specified']))}
- Business domain: {architecture.get('business_domain', 'Not specified')}

**Recommendations:**
- Consider implementing monitoring and observability
- Ensure proper security measures are in place
- Plan for scalability based on expected load

*Note: This is a basic analysis. For detailed insights, please connect to the backend agent system.*
"""
    elif "documentation" in message.lower():
        response = f"""📝 **Architecture Documentation for {architecture['name']}**

## Overview
{architecture.get('description', 'Architecture description not available')}

## Architecture Details
- **Type:** {architecture.get('type', 'Unknown')}
- **Version:** {architecture.get('version', '1.0.0')}
- **Business Domain:** {architecture.get('business_domain', 'Not specified')}

## Technology Stack
{chr(10).join(f'- {tech}' for tech in architecture.get('technology_stack', ['Not specified']))}

## Stakeholders
{chr(10).join(f'- {stakeholder}' for stakeholder in architecture.get('stakeholders', ['Not specified']))}

## Architecture Layers
{chr(10).join(f'- {layer}' for layer in architecture.get('layers', ['Not specified']))}

*Note: This is a basic documentation template. For comprehensive documentation, please connect to the backend agent system.*
"""
    elif "improvement" in message.lower():
        response = f"""🔄 **Improvement Suggestions for {architecture['name']}**

**Scalability Improvements:**
- Consider implementing microservices architecture if not already present
- Add load balancing and auto-scaling capabilities
- Implement caching strategies for better performance

**Security Enhancements:**
- Implement API gateway for centralized security
- Add authentication and authorization layers
- Consider zero-trust security model

**Performance Optimizations:**
- Optimize database queries and indexing
- Implement CDN for static content
- Consider asynchronous processing for heavy workloads

**Maintainability:**
- Implement comprehensive monitoring and logging
- Add automated testing and CI/CD pipelines
- Document APIs and interfaces

*Note: These are general recommendations. For architecture-specific suggestions, please connect to the backend agent system.*
"""
    elif "test" in message.lower():
        response = f"""🧪 **Test Plan for {architecture['name']}**

## Test Strategy
Comprehensive testing approach covering all architecture layers.

## Unit Tests
- Test individual components in isolation
- Mock external dependencies
- Aim for 80%+ code coverage

## Integration Tests
- Test component interactions
- Database integration tests
- API endpoint testing

## Performance Tests
- Load testing for expected traffic
- Stress testing for peak loads
- Memory and resource usage tests

## Security Tests
- Authentication and authorization tests
- Input validation and sanitization
- Penetration testing for vulnerabilities

## End-to-End Tests
- Complete user workflow testing
- Cross-browser compatibility
- Mobile responsiveness testing

*Note: This is a general test plan template. For detailed test specifications, please connect to the backend agent system.*
"""
    else:
        response = f"""🤖 **AI Assistant Response**

I understand you're asking about the '{architecture['name']}' architecture. 

While I can provide basic assistance, for comprehensive AI-powered architecture analysis, design recommendations, and automated change generation, please ensure the backend agent system is connected.

The agent system includes specialized AI agents for:
- 📊 Business Analysis
- 🏢 Business Architecture
- 💻 Application Architecture  
- 🔧 Infrastructure Architecture
- 👨‍💻 Development and Implementation

**Current architecture context:**
- Name: {architecture['name']}
- Type: {architecture.get('type', 'Unknown')}
- Status: {architecture.get('status', 'Draft')}

How can I help you with this architecture?
"""
    
    # Add the response to chat
    chat_interface.add_message("assistant", response)

def render_status_notifications():
    """Render status notifications for user feedback"""
    # Show validation issues if any
    if validation_issues:
        with st.sidebar:
            with st.expander("⚠️ Session Issues Fixed"):
                for issue in validation_issues:
                    st.caption(f"• {issue}")
    
    # Show unsaved changes warning
    if session_manager.has_unsaved_changes():
        st.warning("⚠️ You have unsaved changes. Your work will be automatically saved.")
    
    # Auto-save functionality
    if session_manager.get_preference('auto_save', True):
        # Simulate auto-save every 30 seconds of activity
        import time
        current_time = time.time()
        if 'last_auto_save' not in st.session_state:
            st.session_state.last_auto_save = current_time
        elif current_time - st.session_state.last_auto_save > 30:
            session_manager.mark_saved()
            st.session_state.last_auto_save = current_time
            # Show brief success message
            st.success("💾 Auto-saved", icon="✅")

def render_connection_status():
    """Render connection status in sidebar"""
    with st.sidebar:
        st.markdown("---")
        
        # Connection status
        if api_integration.is_initialized:
            status = api_integration.get_connection_status()
            
            # API status
            api_status = "🟢 Connected" if status['api_healthy'] else "🔴 Disconnected"
            st.caption(f"API: {api_status}")
            
            # WebSocket status
            ws_status = "🟢 Connected" if status['websocket_connected'] else "🔴 Disconnected"
            st.caption(f"WebSocket: {ws_status}")
            
            # Show reconnection attempts if any
            if status['websocket_reconnect_attempts'] > 0:
                st.caption(f"⚠️ Reconnect attempts: {status['websocket_reconnect_attempts']}")
        else:
            st.caption("🔴 Backend: Offline Mode")

def render_session_sidebar():
    """Render session management options in sidebar"""
    with st.sidebar:
        st.markdown("---")
        
        # Show session information
        if session_manager.get_preference('show_tips', True):
            session_info = session_manager.get_session_info()
            st.caption(f"Session: {session_info['duration']}")
        
        # Session management expander
        with st.expander("💾 Session Management"):
            col1, col2 = st.columns(2)
            
            with col1:
                if st.button("💾 Save", use_container_width=True, help="Save current session state"):
                    session_manager.mark_saved()
                    st.success("Session saved!")
            
            with col2:
                if st.button("🔄 Refresh", use_container_width=True, help="Refresh application state"):
                    st.rerun()
            
            # API integration controls
            if st.button("🔌 Reconnect API", use_container_width=True, help="Reconnect to backend services"):
                with st.spinner("Reconnecting..."):
                    try:
                        success = run_async_in_streamlit(api_integration.initialize())
                        if success:
                            st.success("Reconnected successfully!")
                        else:
                            st.error("Reconnection failed")
                    except Exception as e:
                        st.error(f"Reconnection error: {e}")
                st.rerun()
            
            # Quick preferences
            theme = session_manager.get_preference('theme', 'light')
            if st.button(f"{'🌙' if theme == 'light' else '☀️'} Theme", use_container_width=True):
                new_theme = 'dark' if theme == 'light' else 'light'
                session_manager.set_preference('theme', new_theme)
                st.rerun()
            
            # Show detailed session info
            session_manager.render_session_info_widget()
            
            # Show detailed version information
            render_detailed_version_info()

def handle_page_refresh():
    """Handle page refresh and state restoration"""
    # Check if this is a page refresh (session exists but app state is reset)
    if 'app_initialized' not in st.session_state:
        st.session_state.app_initialized = True
        
        # Restore critical state if needed
        if session_manager.has_unsaved_changes():
            st.info("🔄 Restoring your previous session...")
        
        # Clean up expired data
        session_manager.cleanup_expired_data()

def main():
    """Main application function"""
    # Application Header
    st.markdown("""
    <div style="background: linear-gradient(90deg, #667eea 0%, #764ba2 100%); 
                padding: 1rem; border-radius: 10px; margin-bottom: 2rem; text-align: center;">
        <h1 style="color: white; margin: 0; font-family: 'Segoe UI', sans-serif;">
            🏗️ Visual Architecture Tool
        </h1>
        <p style="color: #f0f0f0; margin: 0.5rem 0 0 0; font-size: 1.1rem;">
            ✨ Enterprise Architecture Design & Management ✨
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    # Handle page refresh and initialization
    handle_page_refresh()
    
    # Initialize API integration
    initialize_api_integration()
    
    # Show status notifications
    render_status_notifications()
    
    # Initialize components
    nav_manager = NavigationManager()
    view_renderer = ViewRenderer()
    
    # Load architectures
    architectures = load_architectures()
    
    # Render navigation sidebar
    nav_manager.render_hamburger_menu(architectures)
    
    # Render connection status
    render_connection_status()
    
    # Render session management in sidebar
    render_session_sidebar()
    
    # Three-pane layout: Main visualization area + Chat interface
    # Check if we're viewing a specific architecture for full visualization
    current_view = nav_manager.get_current_view()
    
    if current_view == ViewType.VIEW:
        # Architecture view with integrated visualization
        selected_arch = nav_manager.get_selected_architecture()
        render_architecture_view_with_chat(view_renderer, selected_arch, nav_manager)
    else:
        # Full-width main content area
        st.markdown('<div class="visualization-area">', unsafe_allow_html=True)
        
        # Render breadcrumb
        nav_manager.render_breadcrumb()
        
        # Render appropriate view based on current state
        if current_view == ViewType.HOME:
            view_renderer.render_dashboard_view(architectures)
        elif current_view == ViewType.CREATE:
            view_renderer.render_create_view()
        elif current_view == ViewType.LIST:
            view_renderer.render_list_view(architectures)
        elif current_view == ViewType.SETTINGS:
            view_renderer.render_settings_view()
            # Add session preferences to settings
            session_manager.render_preferences_widget()
        elif current_view == ViewType.AGENT_STATUS:
            view_renderer.render_agent_status_view()
        
        st.markdown('</div>', unsafe_allow_html=True)
        
        # Chat interface below main content with compact styling
        st.markdown("### 💬 Chat Assistant")
        render_chat_interface()
    
    # Cleanup completed async tasks periodically
    task_manager.cleanup_completed_tasks()
    
    # Render version footer at bottom of page
    render_version_footer()

if __name__ == "__main__":
    main()  # GitOps test comment Sat  5 Jul 2025 16:23:55 SAST
