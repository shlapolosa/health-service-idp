"""
Developer Agent for Microservice

Simplified business analyst agent adapted for microservice deployment.
"""

import asyncio
import logging
import re
import uuid
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
from dataclasses import dataclass, field

import spacy
from spacy.tokens import Doc, Span, Token
from spacy.matcher import Matcher, PhraseMatcher, DependencyMatcher

try:
    from .models import RequirementEntity, BusinessRequirement, AnalysisResult
except ImportError:
    from models import RequirementEntity, BusinessRequirement, AnalysisResult

logger = logging.getLogger(__name__)


@dataclass
class AgentTask:
    """Simple task representation"""
    task_id: str
    task_type: str
    payload: Dict[str, Any]
    metadata: Optional[Dict[str, Any]] = field(default_factory=dict)


@dataclass
class AgentResponse:
    """Simple response representation"""
    success: bool
    result: Optional[Any] = None
    error: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = field(default_factory=dict)


class SpacyNLPProcessor:
    """spaCy-based NLP processor"""
    
    def __init__(self):
        self.nlp = None
        self.matcher = None
        self.phrase_matcher = None
        self.dep_matcher = None
    
    async def initialize(self):
        """Initialize spaCy models and matchers"""
        try:
            self.nlp = spacy.load("en_core_web_sm")
            self._setup_matchers()
            logger.info("SpaCy NLP processor initialized")
        except Exception as e:
            logger.error(f"Failed to initialize NLP processor: {e}")
            # Fallback to basic model
            self.nlp = spacy.blank("en")
    
    def _setup_matchers(self):
        """Setup pattern matchers for requirement extraction"""
        self.matcher = Matcher(self.nlp.vocab)
        self.phrase_matcher = PhraseMatcher(self.nlp.vocab)
        self.dep_matcher = DependencyMatcher(self.nlp.vocab)
        
        # Subject patterns
        subject_patterns = [
            [{"POS": "NOUN", "DEP": "nsubj"}],
            [{"LOWER": {"IN": ["user", "customer", "admin", "system"]}},
             {"POS": "NOUN", "OP": "?"}],
            [{"ENT_TYPE": "PERSON"}, {"POS": "NOUN", "OP": "?"}]
        ]
        
        # Action patterns
        action_patterns = [
            [{"POS": "VERB", "DEP": "ROOT"}],
            [{"LOWER": {"IN": ["create", "update", "delete", "view", "manage", "configure"]}},
             {"POS": "NOUN", "OP": "?"}],
            [{"POS": "AUX"}, {"POS": "VERB"}]
        ]
        
        # Object patterns
        object_patterns = [
            [{"POS": "NOUN", "DEP": "dobj"}],
            [{"ENT_TYPE": {"IN": ["ORG", "PRODUCT", "EVENT"]}}, {"POS": "NOUN", "OP": "?"}],
            [{"POS": "DET", "OP": "?"}, {"POS": "ADJ", "OP": "*"}, {"POS": "NOUN", "OP": "+"}]
        ]
        
        self.matcher.add("SUBJECT", subject_patterns)
        self.matcher.add("ACTION", action_patterns)
        self.matcher.add("OBJECT", object_patterns)
    
    async def process_text(self, text: str) -> Doc:
        """Process text with NLP pipeline"""
        if not self.nlp:
            await self.initialize()
        return self.nlp(text)
    
    async def extract_entities(self, text: str) -> List[RequirementEntity]:
        """Extract entities from text using spaCy"""
        doc = await self.process_text(text)
        entities = []
        
        # Named entities
        for ent in doc.ents:
            entities.append(RequirementEntity(
                text=ent.text,
                label=ent.label_,
                start=ent.start_char,
                end=ent.end_char,
                confidence=1.0,
                attributes={"type": "named_entity"}
            ))
        
        # Pattern matches
        if self.matcher:
            matches = self.matcher(doc)
            for match_id, start, end in matches:
                span = doc[start:end]
                label = self.nlp.vocab.strings[match_id]
                entities.append(RequirementEntity(
                    text=span.text,
                    label=label,
                    start=span.start_char,
                    end=span.end_char,
                    confidence=0.8,
                    attributes={"type": "pattern_match"}
                ))
        
        return entities


