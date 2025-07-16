"""
Unit tests for domain models
"""

from datetime import datetime

import pytest

from src.domain.models import (AppContainerRequest, Capability, CapabilitySet,
                               InvalidAppContainerRequestError,
                               InvalidSlackCommandError,
                               InvalidVClusterRequestError, 
                               MicroserviceRequest, MicroserviceLanguage, 
                               MicroserviceDatabase, MicroserviceCache,
                               ParsedCommand,
                               ResourceSpec, SlackCommand, VClusterRequest,
                               VClusterSize)


class TestResourceSpec:
    """Test ResourceSpec value object."""

    def test_valid_resource_spec(self):
        """Test creating a valid ResourceSpec."""
        spec = ResourceSpec(
            cpu_limit="2000m", memory_limit="4Gi", storage_size="20Gi", node_count=3
        )
        assert spec.cpu_limit == "2000m"
        assert spec.memory_limit == "4Gi"
        assert spec.storage_size == "20Gi"
        assert spec.node_count == 3

    def test_invalid_cpu_limit(self):
        """Test ResourceSpec with invalid CPU limit."""
        with pytest.raises(ValueError, match="CPU limit must end with 'm'"):
            ResourceSpec(
                cpu_limit="2000", memory_limit="4Gi", storage_size="20Gi", node_count=3
            )

    def test_invalid_memory_limit(self):
        """Test ResourceSpec with invalid memory limit."""
        with pytest.raises(ValueError, match="Memory limit must end with 'Gi' or 'Mi'"):
            ResourceSpec(
                cpu_limit="2000m", memory_limit="4G", storage_size="20Gi", node_count=3
            )

    def test_invalid_storage_size(self):
        """Test ResourceSpec with invalid storage size."""
        with pytest.raises(ValueError, match="Storage size must end with 'Gi' or 'Ti'"):
            ResourceSpec(
                cpu_limit="2000m", memory_limit="4Gi", storage_size="20G", node_count=3
            )

    def test_invalid_node_count(self):
        """Test ResourceSpec with invalid node count."""
        with pytest.raises(ValueError, match="Node count must be at least 1"):
            ResourceSpec(
                cpu_limit="2000m", memory_limit="4Gi", storage_size="20Gi", node_count=0
            )


class TestCapabilitySet:
    """Test CapabilitySet value object."""

    def test_default_capabilities(self):
        """Test default capability set."""
        cap_set = CapabilitySet()
        assert cap_set.observability is True
        assert cap_set.security is True
        assert cap_set.gitops is True
        assert cap_set.logging is True
        assert cap_set.networking is True
        assert cap_set.autoscaling is True
        assert cap_set.backup is False

    def test_custom_capabilities(self):
        """Test custom capability set."""
        cap_set = CapabilitySet(observability=False, backup=True)
        assert cap_set.observability is False
        assert cap_set.backup is True
        assert cap_set.security is True  # Default

    def test_to_dict(self):
        """Test converting capabilities to dictionary."""
        cap_set = CapabilitySet(observability=False, backup=True)
        result = cap_set.to_dict()

        assert result["observability"] == "false"
        assert result["backup"] == "true"
        assert result["security"] == "true"
        assert len(result) == 7


