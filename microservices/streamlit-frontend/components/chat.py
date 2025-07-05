import streamlit as st
from typing import Dict, List, Any, Optional, Literal
from datetime import datetime
import json
import uuid

MessageRole = Literal["user", "assistant", "system", "agent"]

class ChatMessage:
    """Represents a single chat message"""
    
    def __init__(self, 
                 content: str, 
                 role: MessageRole, 
                 timestamp: Optional[datetime] = None,
                 metadata: Optional[Dict[str, Any]] = None,
                 message_id: Optional[str] = None):
        self.content = content
        self.role = role
        self.timestamp = timestamp or datetime.now()
        self.metadata = metadata or {}
        self.message_id = message_id or str(uuid.uuid4())
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert message to dictionary for serialization"""
        return {
            "content": self.content,
            "role": self.role,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata,
            "message_id": self.message_id
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ChatMessage':
        """Create message from dictionary"""
        timestamp = datetime.fromisoformat(data["timestamp"]) if "timestamp" in data else datetime.now()
        return cls(
            content=data["content"],
            role=data["role"],
            timestamp=timestamp,
            metadata=data.get("metadata", {}),
            message_id=data.get("message_id")
        )

class ChatInterface:
    """Manages the chat interface and message history"""
    
    def __init__(self):
        self.initialize_session_state()
    
    def initialize_session_state(self):
        """Initialize chat-related session state variables"""
        if 'chat_history' not in st.session_state:
            # Initialize with welcome message
            welcome_message = ChatMessage(
                content="Hello! I'm your Architecture Assistant. I can help you create, modify, and understand your enterprise architectures. What would you like to work on today?",
                role="assistant",
                metadata={"type": "welcome", "agent": "system"}
            )
            st.session_state.chat_history = [welcome_message]
        
        if 'chat_sessions' not in st.session_state:
            st.session_state.chat_sessions = {}
        
        if 'current_chat_session' not in st.session_state:
            st.session_state.current_chat_session = "default"
        
        if 'message_counter' not in st.session_state:
            st.session_state.message_counter = 0
        
        if 'chat_settings' not in st.session_state:
            st.session_state.chat_settings = {
                "show_timestamps": True,
                "show_message_ids": False,
                "auto_scroll": True,
                "message_limit": 100,
                "enable_typing_indicator": True
            }
    
    def render_chat_interface(self):
        """Render the complete chat interface"""
        with st.container():
            # Chat header with controls
            self._render_chat_header()
            
            # Message history container
            self._render_message_history()
            
            # Chat input area
            self._render_chat_input()
            
            # Chat controls
            self._render_chat_controls()
    
    def _render_chat_header(self):
        """Render chat header with session info and controls"""
        col1, col2, col3 = st.columns([2, 1, 1])
        
        with col1:
            st.markdown("### 💬 Architecture Assistant")
            session_info = f"Session: {st.session_state.current_chat_session}"
            message_count = len(st.session_state.chat_history)
            st.caption(f"{session_info} • {message_count} messages")
        
        with col2:
            if st.button("🗑️ Clear", key="clear_chat", help="Clear chat history"):
                self.clear_chat_history()
                st.rerun()
        
        with col3:
            if st.button("💾 Export", key="export_chat", help="Export chat history"):
                self._export_chat_history()
    
    def _render_message_history(self):
        """Render the message history with proper styling"""
        # Create a scrollable container for messages
        with st.container():
            # Reverse order to show latest messages at bottom
            for i, message in enumerate(st.session_state.chat_history):
                self._render_single_message(message, i)
    
    def _render_single_message(self, message: ChatMessage, index: int):
        """Render a single message with appropriate styling"""
        # Message container with role-based styling
        with st.chat_message(message.role, avatar=self._get_avatar(message.role)):
            # Message content
            st.markdown(message.content)
            
            # Message metadata (optional)
            if st.session_state.chat_settings.get("show_timestamps", True):
                timestamp_str = message.timestamp.strftime("%H:%M:%S")
                
                # Additional metadata for different message types
                metadata_parts = [timestamp_str]
                
                if message.metadata.get("agent"):
                    metadata_parts.append(f"Agent: {message.metadata['agent']}")
                
                if message.metadata.get("type"):
                    metadata_parts.append(f"Type: {message.metadata['type']}")
                
                if st.session_state.chat_settings.get("show_message_ids", False):
                    metadata_parts.append(f"ID: {message.message_id[:8]}")
                
                st.caption(" • ".join(metadata_parts))
            
            # Message actions (for assistant messages)
            if message.role == "assistant":
                self._render_message_actions(message, index)
    
    def _render_message_actions(self, message: ChatMessage, index: int):
        """Render action buttons for assistant messages"""
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            if st.button("👍", key=f"like_{index}", help="Helpful response"):
                self._handle_message_feedback(message, "like")
        
        with col2:
            if st.button("👎", key=f"dislike_{index}", help="Not helpful"):
                self._handle_message_feedback(message, "dislike")
        
        with col3:
            if st.button("📋", key=f"copy_{index}", help="Copy message"):
                st.write(f"```\n{message.content}\n```")
        
        with col4:
            if st.button("🔄", key=f"regenerate_{index}", help="Regenerate response"):
                self._regenerate_response(message, index)
    
    def _render_chat_input(self):
        """Render the chat input area with enhanced features"""
        # Chat input with placeholder text
        prompt = st.chat_input(
            placeholder="Ask me about your architecture... (e.g., 'Create a new microservices architecture')",
            key="chat_input"
        )
        
        # Quick action buttons
        st.markdown("**Quick Actions:**")
        col1, col2, col3, col4 = st.columns(4)
        
        quick_actions = [
            ("🎨 Create Architecture", "Help me create a new architecture"),
            ("📊 Analyze Current", "Analyze my current architecture"),
            ("🔍 Find Components", "Help me find specific components"),
            ("📝 Generate Docs", "Generate documentation for my architecture")
        ]
        
        for i, (label, action_prompt) in enumerate(quick_actions):
            with [col1, col2, col3, col4][i]:
                if st.button(label, key=f"quick_action_{i}", use_container_width=True):
                    self._process_user_message(action_prompt, is_quick_action=True)
                    st.rerun()
        
        # Process user input
        if prompt:
            self._process_user_message(prompt)
            st.rerun()
    
    def _render_chat_controls(self):
        """Render additional chat controls in an expander"""
        with st.expander("⚙️ Chat Settings"):
            col1, col2 = st.columns(2)
            
            with col1:
                st.session_state.chat_settings["show_timestamps"] = st.checkbox(
                    "Show timestamps", 
                    value=st.session_state.chat_settings.get("show_timestamps", True)
                )
                
                st.session_state.chat_settings["auto_scroll"] = st.checkbox(
                    "Auto-scroll to latest", 
                    value=st.session_state.chat_settings.get("auto_scroll", True)
                )
            
            with col2:
                st.session_state.chat_settings["show_message_ids"] = st.checkbox(
                    "Show message IDs", 
                    value=st.session_state.chat_settings.get("show_message_ids", False)
                )
                
                st.session_state.chat_settings["message_limit"] = st.number_input(
                    "Message history limit", 
                    min_value=10, 
                    max_value=500, 
                    value=st.session_state.chat_settings.get("message_limit", 100)
                )
    
    def _process_user_message(self, content: str, is_quick_action: bool = False):
        """Process a user message and generate response"""
        # Create user message
        user_message = ChatMessage(
            content=content,
            role="user",
            metadata={"is_quick_action": is_quick_action}
        )
        
        # Add to history
        self.add_message(user_message)
        
        # Generate and add assistant response
        assistant_response = self._generate_assistant_response(content)
        self.add_message(assistant_response)
    
    def _generate_assistant_response(self, user_input: str) -> ChatMessage:
        """Generate assistant response based on user input"""
        content = self._get_response_content(user_input)
        agent_type = self._determine_agent_type(user_input)
        
        return ChatMessage(
            content=content,
            role="assistant",
            metadata={
                "agent": agent_type,
                "type": "response",
                "user_input_length": len(user_input)
            }
        )
    
    def _get_response_content(self, user_input: str) -> str:
        """Generate response content based on user input"""
        user_input_lower = user_input.lower()
        
        # Architecture creation requests
        if any(keyword in user_input_lower for keyword in ["create", "new", "build", "design"]) and "architecture" in user_input_lower:
            if "microservices" in user_input_lower:
                return """I'll help you create a microservices architecture! Let me break this down:

