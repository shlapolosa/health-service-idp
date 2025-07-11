"""
Infrastructure Layer - Slack Signature Verifier
Implements Slack request signature verification
"""

import hashlib
import hmac
import logging
import time
from typing import Optional

from ..application.use_cases import SlackVerifierInterface

logger = logging.getLogger(__name__)


class SlackSignatureVerifier(SlackVerifierInterface):
    """Verifies Slack request signatures using HMAC-SHA256."""

    def __init__(self, signing_secret: str):
        """Initialize verifier with Slack signing secret."""
        self.signing_secret = signing_secret.encode("utf-8")

    def verify_request(
        self, request_data: bytes, timestamp: str, signature: str
    ) -> bool:
        """Verify Slack request signature."""
        try:
            # Check timestamp to prevent replay attacks (within 5 minutes)
            request_timestamp = int(timestamp)
            current_timestamp = int(time.time())

            if abs(current_timestamp - request_timestamp) > 300:
                logger.warning(f"Request timestamp too old: {request_timestamp}")
                return False

            # Create signature base string
            sig_basestring = f"v0:{timestamp}:".encode("utf-8") + request_data

            # Compute expected signature
            expected_signature = (
                "v0="
                + hmac.new(
                    self.signing_secret, sig_basestring, hashlib.sha256
                ).hexdigest()
            )

            # Compare signatures using constant-time comparison
            is_valid = hmac.compare_digest(expected_signature, signature)

            if not is_valid:
                logger.warning(
                    f"Invalid signature. Expected: {expected_signature[:20]}..., Got: {signature[:20]}..."
                )

            return is_valid

        except (ValueError, TypeError) as e:
            logger.error(f"Error verifying Slack signature: {e}")
            return False

        except Exception as e:
            logger.error(
                f"Unexpected error verifying Slack signature: {e}", exc_info=True
            )
            return False