class BusinessRequirementTemplateEngine:
    """Template engine for business requirements"""
    
    def __init__(self):
        self.templates = {
            "user_story": "As a {subject}, I want to {action} {object} so that {rationale}",
            "acceptance_criteria": "Given {precondition}, when {action}, then {expected_result}",
            "epic": "As a {stakeholder}, I need {capability} to achieve {business_goal}"
        }
    
    async def generate_user_stories(self, requirements: List[BusinessRequirement]) -> List[str]:
        """Generate user stories from requirements"""
        user_stories = []
        
        for req in requirements:
            story = self.templates["user_story"].format(
                subject=req.subject,
                action=req.action,
                object=req.object,
                rationale=req.rationale or "achieve business goals"
            )
            user_stories.append(story)
            
            # Generate acceptance criteria
            for criteria in req.acceptance_criteria:
                user_stories.append(f"  - {criteria}")
        
        return user_stories
    
    async def assess_complexity(self, requirement: BusinessRequirement) -> str:
        """Assess requirement complexity"""
        complexity_score = 0
        
        # Factors that increase complexity
        if len(requirement.entities) > 5:
            complexity_score += 2
        if len(requirement.acceptance_criteria) > 3:
            complexity_score += 1
        if "integration" in requirement.action.lower():
            complexity_score += 2
        if "security" in requirement.category.lower():
            complexity_score += 1
        if len(requirement.stakeholders) > 2:
            complexity_score += 1
        
        if complexity_score <= 2:
            return "low"
        elif complexity_score <= 4:
            return "medium"
        else:
            return "high"


class BusinessKnowledgeBase:
    """Business knowledge base implementation"""
    
    def __init__(self):
        self.stakeholder_mappings = {
            "ecommerce": {
                "primary": ["customer", "buyer", "shopper"],
                "secondary": ["admin", "manager", "support"],
                "technical": ["developer", "analyst", "architect"]
            },
            "healthcare": {
                "primary": ["patient", "doctor", "nurse"],
                "secondary": ["admin", "manager", "insurance"],
                "technical": ["it_support", "analyst", "compliance"]
            },
            "finance": {
                "primary": ["customer", "trader", "advisor"],
                "secondary": ["manager", "compliance", "auditor"],
                "technical": ["developer", "analyst", "risk_manager"]
            }
        }
        
        self.business_patterns = {
            "CRUD": {
                "actions": ["create", "read", "update", "delete"],
                "complexity": "low",
                "common_objects": ["record", "item", "entity"]
            },
            "Workflow": {
                "actions": ["approve", "review", "submit", "process"],
                "complexity": "medium",
                "common_objects": ["request", "application", "document"]
            },
            "Integration": {
                "actions": ["sync", "import", "export", "integrate"],
                "complexity": "high",
                "common_objects": ["data", "system", "service"]
            }
        }
    
    async def get_stakeholder_mapping(self, domain: str) -> Dict[str, List[str]]:
        """Get stakeholder mapping for domain"""
        return self.stakeholder_mappings.get(domain.lower(), {
            "primary": ["user"],
            "secondary": ["admin"],
            "technical": ["developer"]
        })
    
    async def get_business_patterns(self) -> Dict[str, Any]:
        """Get business pattern library"""
        return self.business_patterns


