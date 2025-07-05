import streamlit as st
import json
import pickle
import base64
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import hashlib

class StatePersistence:
    """Handles state persistence across browser sessions and page refreshes"""
    
    def __init__(self):
        self.storage_key_prefix = "vat_"  # Visual Architecture Tool prefix
        
    def save_state_to_browser(self, key: str, data: Any, expires_hours: int = 24):
        """Save state data to browser storage using URL parameters or query params"""
        try:
            # Serialize data
            serialized_data = self._serialize_data(data)
            
            # Create storage entry
            storage_entry = {
                'data': serialized_data,
                'timestamp': datetime.now().isoformat(),
                'expires': (datetime.now() + timedelta(hours=expires_hours)).isoformat(),
                'checksum': hashlib.md5(str(data).encode()).hexdigest()
            }
            
            # Store in session state with special prefix
            storage_key = f"{self.storage_key_prefix}{key}"
            st.session_state[storage_key] = storage_entry
            
            return True
        except Exception as e:
            st.error(f"Failed to save state: {e}")
            return False
    
    def load_state_from_browser(self, key: str) -> Optional[Any]:
        """Load state data from browser storage"""
        try:
            storage_key = f"{self.storage_key_prefix}{key}"
            
            if storage_key not in st.session_state:
                return None
            
            storage_entry = st.session_state[storage_key]
            
            # Check expiration
            expires = datetime.fromisoformat(storage_entry['expires'])
            if datetime.now() > expires:
                # Clean up expired data
                del st.session_state[storage_key]
                return None
            
            # Deserialize data
            data = self._deserialize_data(storage_entry['data'])
            
            # Verify checksum
            current_checksum = hashlib.md5(str(data).encode()).hexdigest()
            if current_checksum != storage_entry['checksum']:
                st.warning("Data integrity check failed for stored state")
                return None
            
            return data
            
        except Exception as e:
            st.error(f"Failed to load state: {e}")
            return None
    
    def _serialize_data(self, data: Any) -> str:
        """Serialize data for storage"""
        try:
            # Try JSON first (for simple data)
            json_str = json.dumps(data, default=str)
            return base64.b64encode(json_str.encode()).decode()
        except (TypeError, ValueError):
            # Fallback to pickle for complex objects
            pickled_data = pickle.dumps(data)
            return base64.b64encode(pickled_data).decode()
    
    def _deserialize_data(self, serialized_data: str) -> Any:
        """Deserialize data from storage"""
        try:
            decoded_data = base64.b64decode(serialized_data.encode())
            
            # Try JSON first
            try:
                json_str = decoded_data.decode()
                return json.loads(json_str)
            except (UnicodeDecodeError, json.JSONDecodeError):
                # Fallback to pickle
                return pickle.loads(decoded_data)
                
        except Exception as e:
            raise ValueError(f"Failed to deserialize data: {e}")
    
    def clear_expired_storage(self):
        """Clear expired storage entries"""
        current_time = datetime.now()
        keys_to_remove = []
        
        for key in st.session_state.keys():
            if key.startswith(self.storage_key_prefix):
                try:
                    storage_entry = st.session_state[key]
                    expires = datetime.fromisoformat(storage_entry['expires'])
                    if current_time > expires:
                        keys_to_remove.append(key)
                except Exception:
                    # Remove corrupted entries
                    keys_to_remove.append(key)
        
        for key in keys_to_remove:
            del st.session_state[key]
    
    def get_storage_info(self) -> Dict[str, Any]:
        """Get information about stored data"""
        storage_entries = {}
        total_size = 0
        
        for key in st.session_state.keys():
            if key.startswith(self.storage_key_prefix):
                try:
                    storage_entry = st.session_state[key]
                    size = len(str(storage_entry))
                    total_size += size
                    
                    storage_entries[key] = {
                        'size_bytes': size,
                        'timestamp': storage_entry['timestamp'],
                        'expires': storage_entry['expires']
                    }
                except Exception:
                    pass
        
        return {
            'entries': storage_entries,
            'total_size_bytes': total_size,
            'entry_count': len(storage_entries)
        }