**🎯 Key Components for Microservices Architecture:**
• **API Gateway** - Single entry point for client requests
• **Service Discovery** - Dynamic service registration and discovery
• **Load Balancer** - Distribute traffic across service instances
• **Database per Service** - Each microservice has its own database
• **Message Queue** - Asynchronous communication between services
• **Monitoring & Logging** - Distributed tracing and centralized logging

**📋 Next Steps:**
1. Click "Create New" in the sidebar to start the architecture wizard
2. Select "Microservices Architecture" as the template
3. I'll guide you through defining services, data flow, and deployment strategy

Would you like me to help you define the specific microservices for your use case?"""
            
            else:
                return """I'd be happy to help you create a new architecture! Here's how we can proceed:

**🎨 Architecture Creation Options:**
• **Business Architecture** - Organizational structure and business processes
• **Application Architecture** - Software components and their interactions  
• **Technology Architecture** - Infrastructure, platforms, and technology stack
• **Integrated Architecture** - Complete end-to-end system design

**⚡ Quick Start:**
1. Use the "➕ Create New" button in the sidebar
2. Fill out the architecture details form
3. I'll help you design components and relationships

What type of system or domain are you looking to architect?"""
        
        # Analysis requests
        elif any(keyword in user_input_lower for keyword in ["analyze", "review", "assess", "evaluate"]):
            return """I can help you analyze your architecture! Here's what I can assess:

