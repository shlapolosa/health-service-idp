"""Best-effort platform-secret loader for the realtime transport path.

This is the subset of agent_common.secret_loader the realtime path uses:
``load_realtime_platform_secrets`` + ``configure_config_from_secrets``. The
binding env (envFrom: KAFKA_BOOTSTRAP_SERVERS, CONSUME_*/PRODUCE_*, ...) is the
primary source of truth; this loader is a SUPPLEMENT that reads Kubernetes
secrets mounted at /var/secrets and never raises into startup.

Cross-component discovery / injection helpers from agent_common are dropped —
they are scaffolding tools, not part of the runtime transport.
"""

import os
import logging
from typing import Dict, Any, Optional
from pathlib import Path

logger = logging.getLogger(__name__)


class PlatformSecretLoader:
    """Loads secrets from Kubernetes mounted volumes or environment variables
    following the {name}-{service}-secret naming pattern of the realtime platform.
    """

    def __init__(self, platform_name: Optional[str] = None):
        self.platform_name = platform_name
        self.secret_mount_path = "/var/secrets"

    def generate_secret_name(self, component_name: str, service_name: str) -> str:
        return f"{component_name}-{service_name}-secret"

    async def load_platform_secrets(self, platform_name: Optional[str] = None) -> Dict[str, Any]:
        platform = platform_name or self.platform_name
        if not platform:
            raise ValueError("Platform name must be provided")

        secrets: Dict[str, Any] = {}
        secrets.update(await self._load_kafka_secrets(platform))
        secrets.update(await self._load_mqtt_secrets(platform))
        secrets.update(await self._load_database_secrets(platform))
        logger.info(f"Loaded secrets for platform: {platform}")
        return secrets

    async def _load_kafka_secrets(self, platform_name: str) -> Dict[str, Any]:
        s = await self._load_mounted_secret(self.generate_secret_name(platform_name, "kafka"))
        if s:
            return {
                "kafka_bootstrap_servers": s.get("KAFKA_BOOTSTRAP_SERVERS"),
                "kafka_schema_registry_url": s.get("KAFKA_SCHEMA_REGISTRY_URL"),
            }
        return {
            "kafka_bootstrap_servers": os.getenv("KAFKA_BOOTSTRAP_SERVERS"),
            "kafka_schema_registry_url": os.getenv("KAFKA_SCHEMA_REGISTRY_URL"),
        }

    async def _load_mqtt_secrets(self, platform_name: str) -> Dict[str, Any]:
        s = await self._load_mounted_secret(self.generate_secret_name(platform_name, "mqtt"))
        if s:
            return {
                "mqtt_host": s.get("MQTT_HOST"),
                "mqtt_port": int(s.get("MQTT_PORT", "1883")),
                "mqtt_user": s.get("MQTT_USER"),
                "mqtt_password": s.get("MQTT_PASSWORD"),
            }
        return {
            "mqtt_host": os.getenv("MQTT_HOST"),
            "mqtt_port": int(os.getenv("MQTT_PORT", "1883")),
            "mqtt_user": os.getenv("MQTT_USER"),
            "mqtt_password": os.getenv("MQTT_PASSWORD"),
        }

    async def _load_database_secrets(self, platform_name: str) -> Dict[str, Any]:
        s = await self._load_mounted_secret(self.generate_secret_name(platform_name, "db"))
        if s:
            return {
                "db_host": s.get("DB_HOST"),
                "db_port": int(s.get("DB_PORT", "5432")),
                "db_name": s.get("DB_NAME"),
                "db_user": s.get("DB_USER"),
                "db_password": s.get("DB_PASSWORD"),
            }
        return {
            "db_host": os.getenv("DB_HOST"),
            "db_port": int(os.getenv("DB_PORT", "5432")),
            "db_name": os.getenv("DB_NAME"),
            "db_user": os.getenv("DB_USER"),
            "db_password": os.getenv("DB_PASSWORD"),
        }

    async def _load_mounted_secret(self, secret_name: str) -> Optional[Dict[str, str]]:
        secret_path = Path(self.secret_mount_path) / secret_name
        if not secret_path.exists():
            logger.debug(f"Secret path not found: {secret_path}")
            return None
        try:
            secrets = {}
            for secret_file in secret_path.iterdir():
                if secret_file.is_file():
                    secrets[secret_file.name] = secret_file.read_text().strip()
            return secrets or None
        except Exception as e:
            logger.error(f"Failed to load mounted secret {secret_name}: {e}")
            return None


async def load_realtime_platform_secrets(platform_name: str) -> Dict[str, Any]:
    """Load all connection secrets for a realtime platform (best-effort)."""
    loader = PlatformSecretLoader(platform_name)
    return await loader.load_platform_secrets()


def configure_config_from_secrets(config, secrets: Dict[str, Any]):
    """Overlay loaded secrets onto a RealtimeConfig (only when present)."""
    for attr, key in (
        ("kafka_bootstrap_servers", "kafka_bootstrap_servers"),
        ("kafka_schema_registry_url", "kafka_schema_registry_url"),
        ("mqtt_host", "mqtt_host"),
        ("mqtt_port", "mqtt_port"),
        ("mqtt_user", "mqtt_user"),
        ("mqtt_password", "mqtt_password"),
        ("db_host", "db_host"),
        ("db_port", "db_port"),
        ("db_name", "db_name"),
        ("db_user", "db_user"),
        ("db_password", "db_password"),
    ):
        if secrets.get(key):
            setattr(config, attr, secrets[key])
    return config
