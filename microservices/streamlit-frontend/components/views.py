import streamlit as st
from typing import Dict, List, Any, Optional
from .navigation import ViewType
from .archimate_visualization import (
    get_visualization_manager, 
    create_sample_architecture,
    ArchimateVisualization,
    VisualizationEngine
)
import json
from datetime import datetime

class ViewRenderer:
    """Handles rendering of different views in the application"""
    
    def __init__(self):
        pass
    
    def render_dashboard_view(self, architectures: List[Dict[str, Any]]):
        """Render the dashboard/home view"""
        st.markdown("## 🏠 Dashboard")
        st.markdown("Welcome to the Visual Architecture Tool")
        
        # Quick stats
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric(
                label="Total Architectures",
                value=len(architectures),
                delta=f"+{len([a for a in architectures if a.get('created_recently', False)])}" if architectures else None
            )
        
        with col2:
            active_changes = self._get_active_changes_count()
            st.metric(
                label="Active Changes",
                value=active_changes,
                delta=f"+{active_changes}" if active_changes > 0 else None
            )
        
        with col3:
            agent_status = self._get_agent_summary()
            st.metric(
                label="Agents Online",
                value=f"{agent_status['online']}/{agent_status['total']}",
                delta="All systems operational" if agent_status['online'] == agent_status['total'] else "Some agents offline"
            )
        
        with col4:
            pending_approvals = self._get_pending_approvals_count()
            st.metric(
                label="Pending Approvals",
                value=pending_approvals,
                delta=f"+{pending_approvals}" if pending_approvals > 0 else None
            )
        
        # Recent activity
        st.markdown("### 📈 Recent Activity")
        self._render_recent_activity()
        
        # Quick actions
        st.markdown("### ⚡ Quick Actions")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("🎨 Create New Architecture", key="dashboard_create", use_container_width=True):
                st.session_state.current_view = ViewType.CREATE.value
                st.rerun()
        
        with col2:
            if st.button("📊 View All Architectures", key="dashboard_list", use_container_width=True):
                st.session_state.current_view = ViewType.LIST.value
                st.rerun()
        
        with col3:
            if st.button("🤖 Check Agent Status", key="dashboard_agents", use_container_width=True):
                st.session_state.current_view = ViewType.AGENT_STATUS.value
                st.rerun()
    
    def render_create_view(self):
        """Render the create new architecture view"""
        st.markdown("## ➕ Create New Architecture")
        
        with st.form("create_architecture_form"):
            st.markdown("### Basic Information")
            
            col1, col2 = st.columns(2)
            with col1:
                name = st.text_input(
                    "Architecture Name *",
                    placeholder="e.g., Customer Management System"
                )
                type_selection = st.selectbox(
                    "Architecture Type",
                    ["Business Architecture", "Application Architecture", "Technology Architecture", "Integrated Architecture"]
                )
            
            with col2:
                version = st.text_input("Version", value="1.0.0")
                status = st.selectbox("Status", ["Draft", "In Review", "Approved", "Deprecated"])
            
            description = st.text_area(
                "Description",
                placeholder="Describe the purpose and scope of this architecture...",
                height=100
            )
            
            st.markdown("### Scope and Context")
            
            col1, col2 = st.columns(2)
            with col1:
                business_domain = st.text_input(
                    "Business Domain",
                    placeholder="e.g., Customer Service, Finance, Operations"
                )
                stakeholders = st.text_area(
                    "Key Stakeholders",
                    placeholder="List key stakeholders separated by commas",
                    height=80
                )
            
            with col2:
                technology_stack = st.multiselect(
                    "Technology Stack",
                    ["Java", "Python", "JavaScript", "C#", ".NET", "React", "Angular", "Vue.js", 
                     "Kubernetes", "Docker", "AWS", "Azure", "GCP"],
                    default=[]
                )
                complexity = st.select_slider(
                    "Complexity Level",
                    options=["Simple", "Moderate", "Complex", "Very Complex"],
                    value="Moderate"
                )
            
            st.markdown("### Architecture Layers")
            
            layers_to_include = st.multiselect(
                "Include Layers",
                ["Strategy", "Business", "Application", "Technology", "Physical", "Implementation & Migration"],
                default=["Business", "Application", "Technology"]
            )
            
            # Advanced options
            with st.expander("🔧 Advanced Options"):
                use_template = st.checkbox("Use Architecture Template")
                if use_template:
                    template = st.selectbox(
                        "Select Template",
                        ["Microservices Architecture", "Monolithic Architecture", "Event-Driven Architecture", 
                         "Layered Architecture", "Serverless Architecture"]
                    )
                
                auto_generate = st.checkbox("Auto-generate initial components", value=True)
                enable_collaboration = st.checkbox("Enable collaborative editing", value=True)
            
            # Submit button
            col1, col2, col3 = st.columns([2, 1, 1])
            with col2:
                submitted = st.form_submit_button("Create Architecture", use_container_width=True)
            with col3:
                if st.form_submit_button("Save as Draft", use_container_width=True):
                    st.info("Architecture saved as draft")
        
        if submitted and name:
            # Create new architecture
            new_architecture = {
                "id": len(st.session_state.get('architectures', [])) + 1,
                "name": name,
                "description": description,
                "type": type_selection,
                "version": version,
                "status": status,
                "business_domain": business_domain,
                "stakeholders": [s.strip() for s in stakeholders.split(",") if s.strip()],
                "technology_stack": technology_stack,
                "complexity": complexity,
                "layers": layers_to_include,
                "created_date": datetime.now().isoformat(),
                "created_recently": True
            }
            
            # Add to architectures list
            if 'architectures' not in st.session_state:
                st.session_state.architectures = []
            st.session_state.architectures.append(new_architecture)
            
            st.success(f"✅ Architecture '{name}' created successfully!")
            
            # Offer to navigate to the new architecture
            col1, col2 = st.columns(2)
            with col1:
                if st.button("📊 View Architecture", key="view_new_arch"):
                    st.session_state.selected_architecture = new_architecture
                    st.session_state.current_view = ViewType.VIEW.value
                    st.rerun()
            with col2:
                if st.button("🏠 Back to Dashboard", key="back_to_dashboard"):
                    st.session_state.current_view = ViewType.HOME.value
                    st.rerun()
    
    def render_list_view(self, architectures: List[Dict[str, Any]]):
        """Render the list all architectures view"""
        st.markdown("## 📋 All Architectures")
        
        if not architectures:
            st.info("No architectures found. Create your first architecture to get started!")
            if st.button("➕ Create New Architecture", key="empty_state_create"):
                st.session_state.current_view = ViewType.CREATE.value
                st.rerun()
            return
        
        # Search and filter controls
        col1, col2, col3 = st.columns([2, 1, 1])
        with col1:
            search_term = st.text_input("🔍 Search architectures", placeholder="Search by name or description...")
        with col2:
            type_filter = st.selectbox("Filter by Type", ["All Types"] + list(set([arch.get('type', 'Unknown') for arch in architectures])))
        with col3:
            sort_by = st.selectbox("Sort by", ["Name", "Created Date", "Type", "Status"])
        
        # Filter architectures based on search and filters
        filtered_architectures = self._filter_architectures(architectures, search_term, type_filter)
        
        # Sort architectures
        filtered_architectures = self._sort_architectures(filtered_architectures, sort_by)
        
        st.markdown(f"**Showing {len(filtered_architectures)} of {len(architectures)} architectures**")
        
        # Display architectures in a grid
        for i in range(0, len(filtered_architectures), 2):
            col1, col2 = st.columns(2)
            
            with col1:
                if i < len(filtered_architectures):
                    self._render_architecture_card(filtered_architectures[i])
            
            with col2:
                if i + 1 < len(filtered_architectures):
                    self._render_architecture_card(filtered_architectures[i + 1])
    
    def render_view_architecture(self, architecture: Dict[str, Any]):
        """Render the view specific architecture"""
        if not architecture:
            st.error("Architecture not found")
            return
        
        st.markdown(f"## 📊 {architecture['name']}")
        
        # Architecture details header
        col1, col2, col3 = st.columns([2, 1, 1])
        with col1:
            st.markdown(f"**Type:** {architecture.get('type', 'Unknown')}")
            st.markdown(f"**Version:** {architecture.get('version', '1.0.0')}")
        with col2:
            status_color = {"Draft": "🟡", "In Review": "🔵", "Approved": "🟢", "Deprecated": "🔴"}.get(architecture.get('status', 'Draft'), "⚪")
            st.markdown(f"**Status:** {status_color} {architecture.get('status', 'Draft')}")
        with col3:
            st.markdown(f"**Complexity:** {architecture.get('complexity', 'Moderate')}")
        
        # Description
        if architecture.get('description'):
            st.markdown("### 📝 Description")
            st.markdown(architecture['description'])
        
        # Architecture layers tabs
        st.markdown("### 🎨 Architecture Visualization")
        
        tabs = st.tabs(["📐 Overview", "🏢 Business Layer", "💻 Application Layer", "🔧 Technology Layer", "📊 Dependencies", "🛠️ Editor"])
        
        with tabs[0]:
            self._render_architecture_overview(architecture)
        
        with tabs[1]:
            self._render_business_layer_view(architecture)
        
        with tabs[2]:
            self._render_application_layer_view(architecture)
        
        with tabs[3]:
            self._render_technology_layer_view(architecture)
        
        with tabs[4]:
            self._render_dependencies_view(architecture)
        
        with tabs[5]:
            self._render_architecture_editor(architecture)
        
        # Architecture metadata
        with st.expander("📊 Architecture Details"):
            col1, col2 = st.columns(2)
            with col1:
                st.markdown("**Business Domain:**")
                st.write(architecture.get('business_domain', 'Not specified'))
                
                st.markdown("**Technology Stack:**")
                tech_stack = architecture.get('technology_stack', [])
                if tech_stack:
                    for tech in tech_stack:
                        st.write(f"• {tech}")
                else:
                    st.write("Not specified")
            
            with col2:
                st.markdown("**Stakeholders:**")
                stakeholders = architecture.get('stakeholders', [])
                if stakeholders:
                    for stakeholder in stakeholders:
                        st.write(f"• {stakeholder}")
                else:
                    st.write("Not specified")
                
                st.markdown("**Included Layers:**")
                layers = architecture.get('layers', [])
                for layer in layers:
                    st.write(f"• {layer}")
        
        # Action buttons
        st.markdown("### ⚡ Actions")
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            if st.button("✏️ Edit", key="edit_arch", use_container_width=True):
                st.info("Edit functionality coming soon!")
        
        with col2:
            if st.button("🔄 Version", key="version_arch", use_container_width=True):
                st.info("Version management coming soon!")
        
        with col3:
            if st.button("📤 Export", key="export_arch", use_container_width=True):
                st.info("Export functionality coming soon!")
        
        with col4:
            if st.button("🗑️ Delete", key="delete_arch", use_container_width=True):
                st.warning("Delete functionality coming soon!")
    
    def render_settings_view(self):
        """Render the settings and preferences view"""
        st.markdown("## ⚙️ Settings & Preferences")
        
        tabs = st.tabs(["👤 User Preferences", "🎨 Display Settings", "🔧 System Settings", "💾 Data Management", "🔌 Integrations"])
        
        with tabs[0]:
            st.markdown("### 👤 User Preferences")
            
            col1, col2 = st.columns(2)
            with col1:
                st.text_input("Display Name", value="Architecture User")
                st.text_input("Email", value="user@example.com")
                st.selectbox("Default View", ["Dashboard", "Architecture List", "Last Visited"])
            
            with col2:
                st.selectbox("Language", ["English", "Spanish", "French", "German"])
                st.selectbox("Time Zone", ["UTC", "EST", "PST", "GMT"])
                st.checkbox("Email Notifications", value=True)
        
        with tabs[1]:
            st.markdown("### 🎨 Display Settings")
            
            col1, col2 = st.columns(2)
            with col1:
                theme = st.selectbox("Theme", ["Light", "Dark", "Auto"])
                st.selectbox("Architecture Diagram Style", ["ArchiMate Standard", "Simplified", "Custom"])
                st.slider("Zoom Level", 50, 200, 100, 10)
            
            with col2:
                st.checkbox("Show Grid", value=True)
                st.checkbox("Show Relationships", value=True)
                st.checkbox("Auto-layout", value=False)
        
        with tabs[2]:
            st.markdown("### 🔧 System Settings")
            
            col1, col2 = st.columns(2)
            with col1:
                st.selectbox("Auto-save Interval", ["1 minute", "5 minutes", "10 minutes", "Disabled"])
                st.slider("Max Recent Architectures", 5, 20, 10)
                st.checkbox("Enable Debug Mode", value=False)
            
            with col2:
                st.selectbox("Default Architecture Type", ["Business", "Application", "Technology", "Integrated"])
                st.checkbox("Show Performance Metrics", value=False)
                st.checkbox("Enable Experimental Features", value=False)
        
        with tabs[3]:
            st.markdown("### 💾 Data Management")
            
            # Import backup management
            from utils.state_persistence import state_backup, state_persistence
            
            # Render backup interface
            state_backup.render_backup_interface()
            
            st.markdown("---")
            
            # Storage information
            st.markdown("### 📊 Storage Information")
            storage_info = state_persistence.get_storage_info()
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Stored Entries", storage_info['entry_count'])
            with col2:
                st.metric("Total Size", f"{storage_info['total_size_bytes']} bytes")
            with col3:
                if st.button("🧹 Clean Storage", use_container_width=True):
                    state_persistence.clear_expired_storage()
                    st.success("Cleaned expired storage entries")
                    st.rerun()
            
            # Data export/import
            st.markdown("### 📤 Data Export/Import")
            col1, col2 = st.columns(2)
            
            with col1:
                if st.button("📤 Export All Data", use_container_width=True):
                    from utils.session_manager import session_manager
                    export_data = session_manager.export_session_state()
                    st.download_button(
                        label="💾 Download Export",
                        data=export_data,
                        file_name=f"architecture_tool_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                        mime="application/json"
                    )
            
            with col2:
                uploaded_file = st.file_uploader(
                    "📥 Import Data",
                    type=['json'],
                    key="data_import"
                )
                if uploaded_file:
                    try:
                        import_data = uploaded_file.read().decode('utf-8')
                        from utils.session_manager import session_manager
                        if session_manager.import_session_state(import_data):
                            st.success("Data imported successfully!")
                            st.rerun()
                    except Exception as e:
                        st.error(f"Import failed: {e}")
        
        with tabs[4]:
            st.markdown("### 🔌 Integrations")
            st.info("Integration settings for external services will be available here")
    
    def render_agent_status_view(self):
        """Render the agent status and management view"""
        st.markdown("## 🤖 AI Agent Status")
        
        # Overall status
        agent_data = self._get_detailed_agent_status()
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Agents", agent_data['total'])
        with col2:
            st.metric("Online", agent_data['online'], delta=f"{agent_data['online_percentage']:.0f}%")
        with col3:
            st.metric("Response Time", f"{agent_data['avg_response_time']:.1f}s")
        
        # Individual agent status
        st.markdown("### 📋 Individual Agent Status")
        
        for agent in agent_data['agents']:
            with st.expander(f"{agent['icon']} {agent['name']} - {'🟢 Online' if agent['online'] else '🔴 Offline'}"):
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.markdown(f"**Status:** {'Online' if agent['online'] else 'Offline'}")
                    st.markdown(f"**Last Heartbeat:** {agent['last_heartbeat']}")
                
                with col2:
                    st.markdown(f"**Tasks Completed:** {agent['tasks_completed']}")
                    st.markdown(f"**Average Response:** {agent['response_time']:.1f}s")
                
                with col3:
                    st.markdown(f"**Memory Usage:** {agent['memory_usage']:.1f}%")
                    st.markdown(f"**CPU Usage:** {agent['cpu_usage']:.1f}%")
                
                if not agent['online']:
                    if st.button(f"🔄 Restart {agent['name']}", key=f"restart_{agent['name'].lower().replace(' ', '_')}"):
                        st.success(f"Restart request sent for {agent['name']}")
    
    def _filter_architectures(self, architectures: List[Dict[str, Any]], search_term: str, type_filter: str) -> List[Dict[str, Any]]:
        """Filter architectures based on search term and type filter"""
        filtered = architectures
        
        if search_term:
            filtered = [
                arch for arch in filtered
                if search_term.lower() in arch.get('name', '').lower() 
                or search_term.lower() in arch.get('description', '').lower()
            ]
        
        if type_filter != "All Types":
            filtered = [arch for arch in filtered if arch.get('type') == type_filter]
        
        return filtered
    
    def _sort_architectures(self, architectures: List[Dict[str, Any]], sort_by: str) -> List[Dict[str, Any]]:
        """Sort architectures based on the selected criteria"""
        if sort_by == "Name":
            return sorted(architectures, key=lambda x: x.get('name', '').lower())
        elif sort_by == "Created Date":
            return sorted(architectures, key=lambda x: x.get('created_date', ''), reverse=True)
        elif sort_by == "Type":
            return sorted(architectures, key=lambda x: x.get('type', ''))
        elif sort_by == "Status":
            return sorted(architectures, key=lambda x: x.get('status', ''))
        return architectures
    
    def _render_architecture_card(self, architecture: Dict[str, Any]):
        """Render a single architecture card"""
        with st.container():
            st.markdown(f"### 📊 {architecture['name']}")
            st.markdown(f"**Type:** {architecture.get('type', 'Unknown')}")
            st.markdown(f"**Status:** {architecture.get('status', 'Draft')}")
            
            if architecture.get('description'):
                description = architecture['description']
                if len(description) > 100:
                    description = description[:100] + "..."
                st.markdown(f"*{description}*")
            
            col1, col2 = st.columns(2)
            with col1:
                if st.button("👁️ View", key=f"view_{architecture['id']}", use_container_width=True):
                    st.session_state.selected_architecture = architecture
                    st.session_state.current_view = ViewType.VIEW.value
                    st.rerun()
            with col2:
                if st.button("✏️ Edit", key=f"edit_{architecture['id']}", use_container_width=True):
                    st.info("Edit functionality coming soon!")
            
            st.markdown("---")
    
    def _render_recent_activity(self):
        """Render recent activity feed"""
        activities = [
            {"action": "Created", "item": "Customer Service Architecture", "time": "2 hours ago", "user": "John Doe"},
            {"action": "Updated", "item": "E-commerce Platform", "time": "4 hours ago", "user": "Jane Smith"},
            {"action": "Approved", "item": "Payment Gateway Integration", "time": "1 day ago", "user": "Mike Johnson"},
            {"action": "Reviewed", "item": "Data Warehouse Architecture", "time": "2 days ago", "user": "Sarah Wilson"}
        ]
        
        for activity in activities:
            col1, col2, col3 = st.columns([2, 2, 1])
            with col1:
                st.markdown(f"**{activity['action']}** {activity['item']}")
            with col2:
                st.markdown(f"by {activity['user']}")
            with col3:
                st.markdown(f"*{activity['time']}*")
    
    def _get_active_changes_count(self) -> int:
        """Get count of active changes"""
        return 3  # Mock data
    
    def _get_pending_approvals_count(self) -> int:
        """Get count of pending approvals"""
        return 2  # Mock data
    
    def _get_agent_summary(self) -> Dict[str, int]:
        """Get agent status summary"""
        return {"total": 8, "online": 8}  # Mock data
    
    def _get_detailed_agent_status(self) -> Dict[str, Any]:
        """Get detailed agent status information"""
        agents = [
            {"name": "Business Analyst", "icon": "📊", "online": True, "tasks_completed": 45, "response_time": 1.2, "memory_usage": 67.3, "cpu_usage": 23.1, "last_heartbeat": "Just now"},
            {"name": "Business Architect", "icon": "🏢", "online": True, "tasks_completed": 32, "response_time": 1.8, "memory_usage": 54.2, "cpu_usage": 18.7, "last_heartbeat": "1 min ago"},
            {"name": "Application Architect", "icon": "💻", "online": True, "tasks_completed": 38, "response_time": 1.5, "memory_usage": 71.9, "cpu_usage": 31.4, "last_heartbeat": "Just now"},
            {"name": "Infrastructure Architect", "icon": "🔧", "online": True, "tasks_completed": 29, "response_time": 2.1, "memory_usage": 45.6, "cpu_usage": 15.2, "last_heartbeat": "2 min ago"},
            {"name": "Solution Architect", "icon": "🎯", "online": True, "tasks_completed": 41, "response_time": 1.7, "memory_usage": 58.3, "cpu_usage": 26.8, "last_heartbeat": "Just now"},
            {"name": "Project Manager", "icon": "📋", "online": True, "tasks_completed": 22, "response_time": 1.3, "memory_usage": 42.1, "cpu_usage": 12.5, "last_heartbeat": "1 min ago"},
            {"name": "Accountant", "icon": "💰", "online": True, "tasks_completed": 18, "response_time": 1.9, "memory_usage": 38.7, "cpu_usage": 9.3, "last_heartbeat": "3 min ago"},
            {"name": "Developer", "icon": "👨‍💻", "online": True, "tasks_completed": 52, "response_time": 1.4, "memory_usage": 76.2, "cpu_usage": 34.6, "last_heartbeat": "Just now"}
        ]
        
        online_count = sum(1 for agent in agents if agent['online'])
        avg_response_time = sum(agent['response_time'] for agent in agents) / len(agents)
        
        return {
            "total": len(agents),
            "online": online_count,
            "online_percentage": (online_count / len(agents)) * 100,
            "avg_response_time": avg_response_time,
            "agents": agents
        }
    
    def _render_architecture_overview(self, architecture: Dict[str, Any]):
        """Render complete architecture overview with ArchiMate visualization"""
        st.markdown("**Architecture Overview**")
        st.markdown("Complete architecture visualization with all layers and relationships.")
        
        # Get or create visualization manager
        viz_manager = get_visualization_manager()
        
        # Create visualization ID based on architecture
        viz_id = f"arch_{architecture.get('id', 'default')}_overview"
        
        # Load or create visualization
        visualization = viz_manager.load_visualization(viz_id)
        if not visualization:
            # Create sample visualization for demonstration
            visualization = create_sample_architecture()
            viz_manager.current_visualization = visualization
            viz_manager.save_current_visualization()
        
        # Render visualization controls
        col1, col2 = st.columns([3, 1])
        
        with col1:
            # Render the ArchiMate visualization
            if visualization:
                result = visualization.render_streamlit_component(
                    width=700,
                    height=500,
                    key=f"{viz_id}_overview"
                )
        
        with col2:
            # Render controls
            viz_manager.render_visualization_controls()
            
            # Quick stats
            if visualization:
                st.markdown("#### 📊 Quick Stats")
                total_elements = len(visualization.elements)
                total_relationships = len(visualization.relationships)
                
                st.metric("Elements", total_elements)
                st.metric("Relationships", total_relationships)
                
                # Layer breakdown
                from collections import Counter
                layer_counts = Counter(elem.layer.value for elem in visualization.elements.values())
                
                st.markdown("**Elements by Layer:**")
                for layer, count in layer_counts.items():
                    st.markdown(f"• {layer.title()}: {count}")
    
    def _render_business_layer_view(self, architecture: Dict[str, Any]):
        """Render business layer specific view"""
        st.markdown("**Business Layer Components**")
        st.markdown("Business processes, services, actors, and organizational units.")
        
        viz_manager = get_visualization_manager()
        viz_id = f"arch_{architecture.get('id', 'default')}_business"
        
        # Get current visualization or create filtered view
        if viz_manager.current_visualization:
            # Filter to show only business layer elements
            business_viz = ArchimateVisualization(engine=viz_manager.current_visualization.engine)
            
            # Copy business layer elements
            for element in viz_manager.current_visualization.elements.values():
                if element.layer.value == "business":
                    business_viz.add_element(element)
            
            # Copy relationships between business elements
            for relationship in viz_manager.current_visualization.relationships.values():
                if (relationship.source_id in business_viz.elements and 
                    relationship.target_id in business_viz.elements):
                    business_viz.add_relationship(relationship)
            
            # Render filtered visualization
            if business_viz.elements:
                business_viz.render_streamlit_component(
                    width=700,
                    height=400,
                    key=f"{viz_id}_business"
                )
            else:
                st.info("No business layer elements found in current architecture.")
        else:
            st.info("Load an architecture visualization to view business layer components.")
    
    def _render_application_layer_view(self, architecture: Dict[str, Any]):
        """Render application layer specific view"""
        st.markdown("**Application Layer Components**")
        st.markdown("Application services, components, interfaces, and data objects.")
        
        viz_manager = get_visualization_manager()
        viz_id = f"arch_{architecture.get('id', 'default')}_application"
        
        if viz_manager.current_visualization:
            # Filter to show only application layer elements
            app_viz = ArchimateVisualization(engine=viz_manager.current_visualization.engine)
            
            for element in viz_manager.current_visualization.elements.values():
                if element.layer.value == "application":
                    app_viz.add_element(element)
            
            for relationship in viz_manager.current_visualization.relationships.values():
                if (relationship.source_id in app_viz.elements and 
                    relationship.target_id in app_viz.elements):
                    app_viz.add_relationship(relationship)
            
            if app_viz.elements:
                app_viz.render_streamlit_component(
                    width=700,
                    height=400,
                    key=f"{viz_id}_application"
                )
            else:
                st.info("No application layer elements found in current architecture.")
        else:
            st.info("Load an architecture visualization to view application layer components.")
    
    def _render_technology_layer_view(self, architecture: Dict[str, Any]):
        """Render technology layer specific view"""
        st.markdown("**Technology Layer Components**")
        st.markdown("Infrastructure, platforms, technology services, and communication networks.")
        
        viz_manager = get_visualization_manager()
        viz_id = f"arch_{architecture.get('id', 'default')}_technology"
        
        if viz_manager.current_visualization:
            # Filter to show only technology layer elements
            tech_viz = ArchimateVisualization(engine=viz_manager.current_visualization.engine)
            
            for element in viz_manager.current_visualization.elements.values():
                if element.layer.value == "technology":
                    tech_viz.add_element(element)
            
            for relationship in viz_manager.current_visualization.relationships.values():
                if (relationship.source_id in tech_viz.elements and 
                    relationship.target_id in tech_viz.elements):
                    tech_viz.add_relationship(relationship)
            
            if tech_viz.elements:
                tech_viz.render_streamlit_component(
                    width=700,
                    height=400,
                    key=f"{viz_id}_technology"
                )
            else:
                st.info("No technology layer elements found in current architecture.")
        else:
            st.info("Load an architecture visualization to view technology layer components.")
    
    def _render_dependencies_view(self, architecture: Dict[str, Any]):
        """Render dependencies and relationships view"""
        st.markdown("**Dependencies and Relationships**")
        st.markdown("Component dependencies, data flows, and cross-layer relationships.")
        
        viz_manager = get_visualization_manager()
        
        if viz_manager.current_visualization:
            # Show relationship analysis
            relationships = viz_manager.current_visualization.relationships
            
            if relationships:
                st.markdown("#### 🔗 Relationship Analysis")
                
                # Relationship type breakdown
                from collections import Counter
                rel_types = Counter(rel.relationship_type for rel in relationships.values())
                
                col1, col2 = st.columns(2)
                
                with col1:
                    st.markdown("**Relationship Types:**")
                    for rel_type, count in rel_types.items():
                        st.markdown(f"• {rel_type.replace('_', ' ').title()}: {count}")
                
                with col2:
                    st.markdown("**Cross-Layer Dependencies:**")
                    cross_layer_count = 0
                    for rel in relationships.values():
                        source_elem = viz_manager.current_visualization.elements.get(rel.source_id)
                        target_elem = viz_manager.current_visualization.elements.get(rel.target_id)
                        if source_elem and target_elem and source_elem.layer != target_elem.layer:
                            cross_layer_count += 1
                    st.metric("Cross-layer relationships", cross_layer_count)
                
                # Detailed relationship list
                with st.expander("📋 Detailed Relationships"):
                    for rel in relationships.values():
                        source_elem = viz_manager.current_visualization.elements.get(rel.source_id)
                        target_elem = viz_manager.current_visualization.elements.get(rel.target_id)
                        
                        if source_elem and target_elem:
                            st.markdown(f"**{source_elem.name}** → **{target_elem.name}**")
                            st.markdown(f"Type: {rel.relationship_type.replace('_', ' ').title()}")
                            if rel.description:
                                st.markdown(f"Description: {rel.description}")
                            st.markdown("---")
                
                # Render visualization focused on relationships
                viz_manager.current_visualization.render_streamlit_component(
                    width=700,
                    height=400,
                    key=f"arch_{architecture.get('id', 'default')}_dependencies"
                )
            else:
                st.info("No relationships found in current architecture.")
        else:
            st.info("Load an architecture visualization to analyze dependencies.")
    
    def _render_architecture_editor(self, architecture: Dict[str, Any]):
        """Render architecture editor interface"""
        st.markdown("**Architecture Editor**")
        st.markdown("Create and modify architecture elements and relationships.")
        
        viz_manager = get_visualization_manager()
        
        # Editor tabs
        editor_tabs = st.tabs(["➕ Add Elements", "🔗 Add Relationships", "🔍 Inspector", "⚙️ Settings"])
        
        with editor_tabs[0]:
            self._render_element_creator(viz_manager)
        
        with editor_tabs[1]:
            self._render_relationship_creator(viz_manager)
        
        with editor_tabs[2]:
            viz_manager.render_element_inspector()
        
        with editor_tabs[3]:
            self._render_visualization_settings(viz_manager)
    
    def _render_element_creator(self, viz_manager):
        """Render element creation interface"""
        st.markdown("#### ➕ Add New Element")
        
        if not viz_manager.current_visualization:
            if st.button("🎨 Create New Visualization"):
                viz_manager.create_visualization("new_arch", VisualizationEngine.CYTOSCAPE)
                st.rerun()
            return
        
        with st.form("add_element_form"):
            col1, col2 = st.columns(2)
            
            with col1:
                element_name = st.text_input("Element Name", placeholder="e.g., User Management Service")
                element_description = st.text_area("Description", placeholder="Brief description of the element")
            
            with col2:
                from .archimate_visualization import ArchimateLayer, ArchimateElementType
                
                layer = st.selectbox("Layer", list(ArchimateLayer), format_func=lambda x: x.value.title())
                
                # Filter element types by layer
                if layer == ArchimateLayer.BUSINESS:
                    element_types = [
                        ArchimateElementType.BUSINESS_ACTOR,
                        ArchimateElementType.BUSINESS_ROLE,
                        ArchimateElementType.BUSINESS_SERVICE,
                        ArchimateElementType.BUSINESS_PROCESS,
                        ArchimateElementType.BUSINESS_FUNCTION,
                        ArchimateElementType.BUSINESS_OBJECT
                    ]
                elif layer == ArchimateLayer.APPLICATION:
                    element_types = [
                        ArchimateElementType.APPLICATION_COMPONENT,
                        ArchimateElementType.APPLICATION_SERVICE,
                        ArchimateElementType.APPLICATION_INTERFACE,
                        ArchimateElementType.APPLICATION_FUNCTION,
                        ArchimateElementType.DATA_OBJECT
                    ]
                elif layer == ArchimateLayer.TECHNOLOGY:
                    element_types = [
                        ArchimateElementType.NODE,
                        ArchimateElementType.DEVICE,
                        ArchimateElementType.SYSTEM_SOFTWARE,
                        ArchimateElementType.TECHNOLOGY_SERVICE,
                        ArchimateElementType.COMMUNICATION_NETWORK
                    ]
                else:
                    element_types = [ArchimateElementType.RESOURCE, ArchimateElementType.CAPABILITY]
                
                element_type = st.selectbox(
                    "Element Type", 
                    element_types,
                    format_func=lambda x: x.value.replace('_', ' ').title()
                )
            
            is_pending = st.checkbox("Mark as pending change", help="Element will be shown in gray until approved")
            
            if st.form_submit_button("Add Element"):
                if element_name:
                    from .archimate_visualization import ArchimateElement
                    import uuid
                    
                    element = ArchimateElement(
                        element_id=str(uuid.uuid4()),
                        name=element_name,
                        element_type=element_type,
                        layer=layer,
                        description=element_description,
                        position=(200, 200),  # Default position
                        is_pending=is_pending
                    )
                    
                    viz_manager.current_visualization.add_element(element)
                    viz_manager.save_current_visualization()
                    st.success(f"Added element: {element_name}")
                    st.rerun()
    
    def _render_relationship_creator(self, viz_manager):
        """Render relationship creation interface"""
        st.markdown("#### 🔗 Add New Relationship")
        
        if not viz_manager.current_visualization or not viz_manager.current_visualization.elements:
            st.info("Add some elements first before creating relationships.")
            return
        
        elements = list(viz_manager.current_visualization.elements.values())
        element_options = {f"{elem.name} ({elem.layer.value})": elem.element_id for elem in elements}
        
        with st.form("add_relationship_form"):
            col1, col2 = st.columns(2)
            
            with col1:
                source_name = st.selectbox("Source Element", list(element_options.keys()))
                target_name = st.selectbox("Target Element", list(element_options.keys()))
            
            with col2:
                relationship_types = [
                    "composition", "aggregation", "assignment", "serving",
                    "realization", "triggering", "flow", "access"
                ]
                rel_type = st.selectbox("Relationship Type", relationship_types)
                
                rel_description = st.text_input("Description (optional)")
            
            is_pending = st.checkbox("Mark as pending change", help="Relationship will be shown as dashed until approved")
            
            if st.form_submit_button("Add Relationship"):
                if source_name != target_name:
                    from .archimate_visualization import ArchimateRelationship
                    import uuid
                    
                    source_id = element_options[source_name]
                    target_id = element_options[target_name]
                    
                    relationship = ArchimateRelationship(
                        relationship_id=str(uuid.uuid4()),
                        source_id=source_id,
                        target_id=target_id,
                        relationship_type=rel_type,
                        description=rel_description,
                        is_pending=is_pending
                    )
                    
                    viz_manager.current_visualization.add_relationship(relationship)
                    viz_manager.save_current_visualization()
                    st.success(f"Added relationship: {rel_type}")
                    st.rerun()
                else:
                    st.error("Source and target must be different elements")
    
    def _render_visualization_settings(self, viz_manager):
        """Render visualization settings"""
        st.markdown("#### ⚙️ Visualization Settings")
        
        if not viz_manager.current_visualization:
            st.info("No active visualization to configure.")
            return
        
        # Layout settings
        st.markdown("**Layout Settings**")
        col1, col2 = st.columns(2)
        
        with col1:
            layout_algorithms = ["cose", "breadthfirst", "circle", "concentric", "grid", "random"]
            current_layout = viz_manager.current_visualization.layout_settings.get("algorithm", "cose")
            new_layout = st.selectbox("Layout Algorithm", layout_algorithms, index=layout_algorithms.index(current_layout))
            
            if new_layout != current_layout:
                viz_manager.current_visualization.layout_settings["algorithm"] = new_layout
        
        with col2:
            animate = st.checkbox("Animate Layout", value=viz_manager.current_visualization.layout_settings.get("animate", True))
            fit_view = st.checkbox("Fit to View", value=viz_manager.current_visualization.layout_settings.get("fit", True))
            
            viz_manager.current_visualization.layout_settings["animate"] = animate
            viz_manager.current_visualization.layout_settings["fit"] = fit_view
        
        # View settings
        st.markdown("**View Settings**")
        col1, col2 = st.columns(2)
        
        with col1:
            show_labels = st.checkbox("Show Labels", value=viz_manager.current_visualization.view_settings.get("show_labels", True))
            show_relationships = st.checkbox("Show Relationships", value=viz_manager.current_visualization.view_settings.get("show_relationships", True))
        
        with col2:
            enable_pan = st.checkbox("Enable Panning", value=viz_manager.current_visualization.view_settings.get("enable_pan", True))
            enable_zoom = st.checkbox("Enable Zooming", value=viz_manager.current_visualization.view_settings.get("enable_zoom", True))
        
        viz_manager.current_visualization.view_settings.update({
            "show_labels": show_labels,
            "show_relationships": show_relationships,
            "enable_pan": enable_pan,
            "enable_zoom": enable_zoom
        })
        
        # Data management
        st.markdown("**Data Management**")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("📥 Import Architecture"):
                st.info("Import functionality coming soon!")
        
        with col2:
            if st.button("📤 Export Architecture"):
                if viz_manager.current_visualization:
                    export_data = viz_manager.current_visualization.export_to_dict()
                    st.download_button(
                        "💾 Download JSON",
                        data=json.dumps(export_data, indent=2),
                        file_name=f"architecture_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                        mime="application/json"
                    )
        
        with col3:
            if st.button("🗑️ Clear All"):
                if st.button("⚠️ Confirm Clear", key="confirm_clear"):
                    viz_manager.current_visualization.elements.clear()
                    viz_manager.current_visualization.relationships.clear()
                    viz_manager.save_current_visualization()
                    st.success("Visualization cleared!")
                    st.rerun()