class DeveloperAgent:
    """
    Developer Agent for Microservice
    
    Processes natural language requirements and converts them into structured
    architecture change requests using Subject-Action-Object format.
    """
    
    def __init__(self):
        self.agent_id = str(uuid.uuid4())
        self.name = "Developer"
        self.description = "Developer processing and analysis"
        
        # Dependencies
        self.nlp_processor = SpacyNLPProcessor()
        self.template_engine = BusinessRequirementTemplateEngine()
        self.knowledge_base = BusinessKnowledgeBase()
        
        logger.info(f"Developer Agent {self.agent_id} initialized")
    
    async def initialize(self):
        """Initialize agent and dependencies"""
        await self.nlp_processor.initialize()
        logger.info(f"Developer Agent {self.agent_id} fully initialized")
    
    async def cleanup(self):
        """Cleanup agent resources"""
        logger.info(f"Developer Agent {self.agent_id} cleanup completed")
    
    async def process_task(self, task: AgentTask) -> AgentResponse:
        """Process task specific to business analyst"""
        try:
            task_type = task.task_type
            
            if task_type == "analyze_requirements":
                result = await self._analyze_requirements(task.payload)
            elif task_type == "extract_entities":
                result = await self._extract_entities(task.payload)
            elif task_type == "generate_user_stories":
                result = await self._generate_user_stories(task.payload)
            elif task_type == "assess_complexity":
                result = await self._assess_complexity(task.payload)
            elif task_type == "validate_requirements":
                result = await self._validate_requirements(task.payload)
            else:
                raise ValueError(f"Unknown task type: {task_type}")
            
            return AgentResponse(
                success=True,
                result=result,
                metadata={"task_id": task.task_id, "processing_time": 0.1}
            )
        
        except Exception as e:
            logger.error(f"Error processing task {task.task_id}: {e}")
            return AgentResponse(
                success=False,
                error=str(e),
                metadata={"task_id": task.task_id}
            )
    
    async def _analyze_requirements(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze natural language requirements"""
        requirements_text = payload.get("requirements_text", "")
        domain = payload.get("domain", "general")
        
        if not requirements_text:
            raise ValueError("requirements_text is required")
        
        start_time = datetime.now()
        
        # Extract entities from text
        entities = await self.nlp_processor.extract_entities(requirements_text)
        
        # Process text with NLP
        doc = await self.nlp_processor.process_text(requirements_text)
        
        # Extract subject-action-object triplets
        requirements = await self._extract_requirements(doc, entities)
        
        # Enhance with business knowledge
        await self._enhance_requirements_with_knowledge(requirements, domain)
        
        # Generate analysis result
        processing_time = (datetime.now() - start_time).total_seconds()
        
        return {
            "requirements": [req.dict() for req in requirements],
            "entities": [ent.dict() for ent in entities],
            "processing_time": processing_time,
            "domain": domain,
            "confidence": self._calculate_overall_confidence(requirements),
            "metadata": {
                "text_length": len(requirements_text),
                "entity_count": len(entities),
                "requirement_count": len(requirements)
            }
        }
    
    async def _extract_entities(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Extract entities from text"""
        text = payload.get("text", "")
        
        if not text:
            raise ValueError("text is required")
        
        entities = await self.nlp_processor.extract_entities(text)
        
        return {
            "entities": [ent.dict() for ent in entities],
            "entity_count": len(entities),
            "confidence": sum(ent.confidence for ent in entities) / max(len(entities), 1)
        }
    
    async def _generate_user_stories(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Generate user stories from requirements"""
        requirements_data = payload.get("requirements", [])
        
        if not requirements_data:
            raise ValueError("requirements are required")
        
        # Convert dict data back to BusinessRequirement objects
        requirements = [
            BusinessRequirement(**req_data) for req_data in requirements_data
        ]
        
        user_stories = await self.template_engine.generate_user_stories(requirements)
        
        return {
            "user_stories": user_stories,
            "story_count": len(user_stories),
            "requirements_processed": len(requirements)
        }
    
    async def _assess_complexity(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Assess complexity of requirements"""
        requirements_data = payload.get("requirements", [])
        
        if not requirements_data:
            raise ValueError("requirements are required")
        
        complexity_assessments = []
        
        for req_data in requirements_data:
            requirement = BusinessRequirement(**req_data)
            complexity = await self.template_engine.assess_complexity(requirement)
            complexity_assessments.append({
                "requirement_id": req_data.get("subject", "unknown"),
                "complexity": complexity,
                "factors": self._get_complexity_factors(requirement)
            })
        
        return {
            "complexity_assessments": complexity_assessments,
            "overall_complexity": self._calculate_overall_complexity(complexity_assessments)
        }
    
    async def _validate_requirements(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Validate requirements for completeness and consistency"""
        requirements_data = payload.get("requirements", [])
        
        if not requirements_data:
            raise ValueError("requirements are required")
        
        validation_results = []
        
        for req_data in requirements_data:
            requirement = BusinessRequirement(**req_data)
            validation = self._validate_single_requirement(requirement)
            validation_results.append(validation)
        
        return {
            "validation_results": validation_results,
            "valid_count": sum(1 for v in validation_results if v["is_valid"]),
            "total_count": len(validation_results),
            "overall_valid": all(v["is_valid"] for v in validation_results)
        }
    
    async def _extract_requirements(self, doc, entities: List[RequirementEntity]) -> List[BusinessRequirement]:
        """Extract structured requirements from processed text"""
        requirements = []
        
        # Simple sentence-based extraction
        for sent in doc.sents:
            requirement = await self._extract_requirement_from_sentence(sent, entities)
            if requirement:
                requirements.append(requirement)
        
        return requirements
    
    async def _extract_requirement_from_sentence(self, sent, entities: List[RequirementEntity]) -> Optional[BusinessRequirement]:
        """Extract requirement from a single sentence"""
        # Find subject, action, object in sentence
        subject = self._find_subject(sent)
        action = self._find_action(sent)
        obj = self._find_object(sent)
        
        if subject and action and obj:
            # Find relevant entities for this sentence
            sent_entities = [
                ent for ent in entities
                if sent.start_char <= ent.start <= sent.end_char
            ]
            
            return BusinessRequirement(
                subject=subject,
                action=action,
                object=obj,
                entities=sent_entities,
                confidence_score=self._calculate_sentence_confidence(sent, sent_entities)
            )
        
        return None
    
    def _find_subject(self, sent) -> Optional[str]:
        """Find subject in sentence"""
        for token in sent:
            if token.dep_ == "nsubj" or token.dep_ == "nsubjpass":
                return token.text
        
        # Fallback: look for pronouns or common subjects
        for token in sent:
            if token.text.lower() in ["user", "system", "admin", "customer"]:
                return token.text
        
        return None
    
    def _find_action(self, sent) -> Optional[str]:
        """Find action (verb) in sentence"""
        for token in sent:
            if token.pos_ == "VERB" and token.dep_ == "ROOT":
                return token.lemma_
        
        # Fallback: any verb
        for token in sent:
            if token.pos_ == "VERB":
                return token.lemma_
        
        return None
    
    def _find_object(self, sent) -> Optional[str]:
        """Find object in sentence"""
        for token in sent:
            if token.dep_ in ["dobj", "pobj"]:
                return token.text
        
        # Fallback: look for nouns
        for token in sent:
            if token.pos_ == "NOUN" and token.dep_ != "nsubj":
                return token.text
        
        return None
    
    async def _enhance_requirements_with_knowledge(self, requirements: List[BusinessRequirement], domain: str):
        """Enhance requirements with business knowledge"""
        stakeholder_mapping = await self.knowledge_base.get_stakeholder_mapping(domain)
        business_patterns = await self.knowledge_base.get_business_patterns()
        
        for req in requirements:
            # Enhance stakeholders
            req.stakeholders = self._identify_stakeholders(req, stakeholder_mapping)
            
            # Enhance category based on patterns
            req.category = self._categorize_requirement(req, business_patterns)
            
            # Assess complexity
            req.complexity = await self.template_engine.assess_complexity(req)
    
    def _identify_stakeholders(self, requirement: BusinessRequirement, stakeholder_mapping: Dict[str, List[str]]) -> List[str]:
        """Identify stakeholders for requirement"""
        stakeholders = []
        
        for category, stakeholder_list in stakeholder_mapping.items():
            for stakeholder in stakeholder_list:
                if stakeholder.lower() in requirement.subject.lower():
                    stakeholders.append(stakeholder)
        
        return stakeholders or ["user"]
    
    def _categorize_requirement(self, requirement: BusinessRequirement, business_patterns: Dict[str, Any]) -> str:
        """Categorize requirement based on business patterns"""
        for pattern_name, pattern_info in business_patterns.items():
            if requirement.action.lower() in [action.lower() for action in pattern_info["actions"]]:
                return pattern_name.lower()
        
        return "functional"
    
    def _calculate_sentence_confidence(self, sent, entities: List[RequirementEntity]) -> float:
        """Calculate confidence score for sentence"""
        confidence = 0.5  # Base confidence
        
        # Higher confidence for sentences with more entities
        confidence += min(len(entities) * 0.1, 0.3)
        
        # Higher confidence for longer sentences (up to a point)
        confidence += min(len(sent) * 0.01, 0.2)
        
        return min(confidence, 1.0)
    
    def _calculate_overall_confidence(self, requirements: List[BusinessRequirement]) -> float:
        """Calculate overall confidence for all requirements"""
        if not requirements:
            return 0.0
        
        return sum(req.confidence_score for req in requirements) / len(requirements)
    
    def _get_complexity_factors(self, requirement: BusinessRequirement) -> List[str]:
        """Get factors that contribute to complexity"""
        factors = []
        
        if len(requirement.entities) > 5:
            factors.append("high_entity_count")
        if len(requirement.acceptance_criteria) > 3:
            factors.append("many_acceptance_criteria")
        if "integration" in requirement.action.lower():
            factors.append("integration_requirement")
        if len(requirement.stakeholders) > 2:
            factors.append("multiple_stakeholders")
        
        return factors
    
    def _calculate_overall_complexity(self, complexity_assessments: List[Dict[str, Any]]) -> str:
        """Calculate overall complexity from individual assessments"""
        complexity_scores = {"low": 1, "medium": 2, "high": 3}
        
        if not complexity_assessments:
            return "medium"
        
        total_score = sum(complexity_scores.get(assessment["complexity"], 2) for assessment in complexity_assessments)
        avg_score = total_score / len(complexity_assessments)
        
        if avg_score <= 1.5:
            return "low"
        elif avg_score <= 2.5:
            return "medium"
        else:
            return "high"
    
    def _validate_single_requirement(self, requirement: BusinessRequirement) -> Dict[str, Any]:
        """Validate a single requirement"""
        issues = []
        
        if not requirement.subject:
            issues.append("Missing subject")
        if not requirement.action:
            issues.append("Missing action")
        if not requirement.object:
            issues.append("Missing object")
        if not requirement.rationale:
            issues.append("Missing rationale")
        if not requirement.acceptance_criteria:
            issues.append("Missing acceptance criteria")
        
        return {
            "is_valid": len(issues) == 0,
            "issues": issues,
            "requirement_text": f"{requirement.subject} {requirement.action} {requirement.object}"
        }