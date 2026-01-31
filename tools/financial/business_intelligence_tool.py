"""
Business Intelligence Tool for CEO and CFO Agents

Provides real-time business intelligence, KPI monitoring, and performance analytics.
Integrates with system_health_tool and token_calculator_tool for comprehensive metrics.

CFO Priority Access: The CFO agent has priority access to all financial and system metrics.
"""

import json
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
import uuid
from pathlib import Path

from agents.core.bdi_agent import BaseTool
from agents.memory_agent import MemoryAgent
from utils.config import Config, PROJECT_ROOT
from utils.logging_config import get_logger

logger = get_logger(__name__)

@dataclass
class BusinessMetrics:
    """Business metrics data structure"""
    timestamp: str
    revenue_metrics: Dict[str, float]
    cost_metrics: Dict[str, float]
    performance_metrics: Dict[str, float]
    growth_metrics: Dict[str, float]
    efficiency_metrics: Dict[str, float]

@dataclass
class KPIReport:
    """KPI report structure"""
    report_id: str
    timestamp: str
    period: str
    kpis: Dict[str, Any]
    trends: Dict[str, str]
    alerts: List[str]
    recommendations: List[str]

class BusinessIntelligenceTool(BaseTool):
    """
    Business Intelligence Tool for CEO and CFO Dashboard
    
    Provides comprehensive business intelligence with integration to:
    - system_health_tool: System performance and resource metrics
    - token_calculator_tool: Cost tracking and budget management
    - Memory system: Historical data and trend analysis
    
    CFO Priority Access: CFO agent has priority access to all financial metrics,
    cost data, and system health information for capital discipline enforcement.
    """
    
    def __init__(self, 
                 memory_agent: Optional[MemoryAgent] = None,
                 config: Optional[Config] = None,
                 **kwargs):
        super().__init__(config=config, **kwargs)
        self.memory_agent = memory_agent
        self.config = config or Config()
        self.logger = get_logger(__name__)
        self.tool_name = "business_intelligence"
        self.version = "2.0"
        
        # CFO priority access flag
        self.cfo_priority_enabled = True
        
        # Tool references (lazy loaded)
        self._system_health_tool = None
        self._token_calculator_tool = None
        
        # Sample business data for demo (can be replaced with real data sources)
        self.business_data = {
            "revenue": {
                "monthly_recurring": 25000.0,
                "total_lifetime": 150000.0,
                "growth_rate": 15.5
            },
            "costs": {
                "operational": 8000.0,
                "infrastructure": 3000.0,
                "personnel": 12000.0
            },
            "customers": {
                "total_active": 45,
                "new_this_month": 8,
                "churn_rate": 2.1
            },
            "operations": {
                "uptime_percentage": 99.8,
                "response_time_ms": 150,
                "error_rate": 0.2
            }
        }
    
    async def _get_system_health_tool(self):
        """Lazy load system health tool"""
        if self._system_health_tool is None:
            try:
                from tools.core.system_health_tool import SystemHealthTool
                self._system_health_tool = SystemHealthTool(config=self.config)
            except Exception as e:
                self.logger.warning(f"Could not load system_health_tool: {e}")
                self._system_health_tool = None
        return self._system_health_tool
    
    async def _get_token_calculator_tool(self):
        """Lazy load token calculator tool"""
        if self._token_calculator_tool is None:
            try:
                from tools.financial.token_calculator_tool_robust import TokenCalculatorToolRobust
                self._token_calculator_tool = TokenCalculatorToolRobust(
                    memory_agent=self.memory_agent,
                    config=self.config
                )
            except Exception as e:
                self.logger.warning(f"Could not load token_calculator_tool: {e}")
                self._token_calculator_tool = None
        return self._token_calculator_tool
    
    async def get_business_metrics(self, period: str = "current") -> BusinessMetrics:
        """Get comprehensive business metrics"""
        try:
            self.logger.info(f"Generating business metrics for period: {period}")
            
            # Simulate metrics calculation
            revenue_metrics = {
                "monthly_recurring_revenue": self.business_data["revenue"]["monthly_recurring"],
                "annual_run_rate": self.business_data["revenue"]["monthly_recurring"] * 12,
                "revenue_growth_rate": self.business_data["revenue"]["growth_rate"],
                "average_revenue_per_user": self.business_data["revenue"]["monthly_recurring"] / max(self.business_data["customers"]["total_active"], 1),
                "customer_lifetime_value": 50000.0
            }
            
            cost_metrics = {
                "total_operating_costs": sum(self.business_data["costs"].values()),
                "cost_per_customer": sum(self.business_data["costs"].values()) / max(self.business_data["customers"]["total_active"], 1),
                "burn_rate": sum(self.business_data["costs"].values()),
                "runway_months": 100000.0 / sum(self.business_data["costs"].values())  # Assuming 100k cash
            }
            
            performance_metrics = {
                "gross_margin": (revenue_metrics["monthly_recurring_revenue"] - cost_metrics["total_operating_costs"]) / revenue_metrics["monthly_recurring_revenue"] * 100,
                "net_margin": 15.5,
                "ebitda": revenue_metrics["monthly_recurring_revenue"] - cost_metrics["total_operating_costs"],
                "cash_flow": 2000.0
            }
            
            growth_metrics = {
                "customer_growth_rate": 25.0,
                "revenue_growth_rate": self.business_data["revenue"]["growth_rate"],
                "market_penetration": 2.5,
                "brand_awareness": 15.0
            }
            
            efficiency_metrics = {
                "customer_acquisition_cost": 1500.0,
                "payback_period_months": 3.2,
                "operational_efficiency": 85.0,
                "automation_ratio": 75.0
            }
            
            return BusinessMetrics(
                timestamp=datetime.now().isoformat(),
                revenue_metrics=revenue_metrics,
                cost_metrics=cost_metrics,
                performance_metrics=performance_metrics,
                growth_metrics=growth_metrics,
                efficiency_metrics=efficiency_metrics
            )
            
        except Exception as e:
            self.logger.error(f"Failed to generate business metrics: {e}")
            raise
    
    async def generate_kpi_report(self, period: str = "monthly") -> KPIReport:
        """Generate KPI report with trends and alerts"""
        try:
            self.logger.info(f"Generating KPI report for period: {period}")
            
            report_id = str(uuid.uuid4())
            
            # Key Performance Indicators
            kpis = {
                "revenue": {
                    "value": self.business_data["revenue"]["monthly_recurring"],
                    "target": 30000.0,
                    "achievement": 83.3,
                    "status": "ON_TRACK"
                },
                "customers": {
                    "value": self.business_data["customers"]["total_active"],
                    "target": 50,
                    "achievement": 90.0,
                    "status": "AHEAD"
                },
                "growth_rate": {
                    "value": self.business_data["revenue"]["growth_rate"],
                    "target": 20.0,
                    "achievement": 77.5,
                    "status": "NEEDS_ATTENTION"
                },
                "uptime": {
                    "value": self.business_data["operations"]["uptime_percentage"],
                    "target": 99.9,
                    "achievement": 99.9,
                    "status": "EXCELLENT"
                }
            }
            
            # Trend analysis
            trends = {
                "revenue": "INCREASING",
                "customers": "INCREASING",
                "costs": "STABLE",
                "efficiency": "IMPROVING",
                "market_position": "STRENGTHENING"
            }
            
            # Alerts and notifications
            alerts = []
            if kpis["growth_rate"]["achievement"] < 80:
                alerts.append("Growth rate below target - review acquisition strategy")
            if self.business_data["operations"]["uptime_percentage"] < 99.5:
                alerts.append("System uptime below acceptable threshold")
            if self.business_data["customers"]["churn_rate"] > 5.0:
                alerts.append("Customer churn rate increasing - investigate retention")
            
            # Strategic recommendations
            recommendations = [
                "Increase marketing spend to accelerate customer acquisition",
                "Focus on customer success to improve retention rates",
                "Explore new market segments for revenue diversification",
                "Invest in automation to improve operational efficiency"
            ]
            
            return KPIReport(
                report_id=report_id,
                timestamp=datetime.now().isoformat(),
                period=period,
                kpis=kpis,
                trends=trends,
                alerts=alerts,
                recommendations=recommendations
            )
            
        except Exception as e:
            self.logger.error(f"Failed to generate KPI report: {e}")
            raise
    
    async def get_cfo_metrics(self, agent_id: str = "cfo") -> Dict[str, Any]:
        """
        Get comprehensive CFO metrics with priority access.
        
        CFO has priority access to:
        - System health metrics (CPU, memory, disk, network)
        - Token/cost metrics (LLM usage, costs, budgets)
        - Financial metrics (revenue, costs, margins)
        - Operational efficiency metrics
        """
        try:
            self.logger.info(f"Generating CFO metrics for agent: {agent_id}")
            
            # Get system health metrics
            system_health = None
            health_tool = await self._get_system_health_tool()
            if health_tool:
                try:
                    # Get CPU and memory metrics
                    cpu_result = await health_tool.execute("monitor_cpu")
                    memory_result = await health_tool.execute("monitor_memory_disk")
                    system_health = {
                        "cpu_usage": cpu_result.get("cpu_percent", 0) if isinstance(cpu_result, dict) else 0,
                        "memory_usage": memory_result.get("memory_percent", 0) if isinstance(memory_result, dict) else 0,
                        "disk_usage": memory_result.get("disk_percent", 0) if isinstance(memory_result, dict) else 0,
                        "timestamp": datetime.now().isoformat()
                    }
                except Exception as e:
                    self.logger.warning(f"Could not fetch system health: {e}")
            
            # Get token/cost metrics
            cost_metrics = None
            token_tool = await self._get_token_calculator_tool()
            if token_tool:
                try:
                    # Get usage report
                    usage_result = await token_tool.execute("get_usage_report", agent_id=agent_id, days_back=30)
                    metrics_result = await token_tool.execute("get_metrics")
                    
                    if isinstance(usage_result, tuple):
                        success, data = usage_result
                        if success and isinstance(data, dict):
                            cost_metrics = {
                                "total_cost_30d": data.get("total_cost", 0),
                                "total_tokens": data.get("total_tokens", 0),
                                "operations_count": data.get("operations_count", 0),
                                "average_cost_per_operation": data.get("avg_cost_per_op", 0)
                            }
                    
                    if isinstance(metrics_result, tuple):
                        success, metrics_data = metrics_result
                        if success and isinstance(metrics_data, dict):
                            if cost_metrics:
                                cost_metrics.update({
                                    "budget_status": metrics_data.get("budget_status", "UNKNOWN"),
                                    "budget_utilization": metrics_data.get("budget_utilization", 0),
                                    "cost_trend": metrics_data.get("cost_trend", "STABLE")
                                })
                except Exception as e:
                    self.logger.warning(f"Could not fetch cost metrics: {e}")
            
            # Get business metrics
            business_metrics = await self.get_business_metrics()
            
            # Combine all metrics for CFO
            cfo_metrics = {
                "report_id": str(uuid.uuid4()),
                "timestamp": datetime.now().isoformat(),
                "agent_id": agent_id,
                "priority_access": True,
                "system_health": system_health,
                "cost_metrics": cost_metrics,
                "financial_metrics": {
                    "revenue": business_metrics.revenue_metrics,
                    "costs": business_metrics.cost_metrics,
                    "performance": business_metrics.performance_metrics,
                    "efficiency": business_metrics.efficiency_metrics
                },
                "roi_analysis": {
                    "llm_cost_per_revenue": (cost_metrics.get("total_cost_30d", 0) / max(business_metrics.revenue_metrics.get("monthly_recurring_revenue", 1), 1) * 100) if cost_metrics else 0,
                    "operational_efficiency": business_metrics.efficiency_metrics.get("operational_efficiency", 0),
                    "cost_per_customer": business_metrics.cost_metrics.get("cost_per_customer", 0)
                },
                "alerts": [],
                "recommendations": []
            }
            
            # Generate alerts based on metrics
            if cost_metrics and cost_metrics.get("budget_utilization", 0) > 75:
                cfo_metrics["alerts"].append("Budget utilization exceeds 75% - review spending")
            if system_health and system_health.get("cpu_usage", 0) > 80:
                cfo_metrics["alerts"].append("High CPU usage may indicate resource inefficiency")
            if business_metrics.performance_metrics.get("gross_margin", 0) < 20:
                cfo_metrics["alerts"].append("Gross margin below 20% - cost optimization needed")
            
            # Generate recommendations
            if cost_metrics:
                cfo_metrics["recommendations"].append("Monitor LLM costs and optimize model selection")
            if system_health and system_health.get("memory_usage", 0) > 80:
                cfo_metrics["recommendations"].append("Consider infrastructure scaling for memory efficiency")
            
            return cfo_metrics
            
        except Exception as e:
            self.logger.error(f"Failed to generate CFO metrics: {e}", exc_info=True)
            raise
    
    async def get_financial_dashboard(self) -> Dict[str, Any]:
        """Get comprehensive financial dashboard data"""
        try:
            self.logger.info("Generating financial dashboard")
            
            metrics = await self.get_business_metrics()
            
            dashboard = {
                "dashboard_id": str(uuid.uuid4()),
                "timestamp": datetime.now().isoformat(),
                "financial_summary": {
                    "total_revenue": metrics.revenue_metrics["monthly_recurring_revenue"],
                    "total_costs": metrics.cost_metrics["total_operating_costs"],
                    "net_profit": metrics.performance_metrics["ebitda"],
                    "profit_margin": metrics.performance_metrics["gross_margin"],
                    "cash_position": 100000.0,  # Simulated
                    "burn_rate": metrics.cost_metrics["burn_rate"]
                },
                "key_ratios": {
                    "revenue_growth": metrics.growth_metrics["revenue_growth_rate"],
                    "customer_acquisition_cost": metrics.efficiency_metrics["customer_acquisition_cost"],
                    "customer_lifetime_value": metrics.revenue_metrics["customer_lifetime_value"],
                    "payback_period": metrics.efficiency_metrics["payback_period_months"]
                },
                "forecasts": {
                    "revenue_6_months": metrics.revenue_metrics["monthly_recurring_revenue"] * 6 * 1.15,
                    "break_even_date": "2024-03-15",
                    "profitability_timeline": "Q2 2024"
                },
                "alerts": [
                    "Cash runway: 36 months at current burn rate",
                    "Revenue growth accelerating - consider scaling",
                    "Customer acquisition efficiency improving"
                ]
            }
            
            return dashboard
            
        except Exception as e:
            self.logger.error(f"Failed to generate financial dashboard: {e}")
            raise
    
    async def monitor_business_health(self) -> Dict[str, Any]:
        """Monitor overall business health with scoring"""
        try:
            self.logger.info("Monitoring business health")
            
            # Get system health if available
            system_health_score = 90.0
            health_tool = await self._get_system_health_tool()
            if health_tool:
                try:
                    cpu_result = await health_tool.execute("monitor_cpu")
                    if isinstance(cpu_result, dict):
                        cpu_usage = cpu_result.get("cpu_percent", 0)
                        system_health_score = max(0, 100 - cpu_usage)  # Invert CPU usage for health score
                except:
                    pass
            
            # Health scoring algorithm
            health_scores = {
                "financial_health": 85.0,  # Based on profitability, cash flow
                "operational_health": system_health_score,  # Based on system metrics
                "customer_health": 88.0,  # Based on satisfaction, retention
                "growth_health": 78.0,  # Based on acquisition, expansion
                "competitive_health": 82.0  # Based on market position
            }
            
            overall_health = sum(health_scores.values()) / len(health_scores)
            
            # Health status determination
            if overall_health >= 90:
                status = "EXCELLENT"
            elif overall_health >= 80:
                status = "GOOD"
            elif overall_health >= 70:
                status = "FAIR"
            else:
                status = "NEEDS_ATTENTION"
            
            health_report = {
                "health_id": str(uuid.uuid4()),
                "timestamp": datetime.now().isoformat(),
                "overall_health_score": overall_health,
                "health_status": status,
                "component_scores": health_scores,
                "strengths": [
                    "Strong operational performance",
                    "Good customer satisfaction",
                    "Solid financial foundation"
                ],
                "areas_for_improvement": [
                    "Accelerate growth initiatives",
                    "Strengthen competitive positioning",
                    "Diversify revenue streams"
                ],
                "action_items": [
                    "Review and optimize growth strategy",
                    "Conduct competitive analysis",
                    "Explore new market opportunities"
                ]
            }
            
            return health_report
            
        except Exception as e:
            self.logger.error(f"Failed to monitor business health: {e}")
            raise
    
    async def execute(self, action: str, agent_id: str = None, **kwargs) -> Tuple[bool, Any]:
        """
        Execute business intelligence operations.
        
        Actions:
        - "get_metrics": Get business metrics
        - "get_kpi_report": Generate KPI report
        - "get_cfo_metrics": Get CFO priority metrics (includes system health and costs)
        - "get_financial_dashboard": Get financial dashboard
        - "monitor_health": Monitor business health
        """
        try:
            if action == "get_metrics":
                metrics = await self.get_business_metrics(kwargs.get("period", "current"))
                return True, asdict(metrics)
            
            elif action == "get_kpi_report":
                report = await self.generate_kpi_report(kwargs.get("period", "monthly"))
                return True, asdict(report)
            
            elif action == "get_cfo_metrics":
                # CFO priority access
                cfo_metrics = await self.get_cfo_metrics(agent_id=agent_id or kwargs.get("agent_id", "cfo"))
                return True, cfo_metrics
            
            elif action == "get_financial_dashboard":
                dashboard = await self.get_financial_dashboard()
                return True, dashboard
            
            elif action == "monitor_health":
                health = await self.monitor_business_health()
                return True, health
            
            else:
                return False, f"Unknown action: {action}"
                
        except Exception as e:
            self.logger.error(f"Error executing business intelligence action {action}: {e}", exc_info=True)
            return False, str(e)

def create_business_intelligence_tool(memory_agent: Optional[MemoryAgent] = None, config: Optional[Config] = None) -> BusinessIntelligenceTool:
    """Factory function to create business intelligence tool"""
    return BusinessIntelligenceTool(memory_agent=memory_agent, config=config)

if __name__ == "__main__":
    async def main():
        tool = BusinessIntelligenceTool()
        
        print("=== Business Intelligence Demo ===")
        
        # Business metrics
        metrics = await tool.get_business_metrics()
        print(f"Revenue: ${metrics.revenue_metrics['monthly_recurring_revenue']:,.2f}")
        print(f"Growth Rate: {metrics.growth_metrics['revenue_growth_rate']:.1f}%")
        
        # KPI report
        kpi_report = await tool.generate_kpi_report()
        print(f"KPIs tracked: {len(kpi_report.kpis)}")
        print(f"Alerts: {len(kpi_report.alerts)}")
        
        # Business health
        health = await tool.monitor_business_health()
        print(f"Business Health: {health['overall_health_score']:.1f} ({health['health_status']})")
        
        # CFO metrics
        cfo_metrics = await tool.get_cfo_metrics()
        print(f"CFO Metrics: {cfo_metrics.get('priority_access', False)}")
    
    asyncio.run(main())
