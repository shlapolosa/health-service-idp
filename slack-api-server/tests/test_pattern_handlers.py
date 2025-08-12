"""Unit tests for pattern handlers."""

import pytest
from unittest.mock import Mock, MagicMock, patch

from src.domain.strategies.base import PatternHandler, ComponentPattern, HandlerContext, HandlerResult
from src.domain.strategies.pattern1_foundational import Pattern1FoundationalHandler
from src.domain.strategies.pattern2_compositional import Pattern2CompositionalHandler
from src.domain.strategies.pattern3_infrastructural import Pattern3InfrastructuralHandler
from src.domain.strategies.orchestrator import PatternOrchestrator


class TestPattern3InfrastructuralHandler:
    """Test Pattern 3 infrastructural handler."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.handler = Pattern3InfrastructuralHandler()
        self.context = HandlerContext(
            app_container="test-container",
            namespace="default",
            vcluster="test-vcluster",
            oam_application_name="test-app",
            oam_application_namespace="default",
            github_owner="test-owner",
            existing_components=[],
            processed_components={}
        )
    
    def test_can_handle_provider_types(self):
        """Test handler recognizes provider types."""
        assert self.handler.can_handle("neon-postgres") is True
        assert self.handler.can_handle("auth0-idp") is True
        assert self.handler.can_handle("unknown-provider") is False
    
    def test_can_handle_infrastructure_types(self):
        """Test handler recognizes infrastructure types."""
        assert self.handler.can_handle("postgresql") is True
        assert self.handler.can_handle("mongodb") is True
        assert self.handler.can_handle("redis") is True
        assert self.handler.can_handle("kafka") is True
        assert self.handler.can_handle("clickhouse") is True
    
    def test_can_handle_platform_types(self):
        """Test handler recognizes platform types."""
        assert self.handler.can_handle("realtime-platform") is True
        assert self.handler.can_handle("camunda-orchestrator") is True
    
    def test_get_pattern(self):
        """Test pattern classification."""
        assert self.handler.get_pattern() == ComponentPattern.INFRASTRUCTURAL
    
    def test_get_workflow_name_provider(self):
        """Test workflow selection for provider types."""
        component = {"type": "neon-postgres", "name": "test-db"}
        assert self.handler.get_workflow_name(component) == "pattern3-provider-workflow"
        
        component = {"type": "auth0-idp", "name": "test-auth"}
        assert self.handler.get_workflow_name(component) == "pattern3-provider-workflow"
    
    def test_get_workflow_name_infrastructure(self):
        """Test workflow selection for infrastructure types."""
        component = {"type": "postgresql", "name": "test-pg"}
        assert self.handler.get_workflow_name(component) == "pattern3-infrastructure-workflow"
        
        component = {"type": "redis", "name": "test-cache"}
        assert self.handler.get_workflow_name(component) == "pattern3-infrastructure-workflow"
    
    def test_get_workflow_name_platform(self):
        """Test workflow selection for platform types."""
        component = {"type": "realtime-platform", "name": "test-rt"}
        assert self.handler.get_workflow_name(component) == "realtime-platform-workflow"
        
        component = {"type": "camunda-orchestrator", "name": "test-camunda"}
        assert self.handler.get_workflow_name(component) == "orchestration-workflow"
    
    def test_validate_prerequisites_provider_missing_credentials(self):
        """Test validation fails for provider without credentials."""
        component = {
            "type": "neon-postgres",
            "name": "test-db",
            "properties": {}
        }
        result = self.handler.validate_prerequisites(component, self.context)
        assert result.success is False
        assert "requires credentials" in result.error
    
    def test_validate_prerequisites_provider_valid(self):
        """Test validation passes for provider with credentials."""
        component = {
            "type": "neon-postgres",
            "name": "test-db",
            "properties": {
                "credentials": {
                    "connection_string": "postgres://...",
                    "database_url": "postgres://..."
                }
            }
        }
        result = self.handler.validate_prerequisites(component, self.context)
        assert result.success is True
    
    def test_validate_prerequisites_infrastructure_invalid_size(self):
        """Test validation fails for invalid infrastructure size."""
        component = {
            "type": "postgresql",
            "name": "test-pg",
            "properties": {"size": "invalid"}
        }
        result = self.handler.validate_prerequisites(component, self.context)
        assert result.success is False
        assert "Invalid size" in result.error
    
    def test_prepare_workflow_params_provider(self):
        """Test parameter preparation for provider types."""
        component = {
            "type": "neon-postgres",
            "name": "test-db",
            "properties": {
                "credentials": {
                    "connection_string": "postgres://test",
                    "database_url": "postgres://test"
                }
            }
        }
        params = self.handler.prepare_workflow_params(component, self.context)
        
        assert params["provider_type"] == "neon-postgres"
        assert params["secret_name"] == "test-db-secret"
        assert params["namespace"] == "default"
        assert params["vcluster"] == "test-vcluster"


class TestPattern2CompositionalHandler:
    """Test Pattern 2 compositional handler."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.handler = Pattern2CompositionalHandler()
        self.context = HandlerContext(
            app_container="test-container",
            namespace="default",
            vcluster="test-vcluster",
            oam_application_name="test-app",
            oam_application_namespace="default",
            github_owner="test-owner",
            existing_components=[],
            processed_components={}
        )
    
    def test_can_handle_compositional_types(self):
        """Test handler recognizes compositional types."""
        assert self.handler.can_handle("rasa-chatbot") is True
        assert self.handler.can_handle("graphql-gateway") is True
        assert self.handler.can_handle("graphql-platform") is True
        assert self.handler.can_handle("identity-service") is True
        assert self.handler.can_handle("webservice") is False
    
    def test_get_pattern(self):
        """Test pattern classification."""
        assert self.handler.get_pattern() == ComponentPattern.COMPOSITIONAL
    
    def test_get_workflow_name(self):
        """Test workflow selection for compositional types."""
        component = {"type": "rasa-chatbot", "name": "test-chat"}
        assert self.handler.get_workflow_name(component) == "pattern2-compositional-workflow"
        
        component = {"type": "identity-service", "name": "test-identity"}
        assert self.handler.get_workflow_name(component) == "identity-service-generator"
    
    def test_validate_prerequisites_monorepo_required(self):
        """Test validation fails when monorepo is required but missing."""
        context_no_container = HandlerContext(
            app_container=None,  # No container
            namespace="default",
            vcluster="test-vcluster",
            oam_application_name="test-app",
            oam_application_namespace="default",
            github_owner="test-owner",
            existing_components=[],
            processed_components={}
        )
        
        component = {"type": "rasa-chatbot", "name": "test-chat", "properties": {}}
        result = self.handler.validate_prerequisites(component, context_no_container)
        assert result.success is False
        assert "requires an existing AppContainer" in result.error
    
    def test_validate_prerequisites_identity_service_domain(self):
        """Test validation for identity service domain requirement."""
        component = {
            "type": "identity-service",
            "name": "test-identity",
            "properties": {}  # Missing domain
        }
        result = self.handler.validate_prerequisites(component, self.context)
        assert result.success is False
        assert "requires 'domain' property" in result.error
        
        # Valid domain
        component["properties"]["domain"] = "healthcare"
        result = self.handler.validate_prerequisites(component, self.context)
        assert result.success is True
        
        # Invalid domain
        component["properties"]["domain"] = "invalid"
        result = self.handler.validate_prerequisites(component, self.context)
        assert result.success is False
        assert "Invalid domain" in result.error
    
    def test_prepare_workflow_params_rasa(self):
        """Test parameter preparation for RASA chatbot."""
        component = {
            "type": "rasa-chatbot",
            "name": "test-chat",
            "properties": {
                "nlu_pipeline": "custom_pipeline"
            }
        }
        params = self.handler.prepare_workflow_params(component, self.context)
        
        assert params["component_type"] == "rasa-chatbot"
        assert params["service_name"] == "test-chat"
        assert params["nlu_pipeline"] == "custom_pipeline"
        assert params["build_base_image"] == "true"
        assert params["build_rasa_image"] == "true"
        assert params["build_actions_image"] == "true"


