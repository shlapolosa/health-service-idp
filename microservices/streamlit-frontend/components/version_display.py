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
    
    def render_version_footer(self) -> None:
        """Render the version information in a footer at the bottom of the page"""
        version_info = self.get_version_info()
        short_version = self.get_short_version()
        short_commit = self.get_commit_short()
        
        # Format build date for display
        build_date_formatted = self.build_date
        build_date_short = "unknown"
        if self.build_date != 'unknown':
            try:
                # Parse ISO format and format for display
                dt = datetime.fromisoformat(self.build_date.replace('Z', '+00:00'))
                build_date_formatted = dt.strftime('%Y-%m-%d %H:%M UTC')
                build_date_short = dt.strftime('%Y-%m-%d')
            except:
                build_date_formatted = self.build_date
                build_date_short = self.build_date
        
        # CSS styling for footer
        footer_css = """
        <style>
        .version-footer {
            position: relative;
            width: 100%;
            padding: 16px 20px;
            background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
            border-top: 1px solid #dee2e6;
            margin-top: 40px;
            font-family: 'Source Code Pro', 'Courier New', monospace;
            font-size: 12px;
            color: #6c757d;
            text-align: center;
        }
        
        .version-content {
            display: flex;
            justify-content: center;
            align-items: center;
            gap: 20px;
            flex-wrap: wrap;
        }
        
        .version-item {
            display: flex;
            align-items: center;
            gap: 6px;
        }
        
        .version-label {
            font-weight: 600;
            color: #495057;
        }
        
        .version-value {
            font-weight: 500;
            color: #1f77b4;
        }
        
        .commit-link {
            text-decoration: none;
            color: #1f77b4;
            transition: color 0.2s ease;
        }
        
        .commit-link:hover {
            color: #0d47a1;
            text-decoration: underline;
        }
        
        .version-divider {
            height: 12px;
            width: 1px;
            background: #dee2e6;
        }
        
        /* Dark mode support */
        @media (prefers-color-scheme: dark) {
            .version-footer {
                background: linear-gradient(135deg, #2b2b2b 0%, #1a1a1a 100%);
                border-top-color: #404040;
                color: #adb5bd;
            }
            
            .version-label {
                color: #e9ecef;
            }
            
            .version-value {
                color: #6ab7ff;
            }
            
            .commit-link {
                color: #6ab7ff;
            }
            
            .commit-link:hover {
                color: #90caf9;
            }
            
            .version-divider {
                background: #404040;
            }
        }
        
        /* Mobile responsiveness */
        @media (max-width: 768px) {
            .version-footer {
                padding: 12px 16px;
                font-size: 11px;
            }
            
            .version-content {
                gap: 12px;
            }
            
            .version-divider {
                display: none;
            }
        }
        </style>
        """
        
        # Create commit link if commit is available
        commit_display = short_commit
        if version_info['commit'] != 'unknown' and len(version_info['commit']) >= 7:
            commit_url = f"https://github.com/shlapolosa/health-service-idp/commit/{version_info['commit']}"
            commit_display = f'<a href="{commit_url}" target="_blank" class="commit-link">{short_commit}</a>'
        
        # HTML for version footer
        footer_html = f"""
        <div class="version-footer">
            <div class="version-content">
                <div class="version-item">
                    <span class="version-label">Version:</span>
                    <span class="version-value">v{short_version}</span>
                </div>
                <div class="version-divider"></div>
                <div class="version-item">
                    <span class="version-label">Commit:</span>
                    <span class="version-value">{commit_display}</span>
                </div>
                <div class="version-divider"></div>
                <div class="version-item">
                    <span class="version-label">Built:</span>
                    <span class="version-value">{build_date_short}</span>
                </div>
                <div class="version-divider"></div>
                <div class="version-item">
                    <span class="version-label">Environment:</span>
                    <span class="version-value">{version_info['environment']}</span>
                </div>
            </div>
        </div>
        """
        
        # Render the version footer
        st.markdown(footer_css, unsafe_allow_html=True)
        st.markdown(footer_html, unsafe_allow_html=True)
    
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
def render_version_footer():
    """Convenience function to render version footer"""
    version_display = VersionDisplay()
    version_display.render_version_footer()

def render_detailed_version_info():
    """Convenience function to render detailed version info"""
    version_display = VersionDisplay()
    version_display.render_detailed_info()