class TestVClusterRequest:
    """Test VClusterRequest domain entity."""

    def test_valid_vcluster_request(self):
        """Test creating a valid VClusterRequest."""
        capabilities = CapabilitySet()
        resources = ResourceSpec("2000m", "4Gi", "20Gi", 3)

        request = VClusterRequest(
            name="test-cluster",
            namespace="dev",
            user="testuser",
            slack_channel="C123456",
            capabilities=capabilities,
            resources=resources,
        )

        assert request.name == "test-cluster"
        assert request.namespace == "dev"
        assert request.user == "testuser"
        assert request.slack_channel == "C123456"
        assert request.capabilities == capabilities
        assert request.resources == resources
        assert isinstance(request.created_at, datetime)

    def test_invalid_name(self):
        """Test VClusterRequest with invalid name."""
        capabilities = CapabilitySet()
        resources = ResourceSpec("2000m", "4Gi", "20Gi", 3)

        with pytest.raises(ValueError, match="name cannot be empty"):
            VClusterRequest(
                name="",
                namespace="dev",
                user="testuser",
                slack_channel="C123456",
                capabilities=capabilities,
                resources=resources,
            )

    def test_invalid_kubernetes_name(self):
        """Test VClusterRequest with invalid Kubernetes name."""
        capabilities = CapabilitySet()
        resources = ResourceSpec("2000m", "4Gi", "20Gi", 3)

        with pytest.raises(
            ValueError, match="must contain only alphanumeric characters"
        ):
            VClusterRequest(
                name="test_cluster",
                namespace="dev",
                user="testuser",
                slack_channel="C123456",
                capabilities=capabilities,
                resources=resources,
            )

    def test_to_github_payload(self):
        """Test converting VClusterRequest to GitHub payload."""
        capabilities = CapabilitySet(backup=True)
        resources = ResourceSpec("2000m", "4Gi", "20Gi", 3)

        request = VClusterRequest(
            name="test-cluster",
            namespace="dev",
            user="testuser",
            slack_channel="C123456",
            capabilities=capabilities,
            resources=resources,
            repository="test-repo",
        )

        payload = request.to_github_payload()

        assert payload["event_type"] == "slack_create_vcluster"
        assert payload["client_payload"]["vcluster_name"] == "test-cluster"
        assert payload["client_payload"]["namespace"] == "dev"
        assert payload["client_payload"]["user"] == "testuser"
        assert payload["client_payload"]["slack_channel"] == "C123456"
        assert payload["client_payload"]["repository"] == "test-repo"
        assert payload["client_payload"]["capabilities"]["backup"] == "true"
        assert payload["client_payload"]["resources"]["cpu_limit"] == "2000m"
        assert payload["client_payload"]["resources"]["node_count"] == "3"


class TestSlackCommand:
    """Test SlackCommand domain entity."""

    def test_valid_slack_command(self):
        """Test creating a valid SlackCommand."""
        command = SlackCommand(
            command="/vcluster",
            text="create test-cluster",
            user_id="U123456",
            user_name="testuser",
            channel_id="C123456",
            channel_name="general",
            team_id="T123456",
            team_domain="testteam",
        )

        assert command.command == "/vcluster"
        assert command.text == "create test-cluster"
        assert command.user_id == "U123456"
        assert command.user_name == "testuser"
        assert command.channel_id == "C123456"
        assert command.channel_name == "general"
        assert command.team_id == "T123456"
        assert command.team_domain == "testteam"
        assert isinstance(command.timestamp, datetime)


class TestParsedCommand:
    """Test ParsedCommand value object."""

    def test_default_parsed_command(self):
        """Test creating a ParsedCommand with defaults."""
        parsed = ParsedCommand(action="create")

        assert parsed.action == "create"
        assert parsed.vcluster_name is None
        assert parsed.namespace == "default"
        assert parsed.repository is None
        assert parsed.size == VClusterSize.MEDIUM
        assert parsed.enabled_capabilities == []
        assert parsed.disabled_capabilities == []
        assert parsed.parsing_method == "regex"

    def test_custom_parsed_command(self):
        """Test creating a ParsedCommand with custom values."""
        parsed = ParsedCommand(
            action="create",
            vcluster_name="test-cluster",
            namespace="dev",
            repository="test-repo",
            size=VClusterSize.LARGE,
            enabled_capabilities=[Capability.OBSERVABILITY],
            disabled_capabilities=[Capability.BACKUP],
            parsing_method="spacy",
        )

        assert parsed.action == "create"
        assert parsed.vcluster_name == "test-cluster"
        assert parsed.namespace == "dev"
        assert parsed.repository == "test-repo"
        assert parsed.size == VClusterSize.LARGE
        assert parsed.enabled_capabilities == [Capability.OBSERVABILITY]
        assert parsed.disabled_capabilities == [Capability.BACKUP]
        assert parsed.parsing_method == "spacy"


