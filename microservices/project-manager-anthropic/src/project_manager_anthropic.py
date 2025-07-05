"""
Project Manager Agent for Microservice

Provides project planning, work package creation, and project management capabilities.
Creates implementation work packages and manages project execution.
"""

import asyncio
import logging
import re
import uuid
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, field

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


@dataclass
class WorkPackage:
    """Work package representation"""
    id: str
    title: str
    description: str
    deliverables: List[str]
    dependencies: List[str]
    estimated_effort_days: int
    required_skills: List[str]
    priority: str  # high, medium, low
    status: str = "not_started"  # not_started, in_progress, completed, blocked


class ProjectPlanningEngine:
    """Creates comprehensive project plans and work packages"""
    
    def __init__(self):
        self.project_methodologies = {
            "agile": {
                "sprint_length_weeks": 2,
                "planning_overhead": 0.15,
                "retrospective_overhead": 0.05,
                "ceremony_overhead": 0.1,
                "velocity_variance": 0.2
            },
            "scrum": {
                "sprint_length_weeks": 2,
                "planning_overhead": 0.2,
                "retrospective_overhead": 0.1,
                "ceremony_overhead": 0.15,
                "velocity_variance": 0.15
            },
            "kanban": {
                "flow_efficiency": 0.8,
                "wip_limits": True,
                "continuous_delivery": True,
                "cycle_time_variance": 0.3
            },
            "waterfall": {
                "phase_overlap": 0.1,
                "documentation_overhead": 0.25,
                "change_resistance": 0.9,
                "risk_mitigation": 0.3
            }
        }
        
        self.work_package_templates = {
            "analysis": {
                "duration_days": 5,
                "skills": ["business_analyst", "domain_expert"],
                "deliverables": ["requirements_document", "user_stories", "acceptance_criteria"]
            },
            "design": {
                "duration_days": 8,
                "skills": ["solution_architect", "ux_designer"],
                "deliverables": ["system_design", "architecture_diagrams", "ui_mockups"]
            },
            "development": {
                "duration_days": 15,
                "skills": ["developer", "tech_lead"],
                "deliverables": ["source_code", "unit_tests", "api_documentation"]
            },
            "testing": {
                "duration_days": 8,
                "skills": ["qa_engineer", "test_automation"],
                "deliverables": ["test_cases", "automated_tests", "test_reports"]
            },
            "deployment": {
                "duration_days": 3,
                "skills": ["devops_engineer", "sre"],
                "deliverables": ["deployment_scripts", "monitoring_setup", "runbooks"]
            },
            "integration": {
                "duration_days": 10,
                "skills": ["integration_specialist", "api_developer"],
                "deliverables": ["integration_code", "api_contracts", "integration_tests"]
            }
        }
        
        self.risk_factors = {
            "technology_risk": {
                "new_technology": 0.3,
                "legacy_integration": 0.2,
                "performance_requirements": 0.25,
                "scalability_needs": 0.2
            },
            "team_risk": {
                "skill_gaps": 0.4,
                "team_size": 0.15,
                "remote_work": 0.1,
                "turnover_risk": 0.3
            },
            "project_risk": {
                "unclear_requirements": 0.35,
                "changing_scope": 0.3,
                "tight_timeline": 0.25,
                "budget_constraints": 0.2
            }
        }
    
    async def create_project_plan(self, requirements: List[BusinessRequirement], 
                                 methodology: str = "agile", 
                                 team_size: int = 5,
                                 timeline_weeks: int = 12) -> Dict[str, Any]:
        """Create comprehensive project plan"""
        
        # Analyze requirements to determine work packages
        work_packages = self._generate_work_packages(requirements)
        
        # Create project phases
        phases = self._create_project_phases(work_packages, methodology)
        
        # Calculate timeline and dependencies
        project_schedule = self._calculate_project_schedule(phases, team_size, timeline_weeks)
        
        # Identify risks and mitigation strategies
        risk_assessment = self._assess_project_risks(requirements, methodology, team_size)
        
        # Create resource allocation plan
        resource_plan = self._create_resource_plan(work_packages, team_size)
        
        # Generate milestones and deliverables
        milestones = self._generate_milestones(phases, project_schedule)
        
        return {
            "project_overview": {
                "methodology": methodology,
                "total_duration_weeks": timeline_weeks,
                "team_size": team_size,
                "total_work_packages": len(work_packages),
                "estimated_effort_days": sum(wp.estimated_effort_days for wp in work_packages)
            },
            "work_packages": [self._work_package_to_dict(wp) for wp in work_packages],
            "project_phases": phases,
            "project_schedule": project_schedule,
            "resource_allocation": resource_plan,
            "milestones": milestones,
            "risk_assessment": risk_assessment,
            "success_criteria": self._define_success_criteria(requirements),
            "communication_plan": self._create_communication_plan(methodology, team_size)
        }
    
    def _generate_work_packages(self, requirements: List[BusinessRequirement]) -> List[WorkPackage]:
        """Generate work packages from requirements"""
        work_packages = []
        package_id = 1
        
        # Group requirements by type/domain
        requirement_groups = self._group_requirements(requirements)
        
        for group_name, group_requirements in requirement_groups.items():
            # Create work packages for each group
            wp_base_id = f"WP-{package_id:03d}"
            
            # Analysis work package
            analysis_wp = WorkPackage(
                id=f"{wp_base_id}-ANALYSIS",
                title=f"{group_name} Requirements Analysis",
                description=f"Analyze and document requirements for {group_name}",
                deliverables=self.work_package_templates["analysis"]["deliverables"].copy(),
                dependencies=[],
                estimated_effort_days=self.work_package_templates["analysis"]["duration_days"],
                required_skills=self.work_package_templates["analysis"]["skills"].copy(),
                priority=self._determine_priority(group_requirements)
            )
            work_packages.append(analysis_wp)
            
            # Design work package
            design_wp = WorkPackage(
                id=f"{wp_base_id}-DESIGN",
                title=f"{group_name} System Design",
                description=f"Design system architecture and components for {group_name}",
                deliverables=self.work_package_templates["design"]["deliverables"].copy(),
                dependencies=[analysis_wp.id],
                estimated_effort_days=self.work_package_templates["design"]["duration_days"],
                required_skills=self.work_package_templates["design"]["skills"].copy(),
                priority=self._determine_priority(group_requirements)
            )
            work_packages.append(design_wp)
            
            # Development work package
            development_wp = WorkPackage(
                id=f"{wp_base_id}-DEV",
                title=f"{group_name} Development",
                description=f"Implement {group_name} functionality",
                deliverables=self.work_package_templates["development"]["deliverables"].copy(),
                dependencies=[design_wp.id],
                estimated_effort_days=self._estimate_development_effort(group_requirements),
                required_skills=self.work_package_templates["development"]["skills"].copy(),
                priority=self._determine_priority(group_requirements)
            )
            work_packages.append(development_wp)
            
            # Testing work package
            testing_wp = WorkPackage(
                id=f"{wp_base_id}-TEST",
                title=f"{group_name} Testing",
                description=f"Test {group_name} functionality",
                deliverables=self.work_package_templates["testing"]["deliverables"].copy(),
                dependencies=[development_wp.id],
                estimated_effort_days=self.work_package_templates["testing"]["duration_days"],
                required_skills=self.work_package_templates["testing"]["skills"].copy(),
                priority=self._determine_priority(group_requirements)
            )
            work_packages.append(testing_wp)
            
            package_id += 1
        
        # Add integration and deployment work packages
        if len(requirement_groups) > 1:
            integration_wp = WorkPackage(
                id=f"WP-{package_id:03d}-INTEGRATION",
                title="System Integration",
                description="Integrate all system components",
                deliverables=self.work_package_templates["integration"]["deliverables"].copy(),
                dependencies=[wp.id for wp in work_packages if "DEV" in wp.id],
                estimated_effort_days=self.work_package_templates["integration"]["duration_days"],
                required_skills=self.work_package_templates["integration"]["skills"].copy(),
                priority="high"
            )
            work_packages.append(integration_wp)
            package_id += 1
        
        # Deployment work package
        deployment_wp = WorkPackage(
            id=f"WP-{package_id:03d}-DEPLOY",
            title="System Deployment",
            description="Deploy system to production environment",
            deliverables=self.work_package_templates["deployment"]["deliverables"].copy(),
            dependencies=[wp.id for wp in work_packages if "TEST" in wp.id or "INTEGRATION" in wp.id],
            estimated_effort_days=self.work_package_templates["deployment"]["duration_days"],
            required_skills=self.work_package_templates["deployment"]["skills"].copy(),
            priority="high"
        )
        work_packages.append(deployment_wp)
        
        return work_packages
    
    def _group_requirements(self, requirements: List[BusinessRequirement]) -> Dict[str, List[BusinessRequirement]]:
        """Group requirements by functional domain"""
        groups = {}
        
        for req in requirements:
            # Simple grouping by object (can be enhanced with ML clustering)
            group_key = req.object.lower().replace(" ", "_")
            
            # Merge similar groups
            merged_key = None
            for existing_key in groups.keys():
                if self._are_similar_domains(group_key, existing_key):
                    merged_key = existing_key
                    break
            
            final_key = merged_key or group_key
            
            if final_key not in groups:
                groups[final_key] = []
            groups[final_key].append(req)
        
        return groups
    
    def _are_similar_domains(self, domain1: str, domain2: str) -> bool:
        """Check if two domains are similar enough to merge"""
        # Simple similarity check (can be enhanced)
        common_words = set(domain1.split("_")) & set(domain2.split("_"))
        return len(common_words) > 0
    
    def _determine_priority(self, requirements: List[BusinessRequirement]) -> str:
        """Determine priority based on requirements"""
        # Simple priority determination (can be enhanced)
        high_priority_keywords = ["critical", "essential", "core", "primary"]
        medium_priority_keywords = ["important", "secondary", "supporting"]
        
        for req in requirements:
            req_text = f"{req.action} {req.object} {req.category}".lower()
            
            if any(keyword in req_text for keyword in high_priority_keywords):
                return "high"
            elif any(keyword in req_text for keyword in medium_priority_keywords):
                return "medium"
        
        return "medium"  # Default priority
    
    def _estimate_development_effort(self, requirements: List[BusinessRequirement]) -> int:
        """Estimate development effort in days"""
        base_effort = self.work_package_templates["development"]["duration_days"]
        
        # Adjust based on complexity factors
        complexity_multiplier = 1.0
        
        for req in requirements:
            req_text = f"{req.action} {req.object} {req.category}".lower()
            
            if "complex" in req_text or "advanced" in req_text:
                complexity_multiplier += 0.3
            if "integration" in req_text:
                complexity_multiplier += 0.2
            if "security" in req_text:
                complexity_multiplier += 0.15
            if "performance" in req_text:
                complexity_multiplier += 0.15
            if "real_time" in req_text:
                complexity_multiplier += 0.25
        
        # Factor in number of requirements
        requirement_factor = min(2.0, 1.0 + (len(requirements) - 1) * 0.1)
        
        return int(base_effort * complexity_multiplier * requirement_factor)
    
    def _create_project_phases(self, work_packages: List[WorkPackage], methodology: str) -> List[Dict[str, Any]]:
        """Create project phases based on work packages and methodology"""
        
        if methodology in ["agile", "scrum"]:
            return self._create_agile_phases(work_packages)
        elif methodology == "kanban":
            return self._create_kanban_phases(work_packages)
        elif methodology == "waterfall":
            return self._create_waterfall_phases(work_packages)
        else:
            return self._create_agile_phases(work_packages)  # Default to agile
    
    def _create_agile_phases(self, work_packages: List[WorkPackage]) -> List[Dict[str, Any]]:
        """Create agile phases (sprints)"""
        phases = []
        sprint_capacity_days = 10  # Assume 10 productive days per 2-week sprint
        
        current_sprint = 1
        current_sprint_work = []
        current_sprint_effort = 0
        
        # Sort work packages by priority and dependencies
        sorted_packages = self._sort_packages_by_dependencies(work_packages)
        
        for wp in sorted_packages:
            if current_sprint_effort + wp.estimated_effort_days > sprint_capacity_days:
                # Create sprint phase
                if current_sprint_work:
                    phases.append({
                        "phase": f"Sprint {current_sprint}",
                        "duration_weeks": 2,
                        "work_packages": [pkg.id for pkg in current_sprint_work],
                        "objectives": [f"Complete {pkg.title}" for pkg in current_sprint_work],
                        "deliverables": list(set(sum([pkg.deliverables for pkg in current_sprint_work], []))),
                        "total_effort_days": current_sprint_effort
                    })
                
                # Start new sprint
                current_sprint += 1
                current_sprint_work = [wp]
                current_sprint_effort = wp.estimated_effort_days
            else:
                current_sprint_work.append(wp)
                current_sprint_effort += wp.estimated_effort_days
        
        # Add final sprint if there's remaining work
        if current_sprint_work:
            phases.append({
                "phase": f"Sprint {current_sprint}",
                "duration_weeks": 2,
                "work_packages": [pkg.id for pkg in current_sprint_work],
                "objectives": [f"Complete {pkg.title}" for pkg in current_sprint_work],
                "deliverables": list(set(sum([pkg.deliverables for pkg in current_sprint_work], []))),
                "total_effort_days": current_sprint_effort
            })
        
        return phases
    
    def _create_kanban_phases(self, work_packages: List[WorkPackage]) -> List[Dict[str, Any]]:
        """Create kanban phases (continuous flow)"""
        return [
            {
                "phase": "Continuous Flow",
                "duration_weeks": "ongoing",
                "work_packages": [wp.id for wp in work_packages],
                "objectives": ["Maintain steady flow of work", "Minimize work in progress"],
                "deliverables": list(set(sum([wp.deliverables for wp in work_packages], []))),
                "wip_limits": {
                    "analysis": 2,
                    "development": 3,
                    "testing": 2,
                    "deployment": 1
                }
            }
        ]
    
    def _create_waterfall_phases(self, work_packages: List[WorkPackage]) -> List[Dict[str, Any]]:
        """Create waterfall phases (sequential)"""
        phase_types = ["analysis", "design", "development", "testing", "deployment"]
        phases = []
        
        for phase_type in phase_types:
            phase_packages = [wp for wp in work_packages if phase_type.upper() in wp.id]
            
            if phase_packages:
                total_effort = sum(wp.estimated_effort_days for wp in phase_packages)
                duration_weeks = max(1, total_effort // 5)  # 5 days per week
                
                phases.append({
                    "phase": f"{phase_type.title()} Phase",
                    "duration_weeks": duration_weeks,
                    "work_packages": [wp.id for wp in phase_packages],
                    "objectives": [f"Complete all {phase_type} activities"],
                    "deliverables": list(set(sum([wp.deliverables for wp in phase_packages], []))),
                    "total_effort_days": total_effort,
                    "gate_criteria": self._get_phase_gate_criteria(phase_type)
                })
        
        return phases
    
    def _get_phase_gate_criteria(self, phase_type: str) -> List[str]:
        """Get gate criteria for waterfall phases"""
        criteria = {
            "analysis": [
                "All requirements documented and approved",
                "Stakeholder sign-off received",
                "Acceptance criteria defined"
            ],
            "design": [
                "Architecture review completed",
                "Design documents approved",
                "Technical feasibility confirmed"
            ],
            "development": [
                "All code developed and unit tested",
                "Code review completed",
                "Documentation updated"
            ],
            "testing": [
                "All test cases executed",
                "Defects resolved or documented",
                "Quality gates passed"
            ],
            "deployment": [
                "Production environment ready",
                "Deployment procedures tested",
                "Go-live approval received"
            ]
        }
        
        return criteria.get(phase_type, [])
    
    def _sort_packages_by_dependencies(self, work_packages: List[WorkPackage]) -> List[WorkPackage]:
        """Sort work packages respecting dependencies"""
        sorted_packages = []
        remaining_packages = work_packages.copy()
        
        while remaining_packages:
            # Find packages with no unresolved dependencies
            ready_packages = []
            for wp in remaining_packages:
                dependencies_met = all(
                    dep_id in [sorted_wp.id for sorted_wp in sorted_packages]
                    for dep_id in wp.dependencies
                )
                if dependencies_met:
                    ready_packages.append(wp)
            
            if not ready_packages:
                # If no packages are ready, there might be circular dependencies
                # Just take the first one to break the cycle
                ready_packages = [remaining_packages[0]]
            
            # Sort ready packages by priority
            priority_order = {"high": 1, "medium": 2, "low": 3}
            ready_packages.sort(key=lambda x: priority_order.get(x.priority, 2))
            
            # Add ready packages to sorted list
            for wp in ready_packages:
                sorted_packages.append(wp)
                remaining_packages.remove(wp)
        
        return sorted_packages
    
    def _calculate_project_schedule(self, phases: List[Dict[str, Any]], 
                                  team_size: int, timeline_weeks: int) -> Dict[str, Any]:
        """Calculate detailed project schedule"""
        
        start_date = datetime.now()
        current_date = start_date
        
        schedule_phases = []
        
        for phase in phases:
            phase_duration = phase.get("duration_weeks", 2)
            if isinstance(phase_duration, str):  # Handle "ongoing" case
                phase_duration = timeline_weeks
            
            phase_start = current_date
            phase_end = current_date + timedelta(weeks=phase_duration)
            
            schedule_phases.append({
                "phase_name": phase["phase"],
                "start_date": phase_start.isoformat(),
                "end_date": phase_end.isoformat(),
                "duration_weeks": phase_duration,
                "work_packages": phase["work_packages"],
                "team_allocation": self._calculate_team_allocation(phase, team_size)
            })
            
            current_date = phase_end
        
        return {
            "project_start": start_date.isoformat(),
            "project_end": current_date.isoformat(),
            "total_duration_weeks": (current_date - start_date).days / 7,
            "phases": schedule_phases,
            "critical_path": self._identify_critical_path(phases),
            "buffer_time": max(0, timeline_weeks - (current_date - start_date).days / 7)
        }
    
    def _calculate_team_allocation(self, phase: Dict[str, Any], team_size: int) -> Dict[str, float]:
        """Calculate team allocation for a phase"""
        
        # Simple allocation based on phase type
        if "Sprint" in phase["phase"]:
            return {
                "developers": team_size * 0.6,
                "testers": team_size * 0.2,
                "analysts": team_size * 0.1,
                "architects": team_size * 0.1
            }
        elif "analysis" in phase["phase"].lower():
            return {
                "analysts": team_size * 0.5,
                "architects": team_size * 0.3,
                "developers": team_size * 0.2
            }
        elif "design" in phase["phase"].lower():
            return {
                "architects": team_size * 0.5,
                "developers": team_size * 0.3,
                "analysts": team_size * 0.2
            }
        else:
            return {
                "developers": team_size * 0.5,
                "testers": team_size * 0.3,
                "others": team_size * 0.2
            }
    
    def _identify_critical_path(self, phases: List[Dict[str, Any]]) -> List[str]:
        """Identify critical path through project phases"""
        # For now, return all phases as they're typically sequential
        return [phase["phase"] for phase in phases]
    
    def _assess_project_risks(self, requirements: List[BusinessRequirement], 
                            methodology: str, team_size: int) -> Dict[str, Any]:
        """Assess project risks and mitigation strategies"""
        
        identified_risks = []
        
        # Technology risks
        tech_risk_score = 0
        for req in requirements:
            req_text = f"{req.action} {req.object} {req.category}".lower()
            
            if "new" in req_text or "innovative" in req_text:
                tech_risk_score += self.risk_factors["technology_risk"]["new_technology"]
            if "integration" in req_text:
                tech_risk_score += self.risk_factors["technology_risk"]["legacy_integration"]
            if "performance" in req_text:
                tech_risk_score += self.risk_factors["technology_risk"]["performance_requirements"]
            if "scale" in req_text:
                tech_risk_score += self.risk_factors["technology_risk"]["scalability_needs"]
        
        if tech_risk_score > 0.3:
            identified_risks.append({
                "category": "Technology",
                "risk": "High technology complexity",
                "probability": "medium" if tech_risk_score < 0.6 else "high",
                "impact": "high",
                "score": tech_risk_score,
                "mitigation": [
                    "Conduct proof of concepts early",
                    "Invest in technical training",
                    "Engage technology experts",
                    "Plan for technology spikes"
                ]
            })
        
        # Team risks
        if team_size < 3:
            identified_risks.append({
                "category": "Team",
                "risk": "Small team size may limit capacity",
                "probability": "high",
                "impact": "medium",
                "score": 0.4,
                "mitigation": [
                    "Cross-train team members",
                    "Plan for backup resources",
                    "Consider external contractors",
                    "Prioritize features carefully"
                ]
            })
        elif team_size > 10:
            identified_risks.append({
                "category": "Team",
                "risk": "Large team coordination challenges",
                "probability": "medium",
                "impact": "medium",
                "score": 0.3,
                "mitigation": [
                    "Implement clear communication protocols",
                    "Use collaboration tools effectively",
                    "Define clear roles and responsibilities",
                    "Regular team sync meetings"
                ]
            })
        
        # Project risks
        requirement_complexity = len(requirements) / 10.0  # Normalize
        if requirement_complexity > 0.5:
            identified_risks.append({
                "category": "Project",
                "risk": "Complex requirements may lead to scope creep",
                "probability": "medium",
                "impact": "high",
                "score": requirement_complexity,
                "mitigation": [
                    "Implement change control process",
                    "Regular stakeholder reviews",
                    "Clear acceptance criteria",
                    "Phased delivery approach"
                ]
            })
        
        # Calculate overall risk score
        total_risk_score = sum(risk.get("score", 0) for risk in identified_risks)
        risk_level = "low"
        if total_risk_score > 0.6:
            risk_level = "high"
        elif total_risk_score > 0.3:
            risk_level = "medium"
        
        return {
            "overall_risk_level": risk_level,
            "total_risk_score": total_risk_score,
            "identified_risks": identified_risks,
            "risk_monitoring_plan": [
                "Weekly risk assessment reviews",
                "Risk register maintenance",
                "Mitigation action tracking",
                "Escalation to stakeholders when needed"
            ]
        }
    
    def _create_resource_plan(self, work_packages: List[WorkPackage], team_size: int) -> Dict[str, Any]:
        """Create resource allocation plan"""
        
        # Aggregate required skills
        skill_requirements = {}
        for wp in work_packages:
            for skill in wp.required_skills:
                if skill not in skill_requirements:
                    skill_requirements[skill] = 0
                skill_requirements[skill] += wp.estimated_effort_days
        
        # Calculate skill distribution
        total_effort = sum(skill_requirements.values())
        skill_distribution = {
            skill: (effort / total_effort) * 100
            for skill, effort in skill_requirements.items()
        }
        
        # Recommend team composition
        team_composition = {}
        remaining_team_size = team_size
        
        # Priority skills get dedicated resources
        priority_skills = ["developer", "tech_lead", "qa_engineer"]
        for skill in priority_skills:
            if skill in skill_requirements:
                allocation = max(1, int(team_size * (skill_distribution.get(skill, 0) / 100)))
                team_composition[skill] = min(allocation, remaining_team_size)
                remaining_team_size -= team_composition[skill]
        
        # Distribute remaining team members
        other_skills = [skill for skill in skill_requirements if skill not in priority_skills]
        for skill in other_skills:
            if remaining_team_size > 0:
                team_composition[skill] = 1
                remaining_team_size -= 1
        
        return {
            "team_composition": team_composition,
            "skill_requirements": skill_requirements,
            "skill_distribution": skill_distribution,
            "utilization_plan": self._create_utilization_plan(work_packages, team_composition),
            "training_needs": self._identify_training_needs(skill_requirements, team_composition)
        }
    
    def _create_utilization_plan(self, work_packages: List[WorkPackage], 
                               team_composition: Dict[str, int]) -> Dict[str, Any]:
        """Create team utilization plan"""
        
        # Calculate utilization by skill over time
        utilization = {}
        
        for skill, count in team_composition.items():
            skill_workload = sum(
                wp.estimated_effort_days 
                for wp in work_packages 
                if skill in wp.required_skills
            )
            
            # Assume 20 working days per month
            capacity_days_per_month = count * 20
            months_required = max(1, skill_workload / capacity_days_per_month)
            utilization_percentage = min(100, (skill_workload / (months_required * capacity_days_per_month)) * 100)
            
            utilization[skill] = {
                "team_members": count,
                "total_workload_days": skill_workload,
                "months_required": months_required,
                "utilization_percentage": utilization_percentage
            }
        
        return utilization
    
    def _identify_training_needs(self, skill_requirements: Dict[str, int], 
                               team_composition: Dict[str, int]) -> List[Dict[str, str]]:
        """Identify training needs based on skill gaps"""
        
        training_needs = []
        
        for skill, required_effort in skill_requirements.items():
            team_count = team_composition.get(skill, 0)
            
            if team_count == 0:
                training_needs.append({
                    "skill": skill,
                    "priority": "high",
                    "reason": "No team members with required skill",
                    "recommendation": f"Train existing team members or hire {skill} specialist"
                })
            elif required_effort / team_count > 40:  # More than 40 days per person
                training_needs.append({
                    "skill": skill,
                    "priority": "medium",
                    "reason": "High workload per team member",
                    "recommendation": f"Consider additional {skill} resources or training"
                })
        
        return training_needs
    
    def _generate_milestones(self, phases: List[Dict[str, Any]], 
                           schedule: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate project milestones"""
        
        milestones = []
        
        # Add phase completion milestones
        for i, phase_schedule in enumerate(schedule["phases"]):
            milestone = {
                "name": f"{phase_schedule['phase_name']} Complete",
                "date": phase_schedule["end_date"],
                "deliverables": phases[i].get("deliverables", []),
                "success_criteria": [
                    "All work packages completed",
                    "Quality gates passed",
                    "Stakeholder approval received"
                ]
            }
            milestones.append(milestone)
        
        # Add key project milestones
        if len(schedule["phases"]) >= 2:
            milestones.insert(len(schedule["phases"]) // 2, {
                "name": "Mid-Project Review",
                "date": schedule["phases"][len(schedule["phases"]) // 2]["start_date"],
                "deliverables": ["Project status report", "Risk assessment update"],
                "success_criteria": [
                    "Project on track",
                    "Risks under control",
                    "Quality standards met"
                ]
            })
        
        return milestones
    
    def _define_success_criteria(self, requirements: List[BusinessRequirement]) -> List[str]:
        """Define project success criteria"""
        
        criteria = [
            "All functional requirements implemented and tested",
            "System performance meets specified requirements",
            "Security requirements satisfied",
            "User acceptance testing passed",
            "System deployed to production successfully"
        ]
        
        # Add specific criteria based on requirements
        for req in requirements:
            req_text = f"{req.action} {req.object} {req.category}".lower()
            
            if "performance" in req_text:
                criteria.append("Performance benchmarks achieved")
            if "security" in req_text:
                criteria.append("Security audit passed")
            if "integration" in req_text:
                criteria.append("All integrations tested and working")
            if "mobile" in req_text:
                criteria.append("Mobile compatibility verified")
        
        return list(set(criteria))  # Remove duplicates
    
    def _create_communication_plan(self, methodology: str, team_size: int) -> Dict[str, Any]:
        """Create communication plan"""
        
        base_plan = {
            "stakeholder_updates": {
                "frequency": "weekly",
                "format": "status report",
                "participants": ["project_manager", "stakeholders"]
            },
            "team_meetings": {
                "frequency": "daily",
                "format": "standup",
                "participants": ["development_team"]
            },
            "risk_reviews": {
                "frequency": "weekly",
                "format": "risk_assessment",
                "participants": ["project_manager", "tech_lead"]
            }
        }
        
        # Adjust based on methodology
        if methodology in ["agile", "scrum"]:
            base_plan.update({
                "sprint_planning": {
                    "frequency": "bi-weekly",
                    "format": "planning_meeting",
                    "participants": ["development_team", "product_owner"]
                },
                "retrospectives": {
                    "frequency": "bi-weekly", 
                    "format": "retrospective_meeting",
                    "participants": ["development_team"]
                }
            })
        elif methodology == "waterfall":
            base_plan.update({
                "phase_gate_reviews": {
                    "frequency": "per_phase",
                    "format": "formal_review",
                    "participants": ["project_manager", "stakeholders", "tech_lead"]
                }
            })
        
        # Adjust frequency based on team size
        if team_size > 8:
            base_plan["team_meetings"]["additional"] = "weekly_team_sync"
        
        return base_plan
    
    def _work_package_to_dict(self, wp: WorkPackage) -> Dict[str, Any]:
        """Convert WorkPackage to dictionary"""
        return {
            "id": wp.id,
            "title": wp.title,
            "description": wp.description,
            "deliverables": wp.deliverables,
            "dependencies": wp.dependencies,
            "estimated_effort_days": wp.estimated_effort_days,
            "required_skills": wp.required_skills,
            "priority": wp.priority,
            "status": wp.status
        }


class ProjectTrackingEngine:
    """Tracks project progress and provides analytics"""
    
    def __init__(self):
        self.tracking_metrics = {
            "velocity": "story_points_per_sprint",
            "burndown": "remaining_work_over_time",
            "cycle_time": "time_from_start_to_completion",
            "lead_time": "time_from_request_to_delivery",
            "defect_rate": "defects_per_story_point",
            "team_utilization": "actual_hours_vs_planned"
        }
    
    async def track_progress(self, work_packages: List[Dict[str, Any]], 
                           completed_work: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Track project progress"""
        
        # Calculate completion metrics
        total_packages = len(work_packages)
        completed_packages = len([wp for wp in work_packages if wp.get("status") == "completed"])
        in_progress_packages = len([wp for wp in work_packages if wp.get("status") == "in_progress"])
        
        # Calculate effort metrics
        total_effort = sum(wp.get("estimated_effort_days", 0) for wp in work_packages)
        completed_effort = sum(
            wp.get("estimated_effort_days", 0) 
            for wp in work_packages 
            if wp.get("status") == "completed"
        )
        
        progress_percentage = (completed_effort / total_effort * 100) if total_effort > 0 else 0
        
        # Generate burndown data
        burndown_data = self._generate_burndown_data(work_packages, completed_work)
        
        # Calculate velocity
        velocity_data = self._calculate_velocity(completed_work)
        
        # Identify blockers and issues
        blockers = self._identify_blockers(work_packages)
        
        return {
            "progress_summary": {
                "total_work_packages": total_packages,
                "completed_packages": completed_packages,
                "in_progress_packages": in_progress_packages,
                "progress_percentage": round(progress_percentage, 1),
                "total_effort_days": total_effort,
                "completed_effort_days": completed_effort
            },
            "burndown_chart": burndown_data,
            "velocity_metrics": velocity_data,
            "current_blockers": blockers,
            "performance_indicators": self._calculate_performance_indicators(work_packages, completed_work),
            "recommendations": self._generate_progress_recommendations(progress_percentage, blockers)
        }
    
    def _generate_burndown_data(self, work_packages: List[Dict[str, Any]], 
                              completed_work: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Generate burndown chart data"""
        
        # Simulate burndown data (in real implementation, use historical data)
        total_effort = sum(wp.get("estimated_effort_days", 0) for wp in work_packages)
        project_days = 60  # Assume 60-day project
        
        burndown_data = []
        for day in range(0, project_days + 1, 5):  # Every 5 days
            # Ideal burndown (linear)
            ideal_remaining = total_effort * (1 - day / project_days)
            
            # Simulated actual progress (with some variance)
            if day == 0:
                actual_remaining = total_effort
            else:
                progress_factor = min(1.0, day / project_days + 0.1)  # Slightly behind ideal
                actual_remaining = total_effort * (1 - progress_factor)
            
            burndown_data.append({
                "day": day,
                "ideal_remaining": max(0, ideal_remaining),
                "actual_remaining": max(0, actual_remaining),
                "completed_cumulative": total_effort - actual_remaining
            })
        
        return burndown_data
    
    def _calculate_velocity(self, completed_work: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate team velocity metrics"""
        
        if not completed_work:
            return {
                "current_velocity": 0,
                "average_velocity": 0,
                "velocity_trend": "stable"
            }
        
        # Group completed work by time period (e.g., sprints)
        sprint_velocities = []
        
        # Simulate sprint data (in real implementation, use actual sprint data)
        total_completed_effort = sum(work.get("effort_days", 0) for work in completed_work)
        assumed_sprints = max(1, len(completed_work) // 3)  # Assume 3 items per sprint
        
        for sprint in range(assumed_sprints):
            sprint_effort = total_completed_effort / assumed_sprints
            sprint_velocities.append(sprint_effort)
        
        current_velocity = sprint_velocities[-1] if sprint_velocities else 0
        average_velocity = sum(sprint_velocities) / len(sprint_velocities) if sprint_velocities else 0
        
        # Determine trend
        if len(sprint_velocities) >= 2:
            recent_avg = sum(sprint_velocities[-2:]) / 2
            earlier_avg = sum(sprint_velocities[:-2]) / max(1, len(sprint_velocities) - 2)
            
            if recent_avg > earlier_avg * 1.1:
                trend = "increasing"
            elif recent_avg < earlier_avg * 0.9:
                trend = "decreasing"
            else:
                trend = "stable"
        else:
            trend = "stable"
        
        return {
            "current_velocity": current_velocity,
            "average_velocity": average_velocity,
            "velocity_trend": trend,
            "sprint_history": sprint_velocities
        }
    
    def _identify_blockers(self, work_packages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Identify current blockers and issues"""
        
        blockers = []
        
        for wp in work_packages:
            if wp.get("status") == "blocked":
                blockers.append({
                    "work_package_id": wp.get("id"),
                    "title": wp.get("title"),
                    "blocker_type": "dependency",  # Could be enhanced to detect type
                    "impact": "high" if wp.get("priority") == "high" else "medium",
                    "duration_days": 5  # Placeholder
                })
            elif wp.get("status") == "in_progress":
                # Check if overdue
                estimated_days = wp.get("estimated_effort_days", 0)
                if estimated_days > 0:  # Simplified overdue check
                    blockers.append({
                        "work_package_id": wp.get("id"),
                        "title": wp.get("title"),
                        "blocker_type": "overdue",
                        "impact": "medium",
                        "duration_days": 2
                    })
        
        return blockers
    
    def _calculate_performance_indicators(self, work_packages: List[Dict[str, Any]], 
                                        completed_work: List[Dict[str, Any]]) -> Dict[str, float]:
        """Calculate key performance indicators"""
        
        total_packages = len(work_packages)
        completed_packages = len([wp for wp in work_packages if wp.get("status") == "completed"])
        
        # Calculate various KPIs
        completion_rate = (completed_packages / total_packages * 100) if total_packages > 0 else 0
        
        # Simulated quality metrics
        defect_rate = 0.05  # 5% defect rate (placeholder)
        rework_rate = 0.1   # 10% rework rate (placeholder)
        
        # Team efficiency (placeholder calculation)
        planned_effort = sum(wp.get("estimated_effort_days", 0) for wp in work_packages)
        actual_effort = planned_effort * 1.1  # Assume 10% over estimate
        efficiency = (planned_effort / actual_effort * 100) if actual_effort > 0 else 100
        
        return {
            "completion_rate": completion_rate,
            "defect_rate": defect_rate * 100,
            "rework_rate": rework_rate * 100,
            "team_efficiency": efficiency,
            "schedule_performance": 95.0,  # Placeholder
            "cost_performance": 98.0       # Placeholder
        }
    
    def _generate_progress_recommendations(self, progress_percentage: float, 
                                         blockers: List[Dict[str, Any]]) -> List[str]:
        """Generate recommendations based on progress"""
        
        recommendations = []
        
        if progress_percentage < 50:
            recommendations.append("Project is behind schedule - consider adding resources or reducing scope")
        elif progress_percentage < 75:
            recommendations.append("Monitor progress closely and address any emerging issues")
        
        if len(blockers) > 2:
            recommendations.append("High number of blockers - prioritize blocker resolution")
        
        if any(blocker.get("impact") == "high" for blocker in blockers):
            recommendations.append("Critical blockers identified - escalate to management")
        
        # General recommendations
        recommendations.extend([
            "Maintain regular communication with stakeholders",
            "Continue daily team standups and progress reviews",
            "Update risk register based on current issues",
            "Ensure quality gates are being followed"
        ])
        
        return recommendations


class ProjectManagerAgent:
    """
    Project Manager Agent for Microservice
    
    Provides project planning, work package creation, and project management capabilities.
    Creates implementation work packages and manages project execution.
    """
    
    def __init__(self):
        self.agent_id = str(uuid.uuid4())
        self.name = "Project Manager"
        self.description = "Provides project planning and management capabilities"
        
        # Dependencies
        self.planning_engine = ProjectPlanningEngine()
        self.tracking_engine = ProjectTrackingEngine()
        
        logger.info(f"Project Manager Agent {self.agent_id} initialized")
    
    async def initialize(self):
        """Initialize agent and dependencies"""
        logger.info(f"Project Manager Agent {self.agent_id} fully initialized")
    
    async def cleanup(self):
        """Cleanup agent resources"""
        logger.info(f"Project Manager Agent {self.agent_id} cleanup completed")
    
    async def process_task(self, task: AgentTask) -> AgentResponse:
        """Process task specific to project manager"""
        try:
            task_type = task.task_type
            
            if task_type == "create_project_plan":
                result = await self._create_project_plan(task.payload)
            elif task_type == "create_work_packages":
                result = await self._create_work_packages(task.payload)
            elif task_type == "track_progress":
                result = await self._track_progress(task.payload)
            elif task_type == "manage_risks":
                result = await self._manage_risks(task.payload)
            elif task_type == "allocate_resources":
                result = await self._allocate_resources(task.payload)
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
    
    async def _create_project_plan(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Create comprehensive project plan"""
        requirements_data = payload.get("requirements", [])
        methodology = payload.get("methodology", "agile")
        team_size = payload.get("team_size", 5)
        timeline_weeks = payload.get("timeline_weeks", 12)
        
        if not requirements_data:
            raise ValueError("requirements are required")
        
        # Convert dict data back to BusinessRequirement objects
        requirements = [
            BusinessRequirement(**req_data) for req_data in requirements_data
        ]
        
        # Create project plan
        project_plan = await self.planning_engine.create_project_plan(
            requirements, methodology, team_size, timeline_weeks
        )
        
        return project_plan
    
    async def _create_work_packages(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Create detailed work packages from requirements"""
        requirements_data = payload.get("requirements", [])
        
        if not requirements_data:
            raise ValueError("requirements are required")
        
        # Convert dict data back to BusinessRequirement objects
        requirements = [
            BusinessRequirement(**req_data) for req_data in requirements_data
        ]
        
        # Generate work packages
        work_packages = self.planning_engine._generate_work_packages(requirements)
        
        return {
            "work_packages": [self.planning_engine._work_package_to_dict(wp) for wp in work_packages],
            "total_packages": len(work_packages),
            "total_effort_days": sum(wp.estimated_effort_days for wp in work_packages),
            "package_summary": self._summarize_work_packages(work_packages)
        }
    
    async def _track_progress(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Track project progress and provide analytics"""
        work_packages = payload.get("work_packages", [])
        completed_work = payload.get("completed_work", [])
        
        if not work_packages:
            raise ValueError("work_packages are required")
        
        # Track progress
        progress_data = await self.tracking_engine.track_progress(work_packages, completed_work)
        
        return progress_data
    
    async def _manage_risks(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Manage project risks and provide mitigation strategies"""
        requirements_data = payload.get("requirements", [])
        current_risks = payload.get("current_risks", [])
        project_status = payload.get("project_status", {})
        
        if not requirements_data:
            raise ValueError("requirements are required")
        
        # Convert dict data back to BusinessRequirement objects
        requirements = [
            BusinessRequirement(**req_data) for req_data in requirements_data
        ]
        
        # Assess risks (reuse planning engine logic)
        methodology = project_status.get("methodology", "agile")
        team_size = project_status.get("team_size", 5)
        
        risk_assessment = self.planning_engine._assess_project_risks(
            requirements, methodology, team_size
        )
        
        # Add current risks
        risk_assessment["current_risks"] = current_risks
        
        # Generate risk monitoring recommendations
        risk_assessment["monitoring_recommendations"] = self._generate_risk_monitoring_plan(
            risk_assessment["identified_risks"], current_risks
        )
        
        return risk_assessment
    
    async def _allocate_resources(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Allocate resources to work packages"""
        work_packages_data = payload.get("work_packages", [])
        available_resources = payload.get("available_resources", {})
        timeline_weeks = payload.get("timeline_weeks", 12)
        
        if not work_packages_data:
            raise ValueError("work_packages are required")
        
        # Convert to WorkPackage objects
        work_packages = []
        for wp_data in work_packages_data:
            wp = WorkPackage(
                id=wp_data.get("id", ""),
                title=wp_data.get("title", ""),
                description=wp_data.get("description", ""),
                deliverables=wp_data.get("deliverables", []),
                dependencies=wp_data.get("dependencies", []),
                estimated_effort_days=wp_data.get("estimated_effort_days", 0),
                required_skills=wp_data.get("required_skills", []),
                priority=wp_data.get("priority", "medium")
            )
            work_packages.append(wp)
        
        # Create resource plan
        team_size = sum(available_resources.values()) if available_resources else 5
        resource_plan = self.planning_engine._create_resource_plan(work_packages, team_size)
        
        # Add resource allocation over time
        resource_allocation = self._allocate_resources_over_time(
            work_packages, available_resources, timeline_weeks
        )
        
        resource_plan["allocation_over_time"] = resource_allocation
        
        return resource_plan
    
    def _summarize_work_packages(self, work_packages: List[WorkPackage]) -> Dict[str, Any]:
        """Summarize work packages by type and priority"""
        
        # Count by type (based on ID patterns)
        type_counts = {
            "analysis": len([wp for wp in work_packages if "ANALYSIS" in wp.id]),
            "design": len([wp for wp in work_packages if "DESIGN" in wp.id]),
            "development": len([wp for wp in work_packages if "DEV" in wp.id]),
            "testing": len([wp for wp in work_packages if "TEST" in wp.id]),
            "deployment": len([wp for wp in work_packages if "DEPLOY" in wp.id]),
            "integration": len([wp for wp in work_packages if "INTEGRATION" in wp.id])
        }
        
        # Count by priority
        priority_counts = {
            "high": len([wp for wp in work_packages if wp.priority == "high"]),
            "medium": len([wp for wp in work_packages if wp.priority == "medium"]),
            "low": len([wp for wp in work_packages if wp.priority == "low"])
        }
        
        # Calculate effort distribution
        effort_by_type = {}
        for wp_type, count in type_counts.items():
            effort_by_type[wp_type] = sum(
                wp.estimated_effort_days 
                for wp in work_packages 
                if wp_type.upper() in wp.id
            )
        
        return {
            "type_distribution": type_counts,
            "priority_distribution": priority_counts,
            "effort_by_type": effort_by_type,
            "average_effort_per_package": sum(wp.estimated_effort_days for wp in work_packages) / len(work_packages) if work_packages else 0
        }
    
    def _generate_risk_monitoring_plan(self, identified_risks: List[Dict[str, Any]], 
                                     current_risks: List[Dict[str, Any]]) -> List[Dict[str, str]]:
        """Generate risk monitoring plan"""
        
        monitoring_plan = []
        
        # Monitor high-impact risks more frequently
        high_impact_risks = [risk for risk in identified_risks if risk.get("impact") == "high"]
        if high_impact_risks:
            monitoring_plan.append({
                "activity": "High-Impact Risk Review",
                "frequency": "daily",
                "participants": "project_manager, tech_lead",
                "focus": "Monitor and mitigate high-impact risks"
            })
        
        # Regular risk assessment
        monitoring_plan.append({
            "activity": "Risk Register Update",
            "frequency": "weekly",
            "participants": "project_manager, team_leads",
            "focus": "Update risk register and review mitigation progress"
        })
        
        # Stakeholder risk communication
        monitoring_plan.append({
            "activity": "Risk Communication",
            "frequency": "bi-weekly",
            "participants": "project_manager, stakeholders",
            "focus": "Communicate risk status and escalate as needed"
        })
        
        # Risk trend analysis
        monitoring_plan.append({
            "activity": "Risk Trend Analysis",
            "frequency": "monthly",
            "participants": "project_manager, management",
            "focus": "Analyze risk trends and adjust strategies"
        })
        
        return monitoring_plan
    
    def _allocate_resources_over_time(self, work_packages: List[WorkPackage], 
                                    available_resources: Dict[str, int], 
                                    timeline_weeks: int) -> List[Dict[str, Any]]:
        """Allocate resources over project timeline"""
        
        allocation_timeline = []
        
        # Sort work packages by dependencies and priority
        sorted_packages = self.planning_engine._sort_packages_by_dependencies(work_packages)
        
        # Simulate weekly allocation
        for week in range(1, timeline_weeks + 1):
            week_allocation = {
                "week": week,
                "allocated_resources": {},
                "active_work_packages": [],
                "utilization_percentage": 0
            }
            
            # Determine which packages are active this week (simplified)
            packages_per_week = max(1, len(sorted_packages) // timeline_weeks)
            start_idx = (week - 1) * packages_per_week
            end_idx = min(len(sorted_packages), start_idx + packages_per_week)
            
            active_packages = sorted_packages[start_idx:end_idx]
            week_allocation["active_work_packages"] = [wp.id for wp in active_packages]
            
            # Allocate resources based on package requirements
            required_skills = set()
            for wp in active_packages:
                required_skills.update(wp.required_skills)
            
            total_capacity = sum(available_resources.values())
            utilized_capacity = 0
            
            for skill in required_skills:
                available_count = available_resources.get(skill, 0)
                if available_count > 0:
                    week_allocation["allocated_resources"][skill] = available_count
                    utilized_capacity += available_count
            
            week_allocation["utilization_percentage"] = (utilized_capacity / total_capacity * 100) if total_capacity > 0 else 0
            
            allocation_timeline.append(week_allocation)
        
        return allocation_timeline