class TestPattern1FoundationalHandler:
    """Test Pattern 1 foundational handler."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.handler = Pattern1FoundationalHandler()
        self.context = HandlerContext(
            app_container="test-container",
            namespace="default",
            vcluster="test-vcluster",
            oam_application_name="test-app",
            oam_application_namespace="default",
            github_owner="test-owner",
            existing_components=[],
            processed_components={}
        )
    
    def test_can_handle_foundational_types(self):
        """Test handler recognizes foundational types."""
        assert self.handler.can_handle("webservice") is True
        assert self.handler.can_handle("webservice-k8s") is True
        assert self.handler.can_handle("vcluster") is True
        assert self.handler.can_handle("postgresql") is False
    
    def test_get_pattern(self):
        """Test pattern classification."""
        assert self.handler.get_pattern() == ComponentPattern.FOUNDATIONAL
    
    def test_get_workflow_name(self):
        """Test workflow selection for foundational types."""
        component = {"type": "webservice", "name": "test-service"}
        assert self.handler.get_workflow_name(component) == "microservice-standard-contract"
        
        component = {"type": "vcluster", "name": "test-cluster"}
        assert self.handler.get_workflow_name(component) == "vcluster-workflow"
    
    def test_validate_prerequisites_webservice_missing_language(self):
        """Test validation fails for webservice without language."""
        component = {
            "type": "webservice",
            "name": "test-service",
            "properties": {}
        }
        result = self.handler.validate_prerequisites(component, self.context)
        assert result.success is False
        assert "Language property is required" in result.error
    
    def test_validate_prerequisites_webservice_invalid_language(self):
        """Test validation fails for unsupported language."""
        component = {
            "type": "webservice",
            "name": "test-service",
            "properties": {"language": "rust"}  # Not supported
        }
        result = self.handler.validate_prerequisites(component, self.context)
        assert result.success is False
        assert "Language 'rust' not supported" in result.error
    
    def test_validate_prerequisites_vcluster(self):
        """Test validation for vcluster components."""
        component = {
            "type": "vcluster",
            "name": "test-cluster",
            "properties": {}
        }
        result = self.handler.validate_prerequisites(component, self.context)
        assert result.success is True
    
    def test_prepare_workflow_params_webservice(self):
        """Test parameter preparation for webservice."""
        component = {
            "type": "webservice",
            "name": "test-service",
            "properties": {
                "language": "python",
                "framework": "fastapi",
                "minScale": 2,
                "maxScale": 20
            }
        }
        params = self.handler.prepare_workflow_params(component, self.context)
        
        assert params["service_name"] == "test-service"
        assert params["language"] == "python"
        assert params["framework"] == "fastapi"
        assert params["template_repo"] == "onion-architecture-template"
        assert params["min_scale"] == "2"
        assert params["max_scale"] == "20"
        assert params["platform"] == "knative"
    
    def test_prepare_workflow_params_webservice_k8s(self):
        """Test parameter preparation for K8s webservice."""
        component = {
            "type": "webservice-k8s",
            "name": "test-service",
            "properties": {
                "language": "nodejs",
                "framework": "express"
            }
        }
        params = self.handler.prepare_workflow_params(component, self.context)
        
        assert params["platform"] == "kubernetes"
        assert params["template_repo"] == "nodejs-express-template"


class TestPatternOrchestrator:
    """Test pattern orchestrator."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.orchestrator = PatternOrchestrator()
    
    def test_classify_component(self):
        """Test component classification."""
        # Pattern 3
        assert self.orchestrator.classify_component({"type": "postgresql"}) == ComponentPattern.INFRASTRUCTURAL
        assert self.orchestrator.classify_component({"type": "neon-postgres"}) == ComponentPattern.INFRASTRUCTURAL
        assert self.orchestrator.classify_component({"type": "realtime-platform"}) == ComponentPattern.INFRASTRUCTURAL
        
        # Pattern 2
        assert self.orchestrator.classify_component({"type": "rasa-chatbot"}) == ComponentPattern.COMPOSITIONAL
        assert self.orchestrator.classify_component({"type": "graphql-gateway"}) == ComponentPattern.COMPOSITIONAL
        
        # Pattern 1
        assert self.orchestrator.classify_component({"type": "webservice"}) == ComponentPattern.FOUNDATIONAL
        assert self.orchestrator.classify_component({"type": "vcluster"}) == ComponentPattern.FOUNDATIONAL
        
        # Unknown
        assert self.orchestrator.classify_component({"type": "unknown"}) is None
    
    def test_sort_components_by_pattern(self):
        """Test component sorting by pattern priority."""
        components = [
            {"name": "service1", "type": "webservice"},  # Pattern 1
            {"name": "db1", "type": "postgresql"},  # Pattern 3
            {"name": "chat1", "type": "rasa-chatbot"},  # Pattern 2
            {"name": "cache1", "type": "redis"},  # Pattern 3
            {"name": "service2", "type": "webservice-k8s"},  # Pattern 1
            {"name": "platform1", "type": "realtime-platform"},  # Pattern 3
        ]
        
        sorted_components = self.orchestrator.sort_components_by_pattern(components)
        
        # Check order: Pattern 3 first
        assert sorted_components[0]["type"] in ["postgresql", "redis", "realtime-platform"]
        assert sorted_components[1]["type"] in ["postgresql", "redis", "realtime-platform"]
        assert sorted_components[2]["type"] in ["postgresql", "redis", "realtime-platform"]
        
        # Pattern 2 next
        assert sorted_components[3]["type"] == "rasa-chatbot"
        
        # Pattern 1 last
        assert sorted_components[4]["type"] in ["webservice", "webservice-k8s"]
        assert sorted_components[5]["type"] in ["webservice", "webservice-k8s"]
    
    def test_handle_oam_application_dry_run(self):
        """Test OAM application handling in dry run mode (no argo_client)."""
        oam_app = {
            "metadata": {
                "name": "test-app",
                "namespace": "default",
                "labels": {"app-container": "test-container"}
            },
            "spec": {
                "components": [
                    {
                        "name": "db",
                        "type": "postgresql",
                        "properties": {"size": "small"}
                    },
                    {
                        "name": "service",
                        "type": "webservice",
                        "properties": {"language": "python"}
                    }
                ]
            }
        }
        
        results = self.orchestrator.handle_oam_application(oam_app)
        
        assert len(results) == 2
        # PostgreSQL should be processed first
        assert results[0].pattern == ComponentPattern.INFRASTRUCTURAL
        assert results[0].success is True
        assert results[0].metadata["dry_run"] is True
        
        # Webservice should be processed second
        assert results[1].pattern == ComponentPattern.FOUNDATIONAL
        assert results[1].success is True
    
    def test_get_processing_summary(self):
        """Test processing summary generation."""
        results = [
            HandlerResult(
                success=True,
                workflow_name="pattern3-infrastructure-workflow",
                workflow_run_name="run-123",
                error=None,
                metadata={},
                pattern=ComponentPattern.INFRASTRUCTURAL
            ),
            HandlerResult(
                success=False,
                workflow_name=None,
                workflow_run_name=None,
                error="Test error",
                metadata={},
                pattern=ComponentPattern.FOUNDATIONAL
            ),
            HandlerResult(
                success=True,
                workflow_name="microservice-standard-contract",
                workflow_run_name="run-456",
                error=None,
                metadata={},
                pattern=ComponentPattern.FOUNDATIONAL
            )
        ]
        
        summary = self.orchestrator.get_processing_summary(results)
        
        assert summary["total"] == 3
        assert summary["successful"] == 2
        assert summary["failed"] == 1
        assert len(summary["workflows_triggered"]) == 2
        assert len(summary["errors"]) == 1
        assert summary["by_pattern"]["pattern_3"]["successful"] == 1
        assert summary["by_pattern"]["pattern_1"]["total"] == 2
        assert summary["by_pattern"]["pattern_1"]["successful"] == 1
        assert summary["by_pattern"]["pattern_1"]["failed"] == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])