"""
Platform secret loading utilities for real-time platform integration
"""

import os
import json
import logging
from typing import Dict, Any, Optional
from pathlib import Path

logger = logging.getLogger(__name__)


class PlatformSecretLoader:
    """
    Loads secrets from Kubernetes mounted secrets or environment variables
    following the standardized naming pattern from realtime platform
    """
    
    def __init__(self, platform_name: Optional[str] = None):
        self.platform_name = platform_name
        self.secret_mount_path = "/var/secrets"  # Standard Kubernetes secret mount path
    
    async def load_platform_secrets(self, platform_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Load all secrets for a realtime platform
        
        Args:
            platform_name: Name of the realtime platform (overrides instance setting)
        
        Returns:
            Dictionary containing all connection details
        """
        platform = platform_name or self.platform_name
        if not platform:
            raise ValueError("Platform name must be provided")
        
        secrets = {}
        
        # Load each type of secret
        secrets.update(await self._load_kafka_secrets(platform))
        secrets.update(await self._load_mqtt_secrets(platform))
        secrets.update(await self._load_database_secrets(platform))
        secrets.update(await self._load_analytics_secrets(platform))
        secrets.update(await self._load_streaming_secrets(platform))
        
        logger.info(f"Loaded secrets for platform: {platform}")
        logger.debug(f"Available secret types: {list(secrets.keys())}")
        
        return secrets
    
    async def _load_kafka_secrets(self, platform_name: str) -> Dict[str, Any]:
        """Load Kafka connection secrets"""
        secret_name = f"{platform_name}-kafka-secret"
        
        # Try mounted secret first
        kafka_secrets = await self._load_mounted_secret(secret_name)
        if kafka_secrets:
            return {
                "kafka_bootstrap_servers": kafka_secrets.get("KAFKA_BOOTSTRAP_SERVERS"),
                "kafka_schema_registry_url": kafka_secrets.get("KAFKA_SCHEMA_REGISTRY_URL"),
                "kafka_username": kafka_secrets.get("KAFKA_USERNAME"),
                "kafka_password": kafka_secrets.get("KAFKA_PASSWORD"),
                "kafka_security_protocol": kafka_secrets.get("KAFKA_SECURITY_PROTOCOL", "PLAINTEXT"),
                "kafka_sasl_mechanism": kafka_secrets.get("KAFKA_SASL_MECHANISM")
            }
        
        # Fallback to environment variables
        return {
            "kafka_bootstrap_servers": os.getenv("KAFKA_BOOTSTRAP_SERVERS"),
            "kafka_schema_registry_url": os.getenv("KAFKA_SCHEMA_REGISTRY_URL"),
            "kafka_username": os.getenv("KAFKA_USERNAME"),
            "kafka_password": os.getenv("KAFKA_PASSWORD"),
            "kafka_security_protocol": os.getenv("KAFKA_SECURITY_PROTOCOL", "PLAINTEXT"),
            "kafka_sasl_mechanism": os.getenv("KAFKA_SASL_MECHANISM")
        }
    
    async def _load_mqtt_secrets(self, platform_name: str) -> Dict[str, Any]:
        """Load MQTT connection secrets"""
        secret_name = f"{platform_name}-mqtt-secret"
        
        # Try mounted secret first
        mqtt_secrets = await self._load_mounted_secret(secret_name)
        if mqtt_secrets:
            return {
                "mqtt_host": mqtt_secrets.get("MQTT_HOST"),
                "mqtt_port": int(mqtt_secrets.get("MQTT_PORT", "1883")),
                "mqtt_user": mqtt_secrets.get("MQTT_USER"),
                "mqtt_password": mqtt_secrets.get("MQTT_PASSWORD"),
                "mqtt_protocol": mqtt_secrets.get("MQTT_PROTOCOL", "tcp"),
                "mqtt_client_id": mqtt_secrets.get("MQTT_CLIENT_ID")
            }
        
        # Fallback to environment variables
        return {
            "mqtt_host": os.getenv("MQTT_HOST"),
            "mqtt_port": int(os.getenv("MQTT_PORT", "1883")),
            "mqtt_user": os.getenv("MQTT_USER"),
            "mqtt_password": os.getenv("MQTT_PASSWORD"),
            "mqtt_protocol": os.getenv("MQTT_PROTOCOL", "tcp"),
            "mqtt_client_id": os.getenv("MQTT_CLIENT_ID")
        }
    
    async def _load_database_secrets(self, platform_name: str) -> Dict[str, Any]:
        """Load database connection secrets"""
        secret_name = f"{platform_name}-db-secret"
        
        # Try mounted secret first
        db_secrets = await self._load_mounted_secret(secret_name)
        if db_secrets:
            return {
                "db_host": db_secrets.get("DB_HOST"),
                "db_port": int(db_secrets.get("DB_PORT", "5432")),
                "db_name": db_secrets.get("DB_NAME"),
                "db_user": db_secrets.get("DB_USER"),
                "db_password": db_secrets.get("DB_PASSWORD"),
                "db_ssl_mode": db_secrets.get("DB_SSL_MODE", "prefer"),
                "db_connection_string": db_secrets.get("DB_CONNECTION_STRING")
            }
        
        # Fallback to environment variables
        return {
            "db_host": os.getenv("DB_HOST"),
            "db_port": int(os.getenv("DB_PORT", "5432")),
            "db_name": os.getenv("DB_NAME"),
            "db_user": os.getenv("DB_USER"),
            "db_password": os.getenv("DB_PASSWORD"),
            "db_ssl_mode": os.getenv("DB_SSL_MODE", "prefer"),
            "db_connection_string": os.getenv("DB_CONNECTION_STRING")
        }
    
    async def _load_analytics_secrets(self, platform_name: str) -> Dict[str, Any]:
        """Load analytics dashboard secrets (Metabase)"""
        secret_name = f"{platform_name}-metabase-secret"
        
        # Try mounted secret first
        analytics_secrets = await self._load_mounted_secret(secret_name)
        if analytics_secrets:
            return {
                "metabase_url": analytics_secrets.get("METABASE_URL"),
                "metabase_user": analytics_secrets.get("METABASE_USER"),
                "metabase_password": analytics_secrets.get("METABASE_PASSWORD"),
                "metabase_api_key": analytics_secrets.get("METABASE_API_KEY"),
                "metabase_database_id": analytics_secrets.get("METABASE_DATABASE_ID")
            }
        
        # Fallback to environment variables
        return {
            "metabase_url": os.getenv("METABASE_URL"),
            "metabase_user": os.getenv("METABASE_USER"),
            "metabase_password": os.getenv("METABASE_PASSWORD"),
            "metabase_api_key": os.getenv("METABASE_API_KEY"),
            "metabase_database_id": os.getenv("METABASE_DATABASE_ID")
        }
    
    async def _load_streaming_secrets(self, platform_name: str) -> Dict[str, Any]:
        """Load stream processing secrets (Lenses)"""
        secret_name = f"{platform_name}-lenses-secret"
        
        # Try mounted secret first
        streaming_secrets = await self._load_mounted_secret(secret_name)
        if streaming_secrets:
            return {
                "lenses_url": streaming_secrets.get("LENSES_URL"),
                "lenses_user": streaming_secrets.get("LENSES_USER"),
                "lenses_password": streaming_secrets.get("LENSES_PASSWORD"),
                "lenses_api_key": streaming_secrets.get("LENSES_API_KEY"),
                "lenses_ws_url": streaming_secrets.get("LENSES_WS_URL")
            }
        
        # Fallback to environment variables
        return {
            "lenses_url": os.getenv("LENSES_URL"),
            "lenses_user": os.getenv("LENSES_USER"),
            "lenses_password": os.getenv("LENSES_PASSWORD"),
            "lenses_api_key": os.getenv("LENSES_API_KEY"),
            "lenses_ws_url": os.getenv("LENSES_WS_URL")
        }
    
    async def _load_mounted_secret(self, secret_name: str) -> Optional[Dict[str, str]]:
        """
        Load secret from Kubernetes mounted volume
        
        Args:
            secret_name: Name of the secret to load
            
        Returns:
            Dictionary of secret keys and values, or None if not found
        """
        secret_path = Path(self.secret_mount_path) / secret_name
        
        if not secret_path.exists():
            logger.debug(f"Secret path not found: {secret_path}")
            return None
        
        try:
            secrets = {}
            
            # Kubernetes secrets are mounted as individual files
            for secret_file in secret_path.iterdir():
                if secret_file.is_file():
                    key = secret_file.name
                    value = secret_file.read_text().strip()
                    secrets[key] = value
            
            if secrets:
                logger.debug(f"Loaded mounted secret: {secret_name}")
                return secrets
            else:
                logger.warning(f"Empty secret found: {secret_name}")
                return None
                
        except Exception as e:
            logger.error(f"Failed to load mounted secret {secret_name}: {e}")
            return None
    
    async def load_specific_secret(self, secret_name: str) -> Optional[Dict[str, str]]:
        """
        Load a specific secret by name
        
        Args:
            secret_name: Full name of the secret to load
            
        Returns:
            Dictionary of secret keys and values, or None if not found
        """
        return await self._load_mounted_secret(secret_name)
    
    def validate_required_secrets(self, secrets: Dict[str, Any], required_services: List[str]) -> bool:
        """
        Validate that all required secrets are present
        
        Args:
            secrets: Dictionary of loaded secrets
            required_services: List of required services ('kafka', 'mqtt', 'database', etc.)
            
        Returns:
            True if all required secrets are present
        """
        validation_map = {
            'kafka': ['kafka_bootstrap_servers'],
            'mqtt': ['mqtt_host', 'mqtt_port'],
            'database': ['db_host', 'db_name', 'db_user'],
            'analytics': ['metabase_url'],
            'streaming': ['lenses_url']
        }
        
        for service in required_services:
            if service not in validation_map:
                logger.warning(f"Unknown service for validation: {service}")
                continue
            
            required_fields = validation_map[service]
            for field in required_fields:
                if not secrets.get(field):
                    logger.error(f"Missing required secret for {service}: {field}")
                    return False
        
        logger.info(f"All required secrets present for services: {required_services}")
        return True
    
    def get_connection_string(self, secrets: Dict[str, Any], service_type: str) -> Optional[str]:
        """
        Generate connection string for a service
        
        Args:
            secrets: Dictionary of loaded secrets
            service_type: Type of service ('database', 'kafka', 'mqtt')
            
        Returns:
            Connection string or None if cannot be generated
        """
        if service_type == 'database':
            if all(secrets.get(k) for k in ['db_host', 'db_port', 'db_name', 'db_user', 'db_password']):
                return f"postgresql://{secrets['db_user']}:{secrets['db_password']}@{secrets['db_host']}:{secrets['db_port']}/{secrets['db_name']}"
        
        elif service_type == 'kafka':
            return secrets.get('kafka_bootstrap_servers')
        
        elif service_type == 'mqtt':
            if secrets.get('mqtt_host') and secrets.get('mqtt_port'):
                protocol = secrets.get('mqtt_protocol', 'tcp')
                return f"{protocol}://{secrets['mqtt_host']}:{secrets['mqtt_port']}"
        
        return None


# Convenience function for quick secret loading
async def load_realtime_platform_secrets(platform_name: str) -> Dict[str, Any]:
    """
    Convenience function to load all secrets for a realtime platform
    
    Args:
        platform_name: Name of the realtime platform
        
    Returns:
        Dictionary containing all connection details
    """
    loader = PlatformSecretLoader(platform_name)
    return await loader.load_platform_secrets()


# Auto-configuration helper
def configure_agent_from_secrets(config: 'AgentConfig', secrets: Dict[str, Any]) -> 'AgentConfig':
    """
    Auto-configure AgentConfig from loaded secrets
    
    Args:
        config: Existing AgentConfig instance
        secrets: Dictionary of loaded secrets
        
    Returns:
        Updated AgentConfig instance
    """
    # Update Kafka settings
    if secrets.get('kafka_bootstrap_servers'):
        config.kafka_bootstrap_servers = secrets['kafka_bootstrap_servers']
    if secrets.get('kafka_schema_registry_url'):
        config.kafka_schema_registry_url = secrets['kafka_schema_registry_url']
    
    # Update MQTT settings
    if secrets.get('mqtt_host'):
        config.mqtt_host = secrets['mqtt_host']
    if secrets.get('mqtt_port'):
        config.mqtt_port = secrets['mqtt_port']
    if secrets.get('mqtt_user'):
        config.mqtt_user = secrets['mqtt_user']
    if secrets.get('mqtt_password'):
        config.mqtt_password = secrets['mqtt_password']
    
    # Update database settings
    if secrets.get('db_host'):
        config.db_host = secrets['db_host']
    if secrets.get('db_port'):
        config.db_port = secrets['db_port']
    if secrets.get('db_name'):
        config.db_name = secrets['db_name']
    if secrets.get('db_user'):
        config.db_user = secrets['db_user']
    if secrets.get('db_password'):
        config.db_password = secrets['db_password']
    
    # Update analytics settings
    if secrets.get('metabase_url'):
        config.metabase_url = secrets['metabase_url']
    if secrets.get('metabase_user'):
        config.metabase_user = secrets['metabase_user']
    if secrets.get('metabase_password'):
        config.metabase_password = secrets['metabase_password']
    
    # Update streaming settings
    if secrets.get('lenses_url'):
        config.lenses_url = secrets['lenses_url']
    if secrets.get('lenses_user'):
        config.lenses_user = secrets['lenses_user']
    if secrets.get('lenses_password'):
        config.lenses_password = secrets['lenses_password']
    
    logger.info(f"AgentConfig updated with platform secrets")
    return config