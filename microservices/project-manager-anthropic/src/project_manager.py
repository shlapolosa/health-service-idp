"""
Project Manager Agent - Project planning and management
"""

from typing import Dict, List, Any
from datetime import datetime, timedelta
from agent_common.base_microservice_agent import BaseMicroserviceAgent, BaseProcessor


class ProjectManagementProcessor(BaseProcessor):
    """Processor for Project Manager tasks"""
    
    def _initialize_knowledge_base(self) -> Dict[str, Any]:
        """Initialize project management knowledge base"""
        return {
            "methodologies": ["Agile", "Scrum", "Kanban", "Waterfall", "DevOps"],
            "estimation_techniques": ["Story Points", "T-Shirt Sizing", "Planning Poker", "Historical Data"],
            "risk_categories": ["Technical", "Business", "Resource", "Schedule", "Quality"],
            "team_roles": ["Developer", "Tester", "Designer", "Architect", "Product Owner", "Scrum Master"],
            "project_phases": ["Initiation", "Planning", "Execution", "Monitoring", "Closure"]
        }
    
    def _initialize_templates(self) -> Dict[str, str]:
        """Initialize project templates"""
        return {
            "user_story": "As a {role}, I want {feature} so that {benefit}",
            "task": "Task: {title}\nDescription: {description}\nAcceptance Criteria: {criteria}",
            "epic": "Epic: {title}\nGoal: {goal}\nSuccess Criteria: {criteria}"
        }
    
    async def create_project_plan(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create comprehensive project plan"""
        requirements = input_data.get("requirements", input_data.get("query", ""))
        methodology = input_data.get("methodology", "Agile")
        team_size = input_data.get("team_size", 5)
        
        # Create project phases
        phases = [
            {
                "name": "Requirements Analysis",
                "duration_weeks": 2,
                "deliverables": ["Requirements Document", "User Stories", "Acceptance Criteria"],
                "resources": ["Business Analyst", "Product Owner"]
            },
            {
                "name": "Architecture Design", 
                "duration_weeks": 3,
                "deliverables": ["System Architecture", "Technical Design", "Database Design"],
                "resources": ["Solution Architect", "Technical Lead"]
            },
            {
                "name": "Development",
                "duration_weeks": 8,
                "deliverables": ["Core Features", "API Implementation", "Database Schema"],
                "resources": ["Developers", "Tech Lead"]
            },
            {
                "name": "Testing",
                "duration_weeks": 3,
                "deliverables": ["Test Cases", "Automated Tests", "Bug Reports"],
                "resources": ["QA Engineers", "Developers"]
            },
            {
                "name": "Deployment",
                "duration_weeks": 2,
                "deliverables": ["Production Deployment", "Documentation", "Training"],
                "resources": ["DevOps Engineer", "Tech Lead"]
            }
        ]
        
        # Calculate timeline
        total_duration = sum(phase["duration_weeks"] for phase in phases)
        start_date = datetime.now()
        end_date = start_date + timedelta(weeks=total_duration)
        
        return {
            "project_plan": {
                "methodology": methodology,
                "phases": phases,
                "total_duration_weeks": total_duration,
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
                "team_size": team_size
            },
            "milestones": [
                {"name": "Requirements Complete", "week": 2},
                {"name": "Architecture Approved", "week": 5},
                {"name": "MVP Delivery", "week": 10},
                {"name": "Testing Complete", "week": 16},
                {"name": "Production Ready", "week": 18}
            ],
            "success_metrics": [
                "On-time delivery",
                "Budget adherence",
                "Quality standards met",
                "Stakeholder satisfaction"
            ]
        }
    
    async def estimate_effort(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Estimate project effort and timeline"""
        requirements = input_data.get("requirements", input_data.get("query", ""))
        complexity = input_data.get("complexity", "medium")
        
        # Base estimates by complexity
        base_estimates = {
            "low": {"weeks": 4, "team_size": 3, "story_points": 50},
            "medium": {"weeks": 8, "team_size": 5, "story_points": 100},
            "high": {"weeks": 16, "team_size": 8, "story_points": 200}
        }
        
        estimate = base_estimates.get(complexity, base_estimates["medium"])
        
        # Adjust based on requirements content
        adjustment_factor = 1.0
        if "integration" in requirements.lower():
            adjustment_factor += 0.3
        if "security" in requirements.lower():
            adjustment_factor += 0.2
        if "performance" in requirements.lower():
            adjustment_factor += 0.2
        if "mobile" in requirements.lower():
            adjustment_factor += 0.1
        
        adjusted_weeks = int(estimate["weeks"] * adjustment_factor)
        adjusted_story_points = int(estimate["story_points"] * adjustment_factor)
        
        return {
            "effort_estimate": {
                "duration_weeks": adjusted_weeks,
                "team_size": estimate["team_size"],
                "story_points": adjusted_story_points,
                "complexity": complexity,
                "adjustment_factor": adjustment_factor
            },
            "breakdown": {
                "development": f"{int(adjusted_weeks * 0.5)} weeks",
                "testing": f"{int(adjusted_weeks * 0.25)} weeks", 
                "planning": f"{int(adjusted_weeks * 0.15)} weeks",
                "deployment": f"{int(adjusted_weeks * 0.1)} weeks"
            },
            "confidence_level": "75%",
            "assumptions": [
                "Team has required skills",
                "Requirements are stable",
                "No major technical blockers",
                "Standard development tools available"
            ]
        }
    
    async def track_progress(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Track project progress"""
        completed_tasks = input_data.get("completed_tasks", 0)
        total_tasks = input_data.get("total_tasks", 100)
        current_sprint = input_data.get("current_sprint", 1)
        
        progress_percentage = (completed_tasks / total_tasks) * 100 if total_tasks > 0 else 0
        
        # Calculate burndown data
        burndown_data = []
        for day in range(1, 11):  # 10-day sprint
            ideal_remaining = total_tasks * (1 - (day / 10))
            actual_remaining = max(0, total_tasks - (completed_tasks * (day / 10)))
            burndown_data.append({
                "day": day,
                "ideal_remaining": ideal_remaining,
                "actual_remaining": actual_remaining
            })
        
        status = "on_track"
        if progress_percentage < 70:
            status = "at_risk"
        elif progress_percentage < 50:
            status = "behind"
        
        return {
            "progress_tracking": {
                "completed_tasks": completed_tasks,
                "total_tasks": total_tasks,
                "progress_percentage": round(progress_percentage, 1),
                "current_sprint": current_sprint,
                "status": status
            },
            "burndown_chart": burndown_data,
            "key_metrics": {
                "velocity": completed_tasks / current_sprint if current_sprint > 0 else 0,
                "remaining_sprints": max(1, int((total_tasks - completed_tasks) / (completed_tasks / current_sprint))) if completed_tasks > 0 else "Unknown"
            },
            "recommendations": [
                "Review sprint backlog priorities",
                "Identify and remove blockers",
                "Consider team capacity adjustments",
                "Update stakeholders on progress"
            ]
        }
    
    async def manage_risks(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Identify and manage project risks"""
        project_type = input_data.get("project_type", "software_development")
        requirements = input_data.get("requirements", input_data.get("query", ""))
        
        # Common risks by category
        identified_risks = [
            {
                "category": "Technical",
                "risk": "Technology integration complexity",
                "probability": "medium",
                "impact": "high",
                "mitigation": "Proof of concept early in project"
            },
            {
                "category": "Resource",
                "risk": "Key team member unavailability",
                "probability": "low",
                "impact": "high", 
                "mitigation": "Cross-training and knowledge sharing"
            },
            {
                "category": "Schedule",
                "risk": "Requirement changes during development",
                "probability": "high",
                "impact": "medium",
                "mitigation": "Agile methodology with regular stakeholder reviews"
            },
            {
                "category": "Quality",
                "risk": "Insufficient testing time",
                "probability": "medium",
                "impact": "high",
                "mitigation": "Automated testing and continuous integration"
            }
        ]
        
        # Add specific risks based on requirements
        if "integration" in requirements.lower():
            identified_risks.append({
                "category": "Technical",
                "risk": "Third-party API changes or downtime",
                "probability": "medium",
                "impact": "medium",
                "mitigation": "Implement circuit breakers and fallback mechanisms"
            })
        
        return {
            "risk_assessment": {
                "total_risks": len(identified_risks),
                "high_priority_risks": len([r for r in identified_risks if r["impact"] == "high"]),
                "risk_categories": list(set(r["category"] for r in identified_risks))
            },
            "identified_risks": identified_risks,
            "risk_monitoring_plan": [
                "Weekly risk review meetings",
                "Risk register updates",
                "Mitigation action tracking",
                "Stakeholder risk communication"
            ],
            "escalation_criteria": [
                "High impact risks become likely",
                "Multiple risks materialize simultaneously", 
                "Risk mitigation plans fail",
                "New critical risks identified"
            ]
        }


class ProjectManagerAgent(BaseMicroserviceAgent):
    """Project Manager Agent for project planning and management"""
    
    def __init__(self):
        super().__init__(
            agent_type="project-manager",
            agent_name="Project Manager",
            description="Project planning and management"
        )
    
    def _create_processor(self) -> BaseProcessor:
        return ProjectManagementProcessor()
    
    def _get_supported_task_types(self) -> List[str]:
        return ["create_project_plan", "estimate_effort", "track_progress", "manage_risks"]
    
    async def _create_project_plan(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        return await self.processor.create_project_plan(payload)
    
    async def _estimate_effort(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        return await self.processor.estimate_effort(payload)
    
    async def _track_progress(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        return await self.processor.track_progress(payload)
    
    async def _manage_risks(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        return await self.processor.manage_risks(payload)