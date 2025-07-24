"""
Unit tests for infrastructure NLP parser
"""

from unittest.mock import Mock, patch

import pytest

from src.domain.models import (Capability, ParsedCommand, ParsingError,
                               SlackCommand, VClusterSize)
from src.infrastructure.nlp_parser import EnhancedNLPParser


class TestEnhancedNLPParser:
    """Test EnhancedNLPParser infrastructure service."""

    def setup_method(self):
        """Set up test fixtures."""
        self.parser = EnhancedNLPParser()

    def test_parse_help_command(self):
        """Test parsing help command."""
        command = SlackCommand(
            command="/vcluster",
            text="help",
            user_id="U123",
            user_name="testuser",
            channel_id="C123",
            channel_name="general",
            team_id="T123",
            team_domain="testteam",
        )

        result = self.parser.parse_command(command)

        assert result.action == "help"

    def test_parse_empty_command(self):
        """Test parsing empty command."""
        command = SlackCommand(
            command="/vcluster",
            text="",
            user_id="U123",
            user_name="testuser",
            channel_id="C123",
            channel_name="general",
            team_id="T123",
            team_domain="testteam",
        )

        result = self.parser.parse_command(command)

        assert result.action == "help"

    def test_parse_create_command_basic(self):
        """Test parsing basic create command."""
        command = SlackCommand(
            command="/vcluster",
            text="create test-cluster",
            user_id="U123",
            user_name="testuser",
            channel_id="C123",
            channel_name="general",
            team_id="T123",
            team_domain="testteam",
        )

        result = self.parser.parse_command(command)

        assert result.action == "create"
        assert result.vcluster_name == "test-cluster"
        assert result.namespace == "default"
        assert result.size == VClusterSize.MEDIUM
        assert result.enabled_capabilities == []
        assert result.disabled_capabilities == []

    def test_parse_create_command_with_namespace(self):
        """Test parsing create command with namespace."""
        command = SlackCommand(
            command="/vcluster",
            text="create test-cluster in namespace dev",
            user_id="U123",
            user_name="testuser",
            channel_id="C123",
            channel_name="general",
            team_id="T123",
            team_domain="testteam",
        )

        result = self.parser.parse_command(command)

        assert result.action == "create"
        assert result.vcluster_name == "test-cluster"
        assert result.namespace == "dev"

    def test_parse_create_command_with_size(self):
        """Test parsing create command with size."""
        for size_text, expected_size in [
            ("small", VClusterSize.SMALL),
            ("medium", VClusterSize.MEDIUM),
            ("large", VClusterSize.LARGE),
            ("xlarge", VClusterSize.XLARGE),
        ]:
            command = SlackCommand(
                command="/vcluster",
                text=f"create {size_text} test-cluster",
                user_id="U123",
                user_name="testuser",
                channel_id="C123",
                channel_name="general",
                team_id="T123",
                team_domain="testteam",
            )

            result = self.parser.parse_command(command)

            assert result.action == "create"
            assert result.size == expected_size

    def test_parse_create_command_with_capabilities(self):
        """Test parsing create command with capabilities."""
        test_cases = [
            ("create test-cluster with observability", [Capability.OBSERVABILITY], []),
            (
                "create test-cluster with observability and security",
                [Capability.OBSERVABILITY, Capability.SECURITY],
                [],
            ),
            ("create test-cluster without backup", [], [Capability.BACKUP]),
            (
                "create test-cluster with observability without backup",
                [Capability.OBSERVABILITY],
                [Capability.BACKUP],
            ),
        ]

        for text, expected_enabled, expected_disabled in test_cases:
            command = SlackCommand(
                command="/vcluster",
                text=text,
                user_id="U123",
                user_name="testuser",
                channel_id="C123",
                channel_name="general",
                team_id="T123",
                team_domain="testteam",
            )

            result = self.parser.parse_command(command)

            assert result.action == "create"
            assert set(result.enabled_capabilities) == set(expected_enabled)
            assert set(result.disabled_capabilities) == set(expected_disabled)

    def test_parse_create_command_with_repository(self):
        """Test parsing create command with repository."""
        command = SlackCommand(
            command="/vcluster",
            text="create test-cluster repository artifacts",
            user_id="U123",
            user_name="testuser",
            channel_id="C123",
            channel_name="general",
            team_id="T123",
            team_domain="testteam",
        )

        result = self.parser.parse_command(command)

        assert result.action == "create"
        assert result.repository == "artifacts"

    def test_parse_complex_command(self):
        """Test parsing complex command with multiple parameters."""
        command = SlackCommand(
            command="/vcluster",
            text="create large test-cluster with observability and security without backup in namespace prod repository artifacts",
            user_id="U123",
            user_name="testuser",
            channel_id="C123",
            channel_name="general",
            team_id="T123",
            team_domain="testteam",
        )

        result = self.parser.parse_command(command)

        assert result.action == "create"
        assert result.vcluster_name == "test-cluster"
        assert result.namespace == "prod"
        assert result.size == VClusterSize.LARGE
        assert result.repository == "artifacts"
        assert Capability.OBSERVABILITY in result.enabled_capabilities
        assert Capability.SECURITY in result.enabled_capabilities
        assert Capability.BACKUP in result.disabled_capabilities

    def test_parse_unknown_action(self):
        """Test parsing unknown action."""
        command = SlackCommand(
            command="/vcluster",
            text="unknown action",
            user_id="U123",
            user_name="testuser",
            channel_id="C123",
            channel_name="general",
            team_id="T123",
            team_domain="testteam",
        )

        result = self.parser.parse_command(command)

        assert result.action == "unknown"

    def test_extract_action(self):
        """Test action extraction from text."""
        test_cases = [
            ("", "help"),
            ("help", "help"),
            ("create test", "create"),
            ("list", "list"),
            ("delete test", "delete"),
            ("status test", "status"),
            ("unknown", "unknown"),
        ]

        for text, expected_action in test_cases:
            action = self.parser._extract_action(text)
            assert action == expected_action

    def test_find_capability_by_keyword(self):
        """Test finding capability by keyword."""
        test_cases = [
            ("observability", Capability.OBSERVABILITY),
            ("monitoring", Capability.OBSERVABILITY),
            ("security", Capability.SECURITY),
            ("gitops", Capability.GITOPS),
            ("logging", Capability.LOGGING),
            ("networking", Capability.NETWORKING),
            ("autoscaling", Capability.AUTOSCALING),
            ("backup", Capability.BACKUP),
            ("unknown", None),
        ]

        for keyword, expected_capability in test_cases:
            capability = self.parser._find_capability_by_keyword(keyword)
            assert capability == expected_capability

    def test_regex_parsing_fallback(self):
        """Test regex parsing when spaCy is not available."""
        # Mock spaCy as unavailable
        with patch.object(self.parser, "spacy_available", False):
            command = SlackCommand(
                command="/vcluster",
                text="create test-cluster with observability in namespace dev",
                user_id="U123",
                user_name="testuser",
                channel_id="C123",
                channel_name="general",
                team_id="T123",
                team_domain="testteam",
            )

            result = self.parser.parse_command(command)

            assert result.action == "create"
            assert result.vcluster_name == "test-cluster"
            assert result.namespace == "dev"
            assert result.parsing_method == "regex"
            assert Capability.OBSERVABILITY in result.enabled_capabilities

    def test_regex_parsing_direct(self):
        """Test direct regex parsing method."""
        text = "create large test-cluster with observability without backup in namespace prod repository artifacts"

        result = self.parser._parse_with_regex(text)

        assert result["vcluster_name"] == "test-cluster"
        assert result["namespace"] == "prod"
        assert result["size"] == VClusterSize.LARGE
        assert result["repository"] == "artifacts"
        assert Capability.OBSERVABILITY in result["enabled_capabilities"]
        assert Capability.BACKUP in result["disabled_capabilities"]

    def test_parsing_error_handling(self):
        """Test error handling during parsing."""
        # Mock parser to raise exception
        with patch.object(
            self.parser, "_extract_command_type_and_action", side_effect=Exception("Test error")
        ):
            command = SlackCommand(
                command="/vcluster",
                text="create test-cluster",
                user_id="U123",
                user_name="testuser",
                channel_id="C123",
                channel_name="general",
                team_id="T123",
                team_domain="testteam",
            )

            with pytest.raises(ParsingError, match="Failed to parse command"):
                self.parser.parse_command(command)

    @patch("src.infrastructure.nlp_parser.Matcher")
    @patch("src.infrastructure.nlp_parser.spacy")
    def test_spacy_initialization_success(self, mock_spacy, mock_matcher_class):
        """Test successful spaCy initialization."""
        mock_nlp = Mock()
        mock_matcher = Mock()
        mock_spacy.load.return_value = mock_nlp
        mock_matcher_class.return_value = mock_matcher

        parser = EnhancedNLPParser()

        assert parser.spacy_available is True
        assert parser.nlp == mock_nlp
        assert parser.matcher == mock_matcher
        mock_spacy.load.assert_called_once_with("en_core_web_sm")
        mock_matcher_class.assert_called_once_with(mock_nlp.vocab)

    @patch("src.infrastructure.nlp_parser.spacy")
    def test_spacy_initialization_failure(self, mock_spacy):
        """Test spaCy initialization failure."""
        mock_spacy.load.side_effect = OSError("Model not found")

        parser = EnhancedNLPParser()

        assert parser.spacy_available is False
        assert parser.nlp is None

    @patch("src.infrastructure.nlp_parser.SPACY_AVAILABLE", False)
    def test_spacy_not_available(self):
        """Test behavior when spaCy is not available."""
        parser = EnhancedNLPParser()

        assert parser.spacy_available is False
        assert parser.nlp is None

    def test_parse_appcontainer_basic_command(self):
        """Test parsing basic AppContainer command."""
        command = SlackCommand(
            command="/appcontainer",
            text="create my-app",
            user_id="U123",
            user_name="testuser",
            channel_id="C123",
            channel_name="general",
            team_id="T123",
            team_domain="testteam",
        )

        result = self.parser.parse_command(command)

        assert result.action == "create"
        assert result.command_type == "appcontainer"
        assert result.appcontainer_name == "my-app"
        assert result.namespace == "default"
        assert result.description == "CLAUDE.md-compliant application container"
        assert result.github_org == "shlapolosa"
        assert result.enable_observability is True
        assert result.enable_security is True

    def test_parse_appcontainer_with_namespace(self):
        """Test parsing AppContainer command with namespace."""
        command = SlackCommand(
            command="/appcontainer",
            text="create my-backend in namespace production",
            user_id="U123",
            user_name="testuser",
            channel_id="C123",
            channel_name="general",
            team_id="T123",
            team_domain="testteam",
        )

        result = self.parser.parse_command(command)

        assert result.action == "create"
        assert result.command_type == "appcontainer"
        assert result.appcontainer_name == "my-backend"
        assert result.namespace == "production"

    def test_parse_appcontainer_with_description(self):
        """Test parsing AppContainer command with description."""
        command = SlackCommand(
            command="/appcontainer",
            text='create my-api description "REST API for user management"',
            user_id="U123",
            user_name="testuser",
            channel_id="C123",
            channel_name="general",
            team_id="T123",
            team_domain="testteam",
        )

        result = self.parser.parse_command(command)

        assert result.action == "create"
        assert result.command_type == "appcontainer"
        assert result.appcontainer_name == "my-api"
        assert result.description == "rest api for user management"

    def test_parse_appcontainer_with_github_org(self):
        """Test parsing AppContainer command with GitHub org."""
        command = SlackCommand(
            command="/appcontainer",
            text="create my-service github-org mycompany",
            user_id="U123",
            user_name="testuser",
            channel_id="C123",
            channel_name="general",
            team_id="T123",
            team_domain="testteam",
        )

        result = self.parser.parse_command(command)

        assert result.action == "create"
        assert result.command_type == "appcontainer"
        assert result.appcontainer_name == "my-service"
        assert result.github_org == "mycompany"

    def test_parse_appcontainer_without_security(self):
        """Test parsing AppContainer command without security."""
        command = SlackCommand(
            command="/appcontainer",
            text="create test-app without security",
            user_id="U123",
            user_name="testuser",
            channel_id="C123",
            channel_name="general",
            team_id="T123",
            team_domain="testteam",
        )

        result = self.parser.parse_command(command)

        assert result.action == "create"
        assert result.command_type == "appcontainer"
        assert result.appcontainer_name == "test-app"
        assert result.enable_security is False
        assert result.enable_observability is True  # Should still be default

    def test_parse_appcontainer_help_command(self):
        """Test parsing AppContainer help command."""
        command = SlackCommand(
            command="/appcontainer",
            text="help",
            user_id="U123",
            user_name="testuser",
            channel_id="C123",
            channel_name="general",
            team_id="T123",
            team_domain="testteam",
        )

        result = self.parser.parse_command(command)

        assert result.action == "help"
        assert result.command_type == "appcontainer"

    def test_extract_command_type_and_action(self):
        """Test command type and action extraction."""
        # Test VCluster command
        vcluster_command = SlackCommand(
            command="/vcluster",
            text="create test",
            user_id="U123",
            user_name="testuser",
            channel_id="C123",
            channel_name="general",
            team_id="T123",
            team_domain="testteam",
        )

        command_type, action = self.parser._extract_command_type_and_action(vcluster_command)
        assert command_type == "vcluster"
        assert action == "create"

        # Test AppContainer command
        appcontainer_command = SlackCommand(
            command="/appcontainer",
            text="create test",
            user_id="U123",
            user_name="testuser",
            channel_id="C123",
            channel_name="general",
            team_id="T123",
            team_domain="testteam",
        )

        command_type, action = self.parser._extract_command_type_and_action(appcontainer_command)
        assert command_type == "appcontainer"
        assert action == "create"

        # Test help action
        help_command = SlackCommand(
            command="/appcontainer",
            text="help",
            user_id="U123",
            user_name="testuser",
            channel_id="C123",
            channel_name="general",
            team_id="T123",
            team_domain="testteam",
        )

        command_type, action = self.parser._extract_command_type_and_action(help_command)
        assert command_type == "appcontainer"
        assert action == "help"