**📊 Analysis Capabilities:**
• **Component Dependencies** - Identify tight coupling and potential issues
• **Performance Bottlenecks** - Find areas that may impact scalability
• **Security Vulnerabilities** - Review security patterns and practices
• **Technology Stack** - Evaluate technology choices and compatibility
• **Business Alignment** - Ensure architecture supports business goals

**🔍 To get started:**
1. Select an existing architecture from the sidebar
2. Navigate to the architecture view
3. I'll provide detailed analysis and recommendations

Which architecture would you like me to analyze, or would you like to upload architecture documentation?"""
        
        # Component finding
        elif any(keyword in user_input_lower for keyword in ["find", "search", "locate", "component"]):
            return """I can help you find and manage architecture components! Here's what I can search for:

**🔍 Component Search:**
• **By Layer** - Business, Application, Technology, Physical
• **By Type** - Services, Interfaces, Databases, Infrastructure
• **By Relationship** - Dependencies, data flows, integrations
• **By Technology** - Specific frameworks, platforms, tools

**📋 Available Commands:**
• "Show me all databases in the architecture"
• "Find components using React"
• "List all external integrations"
• "Show business processes for customer management"

What specific components or patterns are you looking for?"""
        
        # Documentation requests
        elif any(keyword in user_input_lower for keyword in ["document", "docs", "report", "export"]):
            return """I can help generate comprehensive architecture documentation! Here are the available formats:

**📄 Documentation Types:**
• **ArchiMate Report** - Standard enterprise architecture documentation
• **Technical Specifications** - Detailed component and interface specs
• **Deployment Guide** - Infrastructure setup and configuration
• **API Documentation** - Service interfaces and contracts
• **Decision Records** - Architecture decisions and rationale

**📤 Export Formats:**
• PDF reports with diagrams
• HTML interactive documentation  
• Word documents for reviews
• Markdown for version control

Which type of documentation would you like me to generate for your architecture?"""
        
        # Agent and system status
        elif any(keyword in user_input_lower for keyword in ["agent", "status", "health", "system"]):
            return """Here's the current system status:

**🤖 AI Agent Status:**
• **Business Analyst** - 🟢 Online (Response: 1.2s)
• **Business Architect** - 🟢 Online (Response: 1.8s)  
• **Application Architect** - 🟢 Online (Response: 1.5s)
• **Infrastructure Architect** - 🟢 Online (Response: 2.1s)
• **Solution Architect** - 🟢 Online (Response: 1.7s)
• **Project Manager** - 🟢 Online (Response: 1.3s)
• **Developer** - 🟢 Online (Response: 1.4s)

**📊 System Health:**
• All agents operational and ready
• Average response time: 1.6 seconds
• No pending issues or alerts

Click "Agent Status" in the sidebar for detailed monitoring and metrics."""
        
        # Help requests
        elif any(keyword in user_input_lower for keyword in ["help", "how", "tutorial", "guide"]):
            return """Welcome! I'm here to help you with enterprise architecture. Here's what I can assist with:

**🏗️ Architecture Management:**
• Create new architectures from scratch or templates
• Modify and evolve existing designs
• Analyze and optimize architecture patterns
• Generate documentation and reports

**🤝 Collaboration Features:**
• Work with specialized AI agents (Business, Technical, Infrastructure)
• Review and approve architecture changes
• Track decision history and rationale
• Export for team collaboration

**⚡ Quick Tips:**
• Use the sidebar to navigate between architectures
• Try quick actions below the chat for common tasks
• Ask specific questions about ArchiMate, patterns, or technologies
• Request analysis of performance, security, or scalability

What specific area would you like help with?"""
        
        # Default response for other inputs
        else:
            return f"""I understand you're asking about: "{user_input}"

