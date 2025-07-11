"""
Infrastructure Layer - GitHub Client Implementation
Handles GitHub API communication for repository dispatch
"""

import logging
from typing import Dict, Tuple

import requests

from ..application.use_cases import GitHubDispatcherInterface

logger = logging.getLogger(__name__)


class GitHubApiClient(GitHubDispatcherInterface):
    """GitHub API client for repository dispatch operations."""

    def __init__(self, token: str, repository: str, timeout: int = 10):
        """Initialize GitHub client with configuration."""
        self.token = token
        self.repository = repository  # Format: owner/repo
        self.timeout = timeout
        self.base_url = "https://api.github.com"

    def trigger_vcluster_creation(self, payload: Dict) -> Tuple[bool, str]:
        """Trigger VCluster creation via GitHub repository dispatch."""
        url = f"{self.base_url}/repos/{self.repository}/dispatches"
        headers = {
            "Authorization": f"token {self.token}",
            "Accept": "application/vnd.github.v3+json",
            "Content-Type": "application/json",
        }

        try:
            logger.info(
                f"Triggering GitHub repository dispatch for VCluster: {payload.get('client_payload', {}).get('vcluster_name', 'unknown')}"
            )

            response = requests.post(
                url, headers=headers, json=payload, timeout=self.timeout
            )

            if response.status_code == 204:
                success_msg = "VCluster creation triggered successfully"
                logger.info(f"✅ {success_msg}")
                return True, success_msg
            else:
                error_msg = (
                    f"GitHub API error: {response.status_code} - {response.text}"
                )
                logger.error(f"❌ {error_msg}")
                return False, error_msg

        except requests.exceptions.Timeout:
            error_msg = f"GitHub API request timed out after {self.timeout} seconds"
            logger.error(error_msg)
            return False, error_msg

        except requests.exceptions.ConnectionError:
            error_msg = "Failed to connect to GitHub API"
            logger.error(error_msg)
            return False, error_msg

        except requests.RequestException as e:
            error_msg = f"GitHub API request failed: {str(e)}"
            logger.error(error_msg)
            return False, error_msg

        except Exception as e:
            error_msg = f"Unexpected error calling GitHub API: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return False, error_msg

    def validate_configuration(self) -> Tuple[bool, str]:
        """Validate GitHub client configuration."""
        if not self.token:
            return False, "GitHub token not configured"

        if not self.repository or "/" not in self.repository:
            return False, "Invalid repository format (should be owner/repo)"

        # Test API connectivity
        url = f"{self.base_url}/repos/{self.repository}"
        headers = {
            "Authorization": f"token {self.token}",
            "Accept": "application/vnd.github.v3+json",
        }

        try:
            response = requests.get(url, headers=headers, timeout=self.timeout)

            if response.status_code == 200:
                return True, "GitHub configuration valid"
            elif response.status_code == 401:
                return False, "Invalid GitHub token"
            elif response.status_code == 404:
                return (
                    False,
                    f"Repository {self.repository} not found or not accessible",
                )
            else:
                return False, f"GitHub API returned status {response.status_code}"

        except Exception as e:
            return False, f"Failed to validate GitHub configuration: {str(e)}"
