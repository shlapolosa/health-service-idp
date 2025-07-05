import streamlit as st
from typing import Dict, Any, Optional, List
import json
from datetime import datetime, timedelta
import uuid

class SessionManager:
    """Manages Streamlit session state and persistence"""
    
    def __init__(self):
        self.initialize_core_session_state()
    
    def initialize_core_session_state(self):
        """Initialize core session state variables"""
        # Session metadata
        if 'session_id' not in st.session_state:
            st.session_state.session_id = str(uuid.uuid4())
        
        if 'session_start_time' not in st.session_state:
            st.session_state.session_start_time = datetime.now()
        
        if 'last_activity' not in st.session_state:
            st.session_state.last_activity = datetime.now()
        
        # User preferences
        if 'user_preferences' not in st.session_state:
            st.session_state.user_preferences = {
                'theme': 'light',
                'language': 'en',
                'timezone': 'UTC',
                'auto_save': True,
                'notifications': True,
                'default_view': 'home',
                'show_tips': True
            }
        
        # Application state
        if 'app_state' not in st.session_state:
            st.session_state.app_state = {
                'initialized': True,
                'version': '1.0.0',
                'last_saved': None,
                'unsaved_changes': False
            }
        
        # Update last activity
        st.session_state.last_activity = datetime.now()
    
    def get_session_info(self) -> Dict[str, Any]:
        """Get session information"""
        duration = datetime.now() - st.session_state.session_start_time
        return {
            'session_id': st.session_state.session_id,
            'start_time': st.session_state.session_start_time,
            'duration': str(duration).split('.')[0],  # Remove microseconds
            'last_activity': st.session_state.last_activity,
            'user_preferences': st.session_state.user_preferences,
            'app_state': st.session_state.app_state
        }
    
    def set_preference(self, key: str, value: Any):
        """Set a user preference"""
        if 'user_preferences' not in st.session_state:
            st.session_state.user_preferences = {}
        
        st.session_state.user_preferences[key] = value
        self.mark_unsaved_changes()
    
    def get_preference(self, key: str, default: Any = None) -> Any:
        """Get a user preference"""
        if 'user_preferences' not in st.session_state:
            return default
        return st.session_state.user_preferences.get(key, default)
    
    def mark_unsaved_changes(self):
        """Mark that there are unsaved changes"""
        if 'app_state' not in st.session_state:
            st.session_state.app_state = {}
        st.session_state.app_state['unsaved_changes'] = True
    
    def mark_saved(self):
        """Mark that changes have been saved"""
        if 'app_state' not in st.session_state:
            st.session_state.app_state = {}
        st.session_state.app_state['unsaved_changes'] = False
        st.session_state.app_state['last_saved'] = datetime.now()
    
    def has_unsaved_changes(self) -> bool:
        """Check if there are unsaved changes"""
        if 'app_state' not in st.session_state:
            return False
        return st.session_state.app_state.get('unsaved_changes', False)
    
    def clear_session_data(self, keep_preferences: bool = True):
        """Clear session data"""
        session_keys_to_keep = ['session_id', 'session_start_time']
        
        if keep_preferences:
            session_keys_to_keep.extend(['user_preferences'])
        
        # Store keys to keep
        data_to_keep = {}
        for key in session_keys_to_keep:
            if key in st.session_state:
                data_to_keep[key] = st.session_state[key]
        
        # Clear all session state
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        
        # Restore kept data
        for key, value in data_to_keep.items():
            st.session_state[key] = value
        
        # Reinitialize
        self.initialize_core_session_state()
    
    def export_session_state(self) -> str:
        """Export session state to JSON string"""
        exportable_state = {}
        
        for key, value in st.session_state.items():
            try:
                # Only export JSON-serializable data
                json.dumps(value)
                exportable_state[key] = value
            except (TypeError, ValueError):
                # Skip non-serializable objects
                exportable_state[key] = f"<Non-serializable: {type(value).__name__}>"
        
        return json.dumps(exportable_state, indent=2, default=str)
    
    def import_session_state(self, json_data: str) -> bool:
        """Import session state from JSON string"""
        try:
            data = json.loads(json_data)
            
            # Only import safe keys (exclude sensitive or system keys)
            safe_keys = [
                'user_preferences', 'architectures', 'chat_history',
                'current_view', 'selected_architecture'
            ]
            
            for key in safe_keys:
                if key in data:
                    st.session_state[key] = data[key]
            
            return True
        except (json.JSONDecodeError, KeyError) as e:
            st.error(f"Failed to import session state: {e}")
            return False
    
    def cleanup_expired_data(self, max_age_hours: int = 24):
        """Clean up expired session data"""
        current_time = datetime.now()
        
        # Clean up old chat sessions
        if 'chat_sessions' in st.session_state:
            for session_id in list(st.session_state.chat_sessions.keys()):
                session_data = st.session_state.chat_sessions[session_id]
                if 'last_activity' in session_data:
                    last_activity = datetime.fromisoformat(session_data['last_activity'])
                    if (current_time - last_activity).total_seconds() > max_age_hours * 3600:
                        del st.session_state.chat_sessions[session_id]
    
    def render_session_info_widget(self):
        """Render session information widget"""
        with st.expander("📊 Session Information"):
            info = self.get_session_info()
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("**Session Details:**")
                st.text(f"ID: {info['session_id'][:8]}...")
                st.text(f"Duration: {info['duration']}")
                st.text(f"Started: {info['start_time'].strftime('%H:%M:%S')}")
            
            with col2:
                st.markdown("**Application State:**")
                st.text(f"Version: {info['app_state']['version']}")
                
                if info['app_state'].get('unsaved_changes'):
                    st.warning("⚠️ Unsaved changes")
                else:
                    st.success("✅ All changes saved")
                
                if info['app_state'].get('last_saved'):
                    last_saved = info['app_state']['last_saved']
                    st.text(f"Last saved: {last_saved.strftime('%H:%M:%S')}")
    
    def render_preferences_widget(self):
        """Render user preferences widget"""
        with st.expander("⚙️ User Preferences"):
            col1, col2 = st.columns(2)
            
            with col1:
                # Theme preference
                current_theme = self.get_preference('theme', 'light')
                new_theme = st.selectbox(
                    "Theme",
                    options=['light', 'dark', 'auto'],
                    index=['light', 'dark', 'auto'].index(current_theme)
                )
                if new_theme != current_theme:
                    self.set_preference('theme', new_theme)
                
                # Language preference
                current_lang = self.get_preference('language', 'en')
                new_lang = st.selectbox(
                    "Language",
                    options=['en', 'es', 'fr', 'de'],
                    index=['en', 'es', 'fr', 'de'].index(current_lang),
                    format_func=lambda x: {'en': 'English', 'es': 'Español', 'fr': 'Français', 'de': 'Deutsch'}[x]
                )
                if new_lang != current_lang:
                    self.set_preference('language', new_lang)
            
            with col2:
                # Auto-save preference
                current_autosave = self.get_preference('auto_save', True)
                new_autosave = st.checkbox("Auto-save", value=current_autosave)
                if new_autosave != current_autosave:
                    self.set_preference('auto_save', new_autosave)
                
                # Notifications preference
                current_notifications = self.get_preference('notifications', True)
                new_notifications = st.checkbox("Enable notifications", value=current_notifications)
                if new_notifications != current_notifications:
                    self.set_preference('notifications', new_notifications)
                
                # Show tips preference
                current_tips = self.get_preference('show_tips', True)
                new_tips = st.checkbox("Show helpful tips", value=current_tips)
                if new_tips != current_tips:
                    self.set_preference('show_tips', new_tips)
            
            # Export/Import buttons
            st.markdown("---")
            col1, col2, col3 = st.columns(3)
            
            with col1:
                if st.button("📤 Export Session", use_container_width=True):
                    session_data = self.export_session_state()
                    st.download_button(
                        label="💾 Download",
                        data=session_data,
                        file_name=f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                        mime="application/json"
                    )
            
            with col2:
                uploaded_file = st.file_uploader(
                    "📥 Import Session",
                    type=['json'],
                    key="session_import"
                )
                if uploaded_file:
                    session_data = uploaded_file.read().decode('utf-8')
                    if self.import_session_state(session_data):
                        st.success("Session imported successfully!")
                        st.rerun()
            
            with col3:
                if st.button("🗑️ Clear Session", use_container_width=True):
                    if st.button("⚠️ Confirm Clear", use_container_width=True):
                        self.clear_session_data(keep_preferences=True)
                        st.success("Session cleared!")
                        st.rerun()

