"""
Accountant Agent for Microservice

Provides cost analysis, budgeting, and financial optimization for architecture projects.
Analyzes infrastructure costs, development costs, and provides ROI analysis.
"""

import asyncio
import logging
import re
import uuid
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from decimal import Decimal

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


class CostAnalysisEngine:
    """Analyzes costs for infrastructure and development"""
    
    def __init__(self):
        # Cloud provider pricing models (simplified)
        self.cloud_pricing = {
            "aws": {
                "compute": {
                    "t3.micro": 0.0104,  # per hour
                    "t3.small": 0.0208,
                    "t3.medium": 0.0416,
                    "t3.large": 0.0832,
                    "t3.xlarge": 0.1664,
                    "c5.large": 0.085,
                    "c5.xlarge": 0.17,
                    "m5.large": 0.096,
                    "m5.xlarge": 0.192
                },
                "storage": {
                    "ebs_gp3": 0.08,  # per GB per month
                    "ebs_io2": 0.125,
                    "s3_standard": 0.023,
                    "s3_glacier": 0.004
                },
                "database": {
                    "rds_t3_micro": 0.017,  # per hour
                    "rds_t3_small": 0.034,
                    "rds_m5_large": 0.192,
                    "dynamodb_on_demand": 1.25  # per million requests
                },
                "networking": {
                    "data_transfer_out": 0.09,  # per GB
                    "load_balancer": 0.0225,  # per hour
                    "nat_gateway": 0.045  # per hour
                }
            },
            "azure": {
                "compute": {
                    "b1s": 0.0104,
                    "b2s": 0.0416,
                    "d2s_v3": 0.096,
                    "d4s_v3": 0.192
                },
                "storage": {
                    "premium_ssd": 0.15,
                    "standard_hdd": 0.045,
                    "blob_hot": 0.0208
                },
                "database": {
                    "sql_s0": 0.02,
                    "sql_s1": 0.03,
                    "cosmos_ru": 0.008  # per 100 RU/s per hour
                }
            },
            "gcp": {
                "compute": {
                    "e2_micro": 0.0063,
                    "e2_small": 0.0126,
                    "e2_medium": 0.0252,
                    "n1_standard_1": 0.0475
                },
                "storage": {
                    "persistent_disk": 0.04,
                    "cloud_storage": 0.020
                },
                "database": {
                    "cloud_sql_micro": 0.0150,
                    "cloud_sql_small": 0.0300
                }
            }
        }
        
        # Development cost factors
        self.development_costs = {
            "hourly_rates": {
                "solution_architect": 150,
                "senior_developer": 120,
                "developer": 80,
                "devops_engineer": 100,
                "qa_engineer": 70,
                "project_manager": 110
            },
            "complexity_multipliers": {
                "simple": 1.0,
                "moderate": 1.5,
                "complex": 2.0,
                "very_complex": 3.0
            },
            "technology_multipliers": {
                "well_known": 1.0,
                "emerging": 1.3,
                "cutting_edge": 1.8
            }
        }
        
        # Operational cost factors
        self.operational_costs = {
            "monitoring": 0.1,  # 10% of infrastructure cost
            "security": 0.15,   # 15% of infrastructure cost
            "backup": 0.05,     # 5% of infrastructure cost
            "support": 0.2      # 20% of infrastructure cost
        }
    
    async def analyze_infrastructure_costs(self, infrastructure_design: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze infrastructure costs from design"""
        
        cloud_provider = infrastructure_design.get("cloud_provider", "aws")
        compute_design = infrastructure_design.get("compute", {})
        storage_design = infrastructure_design.get("storage", {})
        networking_design = infrastructure_design.get("networking", {})
        
        # Calculate compute costs
        compute_costs = self._calculate_compute_costs(compute_design, cloud_provider)
        
        # Calculate storage costs
        storage_costs = self._calculate_storage_costs(storage_design, cloud_provider)
        
        # Calculate networking costs
        networking_costs = self._calculate_networking_costs(networking_design, cloud_provider)
        
        # Calculate operational costs
        base_infrastructure_cost = compute_costs + storage_costs + networking_costs
        operational_costs = self._calculate_operational_costs(base_infrastructure_cost)
        
        total_monthly_cost = base_infrastructure_cost + operational_costs
        
        return {
            "monthly_costs": {
                "compute": compute_costs,
                "storage": storage_costs,
                "networking": networking_costs,
                "operational": operational_costs,
                "total": total_monthly_cost
            },
            "yearly_costs": {
                "total": total_monthly_cost * 12,
                "with_growth": self._project_yearly_costs(total_monthly_cost)
            },
            "cost_breakdown": {
                "compute_percentage": (compute_costs / total_monthly_cost) * 100,
                "storage_percentage": (storage_costs / total_monthly_cost) * 100,
                "networking_percentage": (networking_costs / total_monthly_cost) * 100,
                "operational_percentage": (operational_costs / total_monthly_cost) * 100
            },
            "optimization_opportunities": self._identify_cost_optimizations(infrastructure_design)
        }
    
    def _calculate_compute_costs(self, compute_design: Dict[str, Any], cloud_provider: str) -> float:
        """Calculate compute costs"""
        
        if cloud_provider not in self.cloud_pricing:
            cloud_provider = "aws"  # Default fallback
        
        pricing = self.cloud_pricing[cloud_provider]["compute"]
        
        # Estimate based on primary service and scaling
        primary_service = compute_design.get("primary_service", "t3.medium")
        auto_scaling = compute_design.get("auto_scaling", False)
        high_availability = compute_design.get("high_availability", False)
        
        # Map service names to pricing keys (simplified)
        instance_type = "t3.medium"  # Default
        if "micro" in primary_service.lower():
            instance_type = "t3.micro"
        elif "small" in primary_service.lower():
            instance_type = "t3.small"
        elif "large" in primary_service.lower():
            instance_type = "t3.large"
        
        hourly_cost = pricing.get(instance_type, pricing["t3.medium"])
        
        # Base instances
        base_instances = 2 if high_availability else 1
        
        # Additional instances for auto-scaling
        scaling_instances = 2 if auto_scaling else 0
        
        total_instances = base_instances + scaling_instances
        monthly_hours = 24 * 30  # 720 hours per month
        
        return hourly_cost * total_instances * monthly_hours
    
    def _calculate_storage_costs(self, storage_design: Dict[str, Any], cloud_provider: str) -> float:
        """Calculate storage costs"""
        
        if cloud_provider not in self.cloud_pricing:
            cloud_provider = "aws"
        
        pricing = self.cloud_pricing[cloud_provider]["storage"]
        
        # Estimate storage requirements
        object_storage_gb = 100  # Default assumption
        database_storage_gb = 50
        backup_storage_gb = 75  # 50% more for backups
        
        # Adjust based on design
        if storage_design.get("data_warehouse"):
            object_storage_gb = 500
            database_storage_gb = 200
        
        if storage_design.get("caching"):
            database_storage_gb += 20  # Additional for cache
        
        # Calculate costs
        object_cost = object_storage_gb * pricing.get("s3_standard", 0.023)
        database_cost = database_storage_gb * pricing.get("ebs_gp3", 0.08)
        backup_cost = backup_storage_gb * pricing.get("s3_glacier", 0.004)
        
        return object_cost + database_cost + backup_cost
    
    def _calculate_networking_costs(self, networking_design: Dict[str, Any], cloud_provider: str) -> float:
        """Calculate networking costs"""
        
        if cloud_provider not in self.cloud_pricing:
            cloud_provider = "aws"
        
        pricing = self.cloud_pricing[cloud_provider]["networking"]
        
        # Load balancer costs
        load_balancer_cost = 0
        if networking_design.get("load_balancer"):
            load_balancer_cost = pricing.get("load_balancer", 0.0225) * 24 * 30
        
        # Data transfer costs (estimated)
        data_transfer_gb = 100  # Default monthly transfer
        if networking_design.get("cdn"):
            data_transfer_gb = 50  # CDN reduces origin transfer
        if networking_design.get("multi_region"):
            data_transfer_gb *= 2  # More cross-region traffic
        
        data_transfer_cost = data_transfer_gb * pricing.get("data_transfer_out", 0.09)
        
        # NAT Gateway (if needed)
        nat_cost = 0
        if networking_design.get("vpc"):
            nat_cost = pricing.get("nat_gateway", 0.045) * 24 * 30
        
        return load_balancer_cost + data_transfer_cost + nat_cost
    
    def _calculate_operational_costs(self, base_cost: float) -> float:
        """Calculate operational costs as percentage of base infrastructure"""
        
        total_operational = 0
        for service, percentage in self.operational_costs.items():
            total_operational += base_cost * percentage
        
        return total_operational
    
    def _project_yearly_costs(self, monthly_cost: float) -> float:
        """Project yearly costs with growth"""
        
        # Assume 20% growth over the year
        growth_factor = 1.2
        return monthly_cost * 12 * growth_factor
    
    def _identify_cost_optimizations(self, infrastructure_design: Dict[str, Any]) -> List[Dict[str, str]]:
        """Identify cost optimization opportunities"""
        
        optimizations = []
        
        # Reserved instances
        optimizations.append({
            "opportunity": "Reserved Instances",
            "potential_savings": "30-60%",
            "description": "Use reserved instances for predictable workloads",
            "implementation": "Analyze usage patterns and purchase 1-3 year reserved instances"
        })
        
        # Auto-scaling
        if not infrastructure_design.get("compute", {}).get("auto_scaling"):
            optimizations.append({
                "opportunity": "Auto-scaling",
                "potential_savings": "20-40%",
                "description": "Implement auto-scaling to match demand",
                "implementation": "Configure auto-scaling groups with appropriate metrics"
            })
        
        # Spot instances
        optimizations.append({
            "opportunity": "Spot Instances",
            "potential_savings": "50-90%",
            "description": "Use spot instances for non-critical workloads",
            "implementation": "Identify fault-tolerant workloads suitable for spot instances"
        })
        
        # Storage optimization
        optimizations.append({
            "opportunity": "Storage Lifecycle",
            "potential_savings": "40-60%",
            "description": "Implement storage lifecycle policies",
            "implementation": "Move infrequently accessed data to cheaper storage tiers"
        })
        
        return optimizations


class BudgetingEngine:
    """Provides budgeting and financial planning capabilities"""
    
    def __init__(self):
        self.budget_categories = {
            "development": {
                "personnel": 0.6,      # 60% of development budget
                "tools_licenses": 0.1,  # 10%
                "training": 0.05,      # 5%
                "contingency": 0.25    # 25%
            },
            "infrastructure": {
                "compute": 0.4,        # 40% of infrastructure budget
                "storage": 0.2,        # 20%
                "networking": 0.15,    # 15%
                "security": 0.1,       # 10%
                "monitoring": 0.05,    # 5%
                "contingency": 0.1     # 10%
            },
            "operations": {
                "support": 0.4,        # 40% of operations budget
                "maintenance": 0.3,    # 30%
                "upgrades": 0.2,       # 20%
                "contingency": 0.1     # 10%
            }
        }
    
    async def create_project_budget(self, requirements: List[BusinessRequirement], 
                                  timeline_months: int, team_size: int) -> Dict[str, Any]:
        """Create comprehensive project budget"""
        
        # Estimate development costs
        development_budget = self._estimate_development_budget(requirements, timeline_months, team_size)
        
        # Estimate infrastructure costs
        infrastructure_budget = self._estimate_infrastructure_budget(requirements)
        
        # Estimate operational costs
        operational_budget = self._estimate_operational_budget(infrastructure_budget, timeline_months)
        
        # Calculate total project cost
        total_budget = development_budget + infrastructure_budget + operational_budget
        
        # Add contingency
        contingency = total_budget * 0.2  # 20% contingency
        total_with_contingency = total_budget + contingency
        
        return {
            "budget_summary": {
                "development": development_budget,
                "infrastructure": infrastructure_budget,
                "operations": operational_budget,
                "contingency": contingency,
                "total": total_with_contingency
            },
            "budget_breakdown": {
                "development": self._breakdown_development_budget(development_budget),
                "infrastructure": self._breakdown_infrastructure_budget(infrastructure_budget),
                "operations": self._breakdown_operational_budget(operational_budget)
            },
            "timeline_allocation": self._allocate_budget_over_timeline(
                total_with_contingency, timeline_months
            ),
            "budget_controls": self._recommend_budget_controls(),
            "cost_tracking_metrics": self._define_cost_tracking_metrics()
        }
    
    def _estimate_development_budget(self, requirements: List[BusinessRequirement], 
                                   timeline_months: int, team_size: int) -> float:
        """Estimate development budget"""
        
        # Calculate complexity factor
        complexity_score = self._assess_project_complexity(requirements)
        complexity_multiplier = 1.0 + (complexity_score / 10.0)  # Scale complexity to multiplier
        
        # Base cost calculation
        average_hourly_rate = 100  # Average across all roles
        hours_per_month = 160  # Standard working hours
        base_cost = team_size * hours_per_month * timeline_months * average_hourly_rate
        
        # Apply complexity multiplier
        development_cost = base_cost * complexity_multiplier
        
        return development_cost
    
    def _assess_project_complexity(self, requirements: List[BusinessRequirement]) -> float:
        """Assess project complexity on scale of 1-10"""
        
        complexity_factors = {
            "integration": 2.0,
            "security": 1.5,
            "performance": 1.5,
            "scalability": 2.0,
            "compliance": 2.5,
            "real_time": 2.0,
            "machine_learning": 3.0,
            "blockchain": 3.5
        }
        
        total_complexity = 0
        for req in requirements:
            requirement_text = f"{req.action} {req.object} {req.category}".lower()
            
            for factor, weight in complexity_factors.items():
                if factor in requirement_text:
                    total_complexity += weight
        
        # Normalize to 1-10 scale
        max_possible = len(requirements) * max(complexity_factors.values())
        if max_possible > 0:
            complexity_score = min(10, (total_complexity / max_possible) * 10)
        else:
            complexity_score = 5  # Default moderate complexity
        
        return complexity_score
    
    def _estimate_infrastructure_budget(self, requirements: List[BusinessRequirement]) -> float:
        """Estimate infrastructure budget for project duration"""
        
        # Base infrastructure cost for moderate complexity project
        base_monthly_cost = 2000
        
        # Adjust based on requirements
        scaling_factor = 1.0
        for req in requirements:
            requirement_text = f"{req.action} {req.object} {req.category}".lower()
            
            if "scale" in requirement_text or "high volume" in requirement_text:
                scaling_factor *= 1.5
            if "global" in requirement_text or "multi-region" in requirement_text:
                scaling_factor *= 1.3
            if "analytics" in requirement_text or "big data" in requirement_text:
                scaling_factor *= 1.4
        
        monthly_cost = base_monthly_cost * scaling_factor
        
        # Infrastructure needed during development (assume 6 months minimum)
        project_duration_months = 6
        
        return monthly_cost * project_duration_months
    
    def _estimate_operational_budget(self, infrastructure_budget: float, timeline_months: int) -> float:
        """Estimate operational budget"""
        
        # Operations typically 30% of infrastructure cost
        return infrastructure_budget * 0.3
    
    def _breakdown_development_budget(self, total_budget: float) -> Dict[str, float]:
        """Break down development budget by category"""
        
        breakdown = {}
        for category, percentage in self.budget_categories["development"].items():
            breakdown[category] = total_budget * percentage
        
        return breakdown
    
    def _breakdown_infrastructure_budget(self, total_budget: float) -> Dict[str, float]:
        """Break down infrastructure budget by category"""
        
        breakdown = {}
        for category, percentage in self.budget_categories["infrastructure"].items():
            breakdown[category] = total_budget * percentage
        
        return breakdown
    
    def _breakdown_operational_budget(self, total_budget: float) -> Dict[str, float]:
        """Break down operational budget by category"""
        
        breakdown = {}
        for category, percentage in self.budget_categories["operations"].items():
            breakdown[category] = total_budget * percentage
        
        return breakdown
    
    def _allocate_budget_over_timeline(self, total_budget: float, timeline_months: int) -> List[Dict[str, Any]]:
        """Allocate budget over project timeline"""
        
        # Typical spending pattern: heavy in middle phases
        spending_pattern = {
            "month_1": 0.05,
            "months_2_3": 0.20,
            "months_4_6": 0.45,
            "months_7_9": 0.25,
            "final_months": 0.05
        }
        
        allocation = []
        
        # Adjust pattern to timeline
        if timeline_months <= 6:
            months_per_phase = max(1, timeline_months // 4)
        else:
            months_per_phase = timeline_months // 5
        
        current_month = 1
        for phase, percentage in spending_pattern.items():
            phase_budget = total_budget * percentage
            phase_months = months_per_phase
            
            if current_month + phase_months > timeline_months:
                phase_months = timeline_months - current_month + 1
            
            monthly_budget = phase_budget / phase_months
            
            for month in range(current_month, current_month + phase_months):
                if month <= timeline_months:
                    allocation.append({
                        "month": month,
                        "budget": monthly_budget,
                        "cumulative": sum(item["budget"] for item in allocation) + monthly_budget,
                        "phase": phase
                    })
            
            current_month += phase_months
            
            if current_month > timeline_months:
                break
        
        return allocation
    
    def _recommend_budget_controls(self) -> List[Dict[str, str]]:
        """Recommend budget control measures"""
        
        return [
            {
                "control": "Monthly Budget Reviews",
                "description": "Conduct monthly budget vs actual spending reviews",
                "implementation": "Schedule monthly meetings with stakeholders to review spending"
            },
            {
                "control": "Approval Thresholds",
                "description": "Set approval thresholds for different spending levels",
                "implementation": "Require approvals for expenses over $1000, $5000, and $10000"
            },
            {
                "control": "Cost Center Tracking",
                "description": "Track costs by project phases and components",
                "implementation": "Use cost center codes for all project-related expenses"
            },
            {
                "control": "Variance Analysis",
                "description": "Analyze budget variances and take corrective action",
                "implementation": "Weekly variance reports with action plans for >10% variances"
            },
            {
                "control": "Resource Utilization Monitoring",
                "description": "Monitor team resource utilization and efficiency",
                "implementation": "Track billable hours and productivity metrics"
            }
        ]
    
    def _define_cost_tracking_metrics(self) -> List[Dict[str, str]]:
        """Define cost tracking metrics"""
        
        return [
            {
                "metric": "Cost per Story Point",
                "description": "Development cost divided by delivered story points",
                "frequency": "Sprint"
            },
            {
                "metric": "Infrastructure Cost per User",
                "description": "Monthly infrastructure cost divided by active users",
                "frequency": "Monthly"
            },
            {
                "metric": "Budget Variance",
                "description": "Percentage difference between planned and actual spending",
                "frequency": "Weekly"
            },
            {
                "metric": "Resource Utilization",
                "description": "Percentage of available team hours spent on project",
                "frequency": "Weekly"
            },
            {
                "metric": "Cost Trend",
                "description": "Monthly cost growth rate",
                "frequency": "Monthly"
            }
        ]


class ROIAnalysisEngine:
    """Analyzes return on investment for projects"""
    
    def __init__(self):
        self.roi_factors = {
            "efficiency_gains": {
                "automation": 0.3,        # 30% efficiency gain
                "process_improvement": 0.2, # 20% efficiency gain
                "user_experience": 0.15    # 15% efficiency gain
            },
            "cost_savings": {
                "infrastructure_optimization": 0.25,  # 25% cost reduction
                "process_automation": 0.4,            # 40% cost reduction
                "resource_consolidation": 0.2         # 20% cost reduction
            },
            "revenue_opportunities": {
                "new_features": 0.1,      # 10% revenue increase
                "market_expansion": 0.25,  # 25% revenue increase
                "customer_retention": 0.05 # 5% revenue increase
            }
        }
    
    async def calculate_roi(self, project_budget: float, requirements: List[BusinessRequirement],
                          business_metrics: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate return on investment for project"""
        
        # Analyze benefits from requirements
        efficiency_benefits = self._calculate_efficiency_benefits(requirements, business_metrics)
        cost_savings = self._calculate_cost_savings(requirements, business_metrics)
        revenue_benefits = self._calculate_revenue_benefits(requirements, business_metrics)
        
        # Total annual benefits
        total_annual_benefits = efficiency_benefits + cost_savings + revenue_benefits
        
        # Calculate ROI metrics
        roi_percentage = ((total_annual_benefits - project_budget) / project_budget) * 100
        payback_period = project_budget / (total_annual_benefits / 12)  # months
        net_present_value = self._calculate_npv(project_budget, total_annual_benefits, 5, 0.1)
        
        return {
            "roi_summary": {
                "project_investment": project_budget,
                "annual_benefits": total_annual_benefits,
                "roi_percentage": roi_percentage,
                "payback_period_months": payback_period,
                "net_present_value": net_present_value
            },
            "benefit_breakdown": {
                "efficiency_gains": efficiency_benefits,
                "cost_savings": cost_savings,
                "revenue_opportunities": revenue_benefits
            },
            "risk_adjusted_roi": self._calculate_risk_adjusted_roi(roi_percentage, requirements),
            "sensitivity_analysis": self._perform_sensitivity_analysis(
                project_budget, total_annual_benefits
            ),
            "recommendations": self._generate_roi_recommendations(
                roi_percentage, payback_period, net_present_value
            )
        }
    
    def _calculate_efficiency_benefits(self, requirements: List[BusinessRequirement],
                                     business_metrics: Dict[str, Any]) -> float:
        """Calculate efficiency benefit value"""
        
        current_operational_cost = business_metrics.get("annual_operational_cost", 100000)
        efficiency_gain = 0
        
        for req in requirements:
            requirement_text = f"{req.action} {req.object} {req.category}".lower()
            
            if "automat" in requirement_text:
                efficiency_gain += self.roi_factors["efficiency_gains"]["automation"]
            elif "improve" in requirement_text or "optimize" in requirement_text:
                efficiency_gain += self.roi_factors["efficiency_gains"]["process_improvement"]
            elif "user" in requirement_text or "experience" in requirement_text:
                efficiency_gain += self.roi_factors["efficiency_gains"]["user_experience"]
        
        # Cap efficiency gains at 50%
        efficiency_gain = min(efficiency_gain, 0.5)
        
        return current_operational_cost * efficiency_gain
    
    def _calculate_cost_savings(self, requirements: List[BusinessRequirement],
                              business_metrics: Dict[str, Any]) -> float:
        """Calculate cost savings value"""
        
        current_infrastructure_cost = business_metrics.get("annual_infrastructure_cost", 50000)
        cost_reduction = 0
        
        for req in requirements:
            requirement_text = f"{req.action} {req.object} {req.category}".lower()
            
            if "cloud" in requirement_text or "optimize" in requirement_text:
                cost_reduction += self.roi_factors["cost_savings"]["infrastructure_optimization"]
            elif "automat" in requirement_text:
                cost_reduction += self.roi_factors["cost_savings"]["process_automation"]
            elif "consolidat" in requirement_text or "centraliz" in requirement_text:
                cost_reduction += self.roi_factors["cost_savings"]["resource_consolidation"]
        
        # Cap cost reduction at 40%
        cost_reduction = min(cost_reduction, 0.4)
        
        return current_infrastructure_cost * cost_reduction
    
    def _calculate_revenue_benefits(self, requirements: List[BusinessRequirement],
                                  business_metrics: Dict[str, Any]) -> float:
        """Calculate revenue benefit value"""
        
        current_annual_revenue = business_metrics.get("annual_revenue", 1000000)
        revenue_increase = 0
        
        for req in requirements:
            requirement_text = f"{req.action} {req.object} {req.category}".lower()
            
            if "new feature" in requirement_text or "capability" in requirement_text:
                revenue_increase += self.roi_factors["revenue_opportunities"]["new_features"]
            elif "market" in requirement_text or "expand" in requirement_text:
                revenue_increase += self.roi_factors["revenue_opportunities"]["market_expansion"]
            elif "customer" in requirement_text or "retention" in requirement_text:
                revenue_increase += self.roi_factors["revenue_opportunities"]["customer_retention"]
        
        # Cap revenue increase at 30%
        revenue_increase = min(revenue_increase, 0.3)
        
        return current_annual_revenue * revenue_increase
    
    def _calculate_npv(self, initial_investment: float, annual_benefits: float,
                      years: int, discount_rate: float) -> float:
        """Calculate Net Present Value"""
        
        npv = -initial_investment  # Initial investment is negative cash flow
        
        for year in range(1, years + 1):
            discounted_benefit = annual_benefits / ((1 + discount_rate) ** year)
            npv += discounted_benefit
        
        return npv
    
    def _calculate_risk_adjusted_roi(self, roi_percentage: float,
                                   requirements: List[BusinessRequirement]) -> Dict[str, float]:
        """Calculate risk-adjusted ROI"""
        
        # Assess project risk
        risk_score = self._assess_project_risk(requirements)
        
        # Risk adjustment factors
        risk_adjustments = {
            "low": 0.9,      # 10% reduction for low risk
            "medium": 0.8,   # 20% reduction for medium risk
            "high": 0.6,     # 40% reduction for high risk
            "very_high": 0.4 # 60% reduction for very high risk
        }
        
        risk_level = "medium"  # Default
        if risk_score < 3:
            risk_level = "low"
        elif risk_score < 6:
            risk_level = "medium"
        elif risk_score < 8:
            risk_level = "high"
        else:
            risk_level = "very_high"
        
        risk_adjustment = risk_adjustments[risk_level]
        risk_adjusted_roi = roi_percentage * risk_adjustment
        
        return {
            "original_roi": roi_percentage,
            "risk_level": risk_level,
            "risk_score": risk_score,
            "risk_adjustment_factor": risk_adjustment,
            "risk_adjusted_roi": risk_adjusted_roi
        }
    
    def _assess_project_risk(self, requirements: List[BusinessRequirement]) -> float:
        """Assess project risk on scale of 1-10"""
        
        risk_factors = {
            "new_technology": 3,
            "integration": 2,
            "compliance": 2,
            "scalability": 2,
            "security": 2,
            "real_time": 3,
            "machine_learning": 4,
            "blockchain": 5
        }
        
        total_risk = 0
        for req in requirements:
            requirement_text = f"{req.action} {req.object} {req.category}".lower()
            
            for factor, weight in risk_factors.items():
                if factor.replace("_", " ") in requirement_text:
                    total_risk += weight
        
        # Normalize to 1-10 scale
        max_possible = len(requirements) * max(risk_factors.values())
        if max_possible > 0:
            risk_score = min(10, (total_risk / max_possible) * 10)
        else:
            risk_score = 5  # Default moderate risk
        
        return risk_score
    
    def _perform_sensitivity_analysis(self, project_budget: float,
                                    annual_benefits: float) -> Dict[str, Dict[str, float]]:
        """Perform sensitivity analysis on key variables"""
        
        base_roi = ((annual_benefits - project_budget) / project_budget) * 100
        
        # Test scenarios: budget +/- 20%, benefits +/- 30%
        scenarios = {
            "pessimistic": {
                "budget_multiplier": 1.2,    # 20% over budget
                "benefits_multiplier": 0.7   # 30% lower benefits
            },
            "optimistic": {
                "budget_multiplier": 0.9,    # 10% under budget
                "benefits_multiplier": 1.3   # 30% higher benefits
            },
            "worst_case": {
                "budget_multiplier": 1.5,    # 50% over budget
                "benefits_multiplier": 0.5   # 50% lower benefits
            },
            "best_case": {
                "budget_multiplier": 0.8,    # 20% under budget
                "benefits_multiplier": 1.5   # 50% higher benefits
            }
        }
        
        sensitivity_results = {}
        
        for scenario, multipliers in scenarios.items():
            scenario_budget = project_budget * multipliers["budget_multiplier"]
            scenario_benefits = annual_benefits * multipliers["benefits_multiplier"]
            scenario_roi = ((scenario_benefits - scenario_budget) / scenario_budget) * 100
            
            sensitivity_results[scenario] = {
                "budget": scenario_budget,
                "annual_benefits": scenario_benefits,
                "roi_percentage": scenario_roi,
                "roi_change": scenario_roi - base_roi
            }
        
        return sensitivity_results
    
    def _generate_roi_recommendations(self, roi_percentage: float, payback_period: float,
                                    net_present_value: float) -> List[str]:
        """Generate ROI-based recommendations"""
        
        recommendations = []
        
        if roi_percentage > 100:
            recommendations.append("Excellent ROI - Strong business case for project approval")
        elif roi_percentage > 50:
            recommendations.append("Good ROI - Project should be considered for approval")
        elif roi_percentage > 20:
            recommendations.append("Moderate ROI - Evaluate against other investment opportunities")
        else:
            recommendations.append("Low ROI - Consider optimizing scope or timeline")
        
        if payback_period < 12:
            recommendations.append("Fast payback period - Quick return on investment")
        elif payback_period < 24:
            recommendations.append("Reasonable payback period - Acceptable investment timeline")
        else:
            recommendations.append("Long payback period - Consider phased approach")
        
        if net_present_value > 0:
            recommendations.append("Positive NPV indicates value creation")
        else:
            recommendations.append("Negative NPV - Re-evaluate business case")
        
        # General recommendations
        recommendations.extend([
            "Monitor actual vs projected benefits quarterly",
            "Implement benefit tracking metrics from project start",
            "Consider phased delivery to realize benefits earlier",
            "Plan for benefit realization and change management"
        ])
        
        return recommendations


class AccountantAgent:
    """
    Accountant Agent for Microservice
    
    Provides cost analysis, budgeting, and financial optimization for architecture projects.
    Analyzes infrastructure costs, development costs, and provides ROI analysis.
    """
    
    def __init__(self):
        self.agent_id = str(uuid.uuid4())
        self.name = "Accountant"
        self.description = "Provides cost analysis, budgeting, and ROI analysis for projects"
        
        # Dependencies
        self.cost_analysis_engine = CostAnalysisEngine()
        self.budgeting_engine = BudgetingEngine()
        self.roi_analysis_engine = ROIAnalysisEngine()
        
        logger.info(f"Accountant Agent {self.agent_id} initialized")
    
    async def initialize(self):
        """Initialize agent and dependencies"""
        logger.info(f"Accountant Agent {self.agent_id} fully initialized")
    
    async def cleanup(self):
        """Cleanup agent resources"""
        logger.info(f"Accountant Agent {self.agent_id} cleanup completed")
    
    async def process_task(self, task: AgentTask) -> AgentResponse:
        """Process task specific to accountant"""
        try:
            task_type = task.task_type
            
            if task_type == "analyze_costs":
                result = await self._analyze_costs(task.payload)
            elif task_type == "create_budget":
                result = await self._create_budget(task.payload)
            elif task_type == "calculate_roi":
                result = await self._calculate_roi(task.payload)
            elif task_type == "optimize_costs":
                result = await self._optimize_costs(task.payload)
            elif task_type == "track_expenses":
                result = await self._track_expenses(task.payload)
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
    
    async def _analyze_costs(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze costs for infrastructure and development"""
        infrastructure_design = payload.get("infrastructure_design", {})
        requirements_data = payload.get("requirements", [])
        
        if not infrastructure_design:
            raise ValueError("infrastructure_design is required")
        
        # Analyze infrastructure costs
        infrastructure_costs = await self.cost_analysis_engine.analyze_infrastructure_costs(
            infrastructure_design
        )
        
        # If requirements provided, analyze development costs too
        development_costs = None
        if requirements_data:
            requirements = [BusinessRequirement(**req_data) for req_data in requirements_data]
            complexity_score = self.budgeting_engine._assess_project_complexity(requirements)
            
            development_costs = {
                "complexity_score": complexity_score,
                "estimated_timeline_months": max(3, complexity_score),
                "recommended_team_size": max(3, int(complexity_score / 2)),
                "estimated_cost": complexity_score * 50000  # Rough estimate
            }
        
        return {
            "infrastructure_costs": infrastructure_costs,
            "development_costs": development_costs,
            "cost_summary": {
                "infrastructure_monthly": infrastructure_costs["monthly_costs"]["total"],
                "infrastructure_yearly": infrastructure_costs["yearly_costs"]["total"],
                "development_total": development_costs["estimated_cost"] if development_costs else 0
            }
        }
    
    async def _create_budget(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Create comprehensive project budget"""
        requirements_data = payload.get("requirements", [])
        timeline_months = payload.get("timeline_months", 6)
        team_size = payload.get("team_size", 5)
        
        if not requirements_data:
            raise ValueError("requirements are required")
        
        requirements = [BusinessRequirement(**req_data) for req_data in requirements_data]
        
        # Create project budget
        project_budget = await self.budgeting_engine.create_project_budget(
            requirements, timeline_months, team_size
        )
        
        return project_budget
    
    async def _calculate_roi(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate return on investment"""
        project_budget = payload.get("project_budget", 0)
        requirements_data = payload.get("requirements", [])
        business_metrics = payload.get("business_metrics", {})
        
        if not project_budget:
            raise ValueError("project_budget is required")
        if not requirements_data:
            raise ValueError("requirements are required")
        
        requirements = [BusinessRequirement(**req_data) for req_data in requirements_data]
        
        # Calculate ROI
        roi_analysis = await self.roi_analysis_engine.calculate_roi(
            project_budget, requirements, business_metrics
        )
        
        return roi_analysis
    
    async def _optimize_costs(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Provide cost optimization recommendations"""
        current_costs = payload.get("current_costs", {})
        infrastructure_design = payload.get("infrastructure_design", {})
        optimization_goals = payload.get("optimization_goals", [])
        
        # Generate cost optimization recommendations
        optimizations = []
        
        # Infrastructure optimizations
        if infrastructure_design:
            infra_optimizations = self.cost_analysis_engine._identify_cost_optimizations(
                infrastructure_design
            )
            optimizations.extend(infra_optimizations)
        
        # Development process optimizations
        optimizations.extend([
            {
                "opportunity": "DevOps Automation",
                "potential_savings": "15-25%",
                "description": "Automate development and deployment processes",
                "implementation": "Implement CI/CD pipelines and infrastructure as code"
            },
            {
                "opportunity": "Team Efficiency",
                "potential_savings": "10-20%",
                "description": "Improve team productivity through better tools and processes",
                "implementation": "Invest in development tools and training"
            },
            {
                "opportunity": "Vendor Negotiations",
                "potential_savings": "5-15%",
                "description": "Negotiate better rates with vendors and service providers",
                "implementation": "Review contracts and negotiate volume discounts"
            }
        ])
        
        # Calculate potential savings
        total_current_cost = sum(current_costs.values()) if current_costs else 100000
        potential_savings = total_current_cost * 0.25  # Assume 25% average savings potential
        
        return {
            "optimization_opportunities": optimizations,
            "potential_savings": potential_savings,
            "current_costs": current_costs,
            "optimization_priority": self._prioritize_optimizations(optimizations),
            "implementation_roadmap": self._create_optimization_roadmap(optimizations)
        }
    
    async def _track_expenses(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Track and analyze project expenses"""
        actual_expenses = payload.get("actual_expenses", {})
        budget = payload.get("budget", {})
        period = payload.get("period", "monthly")
        
        # Calculate variances
        variances = {}
        for category, budgeted in budget.items():
            actual = actual_expenses.get(category, 0)
            variance = actual - budgeted
            variance_percentage = (variance / budgeted * 100) if budgeted > 0 else 0
            
            variances[category] = {
                "budgeted": budgeted,
                "actual": actual,
                "variance": variance,
                "variance_percentage": variance_percentage,
                "status": "over_budget" if variance > 0 else "under_budget" if variance < 0 else "on_budget"
            }
        
        # Calculate totals
        total_budgeted = sum(budget.values())
        total_actual = sum(actual_expenses.values())
        total_variance = total_actual - total_budgeted
        total_variance_percentage = (total_variance / total_budgeted * 100) if total_budgeted > 0 else 0
        
        # Generate alerts
        alerts = []
        for category, variance_data in variances.items():
            if abs(variance_data["variance_percentage"]) > 10:
                alerts.append({
                    "category": category,
                    "variance_percentage": variance_data["variance_percentage"],
                    "severity": "high" if abs(variance_data["variance_percentage"]) > 20 else "medium",
                    "message": f"{category} is {abs(variance_data['variance_percentage']):.1f}% {'over' if variance_data['variance'] > 0 else 'under'} budget"
                })
        
        return {
            "expense_summary": {
                "total_budgeted": total_budgeted,
                "total_actual": total_actual,
                "total_variance": total_variance,
                "total_variance_percentage": total_variance_percentage
            },
            "category_variances": variances,
            "alerts": alerts,
            "recommendations": self._generate_expense_recommendations(variances, alerts),
            "trend_analysis": self._analyze_expense_trends(actual_expenses, period)
        }
    
    def _prioritize_optimizations(self, optimizations: List[Dict[str, str]]) -> List[Dict[str, str]]:
        """Prioritize optimization opportunities"""
        
        priority_mapping = {
            "Reserved Instances": "high",
            "Auto-scaling": "high", 
            "DevOps Automation": "medium",
            "Spot Instances": "medium",
            "Storage Lifecycle": "medium",
            "Team Efficiency": "low",
            "Vendor Negotiations": "low"
        }
        
        for optimization in optimizations:
            opportunity = optimization.get("opportunity", "")
            optimization["priority"] = priority_mapping.get(opportunity, "medium")
        
        # Sort by priority (high, medium, low)
        priority_order = {"high": 1, "medium": 2, "low": 3}
        return sorted(optimizations, key=lambda x: priority_order.get(x.get("priority", "medium"), 2))
    
    def _create_optimization_roadmap(self, optimizations: List[Dict[str, str]]) -> List[Dict[str, Any]]:
        """Create implementation roadmap for optimizations"""
        
        roadmap = []
        
        # Phase optimizations over quarters
        phases = [
            {"phase": "Q1", "focus": "Quick wins and high-impact optimizations"},
            {"phase": "Q2", "focus": "Infrastructure and automation improvements"},
            {"phase": "Q3", "focus": "Process and team efficiency improvements"},
            {"phase": "Q4", "focus": "Long-term strategic optimizations"}
        ]
        
        optimizations_per_phase = len(optimizations) // len(phases) + 1
        
        for i, phase in enumerate(phases):
            phase_optimizations = optimizations[i * optimizations_per_phase:(i + 1) * optimizations_per_phase]
            
            if phase_optimizations:
                roadmap.append({
                    "phase": phase["phase"],
                    "focus": phase["focus"],
                    "optimizations": phase_optimizations,
                    "estimated_savings": sum(
                        float(opt.get("potential_savings", "0%").rstrip("%")) 
                        for opt in phase_optimizations
                    ) / len(phase_optimizations) if phase_optimizations else 0
                })
        
        return roadmap
    
    def _generate_expense_recommendations(self, variances: Dict[str, Any], 
                                        alerts: List[Dict[str, Any]]) -> List[str]:
        """Generate expense management recommendations"""
        
        recommendations = []
        
        # High variance recommendations
        high_variance_categories = [
            category for category, data in variances.items()
            if abs(data["variance_percentage"]) > 15
        ]
        
        if high_variance_categories:
            recommendations.append(
                f"Investigate high variances in: {', '.join(high_variance_categories)}"
            )
        
        # Budget control recommendations
        over_budget_categories = [
            category for category, data in variances.items()
            if data["variance"] > 0
        ]
        
        if over_budget_categories:
            recommendations.extend([
                "Implement stricter approval processes for over-budget categories",
                "Review and update budget forecasts based on actual spending patterns",
                "Consider reallocating budget from under-spent categories"
            ])
        
        # General recommendations
        recommendations.extend([
            "Implement weekly expense reviews for early detection of issues",
            "Automate expense tracking and reporting where possible",
            "Establish clear escalation procedures for budget variances",
            "Review vendor contracts and negotiate better terms"
        ])
        
        return recommendations
    
    def _analyze_expense_trends(self, actual_expenses: Dict[str, float], 
                              period: str) -> Dict[str, str]:
        """Analyze expense trends (simplified)"""
        
        # In a real implementation, this would analyze historical data
        # For now, provide general trend analysis
        
        total_expenses = sum(actual_expenses.values())
        
        trends = {
            "overall_trend": "stable",  # Would be calculated from historical data
            "growth_rate": "5% month-over-month",  # Would be calculated
            "seasonal_patterns": "Higher expenses in Q4 due to year-end projects",
            "cost_drivers": "Infrastructure and personnel costs are the main drivers",
            "forecast": f"Projected {period} expenses: ${total_expenses * 1.05:,.2f}"
        }
        
        return trends