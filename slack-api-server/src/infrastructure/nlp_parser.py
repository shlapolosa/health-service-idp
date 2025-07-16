"""
Infrastructure Layer - NLP Command Parser Implementation
Concrete implementation of command parsing using spaCy and regex
"""

import logging
import re
from datetime import datetime
from typing import Dict, List

from ..domain.models import (Capability, MicroserviceCache, MicroserviceDatabase, 
                             MicroserviceLanguage, ParsedCommand, ParsingError,
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
        vcluster_name_patterns = [
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
        self.matcher.add("VCLUSTER_NAME", vcluster_name_patterns)

        # AppContainer name patterns
        appcontainer_name_patterns = [
            [
                {"LOWER": "create"},
                {"TEXT": {"REGEX": r"[a-z0-9-]+"}},
            ],  # Direct pattern: create app-name
            [
                {"LOWER": {"IN": ["name", "called", "named"]}},
                {"TEXT": {"REGEX": r"[a-z0-9-]+"}},
            ],
            [{"LOWER": "appcontainer"}, {"TEXT": {"REGEX": r"[a-z0-9-]+"}}],
            [{"LOWER": "app"}, {"TEXT": {"REGEX": r"[a-z0-9-]+"}}],
        ]
        self.matcher.add("APPCONTAINER_NAME", appcontainer_name_patterns)

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

        # Description patterns for AppContainer
        description_patterns = [
            [
                {"LOWER": {"IN": ["description", "desc"]}},
                {"TEXT": {"REGEX": r"[\"']"}},
                {"TEXT": {"REGEX": r".*"}},
                {"TEXT": {"REGEX": r"[\"']"}},
            ],
        ]
        self.matcher.add("DESCRIPTION", description_patterns)

        # GitHub org patterns
        github_patterns = [
            [
                {"LOWER": {"IN": ["github-org", "org", "organization"]}},
                {"TEXT": {"REGEX": r"[a-z0-9-]+"}},
            ],
        ]
        self.matcher.add("GITHUB_ORG", github_patterns)

        # VCluster patterns for AppContainer
        vcluster_patterns = [
            [
                {"LOWER": {"IN": ["vcluster", "cluster"]}},
                {"TEXT": {"REGEX": r"[a-z0-9-]+"}},
            ],
            [
                {"LOWER": "in"},
                {"LOWER": {"IN": ["vcluster", "cluster"]}},
                {"TEXT": {"REGEX": r"[a-z0-9-]+"}},
            ],
            [
                {"LOWER": {"IN": ["no-vcluster", "no-cluster", "auto-create"]}},
            ],
        ]
        self.matcher.add("TARGET_VCLUSTER", vcluster_patterns)

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

        # AppContainer specific capability patterns
        appcontainer_features = ["observability", "security", "monitoring", "scanning"]
        appcontainer_patterns = [
            [{"LOWER": "with"}, {"LOWER": {"IN": appcontainer_features}}],
            [{"LOWER": "without"}, {"LOWER": {"IN": appcontainer_features}}],
            [{"LOWER": "enable"}, {"LOWER": {"IN": appcontainer_features}}],
            [{"LOWER": "disable"}, {"LOWER": {"IN": appcontainer_features}}],
            [{"LOWER": "no"}, {"LOWER": {"IN": appcontainer_features}}],
        ]
        self.matcher.add("APPCONTAINER_FEATURES", appcontainer_patterns)

        # Microservice name patterns
        microservice_name_patterns = [
            [
                {"LOWER": "create"},
                {"TEXT": {"REGEX": r"[a-z0-9-]+"}},
            ],  # Direct pattern: create service-name
            [
                {"LOWER": {"IN": ["name", "called", "named"]}},
                {"TEXT": {"REGEX": r"[a-z0-9-]+"}},
            ],
            [{"LOWER": "microservice"}, {"TEXT": {"REGEX": r"[a-z0-9-]+"}}],
            [{"LOWER": "service"}, {"TEXT": {"REGEX": r"[a-z0-9-]+"}}],
        ]
        self.matcher.add("MICROSERVICE_NAME", microservice_name_patterns)

        # Language patterns
        language_patterns = [
            [
                {"LOWER": {"IN": ["language", "lang", "type"]}},
                {"LOWER": {"IN": ["python", "java", "springboot", "fastapi"]}},
            ],
            [
                {"LOWER": {"IN": ["python", "java", "springboot", "fastapi"]}},
            ],
        ]
        self.matcher.add("MICROSERVICE_LANGUAGE", language_patterns)

        # Database patterns
        database_patterns = [
            [
                {"LOWER": {"IN": ["database", "db"]}},
                {"LOWER": {"IN": ["postgresql", "postgres", "none"]}},
            ],
            [
                {"LOWER": "with"},
                {"LOWER": {"IN": ["postgresql", "postgres", "database", "db"]}},
            ],
            [
                {"LOWER": "without"},
                {"LOWER": {"IN": ["database", "db"]}},
            ],
        ]
        self.matcher.add("MICROSERVICE_DATABASE", database_patterns)

        # Cache patterns
        cache_patterns = [
            [
                {"LOWER": "cache"},
                {"LOWER": {"IN": ["redis", "none"]}},
            ],
            [
                {"LOWER": "with"},
                {"LOWER": {"IN": ["redis", "cache"]}},
            ],
            [
                {"LOWER": "without"},
                {"LOWER": {"IN": ["cache", "redis"]}},
            ],
        ]
        self.matcher.add("MICROSERVICE_CACHE", cache_patterns)

        # Repository patterns
        repository_patterns = [
            [
                {"LOWER": {"IN": ["repository", "repo", "app"]}},
                {"TEXT": {"REGEX": r"[a-z0-9-]+"}},
            ],
            [
                {"LOWER": {"IN": ["in", "to", "under"]}},
                {"LOWER": {"IN": ["repository", "repo", "app"]}},
                {"TEXT": {"REGEX": r"[a-z0-9-]+"}},
            ],
        ]
        self.matcher.add("MICROSERVICE_REPOSITORY", repository_patterns)

    def parse_command(self, command: SlackCommand) -> ParsedCommand:
        """Parse a Slack command into a structured format."""
        try:
            logger.debug(f"Parsing command: {command.command} {command.text}")

            # Determine command type and action
            command_type, action = self._extract_command_type_and_action(command)

            if action == "help":
                return ParsedCommand(action="help", command_type=command_type)

            if action != "create":
                return ParsedCommand(action=action, command_type=command_type)

            # Parse creation command based on type
            if command_type == "appcontainer":
                return self._parse_appcontainer_command(command.text)
            elif command_type == "microservice":
                return self._parse_microservice_command(command.text)
            else:  # default to vcluster
                return self._parse_vcluster_command(command.text)

        except Exception as e:
            logger.error(f"Error parsing command: {e}", exc_info=True)
            raise ParsingError(f"Failed to parse command: {str(e)}")

    def _parse_vcluster_command(self, text: str) -> ParsedCommand:
        """Parse VCluster creation command."""
        # Parse creation command
        if self.spacy_available and self.nlp:
            parsed = self._parse_with_spacy(text)
            parsed["parsing_method"] = "spacy"
        else:
            parsed = self._parse_with_regex(text)
            parsed["parsing_method"] = "regex"

        return ParsedCommand(
            action="create",
            command_type="vcluster",
            vcluster_name=parsed.get("vcluster_name"),
            namespace=parsed.get("namespace", "default"),
            repository=parsed.get("repository"),
            size=parsed.get("size", VClusterSize.MEDIUM),
            enabled_capabilities=parsed.get("enabled_capabilities", []),
            disabled_capabilities=parsed.get("disabled_capabilities", []),
            parsing_method=parsed["parsing_method"],
        )

    def _parse_appcontainer_command(self, text: str) -> ParsedCommand:
        """Parse AppContainer creation command."""
        # Try spaCy first if available
        if self.spacy_available and self.nlp:
            parsed = self._parse_appcontainer_with_spacy(text)
            parsed["parsing_method"] = "spacy"
        else:
            parsed = self._parse_appcontainer_with_regex(text)
            parsed["parsing_method"] = "regex"

        return ParsedCommand(
            action="create",
            command_type="appcontainer",
            appcontainer_name=parsed.get("appcontainer_name"),
            namespace=parsed.get("namespace", "default"),
            description=parsed.get("description", "CLAUDE.md-compliant application container"),
            github_org=parsed.get("github_org", "socrates12345"),
            docker_registry=parsed.get("docker_registry", "docker.io/socrates12345"),
            enable_observability=parsed.get("enable_observability", True),
            enable_security=parsed.get("enable_security", True),
            target_vcluster=parsed.get("target_vcluster"),
            auto_create_vcluster=parsed.get("auto_create_vcluster", True),
            parsing_method=parsed["parsing_method"],
        )

    def _parse_appcontainer_with_spacy(self, text: str) -> Dict:
        """Parse AppContainer using spaCy NLP."""
        if not self.nlp or not self.matcher:
            return self._parse_appcontainer_with_regex(text)

        doc = self.nlp(text)
        matches = self.matcher(doc)

        extracted = {
            "appcontainer_name": None,
            "namespace": "default",
            "description": "CLAUDE.md-compliant application container",
            "github_org": "socrates12345", 
            "docker_registry": "docker.io/socrates12345",
            "enable_observability": True,
            "enable_security": True,
            "target_vcluster": None,
            "auto_create_vcluster": True,
        }

        # Process spaCy matches
        for match_id, start, end in matches:
            label = self.nlp.vocab.strings[match_id]
            span = doc[start:end]

            if label == "APPCONTAINER_NAME" and len(span) > 1:
                extracted["appcontainer_name"] = span[-1].text.lower()

            elif label == "NAMESPACE" and len(span) > 1:
                extracted["namespace"] = span[-1].text.lower()

            elif label == "GITHUB_ORG" and len(span) > 1:
                extracted["github_org"] = span[-1].text.lower()

            elif label == "TARGET_VCLUSTER":
                if len(span) > 1:
                    # "vcluster my-cluster" or "in vcluster my-cluster"
                    extracted["target_vcluster"] = span[-1].text.lower()
                else:
                    # "no-vcluster" or "auto-create"
                    option = span[0].text.lower()
                    if option in ["no-vcluster", "no-cluster"]:
                        extracted["auto_create_vcluster"] = False
                    elif option == "auto-create":
                        extracted["auto_create_vcluster"] = True

            elif label == "APPCONTAINER_FEATURES":
                if len(span) > 1:
                    feature_text = span[-1].text.lower()
                    action_word = span[0].text.lower()
                    
                    if feature_text in ["observability", "monitoring"]:
                        if action_word in ["with", "enable"]:
                            extracted["enable_observability"] = True
                        elif action_word in ["without", "disable", "no"]:
                            extracted["enable_observability"] = False
                    
                    elif feature_text in ["security", "scanning"]:
                        if action_word in ["with", "enable"]:
                            extracted["enable_security"] = True
                        elif action_word in ["without", "disable", "no"]:
                            extracted["enable_security"] = False

        # Fallback to regex for anything missed
        text_lower = text.lower()
        
        # Extract description if not found by spaCy
        desc_match = re.search(r"(?:description|desc)\s+[\"']([^\"']+)[\"']", text_lower)
        if desc_match:
            extracted["description"] = desc_match.group(1).strip()

        return extracted

    def _parse_appcontainer_with_regex(self, text: str) -> Dict:
        """Parse AppContainer creation command using regex."""
        text = text.lower().strip()
        
        extracted = {
            "appcontainer_name": None,
            "namespace": "default",
            "description": "CLAUDE.md-compliant application container",
            "github_org": "socrates12345",
            "docker_registry": "docker.io/socrates12345",
            "enable_observability": True,
            "enable_security": True,
            "target_vcluster": None,
            "auto_create_vcluster": True,
        }
        
        # Extract AppContainer name - look for various patterns
        name_patterns = [
            r"create\s+([a-z0-9-]+)",  # "create my-app"
            r"(?:name|called?)\s+([a-z0-9-]+)",  # "name my-app" or "called my-app"
            r"appcontainer\s+([a-z0-9-]+)",  # "appcontainer my-app"
        ]
        
        for pattern in name_patterns:
            name_match = re.search(pattern, text)
            if name_match:
                extracted["appcontainer_name"] = name_match.group(1)
                break
        
        # Extract namespace
        namespace_match = re.search(r"(?:in\s+)?(?:namespace|ns)\s+([a-z0-9-]+)", text)
        if namespace_match:
            extracted["namespace"] = namespace_match.group(1)
        
        # Extract description - look for quoted or unquoted descriptions
        desc_patterns = [
            r"(?:description|desc)\s+[\"']([^\"']+)[\"']",  # quoted description
            r"(?:description|desc)\s+([^,\s]+(?:\s+[^,\s]+)*)",  # unquoted description
        ]
        
        for pattern in desc_patterns:
            desc_match = re.search(pattern, text)
            if desc_match:
                extracted["description"] = desc_match.group(1).strip()
                break
        
        # Extract GitHub org
        org_match = re.search(r"(?:github-org|org|organization)\s+([a-z0-9-]+)", text)
        if org_match:
            extracted["github_org"] = org_match.group(1)
        
        # Extract docker registry
        registry_match = re.search(r"(?:docker-registry|registry)\s+([a-z0-9.-/]+)", text)
        if registry_match:
            extracted["docker_registry"] = registry_match.group(1)
        
        # Extract vCluster information
        vcluster_patterns = [
            r"(?:in\s+)?(?:vcluster|cluster)\s+([a-z0-9-]+)",  # "vcluster my-cluster" or "in vcluster my-cluster"
        ]
        for pattern in vcluster_patterns:
            vcluster_match = re.search(pattern, text)
            if vcluster_match:
                extracted["target_vcluster"] = vcluster_match.group(1)
                break
        
        # Check for auto-create disable flags
        if any(phrase in text for phrase in ["no-vcluster", "no-cluster", "disable-auto-create"]):
            extracted["auto_create_vcluster"] = False
        elif "auto-create" in text:
            extracted["auto_create_vcluster"] = True
        
        # Extract observability setting
        if any(phrase in text for phrase in ["no-observability", "disable-observability", "without observability"]):
            extracted["enable_observability"] = False
        elif "observability" in text:
            extracted["enable_observability"] = True
            
        # Extract security setting
        if any(phrase in text for phrase in ["no-security", "disable-security", "without security"]):
            extracted["enable_security"] = False
        elif "security" in text:
            extracted["enable_security"] = True

        return extracted

    def _parse_microservice_command(self, text: str) -> ParsedCommand:
        """Parse Microservice creation command."""
        # Try spaCy first if available
        if self.spacy_available and self.nlp:
            parsed = self._parse_microservice_with_spacy(text)
            parsed["parsing_method"] = "spacy"
        else:
            parsed = self._parse_microservice_with_regex(text)
            parsed["parsing_method"] = "regex"

        return ParsedCommand(
            action="create",
            command_type="microservice",
            microservice_name=parsed.get("microservice_name"),
            namespace=parsed.get("namespace", "default"),
            description=parsed.get("description", "CLAUDE.md-compliant microservice"),
            github_org=parsed.get("github_org", "socrates12345"),
            docker_registry=parsed.get("docker_registry", "docker.io/socrates12345"),
            enable_observability=parsed.get("enable_observability", True),
            enable_security=parsed.get("enable_security", True),
            target_vcluster=parsed.get("target_vcluster"),
            auto_create_vcluster=parsed.get("auto_create_vcluster", True),
            repository=parsed.get("repository"),
            microservice_language=parsed.get("microservice_language", MicroserviceLanguage.PYTHON),
            microservice_database=parsed.get("microservice_database", MicroserviceDatabase.NONE),
            microservice_cache=parsed.get("microservice_cache", MicroserviceCache.NONE),
            parsing_method=parsed["parsing_method"],
        )

    def _parse_microservice_with_spacy(self, text: str) -> Dict:
        """Parse Microservice using spaCy NLP."""
        if not self.nlp or not self.matcher:
            return self._parse_microservice_with_regex(text)

        doc = self.nlp(text)
        matches = self.matcher(doc)

        extracted = {
            "microservice_name": None,
            "namespace": "default",
            "description": "CLAUDE.md-compliant microservice",
            "github_org": "socrates12345",
            "docker_registry": "docker.io/socrates12345",
            "enable_observability": True,
            "enable_security": True,
            "target_vcluster": None,
            "auto_create_vcluster": True,
            "repository": None,
            "microservice_language": MicroserviceLanguage.PYTHON,
            "microservice_database": MicroserviceDatabase.NONE,
            "microservice_cache": MicroserviceCache.NONE,
        }

        # Process spaCy matches
        for match_id, start, end in matches:
            label = self.nlp.vocab.strings[match_id]
            span = doc[start:end]

            if label == "MICROSERVICE_NAME" and len(span) > 1:
                extracted["microservice_name"] = span[-1].text.lower()

            elif label == "NAMESPACE" and len(span) > 1:
                extracted["namespace"] = span[-1].text.lower()

            elif label == "GITHUB_ORG" and len(span) > 1:
                extracted["github_org"] = span[-1].text.lower()

            elif label == "TARGET_VCLUSTER":
                if len(span) > 1:
                    # "vcluster my-cluster" or "in vcluster my-cluster"
                    extracted["target_vcluster"] = span[-1].text.lower()
                else:
                    # "no-vcluster" or "auto-create"
                    option = span[0].text.lower()
                    if option in ["no-vcluster", "no-cluster"]:
                        extracted["auto_create_vcluster"] = False
                    elif option == "auto-create":
                        extracted["auto_create_vcluster"] = True

            elif label == "MICROSERVICE_LANGUAGE":
                if len(span) > 1:
                    lang_text = span[-1].text.lower()
                else:
                    lang_text = span[0].text.lower()
                
                if lang_text in ["python", "fastapi"]:
                    extracted["microservice_language"] = MicroserviceLanguage.PYTHON
                elif lang_text in ["java", "springboot"]:
                    extracted["microservice_language"] = MicroserviceLanguage.JAVA

            elif label == "MICROSERVICE_DATABASE":
                if len(span) > 1:
                    db_text = span[-1].text.lower()
                    action_word = span[0].text.lower()
                    
                    if action_word == "without":
                        extracted["microservice_database"] = MicroserviceDatabase.NONE
                    elif db_text in ["postgresql", "postgres"]:
                        extracted["microservice_database"] = MicroserviceDatabase.POSTGRESQL
                    elif action_word == "with" and db_text in ["database", "db"]:
                        extracted["microservice_database"] = MicroserviceDatabase.POSTGRESQL

            elif label == "MICROSERVICE_CACHE":
                if len(span) > 1:
                    cache_text = span[-1].text.lower()
                    action_word = span[0].text.lower()
                    
                    if action_word == "without":
                        extracted["microservice_cache"] = MicroserviceCache.NONE
                    elif cache_text == "redis":
                        extracted["microservice_cache"] = MicroserviceCache.REDIS
                    elif action_word == "with" and cache_text == "cache":
                        extracted["microservice_cache"] = MicroserviceCache.REDIS

            elif label == "MICROSERVICE_REPOSITORY" and len(span) > 1:
                extracted["repository"] = span[-1].text.lower()

        # Fallback to regex for anything missed
        text_lower = text.lower()
        
        # Extract description if not found by spaCy
        desc_match = re.search(r"(?:description|desc)\s+[\"']([^\"']+)[\"']", text_lower)
        if desc_match:
            extracted["description"] = desc_match.group(1).strip()

        return extracted

    def _parse_microservice_with_regex(self, text: str) -> Dict:
        """Parse Microservice creation command using regex."""
        text = text.lower().strip()
        
        extracted = {
            "microservice_name": None,
            "namespace": "default",
            "description": "CLAUDE.md-compliant microservice",
            "github_org": "socrates12345",
            "docker_registry": "docker.io/socrates12345",
            "enable_observability": True,
            "enable_security": True,
            "target_vcluster": None,
            "auto_create_vcluster": True,
            "repository": None,
            "microservice_language": MicroserviceLanguage.PYTHON,
            "microservice_database": MicroserviceDatabase.NONE,
            "microservice_cache": MicroserviceCache.NONE,
        }
        
        # Extract Microservice name - look for various patterns
        name_patterns = [
            r"create\s+([a-z0-9-]+)",  # "create order-service"
            r"(?:name|called?)\s+([a-z0-9-]+)",  # "name order-service" or "called order-service"
            r"microservice\s+([a-z0-9-]+)",  # "microservice order-service"
            r"service\s+([a-z0-9-]+)",  # "service order-service"
        ]
        
        for pattern in name_patterns:
            name_match = re.search(pattern, text)
            if name_match:
                extracted["microservice_name"] = name_match.group(1)
                break
        
        # Extract namespace - same as AppContainer
        namespace_match = re.search(r"(?:in\s+)?(?:namespace|ns)\s+([a-z0-9-]+)", text)
        if namespace_match:
            extracted["namespace"] = namespace_match.group(1)
        
        # Extract description - same as AppContainer
        desc_patterns = [
            r"(?:description|desc)\s+[\"']([^\"']+)[\"']",  # quoted description
            r"(?:description|desc)\s+([^,\s]+(?:\s+[^,\s]+)*)",  # unquoted description
        ]
        
        for pattern in desc_patterns:
            desc_match = re.search(pattern, text)
            if desc_match:
                extracted["description"] = desc_match.group(1).strip()
                break
        
        # Extract GitHub org - same as AppContainer
        org_match = re.search(r"(?:github-org|org|organization)\s+([a-z0-9-]+)", text)
        if org_match:
            extracted["github_org"] = org_match.group(1)
        
        # Extract docker registry - same as AppContainer
        registry_match = re.search(r"(?:docker-registry|registry)\s+([a-z0-9.-/]+)", text)
        if registry_match:
            extracted["docker_registry"] = registry_match.group(1)
        
        # Extract vCluster information - same as AppContainer
        vcluster_patterns = [
            r"(?:in\s+)?(?:vcluster|cluster)\s+([a-z0-9-]+)",  # "vcluster my-cluster" or "in vcluster my-cluster"
        ]
        for pattern in vcluster_patterns:
            vcluster_match = re.search(pattern, text)
            if vcluster_match:
                extracted["target_vcluster"] = vcluster_match.group(1)
                break
        
        # Check for auto-create disable flags
        if any(phrase in text for phrase in ["no-vcluster", "no-cluster", "disable-auto-create"]):
            extracted["auto_create_vcluster"] = False
        elif "auto-create" in text:
            extracted["auto_create_vcluster"] = True
        
        # Extract language
        if any(lang in text for lang in ["python", "fastapi"]):
            extracted["microservice_language"] = MicroserviceLanguage.PYTHON
        elif any(lang in text for lang in ["java", "springboot"]):
            extracted["microservice_language"] = MicroserviceLanguage.JAVA
        
        # Extract database
        if any(phrase in text for phrase in ["no-database", "without database", "without db"]):
            extracted["microservice_database"] = MicroserviceDatabase.NONE
        elif any(db in text for db in ["postgresql", "postgres"]):
            extracted["microservice_database"] = MicroserviceDatabase.POSTGRESQL
        elif "with database" in text or "with db" in text:
            extracted["microservice_database"] = MicroserviceDatabase.POSTGRESQL
        
        # Extract cache
        if any(phrase in text for phrase in ["no-cache", "without cache", "without redis"]):
            extracted["microservice_cache"] = MicroserviceCache.NONE
        elif "redis" in text or "with cache" in text:
            extracted["microservice_cache"] = MicroserviceCache.REDIS
            
        # Extract repository
        repo_match = re.search(r"(?:repository|repo|app)\s+([a-z0-9-]+)", text)
        if repo_match:
            extracted["repository"] = repo_match.group(1)
            
        # Extract observability setting - same as AppContainer
        if any(phrase in text for phrase in ["no-observability", "disable-observability", "without observability"]):
            extracted["enable_observability"] = False
        elif "observability" in text:
            extracted["enable_observability"] = True
            
        # Extract security setting - same as AppContainer
        if any(phrase in text for phrase in ["no-security", "disable-security", "without security"]):
            extracted["enable_security"] = False
        elif "security" in text:
            extracted["enable_security"] = True

        return extracted

    def _extract_command_type_and_action(self, command: SlackCommand) -> tuple[str, str]:
        """Extract command type and action from Slack command."""
        # Determine command type from the slash command itself
        command_type = "vcluster"  # default
        if command.command == "/appcontainer" or command.command == "/app-cont":
            command_type = "appcontainer"
        elif command.command == "/microservice" or command.command == "/service":
            command_type = "microservice"
        elif command.command == "/application" or command.command == "/app":
            command_type = "application"
        
        # Extract action from text
        text = command.text.lower().strip()
        
        if not text or text.startswith("help"):
            action = "help"
        elif text.startswith("create"):
            action = "create"
        elif text.startswith("list"):
            action = "list"
        elif text.startswith("delete"):
            action = "delete"
        elif text.startswith("status"):
            action = "status"
        else:
            action = "unknown"
            
        return command_type, action

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