class StateValidator:
    """Validates and fixes session state issues"""
    
    @staticmethod
    def validate_and_fix_state():
        """Validate session state and fix common issues"""
        issues_found = []
        
        # Check for required keys
        required_keys = {
            'architectures': list,
            'current_view': str,
            'user_preferences': dict
        }
        
        for key, expected_type in required_keys.items():
            if key not in st.session_state:
                st.session_state[key] = expected_type()
                issues_found.append(f"Missing key '{key}' - initialized with default value")
            elif not isinstance(st.session_state[key], expected_type):
                st.session_state[key] = expected_type()
                issues_found.append(f"Invalid type for '{key}' - reset to default")
        
        # Validate chat history format
        if 'chat_history' in st.session_state:
            from components.chat import ChatMessage
            valid_messages = []
            
            for msg in st.session_state.chat_history:
                if isinstance(msg, ChatMessage):
                    valid_messages.append(msg)
                elif isinstance(msg, dict) and 'role' in msg and 'content' in msg:
                    # Convert old format to new format
                    try:
                        valid_messages.append(ChatMessage.from_dict(msg))
                    except Exception:
                        issues_found.append(f"Invalid chat message format - skipped")
                else:
                    issues_found.append(f"Invalid chat message format - skipped")
            
            st.session_state.chat_history = valid_messages
        
        # Validate architectures format
        if 'architectures' in st.session_state:
            valid_architectures = []
            
            for arch in st.session_state.architectures:
                if isinstance(arch, dict) and 'id' in arch and 'name' in arch:
                    valid_architectures.append(arch)
                else:
                    issues_found.append("Invalid architecture format - skipped")
            
            st.session_state.architectures = valid_architectures
        
        return issues_found

# Global session manager instance
session_manager = SessionManager()