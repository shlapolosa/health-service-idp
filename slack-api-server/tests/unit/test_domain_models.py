"""
Unit tests for domain models
"""

import pytest
from datetime import datetime
from src.domain.models import (
    VClusterSize, Capability, ResourceSpec, CapabilitySet,
    VClusterRequest, SlackCommand, ParsedCommand,
    InvalidVClusterRequestError, InvalidSlackCommandError
)


class TestResourceSpec:
    """Test ResourceSpec value object."""
    
    def test_valid_resource_spec(self):
        """Test creating a valid ResourceSpec."""
        spec = ResourceSpec(
            cpu_limit="2000m",
            memory_limit="4Gi",
            storage_size="20Gi",
            node_count=3
        )
        assert spec.cpu_limit == "2000m"
        assert spec.memory_limit == "4Gi"
        assert spec.storage_size == "20Gi"
        assert spec.node_count == 3
    
    def test_invalid_cpu_limit(self):
        """Test ResourceSpec with invalid CPU limit."""
        with pytest.raises(ValueError, match="CPU limit must end with 'm'"):
            ResourceSpec(
                cpu_limit="2000",
                memory_limit="4Gi",
                storage_size="20Gi",
                node_count=3
            )
    
    def test_invalid_memory_limit(self):
        """Test ResourceSpec with invalid memory limit."""
        with pytest.raises(ValueError, match="Memory limit must end with 'Gi' or 'Mi'"):
            ResourceSpec(
                cpu_limit="2000m",
                memory_limit="4G",
                storage_size="20Gi",
                node_count=3
            )
    
    def test_invalid_storage_size(self):
        """Test ResourceSpec with invalid storage size."""
        with pytest.raises(ValueError, match="Storage size must end with 'Gi' or 'Ti'"):
            ResourceSpec(
                cpu_limit="2000m",
                memory_limit="4Gi",
                storage_size="20G",
                node_count=3
            )
    
    def test_invalid_node_count(self):
        """Test ResourceSpec with invalid node count."""
        with pytest.raises(ValueError, match="Node count must be at least 1"):
            ResourceSpec(
                cpu_limit="2000m",
                memory_limit="4Gi",
                storage_size="20Gi",
                node_count=0
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
        cap_set = CapabilitySet(
            observability=False,
            backup=True
        )
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
            resources=resources
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
                resources=resources
            )
    
    def test_invalid_kubernetes_name(self):
        """Test VClusterRequest with invalid Kubernetes name."""
        capabilities = CapabilitySet()
        resources = ResourceSpec("2000m", "4Gi", "20Gi", 3)
        
        with pytest.raises(ValueError, match="must contain only alphanumeric characters"):
            VClusterRequest(
                name="test_cluster",
                namespace="dev",
                user="testuser",
                slack_channel="C123456",
                capabilities=capabilities,
                resources=resources
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
            repository="test-repo"
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
            team_domain="testteam"
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
            parsing_method="spacy"
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