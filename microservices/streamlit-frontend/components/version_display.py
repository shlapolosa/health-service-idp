"""
Version Display Component

Displays the application version information in the bottom-right corner
of the Streamlit interface with build details and traceability.
"""

import os
import streamlit as st
from datetime import datetime
from typing import Dict, Optional

class VersionDisplay:
    """Component for displaying application version information"""
    
    def __init__(self):
        self.version = os.environ.get('APP_VERSION', 'development')
        self.commit = os.environ.get('APP_COMMIT', 'unknown')
        self.build_date = os.environ.get('APP_BUILD_DATE', 'unknown')
        
    def get_version_info(self) -> Dict[str, str]:
        """Get comprehensive version information"""
        return {
            'version': self.version,
            'commit': self.commit,
            'build_date': self.build_date,
            'environment': 'production' if self.version != 'development' else 'development'
        }
    
    def get_short_version(self) -> str:
        """Get short version for display"""
        if self.version == 'development':
            return 'dev'
        return self.version
    
    def get_commit_short(self) -> str:
        """Get short commit hash for display"""
        if self.commit == 'unknown' or len(self.commit) < 7:
            return self.commit
        return self.commit[:7]
    
    def render_version_badge(self) -> None:
        """Render the version badge in bottom-right corner"""
        version_info = self.get_version_info()
        short_version = self.get_short_version()
        short_commit = self.get_commit_short()
        
        # Format build date for tooltip
        build_date_formatted = self.build_date
        if self.build_date != 'unknown':
            try:
                # Parse ISO format and format for display
                dt = datetime.fromisoformat(self.build_date.replace('Z', '+00:00'))
                build_date_formatted = dt.strftime('%Y-%m-%d %H:%M UTC')
            except:
                build_date_formatted = self.build_date
        
        # Create tooltip content
        tooltip_content = f"""
**Version Information:**
- **Version:** {version_info['version']}
- **Commit:** {version_info['commit']}
- **Built:** {build_date_formatted}
- **Environment:** {version_info['environment']}
"""
        
        # CSS styling for version badge
        version_css = """
        <style>
        .version-badge {
            position: fixed;
            bottom: 20px;
            right: 20px;
            background: rgba(255, 255, 255, 0.9);
            border: 1px solid #e1e5e9;
            border-radius: 20px;
            padding: 8px 16px;
            font-family: 'Source Code Pro', monospace;
            font-size: 12px;
            color: #555;
            z-index: 999999;
            backdrop-filter: blur(10px);
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
            cursor: pointer;
            transition: all 0.2s ease;
            user-select: none;
        }
        
        .version-badge:hover {
            background: rgba(255, 255, 255, 1);
            box-shadow: 0 4px 16px rgba(0, 0, 0, 0.15);
            transform: translateY(-1px);
        }
        
        .version-text {
            display: flex;
            align-items: center;
            gap: 6px;
        }
        
        .version-icon {
            font-size: 10px;
            opacity: 0.7;
        }
        
        .version-number {
            font-weight: 600;
            color: #1f77b4;
        }
        
        .commit-hash {
            color: #888;
            font-size: 10px;
        }
        
        /* Dark mode support */
        @media (prefers-color-scheme: dark) {
            .version-badge {
                background: rgba(30, 30, 30, 0.9);
                border-color: #404040;
                color: #ccc;
            }
            
            .version-badge:hover {
                background: rgba(30, 30, 30, 1);
            }
            
            .version-number {
                color: #6ab7ff;
            }
        }
        
        /* Mobile responsiveness */
        @media (max-width: 768px) {
            .version-badge {
                bottom: 10px;
                right: 10px;
                font-size: 10px;
                padding: 6px 12px;
            }
        }
        </style>
        """
        
        # HTML for version badge
        version_html = f"""
        <div class="version-badge" title="{tooltip_content.strip()}">
            <div class="version-text">
                <span class="version-icon">🏷️</span>
                <span class="version-number">v{short_version}</span>
                {f'<span class="commit-hash">({short_commit})</span>' if short_commit != 'unknown' else ''}
            </div>
        </div>
        """
        
        # Render the version badge
        st.markdown(version_css, unsafe_allow_html=True)
        st.markdown(version_html, unsafe_allow_html=True)
    
    def render_detailed_info(self) -> None:
        """Render detailed version information in sidebar or expander"""
        version_info = self.get_version_info()
        
        with st.expander("📋 Version Information", expanded=False):
            st.markdown(f"**Version:** `{version_info['version']}`")
            st.markdown(f"**Commit:** `{version_info['commit']}`")
            st.markdown(f"**Build Date:** `{self.build_date}`")
            st.markdown(f"**Environment:** `{version_info['environment']}`")
            
            if version_info['commit'] != 'unknown' and len(version_info['commit']) > 7:
                # Link to commit (if we know the repository)
                commit_url = f"https://github.com/shlapolosa/health-service-idp/commit/{version_info['commit']}"
                st.markdown(f"**View Commit:** [GitHub]({commit_url})")

# Convenience function for easy import
def render_version_display():
    """Convenience function to render version display"""
    version_display = VersionDisplay()
    version_display.render_version_badge()

def render_detailed_version_info():
    """Convenience function to render detailed version info"""
    version_display = VersionDisplay()
    version_display.render_detailed_info()