class TestEnums:
    """Test enum definitions."""

    def test_vcluster_size_enum(self):
        """Test VClusterSize enum."""
        assert VClusterSize.SMALL.value == "small"
        assert VClusterSize.MEDIUM.value == "medium"
        assert VClusterSize.LARGE.value == "large"
        assert VClusterSize.XLARGE.value == "xlarge"

    def test_capability_enum(self):
        """Test Capability enum."""
        assert Capability.OBSERVABILITY.value == "observability"
        assert Capability.SECURITY.value == "security"
        assert Capability.GITOPS.value == "gitops"
        assert Capability.LOGGING.value == "logging"
        assert Capability.NETWORKING.value == "networking"
        assert Capability.AUTOSCALING.value == "autoscaling"
        assert Capability.BACKUP.value == "backup"


class TestAppContainerRequest:
    """Test AppContainerRequest domain entity."""

    def test_valid_appcontainer_request(self):
        """Test creating a valid AppContainerRequest."""
        request = AppContainerRequest(
            name="test-app",
            namespace="dev",
            user="testuser",
            slack_channel="C123",
            description="Test application container",
            github_org="testorg",
            docker_registry="registry.example.com/testorg",
            enable_observability=True,
            enable_security=False,
            original_text="create test-app"
        )

        assert request.name == "test-app"
        assert request.namespace == "dev"
        assert request.user == "testuser"
        assert request.slack_channel == "C123"
        assert request.description == "Test application container"
        assert request.github_org == "testorg"
        assert request.docker_registry == "registry.example.com/testorg"
        assert request.enable_observability is True
        assert request.enable_security is False
        assert request.original_text == "create test-app"
        assert isinstance(request.created_at, datetime)

    def test_appcontainer_request_defaults(self):
        """Test AppContainerRequest with default values."""
        request = AppContainerRequest(
            name="test-app",
            namespace="default",
            user="testuser",
            slack_channel="C123"
        )

        assert request.name == "test-app"
        assert request.description == "CLAUDE.md-compliant application container"
        assert request.github_org == "socrates12345"
        assert request.docker_registry == "docker.io/socrates12345"
        assert request.enable_observability is True
        assert request.enable_security is True

    def test_invalid_appcontainer_name(self):
        """Test AppContainerRequest with invalid name."""
        with pytest.raises(ValueError, match="name cannot be empty"):
            AppContainerRequest(
                name="",
                namespace="default",
                user="testuser",
                slack_channel="C123"
            )

    def test_invalid_kubernetes_appcontainer_name(self):
        """Test AppContainerRequest with invalid Kubernetes name."""
        with pytest.raises(ValueError, match="name must start and end with alphanumeric characters"):
            AppContainerRequest(
                name="-invalid-name-",
                namespace="default",
                user="testuser",
                slack_channel="C123"
            )

    def test_appcontainer_to_argo_payload(self):
        """Test converting AppContainerRequest to Argo payload."""
        request = AppContainerRequest(
            name="test-app",
            namespace="production",
            user="alice",
            slack_channel="C456",
            description="Production app container",
            github_org="myorg",
            docker_registry="myregistry.com/myorg",
            enable_observability=False,
            enable_security=True
        )

        payload = request.to_argo_payload()

        expected_payload = {
            "appcontainer-name": "test-app",
            "namespace": "production",
            "description": "Production app container",
            "github-org": "myorg",
            "docker-registry": "myregistry.com/myorg",
            "observability": "false",
            "security": "true",
            "vcluster-name": "",
            "auto-create-vcluster": "true",
            "user": "alice",
            "slack-channel": "C456",
            "slack-user-id": "alice",
        }

        assert payload == expected_payload


