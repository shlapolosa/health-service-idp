"""
Unit tests for domain services
"""

import pytest

from src.domain.models import (Capability, CapabilitySet,
                               InvalidVClusterRequestError, ParsedCommand,
                               ResourceSpec, SlackCommand, VClusterRequest,
                               VClusterSize)
from src.domain.services import (SlackResponseBuilderService,
                                 VClusterFactoryService,
                                 VClusterValidationService)


class TestVClusterFactoryService:
    """Test VClusterFactoryService domain service."""

    def setup_method(self):
        """Set up test fixtures."""
        self.factory = VClusterFactoryService()

    def test_create_vcluster_request_basic(self):
        """Test creating a basic VCluster request."""
        parsed = ParsedCommand(
            action="create", vcluster_name="test-cluster", namespace="dev"
        )

        request = self.factory.create_vcluster_request(
            parsed_command=parsed,
            user="testuser",
            channel="C123456",
            original_text="create test-cluster",
        )

        assert request.name == "test-cluster"
        assert request.namespace == "dev"
        assert request.user == "testuser"
        assert request.slack_channel == "C123456"
        assert request.original_text == "create test-cluster"
        assert request.resources.cpu_limit == "2000m"  # Medium preset
        assert request.resources.memory_limit == "4Gi"
        assert request.resources.node_count == 3

    def test_create_vcluster_request_with_capabilities(self):
        """Test creating VCluster request with specific capabilities."""
        parsed = ParsedCommand(
            action="create",
            vcluster_name="test-cluster",
            enabled_capabilities=[Capability.BACKUP],
            disabled_capabilities=[Capability.SECURITY],
        )

        request = self.factory.create_vcluster_request(
            parsed_command=parsed,
            user="testuser",
            channel="C123456",
            original_text="create test-cluster with backup without security",
        )

        assert request.capabilities.backup is True
        assert request.capabilities.security is False
        assert request.capabilities.observability is True  # Default

    def test_create_vcluster_request_different_sizes(self):
        """Test creating VCluster requests with different sizes."""
        sizes_and_specs = [
            (VClusterSize.SMALL, ("1000m", "2Gi", "10Gi", 1)),
            (VClusterSize.MEDIUM, ("2000m", "4Gi", "20Gi", 3)),
            (VClusterSize.LARGE, ("4000m", "8Gi", "50Gi", 5)),
            (VClusterSize.XLARGE, ("8000m", "16Gi", "100Gi", 10)),
        ]

        for size, (cpu, memory, storage, nodes) in sizes_and_specs:
            parsed = ParsedCommand(
                action="create", vcluster_name="test-cluster", size=size
            )

            request = self.factory.create_vcluster_request(
                parsed_command=parsed,
                user="testuser",
                channel="C123456",
                original_text=f"create {size.value} test-cluster",
            )

            assert request.resources.cpu_limit == cpu
            assert request.resources.memory_limit == memory
            assert request.resources.storage_size == storage
            assert request.resources.node_count == nodes

    def test_create_vcluster_request_auto_name(self):
        """Test creating VCluster request with auto-generated name."""
        parsed = ParsedCommand(action="create")

        request = self.factory.create_vcluster_request(
            parsed_command=parsed,
            user="testuser",
            channel="C123456",
            original_text="create vcluster",
        )

        assert request.name.startswith("vcluster-")
        assert len(request.name) > 10  # Should have timestamp

    def test_invalid_action(self):
        """Test creating VCluster request with invalid action."""
        parsed = ParsedCommand(action="delete")

        with pytest.raises(InvalidVClusterRequestError, match="Invalid action"):
            self.factory.create_vcluster_request(
                parsed_command=parsed,
                user="testuser",
                channel="C123456",
                original_text="delete test-cluster",
            )


