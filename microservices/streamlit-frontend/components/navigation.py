import streamlit as st
from typing import Dict, List, Optional, Any
from enum import Enum

class ViewType(Enum):
    """Enumeration of available views in the application"""
    HOME = "home"
    CREATE = "create"
    LIST = "list"
    VIEW = "view"
    SETTINGS = "settings"
    AGENT_STATUS = "agent_status"

class NavigationManager:
    """Manages navigation state and menu rendering for the Streamlit application"""
    
    def __init__(self):
        self.initialize_session_state()
    
    def initialize_session_state(self):
        """Initialize navigation-related session state variables"""
        if 'current_view' not in st.session_state:
            st.session_state.current_view = ViewType.HOME.value
        if 'selected_architecture' not in st.session_state:
            st.session_state.selected_architecture = None
        if 'navigation_expanded' not in st.session_state:
            st.session_state.navigation_expanded = {
                'architectures': True,
                'settings': False,
                'agents': False
            }
        if 'breadcrumb' not in st.session_state:
            st.session_state.breadcrumb = []
    
    def set_view(self, view: ViewType, architecture: Optional[Dict[str, Any]] = None):
        """Set the current view and update related state"""
        st.session_state.current_view = view.value
        if architecture:
            st.session_state.selected_architecture = architecture
        self.update_breadcrumb(view, architecture)
        st.rerun()
    
    def update_breadcrumb(self, view: ViewType, architecture: Optional[Dict[str, Any]] = None):
        """Update the breadcrumb navigation"""
        breadcrumb = ["Home"]
        
        if view == ViewType.CREATE:
            breadcrumb.append("Create Architecture")
        elif view == ViewType.LIST:
            breadcrumb.append("All Architectures")
        elif view == ViewType.VIEW and architecture:
            breadcrumb.extend(["Architectures", architecture.get('name', 'Unknown')])
        elif view == ViewType.SETTINGS:
            breadcrumb.append("Settings")
        elif view == ViewType.AGENT_STATUS:
            breadcrumb.append("Agent Status")
        
        st.session_state.breadcrumb = breadcrumb
    
    def render_breadcrumb(self):
        """Render breadcrumb navigation"""
        if len(st.session_state.breadcrumb) > 1:
            breadcrumb_text = " > ".join(st.session_state.breadcrumb)
            st.markdown(f"**{breadcrumb_text}**")
            st.markdown("---")
    
    def render_hamburger_menu(self, architectures: List[Dict[str, Any]]):
        """Render the complete hamburger menu in the sidebar"""
        with st.sidebar:
            # Main header
            st.markdown("# 🏗️ Architecture Tool")
            st.markdown("---")
            
            # Dashboard/Home
            if st.button("🏠 Dashboard", key="nav_home", use_container_width=True):
                self.set_view(ViewType.HOME)
            
            # Architecture Management Section
            self._render_architecture_section(architectures)
            
            # Agent Management Section
            self._render_agent_section()
            
            # Settings Section
            self._render_settings_section()
            
            # Quick Actions
            st.markdown("---")
            st.markdown("### ⚡ Quick Actions")
            col1, col2 = st.columns(2)
            with col1:
                if st.button("🔄 Refresh", key="quick_refresh", use_container_width=True):
                    st.rerun()
            with col2:
                if st.button("💾 Export", key="quick_export", use_container_width=True):
                    st.info("Export functionality coming soon!")
    
    def _render_architecture_section(self, architectures: List[Dict[str, Any]]):
        """Render the enhanced architecture management section with quick switching"""
        st.markdown("### 📐 Architectures")
        
        # Quick architecture selector
        if architectures:
            current_arch = st.session_state.get('selected_architecture')
            
            # Create options for selectbox
            arch_options = {"Select Architecture...": None}
            for arch in architectures:
                status_icon = {"Draft": "📝", "In Review": "👀", "Approved": "✅", "Deprecated": "❌"}.get(arch.get('status', 'Draft'), "📄")
                arch_options[f"{status_icon} {arch['name']}"] = arch
            
            # Find current selection
            current_key = "Select Architecture..."
            if current_arch:
                for key, arch in arch_options.items():
                    if arch and arch['id'] == current_arch['id']:
                        current_key = key
                        break
            
            selected_key = st.selectbox(
                "Quick Switch:",
                options=list(arch_options.keys()),
                index=list(arch_options.keys()).index(current_key),
                key="quick_arch_selector"
            )
            
            selected_arch = arch_options[selected_key]
            if selected_arch and (not current_arch or selected_arch['id'] != current_arch['id']):
                self.set_view(ViewType.VIEW, selected_arch)
        
        # Toggle for expandable section
        expanded = st.session_state.navigation_expanded.get('architectures', True)
        if st.button(f"{'📂' if expanded else '📁'} {'Hide' if expanded else 'Show'} Architecture List", key="toggle_arch_section"):
            st.session_state.navigation_expanded['architectures'] = not expanded
        
        if st.session_state.navigation_expanded.get('architectures', True):
            # Management buttons
            col1, col2 = st.columns(2)
            with col1:
                if st.button("➕ Create", key="nav_create", use_container_width=True):
                    self.set_view(ViewType.CREATE)
            with col2:
                if st.button("📋 View All", key="nav_list", use_container_width=True):
                    self.set_view(ViewType.LIST)
            
            # Current architecture highlight
            current_arch = st.session_state.get('selected_architecture')
            if current_arch:
                st.markdown("**📍 Current Architecture:**")
                status_color = {"Draft": "🟡", "In Review": "🔵", "Approved": "🟢", "Deprecated": "🔴"}.get(current_arch.get('status', 'Draft'), "⚪")
                st.markdown(f"{status_color} **{current_arch['name']}**")
                st.caption(f"Type: {current_arch.get('type', 'Unknown')} | Status: {current_arch.get('status', 'Draft')}")
                
                # Quick actions for current architecture
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("👁️ View", key="view_current_arch", use_container_width=True):
                        self.set_view(ViewType.VIEW, current_arch)
                with col2:
                    if st.button("✏️ Edit", key="edit_current_arch", use_container_width=True):
                        self.set_view(ViewType.VIEW, current_arch)
                        st.session_state.edit_mode = True
                
                st.markdown("---")
            
            # Architecture list grouped by status
            if architectures:
                # Group by status
                status_groups = {}
                for arch in architectures:
                    status = arch.get('status', 'Draft')
                    if status not in status_groups:
                        status_groups[status] = []
                    status_groups[status].append(arch)
                
                # Display each group
                for status in ["Approved", "In Review", "Draft", "Deprecated"]:
                    if status in status_groups:
                        group_archs = status_groups[status]
                        status_icon = {"Draft": "📝", "In Review": "👀", "Approved": "✅", "Deprecated": "❌"}.get(status, "📄")
                        
                        with st.expander(f"{status_icon} {status} ({len(group_archs)})", expanded=(status == "Approved")):
                            for arch in group_archs:
                                is_current = (current_arch and current_arch['id'] == arch['id'])
                                button_style = "primary" if is_current else "secondary"
                                prefix = "▶ " if is_current else ""
                                
                                button_key = f"arch_nav_{arch['id']}_{status}"
                                if st.button(f"{prefix}{arch['name']}", key=button_key, 
                                           use_container_width=True, type=button_style):
                                    self.set_view(ViewType.VIEW, arch)
                                
                                # Show architecture metadata
                                if arch.get('description'):
                                    st.caption(arch['description'][:60] + "..." if len(arch['description']) > 60 else arch['description'])
            else:
                st.info("No architectures available")
                if st.button("🚀 Create Your First Architecture", key="create_first_arch", use_container_width=True):
                    self.set_view(ViewType.CREATE)
        
        st.markdown("---")
    
    def _render_agent_section(self):
        """Render the agent status and management section"""
        st.markdown("### 🤖 AI Agents")
        
        # Agent status summary
        agent_status = self._get_agent_status()
        
        # Status indicator
        if agent_status['online'] == agent_status['total']:
            status_color = "🟢"
            status_text = "All Online"
        elif agent_status['online'] > 0:
            status_color = "🟡"
            status_text = f"{agent_status['online']}/{agent_status['total']} Online"
        else:
            status_color = "🔴"
            status_text = "All Offline"
        
        st.markdown(f"{status_color} **{status_text}**")
        
        # Agent details button
        if st.button("📊 Agent Status", key="nav_agent_status", use_container_width=True):
            self.set_view(ViewType.AGENT_STATUS)
        
        # Quick agent actions
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🔄 Restart", key="restart_agents", use_container_width=True):
                st.info("Agent restart requested")
        with col2:
            if st.button("⚙️ Config", key="agent_config", use_container_width=True):
                st.info("Agent configuration coming soon")
        
        st.markdown("---")
    
    def _render_settings_section(self):
        """Render the settings and preferences section"""
        st.markdown("### ⚙️ Settings")
        
        if st.button("🔧 Preferences", key="nav_settings", use_container_width=True):
            self.set_view(ViewType.SETTINGS)
        
        # Theme toggle
        theme = st.session_state.get('theme', 'light')
        if st.button(f"{'🌙' if theme == 'light' else '☀️'} Toggle Theme", 
                    key="toggle_theme", use_container_width=True):
            st.session_state.theme = 'dark' if theme == 'light' else 'light'
            st.rerun()
        
        # Help and documentation
        if st.button("❓ Help", key="nav_help", use_container_width=True):
            st.info("Help documentation coming soon!")
    
    def _get_agent_status(self) -> Dict[str, int]:
        """Get the current status of all agents"""
        # Mock agent status - replace with actual agent monitoring
        agents = [
            "Business Analyst",
            "Business Architect", 
            "Application Architect",
            "Infrastructure Architect",
            "Solution Architect",
            "Project Manager",
            "Accountant",
            "Developer"
        ]
        
        # Simulate some agents being online/offline
        online_count = 8  # Mock all agents online
        
        return {
            'total': len(agents),
            'online': online_count,
            'offline': len(agents) - online_count,
            'agents': agents
        }
    
    def get_current_view(self) -> ViewType:
        """Get the current view as ViewType enum"""
        try:
            return ViewType(st.session_state.current_view)
        except ValueError:
            return ViewType.HOME
    
    def get_selected_architecture(self) -> Optional[Dict[str, Any]]:
        """Get the currently selected architecture"""
        return st.session_state.selected_architecture