class TestMicroserviceRequest:
    """Test MicroserviceRequest domain entity."""

    def test_valid_microservice_request(self):
        """Test creating a valid MicroserviceRequest."""
        request = MicroserviceRequest(
            name="user-service",
            namespace="production",
            user="alice",
            slack_channel="C789",
            language=MicroserviceLanguage.PYTHON,
            database=MicroserviceDatabase.POSTGRESQL,
            cache=MicroserviceCache.REDIS,
            description="User management service",
            github_org="mycompany",
            docker_registry="registry.example.com/mycompany",
            enable_observability=True,
            enable_security=False,
            target_vcluster="prod-cluster",
            auto_create_vcluster=False,
            original_text="create user-service with python and postgres"
        )

        assert request.name == "user-service"
        assert request.namespace == "production"
        assert request.user == "alice"
        assert request.slack_channel == "C789"
        assert request.language == MicroserviceLanguage.PYTHON
        assert request.database == MicroserviceDatabase.POSTGRESQL
        assert request.cache == MicroserviceCache.REDIS
        assert request.description == "User management service"
        assert request.github_org == "mycompany"
        assert request.docker_registry == "registry.example.com/mycompany"
        assert request.enable_observability is True
        assert request.enable_security is False
        assert request.target_vcluster == "prod-cluster"
        assert request.auto_create_vcluster is False
        assert request.original_text == "create user-service with python and postgres"
        assert isinstance(request.created_at, datetime)

    def test_microservice_request_defaults(self):
        """Test MicroserviceRequest with default values."""
        request = MicroserviceRequest(
            name="api-service",
            namespace="default",
            user="testuser",
            slack_channel="C123"
        )

        assert request.name == "api-service"
        assert request.language == MicroserviceLanguage.PYTHON
        assert request.database == MicroserviceDatabase.NONE
        assert request.cache == MicroserviceCache.NONE
        assert request.description == "CLAUDE.md-compliant microservice"
        assert request.github_org == "socrates12345"
        assert request.docker_registry == "docker.io/socrates12345"
        assert request.enable_observability is True
        assert request.enable_security is True
        assert request.target_vcluster is None
        assert request.auto_create_vcluster is True

    def test_language_alias_normalization(self):
        """Test that language aliases are normalized properly."""
        # Test FASTAPI -> PYTHON
        request = MicroserviceRequest(
            name="api-service",
            namespace="default",
            user="testuser",
            slack_channel="C123",
            language=MicroserviceLanguage.FASTAPI
        )
        assert request.language == MicroserviceLanguage.PYTHON

        # Test SPRINGBOOT -> JAVA
        request = MicroserviceRequest(
            name="api-service",
            namespace="default",
            user="testuser",
            slack_channel="C123",
            language=MicroserviceLanguage.SPRINGBOOT
        )
        assert request.language == MicroserviceLanguage.JAVA

    def test_database_alias_normalization(self):
        """Test that database aliases are normalized properly."""
        # Test POSTGRES -> POSTGRESQL
        request = MicroserviceRequest(
            name="api-service",
            namespace="default",
            user="testuser",
            slack_channel="C123",
            database=MicroserviceDatabase.POSTGRES
        )
        assert request.database == MicroserviceDatabase.POSTGRESQL

    def test_invalid_microservice_name(self):
        """Test MicroserviceRequest with invalid name."""
        with pytest.raises(ValueError, match="name cannot be empty"):
            MicroserviceRequest(
                name="",
                namespace="default",
                user="testuser",
                slack_channel="C123"
            )

    def test_invalid_kubernetes_microservice_name(self):
        """Test MicroserviceRequest with invalid Kubernetes name."""
        with pytest.raises(ValueError, match="name must start and end with alphanumeric characters"):
            MicroserviceRequest(
                name="-invalid-service-",
                namespace="default",
                user="testuser",
                slack_channel="C123"
            )

    def test_microservice_to_argo_payload(self):
        """Test converting MicroserviceRequest to Argo payload."""
        request = MicroserviceRequest(
            name="order-service",
            namespace="production",
            user="bob",
            slack_channel="C456",
            language=MicroserviceLanguage.JAVA,
            database=MicroserviceDatabase.POSTGRESQL,
            cache=MicroserviceCache.REDIS,
            description="Order processing service",
            github_org="ecommerce",
            docker_registry="registry.ecommerce.com/services",
            enable_observability=False,
            enable_security=True,
            target_vcluster="prod-cluster",
            auto_create_vcluster=False
        )

        payload = request.to_argo_payload()

        expected_payload = {
            "microservice-name": "order-service",
            "namespace": "production",
            "language": "java",
            "database": "postgres",  # Note: postgresql -> postgres mapping
            "cache": "redis",
            "description": "Order processing service",
            "github-org": "ecommerce",
            "docker-registry": "registry.ecommerce.com/services",
            "observability": "false",
            "security": "true",
            "target-vcluster": "prod-cluster",
            "auto-create-vcluster": "false",
            "repository-name": "",
            "user": "bob",
            "slack-channel": "C456",
            "slack-user-id": "bob",
        }

        assert payload == expected_payload

    def test_microservice_to_argo_payload_database_mapping(self):
        """Test that database value mapping works correctly in Argo payload."""
        # Test postgresql -> postgres mapping
        request = MicroserviceRequest(
            name="test-service",
            namespace="default",
            user="testuser",
            slack_channel="C123",
            database=MicroserviceDatabase.POSTGRESQL
        )
        
        payload = request.to_argo_payload()
        assert payload["database"] == "postgres"

        # Test none remains none
        request = MicroserviceRequest(
            name="test-service",
            namespace="default",
            user="testuser",
            slack_channel="C123",
            database=MicroserviceDatabase.NONE
        )
        
        payload = request.to_argo_payload()
        assert payload["database"] == "none"

    def test_get_repository_name(self):
        """Test repository name generation."""
        # Test with -service suffix
        request = MicroserviceRequest(
            name="user-service",
            namespace="default",
            user="testuser",
            slack_channel="C123"
        )
        assert request.get_repository_name() == "user"

        # Test without -service suffix
        request = MicroserviceRequest(
            name="api",
            namespace="default",
            user="testuser",
            slack_channel="C123"
        )
        assert request.get_repository_name() == "api"

    def test_get_vcluster_name(self):
        """Test vCluster name generation."""
        # Test with target_vcluster specified
        request = MicroserviceRequest(
            name="user-service",
            namespace="default",
            user="testuser",
            slack_channel="C123",
            target_vcluster="my-cluster"
        )
        assert request.get_vcluster_name() == "my-cluster"

        # Test without target_vcluster (auto-generate)
        request = MicroserviceRequest(
            name="user-service",
            namespace="default",
            user="testuser",
            slack_channel="C123"
        )
        assert request.get_vcluster_name() == "user-vcluster"


class TestMicroserviceEnums:
    """Test microservice-related enum definitions."""

    def test_microservice_language_enum(self):
        """Test MicroserviceLanguage enum."""
        assert MicroserviceLanguage.PYTHON.value == "python"
        assert MicroserviceLanguage.JAVA.value == "java"
        assert MicroserviceLanguage.SPRINGBOOT.value == "springboot"
        assert MicroserviceLanguage.FASTAPI.value == "fastapi"

    def test_microservice_database_enum(self):
        """Test MicroserviceDatabase enum."""
        assert MicroserviceDatabase.NONE.value == "none"
        assert MicroserviceDatabase.POSTGRESQL.value == "postgresql"
        assert MicroserviceDatabase.POSTGRES.value == "postgres"

    def test_microservice_cache_enum(self):
        """Test MicroserviceCache enum."""
        assert MicroserviceCache.NONE.value == "none"
        assert MicroserviceCache.REDIS.value == "redis"
