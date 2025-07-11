"""
Infrastructure Layer - NLP Command Parser Implementation
Concrete implementation of command parsing using spaCy and regex
"""

import logging
import re
from datetime import datetime
from typing import Dict, List

from ..domain.models import (Capability, ParsedCommand, ParsingError,
                             SlackCommand, VClusterSize)
from ..domain.services import CommandParserInterface

logger = logging.getLogger(__name__)

# Try to import spaCy for enhanced NLP
try:
    import spacy
    from spacy.matcher import Matcher

    SPACY_AVAILABLE = True
except ImportError:
    SPACY_AVAILABLE = False
    logger.warning("spaCy not available - using regex fallback for command parsing")


class EnhancedNLPParser(CommandParserInterface):
    """Enhanced NLP parser using spaCy with regex fallback."""

    # Capability keyword mappings
    CAPABILITY_KEYWORDS = {
        Capability.OBSERVABILITY: [
            "observability",
            "monitoring",
            "metrics",
            "grafana",
            "prometheus",
        ],
        Capability.SECURITY: ["security", "rbac", "policies", "admission"],
        Capability.GITOPS: ["gitops", "argocd", "deployment", "cd"],
        Capability.LOGGING: ["logging", "logs", "fluentd", "elasticsearch"],
        Capability.NETWORKING: ["networking", "service-mesh", "istio", "ingress"],
        Capability.AUTOSCALING: ["autoscaling", "hpa", "vpa", "scaling"],
        Capability.BACKUP: ["backup", "disaster-recovery", "br"],
    }

    def __init__(self):
        """Initialize the parser with spaCy if available."""
        self.nlp = None
        self.matcher = None
        self.spacy_available = SPACY_AVAILABLE

        if self.spacy_available:
            try:
                # Load spaCy model
                self.nlp = spacy.load("en_core_web_sm")
                self.matcher = Matcher(self.nlp.vocab)
                self._setup_patterns()
                logger.info("✅ spaCy loaded successfully - enhanced NLP enabled")
            except OSError:
                logger.warning(
                    "spaCy model not found. Install with: python -m spacy download en_core_web_sm"
                )
                self.spacy_available = False

        if not self.spacy_available:
            logger.info("Using regex-based parsing fallback")

    def _setup_patterns(self):
        """Set up spaCy patterns for entity extraction."""
        if not self.matcher:
            return

        # VCluster name patterns
        name_patterns = [
            [
                {"LOWER": "create"},
                {"TEXT": {"REGEX": r"[a-z0-9-]+"}},
            ],  # Direct pattern: create cluster-name
            [
                {"LOWER": {"IN": ["name", "called", "named"]}},
                {"TEXT": {"REGEX": r"[a-z0-9-]+"}},
            ],
            [{"LOWER": "vcluster"}, {"TEXT": {"REGEX": r"[a-z0-9-]+"}}],
        ]
        self.matcher.add("VCLUSTER_NAME", name_patterns)

        # Namespace patterns
        namespace_patterns = [
            [
                {"LOWER": {"IN": ["namespace", "ns"]}},
                {"TEXT": {"REGEX": r"[a-z0-9-]+"}},
            ],
            [
                {"LOWER": "in"},
                {"LOWER": {"IN": ["namespace", "ns"]}},
                {"TEXT": {"REGEX": r"[a-z0-9-]+"}},
            ],
        ]
        self.matcher.add("NAMESPACE", namespace_patterns)

        # Size patterns
        size_patterns = [[{"LOWER": {"IN": ["small", "medium", "large", "xlarge"]}}]]
        self.matcher.add("SIZE", size_patterns)

        # Capability patterns
        capability_keywords = []
        for cap_list in self.CAPABILITY_KEYWORDS.values():
            capability_keywords.extend(cap_list)

        capability_patterns = [
            [{"LOWER": "with"}, {"LOWER": {"IN": capability_keywords}}],
            [{"LOWER": "without"}, {"LOWER": {"IN": capability_keywords}}],
            [{"LOWER": "enable"}, {"LOWER": {"IN": capability_keywords}}],
            [{"LOWER": "disable"}, {"LOWER": {"IN": capability_keywords}}],
        ]
        self.matcher.add("CAPABILITIES", capability_patterns)

    def parse_command(self, command: SlackCommand) -> ParsedCommand:
        """Parse a Slack command into a structured format."""
        try:
            logger.debug(f"Parsing command: {command.text}")

            # Determine action
            action = self._extract_action(command.text)

            if action == "help":
                return ParsedCommand(action="help")

            if action != "create":
                return ParsedCommand(action=action)

            # Parse creation command
            if self.spacy_available and self.nlp:
                parsed = self._parse_with_spacy(command.text)
                parsed["parsing_method"] = "spacy"
            else:
                parsed = self._parse_with_regex(command.text)
                parsed["parsing_method"] = "regex"

            return ParsedCommand(
                action="create",
                vcluster_name=parsed.get("vcluster_name"),
                namespace=parsed.get("namespace", "default"),
                repository=parsed.get("repository"),
                size=parsed.get("size", VClusterSize.MEDIUM),
                enabled_capabilities=parsed.get("enabled_capabilities", []),
                disabled_capabilities=parsed.get("disabled_capabilities", []),
                parsing_method=parsed["parsing_method"],
            )

        except Exception as e:
            logger.error(f"Error parsing command: {e}", exc_info=True)
            raise ParsingError(f"Failed to parse command: {str(e)}")

    def _extract_action(self, text: str) -> str:
        """Extract the action from command text."""
        text = text.lower().strip()

        if not text or text.startswith("help"):
            return "help"
        elif text.startswith("create"):
            return "create"
        elif text.startswith("list"):
            return "list"
        elif text.startswith("delete"):
            return "delete"
        elif text.startswith("status"):
            return "status"
        else:
            return "unknown"

    def _parse_with_spacy(self, text: str) -> Dict:
        """Parse using spaCy NLP."""
        if not self.nlp or not self.matcher:
            return self._parse_with_regex(text)

        doc = self.nlp(text)
        matches = self.matcher(doc)

        extracted = {
            "vcluster_name": None,
            "namespace": "default",
            "repository": "",
            "size": VClusterSize.MEDIUM,
            "enabled_capabilities": [],
            "disabled_capabilities": [],
        }

        # Process matches
        for match_id, start, end in matches:
            label = self.nlp.vocab.strings[match_id]
            span = doc[start:end]

            if label == "VCLUSTER_NAME" and len(span) > 1:
                extracted["vcluster_name"] = span[-1].text.lower()

            elif label == "NAMESPACE" and len(span) > 1:
                extracted["namespace"] = span[-1].text.lower()

            elif label == "SIZE":
                size_text = span[0].text.lower()
                if size_text in ["small", "medium", "large", "xlarge"]:
                    extracted["size"] = VClusterSize(size_text)

            elif label == "CAPABILITIES":
                if len(span) > 1:
                    capability_text = span[-1].text.lower()
                    capability = self._find_capability_by_keyword(capability_text)

                    if capability:
                        if span[0].text.lower() in ["with", "enable"]:
                            extracted["enabled_capabilities"].append(capability)
                        elif span[0].text.lower() in ["without", "disable"]:
                            extracted["disabled_capabilities"].append(capability)

        # Additional semantic parsing for capabilities with "and" conjunctions
        text_lower = doc.text.lower()

        # More targeted capability extraction
        # Find "with" and "without" contexts
        import re

        # Extract capabilities mentioned with "with" (enabled)
        with_match = re.search(
            r"with\s+([a-z\s,and]+?)(?:\s+without|\s+in|\s+namespace|$)", text_lower
        )
        if with_match:
            with_text = with_match.group(1)
            logger.debug(f"with_text: {with_text}")
            for capability_enum, keywords in self.CAPABILITY_KEYWORDS.items():
                for keyword in keywords:
                    if keyword in with_text:
                        logger.debug(
                            f"Found keyword '{keyword}' for capability {capability_enum}"
                        )
                        if capability_enum not in extracted["enabled_capabilities"]:
                            extracted["enabled_capabilities"].append(capability_enum)

        # Extract capabilities mentioned with "without" (disabled)
        without_match = re.search(
            r"without\s+([a-z\s,and]+?)(?:\s+with|\s+in|\s+namespace|$)", text_lower
        )
        if without_match:
            without_text = without_match.group(1)
            for capability_enum, keywords in self.CAPABILITY_KEYWORDS.items():
                for keyword in keywords:
                    if keyword in without_text:
                        if capability_enum not in extracted["disabled_capabilities"]:
                            extracted["disabled_capabilities"].append(capability_enum)

        # Use named entities for additional context
        for ent in doc.ents:
            if ent.label_ == "ORG" and not extracted["repository"]:
                extracted["repository"] = ent.text.lower()

        return extracted

    def _parse_with_regex(self, text: str) -> Dict:
        """Fallback regex parsing when spaCy is not available."""
        text = text.lower().strip()

        extracted = {
            "vcluster_name": None,
            "namespace": "default",
            "repository": "",
            "size": VClusterSize.MEDIUM,
            "enabled_capabilities": [],
            "disabled_capabilities": [],
        }

        # Extract name - try explicit patterns first
        name_match = re.search(r"(?:name|called?)\s+([a-z0-9-]+)", text)
        if name_match:
            extracted["vcluster_name"] = name_match.group(1)
        else:
            # Try direct pattern, but skip size keywords
            # Pattern: create [size] cluster-name
            size_keywords = ["xlarge", "large", "medium", "small"]
            direct_match = re.search(
                r"create\s+(?:(?:" + "|".join(size_keywords) + r")\s+)?([a-z0-9-]+)",
                text,
            )
            if direct_match:
                name_candidate = direct_match.group(1)
                # Make sure we didn't just extract a size keyword
                if name_candidate not in size_keywords:
                    extracted["vcluster_name"] = name_candidate

        # Extract namespace
        namespace_match = re.search(r"(?:namespace|ns)\s+([a-z0-9-]+)", text)
        if namespace_match:
            extracted["namespace"] = namespace_match.group(1)

        # Extract repository
        repo_match = re.search(r"(?:repository|repo|app)\s+([a-z0-9-]+)", text)
        if repo_match:
            extracted["repository"] = repo_match.group(1)

        # Extract size
        for size in ["xlarge", "large", "medium", "small"]:  # Check longer sizes first
            if size in text:
                extracted["size"] = VClusterSize(size)
                break

        # Extract capabilities
        # Handle "with X and Y" patterns
        with_match = re.search(
            r"with\s+(.*?)(?:\s+without|\s+in\s+namespace|\s+repository|$)", text
        )
        if with_match:
            with_text = with_match.group(1)
            for capability, keywords in self.CAPABILITY_KEYWORDS.items():
                for keyword in keywords:
                    if keyword in with_text:
                        extracted["enabled_capabilities"].append(capability)

        # Handle "without X and Y" patterns
        without_match = re.search(
            r"without\s+(.*?)(?:\s+with|\s+in\s+namespace|\s+repository|$)", text
        )
        if without_match:
            without_text = without_match.group(1)
            for capability, keywords in self.CAPABILITY_KEYWORDS.items():
                for keyword in keywords:
                    if keyword in without_text:
                        extracted["disabled_capabilities"].append(capability)

        # Fallback to simple patterns for enable/disable
        for capability, keywords in self.CAPABILITY_KEYWORDS.items():
            for keyword in keywords:
                if f"enable {keyword}" in text:
                    if capability not in extracted["enabled_capabilities"]:
                        extracted["enabled_capabilities"].append(capability)
                elif f"disable {keyword}" in text or f"no {keyword}" in text:
                    if capability not in extracted["disabled_capabilities"]:
                        extracted["disabled_capabilities"].append(capability)

        return extracted

    def _find_capability_by_keyword(self, keyword: str) -> Capability:
        """Find capability enum by keyword."""
        for capability, keywords in self.CAPABILITY_KEYWORDS.items():
            if keyword in keywords:
                return capability
        return None