I'm here to help with enterprise architecture tasks. I can assist with:
• **Creating** new architectures and components
• **Analyzing** existing designs for improvements  
• **Finding** specific components or patterns
• **Generating** documentation and reports
• **Collaborating** with specialized AI agents

Could you provide more details about what you'd like to accomplish? For example:
- "Help me design a cloud-native architecture"
- "Analyze the security of my current system"
- "Find all microservices in my e-commerce platform"

What specific architecture challenge are you working on?"""
    
    def _determine_agent_type(self, user_input: str) -> str:
        """Determine which agent type should handle the request"""
        user_input_lower = user_input.lower()
        
        if any(keyword in user_input_lower for keyword in ["business", "process", "stakeholder", "requirement"]):
            return "Business Analyst"
        elif any(keyword in user_input_lower for keyword in ["strategy", "capability", "value"]):
            return "Business Architect"
        elif any(keyword in user_input_lower for keyword in ["application", "software", "service", "api"]):
            return "Application Architect"
        elif any(keyword in user_input_lower for keyword in ["infrastructure", "cloud", "deployment", "server"]):
            return "Infrastructure Architect"
        elif any(keyword in user_input_lower for keyword in ["solution", "integration", "pattern"]):
            return "Solution Architect"
        elif any(keyword in user_input_lower for keyword in ["project", "timeline", "resource"]):
            return "Project Manager"
        elif any(keyword in user_input_lower for keyword in ["code", "implement", "develop"]):
            return "Developer"
        else:
            return "Architecture Assistant"
    
    def _get_avatar(self, role: MessageRole) -> str:
        """Get avatar for message role"""
        avatars = {
            "user": "👤",
            "assistant": "🤖",
            "system": "⚙️",
            "agent": "🎯"
        }
        return avatars.get(role, "💬")
    
    def _handle_message_feedback(self, message: ChatMessage, feedback_type: str):
        """Handle user feedback on messages"""
        if "feedback" not in message.metadata:
            message.metadata["feedback"] = []
        
        message.metadata["feedback"].append({
            "type": feedback_type,
            "timestamp": datetime.now().isoformat()
        })
        
        if feedback_type == "like":
            st.success("Thanks for the positive feedback!")
        else:
            st.info("Thanks for the feedback. I'll work on improving my responses.")
    
    def _regenerate_response(self, message: ChatMessage, index: int):
        """Regenerate a response message"""
        if index > 0:
            # Get the previous user message
            user_message = st.session_state.chat_history[index - 1]
            if user_message.role == "user":
                # Generate new response
                new_response = self._generate_assistant_response(user_message.content)
                new_response.metadata["regenerated"] = True
                new_response.metadata["original_id"] = message.message_id
                
                # Replace the message
                st.session_state.chat_history[index] = new_response
                st.rerun()
    
    def _export_chat_history(self):
        """Export chat history to JSON"""
        history_data = {
            "session": st.session_state.current_chat_session,
            "exported_at": datetime.now().isoformat(),
            "message_count": len(st.session_state.chat_history),
            "messages": [msg.to_dict() for msg in st.session_state.chat_history]
        }
        
        # Convert to JSON string for download
        json_str = json.dumps(history_data, indent=2)
        st.download_button(
            label="💾 Download Chat History",
            data=json_str,
            file_name=f"chat_history_{st.session_state.current_chat_session}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
            mime="application/json"
        )
    
    def add_message(self, message: ChatMessage):
        """Add a message to the chat history"""
        st.session_state.chat_history.append(message)
        st.session_state.message_counter += 1
        
        # Limit message history if needed
        limit = st.session_state.chat_settings.get("message_limit", 100)
        if len(st.session_state.chat_history) > limit:
            # Keep the first message (welcome) and remove oldest messages
            st.session_state.chat_history = (
                st.session_state.chat_history[:1] + 
                st.session_state.chat_history[-(limit-1):]
            )
    
    def clear_chat_history(self):
        """Clear the chat history"""
        # Keep only the welcome message
        if st.session_state.chat_history:
            welcome_message = st.session_state.chat_history[0]
            st.session_state.chat_history = [welcome_message]
        st.session_state.message_counter = 1
    
    def get_message_count(self) -> int:
        """Get total message count"""
        return len(st.session_state.chat_history)
    
    def search_messages(self, query: str) -> List[ChatMessage]:
        """Search messages by content"""
        query_lower = query.lower()
        return [
            msg for msg in st.session_state.chat_history
            if query_lower in msg.content.lower()
        ]