class TestVClusterValidationService:
    """Test VClusterValidationService domain service."""

    def setup_method(self):
        """Set up test fixtures."""
        self.validator = VClusterValidationService()
        self.capabilities = CapabilitySet()
        self.resources = ResourceSpec("2000m", "4Gi", "20Gi", 3)

    def test_valid_request(self):
        """Test validating a valid VCluster request."""
        request = VClusterRequest(
            name="test-cluster",
            namespace="dev",
            user="testuser",
            slack_channel="C123456",
            capabilities=self.capabilities,
            resources=self.resources,
        )

        is_valid, errors = self.validator.validate_request(request)

        assert is_valid is True
        assert errors == []

    def test_invalid_name(self):
        """Test validating request with invalid name."""
        with pytest.raises(
            ValueError,
            match="name must contain only alphanumeric characters and hyphens",
        ):
            VClusterRequest(
                name="test_cluster",  # Invalid: contains underscore
                namespace="dev",
                user="testuser",
                slack_channel="C123456",
                capabilities=self.capabilities,
                resources=self.resources,
            )

    def test_invalid_namespace(self):
        """Test validating request with invalid namespace."""
        with pytest.raises(
            ValueError,
            match="namespace must contain only alphanumeric characters and hyphens",
        ):
            VClusterRequest(
                name="test-cluster",
                namespace="dev_ns",  # Invalid: contains underscore
                user="testuser",
                slack_channel="C123456",
                capabilities=self.capabilities,
                resources=self.resources,
            )

    def test_invalid_resources(self):
        """Test validating request with invalid resources."""
        invalid_resources = ResourceSpec("50000m", "4Gi", "20Gi", 3)  # Too much CPU

        request = VClusterRequest(
            name="test-cluster",
            namespace="dev",
            user="testuser",
            slack_channel="C123456",
            capabilities=self.capabilities,
            resources=invalid_resources,
        )

        is_valid, errors = self.validator.validate_request(request)

        assert is_valid is False
        assert len(errors) == 1
        assert "CPU limit must be between" in errors[0]

    def test_kubernetes_name_validation(self):
        """Test Kubernetes name validation rules."""
        # Valid names
        assert self.validator._is_valid_kubernetes_name("test-cluster") is True
        assert self.validator._is_valid_kubernetes_name("test123") is True
        assert self.validator._is_valid_kubernetes_name("123test") is True

        # Invalid names
        assert self.validator._is_valid_kubernetes_name("") is False
        assert self.validator._is_valid_kubernetes_name("test_cluster") is False
        assert self.validator._is_valid_kubernetes_name("-test") is False
        assert self.validator._is_valid_kubernetes_name("test-") is False
        assert self.validator._is_valid_kubernetes_name("a" * 64) is False  # Too long


class TestSlackResponseBuilderService:
    """Test SlackResponseBuilderService domain service."""

    def setup_method(self):
        """Set up test fixtures."""
        self.builder = SlackResponseBuilderService()
        self.capabilities = CapabilitySet(backup=True)
        self.resources = ResourceSpec("2000m", "4Gi", "20Gi", 3)

    def test_build_success_response(self):
        """Test building success response."""
        request = VClusterRequest(
            name="test-cluster",
            namespace="dev",
            user="testuser",
            slack_channel="C123456",
            capabilities=self.capabilities,
            resources=self.resources,
        )

        response = self.builder.build_success_response(request)

        assert response["response_type"] == "in_channel"
        assert "test-cluster" in response["text"]
        assert "🚀" in response["text"]
        assert len(response["blocks"]) == 3
        assert response["blocks"][0]["type"] == "header"
        assert response["blocks"][1]["type"] == "section"
        assert len(response["blocks"][1]["fields"]) == 4

    def test_build_error_response(self):
        """Test building error response."""
        error_message = "Invalid VCluster name"

        response = self.builder.build_error_response(error_message)

        assert response["response_type"] == "ephemeral"
        assert response["text"] == f"❌ {error_message}"

    def test_build_help_response(self):
        """Test building help response."""
        response = self.builder.build_help_response()

        assert response["response_type"] == "ephemeral"
        assert "VCluster Management Commands" in response["text"]
        assert "🤖" in response["text"]
        assert len(response["blocks"]) == 1
        assert response["blocks"][0]["type"] == "section"
        assert "/vcluster create" in response["blocks"][0]["text"]["text"]
        assert "/vcluster list" in response["blocks"][0]["text"]["text"]
        assert "/vcluster delete" in response["blocks"][0]["text"]["text"]
        assert "/vcluster status" in response["blocks"][0]["text"]["text"]

    def test_success_response_capabilities_formatting(self):
        """Test that capabilities are properly formatted in success response."""
        capabilities = CapabilitySet(observability=True, security=False, backup=True)

        request = VClusterRequest(
            name="test-cluster",
            namespace="dev",
            user="testuser",
            slack_channel="C123456",
            capabilities=capabilities,
            resources=self.resources,
        )

        response = self.builder.build_success_response(request)

        # Find the capabilities field
        capabilities_field = None
        for field in response["blocks"][1]["fields"]:
            if "*Capabilities:*" in field["text"]:
                capabilities_field = field["text"]
                break

        assert capabilities_field is not None
        assert "observability" in capabilities_field
        assert "backup" in capabilities_field
        assert "security" not in capabilities_field  # Should be filtered out (false)