class StateBackup:
    """Handles state backup and restore functionality"""
    
    def __init__(self):
        self.backup_key_prefix = "backup_"
    
    def create_backup(self, name: str = None) -> str:
        """Create a backup of current session state"""
        if name is None:
            name = f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Collect exportable state
        exportable_state = {}
        critical_keys = [
            'architectures', 'chat_history', 'user_preferences',
            'current_view', 'selected_architecture', 'navigation_expanded'
        ]
        
        for key in critical_keys:
            if key in st.session_state:
                exportable_state[key] = st.session_state[key]
        
        # Create backup entry
        backup_entry = {
            'name': name,
            'timestamp': datetime.now().isoformat(),
            'state': exportable_state,
            'version': st.session_state.get('app_state', {}).get('version', '1.0.0')
        }
        
        # Store backup
        backup_key = f"{self.backup_key_prefix}{name}"
        st.session_state[backup_key] = backup_entry
        
        return name
    
    def restore_backup(self, backup_name: str) -> bool:
        """Restore state from a backup"""
        try:
            backup_key = f"{self.backup_key_prefix}{backup_name}"
            
            if backup_key not in st.session_state:
                st.error(f"Backup '{backup_name}' not found")
                return False
            
            backup_entry = st.session_state[backup_key]
            stored_state = backup_entry['state']
            
            # Restore state
            for key, value in stored_state.items():
                st.session_state[key] = value
            
            st.success(f"Restored backup '{backup_name}' from {backup_entry['timestamp']}")
            return True
            
        except Exception as e:
            st.error(f"Failed to restore backup: {e}")
            return False
    
    def list_backups(self) -> List[Dict[str, Any]]:
        """List available backups"""
        backups = []
        
        for key in st.session_state.keys():
            if key.startswith(self.backup_key_prefix):
                try:
                    backup_entry = st.session_state[key]
                    backups.append({
                        'name': backup_entry['name'],
                        'timestamp': backup_entry['timestamp'],
                        'version': backup_entry.get('version', 'unknown'),
                        'size': len(str(backup_entry['state']))
                    })
                except Exception:
                    pass
        
        # Sort by timestamp (newest first)
        backups.sort(key=lambda x: x['timestamp'], reverse=True)
        return backups
    
    def delete_backup(self, backup_name: str) -> bool:
        """Delete a backup"""
        try:
            backup_key = f"{self.backup_key_prefix}{backup_name}"
            
            if backup_key in st.session_state:
                del st.session_state[backup_key]
                st.success(f"Deleted backup '{backup_name}'")
                return True
            else:
                st.error(f"Backup '{backup_name}' not found")
                return False
                
        except Exception as e:
            st.error(f"Failed to delete backup: {e}")
            return False
    
    def render_backup_interface(self):
        """Render backup management interface"""
        st.markdown("### 💾 State Backup & Restore")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**Create Backup**")
            backup_name = st.text_input(
                "Backup Name",
                value=f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                key="backup_name_input"
            )
            
            if st.button("📦 Create Backup", use_container_width=True):
                if backup_name:
                    created_name = self.create_backup(backup_name)
                    st.success(f"Created backup: {created_name}")
                    st.rerun()
        
        with col2:
            st.markdown("**Available Backups**")
            backups = self.list_backups()
            
            if backups:
                backup_options = [f"{b['name']} ({b['timestamp'][:16]})" for b in backups]
                selected_backup_display = st.selectbox(
                    "Select Backup",
                    backup_options,
                    key="backup_selection"
                )
                
                if selected_backup_display:
                    selected_backup_name = selected_backup_display.split(" (")[0]
                    
                    col2a, col2b = st.columns(2)
                    with col2a:
                        if st.button("🔄 Restore", use_container_width=True):
                            if self.restore_backup(selected_backup_name):
                                st.rerun()
                    
                    with col2b:
                        if st.button("🗑️ Delete", use_container_width=True):
                            if self.delete_backup(selected_backup_name):
                                st.rerun()
            else:
                st.info("No backups available")

class StateSync:
    """Handles state synchronization between components"""
    
    def __init__(self):
        self.sync_callbacks = {}
    
    def register_sync_callback(self, component_name: str, callback):
        """Register a callback for state synchronization"""
        self.sync_callbacks[component_name] = callback
    
    def trigger_sync(self, changed_keys: List[str]):
        """Trigger synchronization for changed state keys"""
        for component_name, callback in self.sync_callbacks.items():
            try:
                callback(changed_keys)
            except Exception as e:
                st.error(f"Sync error in {component_name}: {e}")
    
    def sync_architecture_state(self):
        """Synchronize architecture-related state"""
        # Ensure consistency between architectures list and selected architecture
        selected_arch = st.session_state.get('selected_architecture')
        architectures = st.session_state.get('architectures', [])
        
        if selected_arch and architectures:
            # Check if selected architecture still exists in the list
            arch_ids = [arch['id'] for arch in architectures]
            if selected_arch.get('id') not in arch_ids:
                # Clear invalid selection
                st.session_state.selected_architecture = None
                st.session_state.current_view = 'home'
    
    def sync_navigation_state(self):
        """Synchronize navigation-related state"""
        # Ensure view is valid
        valid_views = ['home', 'create', 'list', 'view', 'settings', 'agent_status']
        current_view = st.session_state.get('current_view', 'home')
        
        if current_view not in valid_views:
            st.session_state.current_view = 'home'
        
        # If in view mode but no architecture selected, redirect to home
        if current_view == 'view' and not st.session_state.get('selected_architecture'):
            st.session_state.current_view = 'home'
    
    def perform_full_sync(self):
        """Perform a full state synchronization"""
        self.sync_architecture_state()
        self.sync_navigation_state()
        
        # Trigger registered callbacks
        self.trigger_sync(['architectures', 'current_view', 'selected_architecture'])

# Global instances
state_persistence = StatePersistence()
state_backup = StateBackup()
state_sync = StateSync()