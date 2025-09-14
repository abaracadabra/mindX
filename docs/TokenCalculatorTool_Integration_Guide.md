# TokenCalculatorTool Integration Guide

**Date**: 2025-01-27  
**Version**: 1.0.0  
**Status**: ✅ Active and Ready for Use

## 🎯 Overview

The **TokenCalculatorTool** is now available to all agents in the MindX ecosystem. This critical tool provides comprehensive token cost calculation, usage tracking, and cost optimization for all LLM operations.

## 🚀 Quick Start

### Basic Usage Pattern

```python
from tools.token_calculator_tool import TokenCalculatorTool
from agents.memory_agent import MemoryAgent
from utils.config import Config

# Initialize the tool
memory_agent = MemoryAgent()
config = Config()
token_calc = TokenCalculatorTool(memory_agent=memory_agent, config=config)

# Use the tool
result = await token_calc.execute(action="estimate_cost", text="Your prompt here", model="gemini-2.5-flash")
```

## 📋 Available Actions

### 1. **estimate_cost** - Pre-operation Cost Estimation
```python
result = await token_calc.execute(
    action="estimate_cost",
    text="Analyze this Python code for optimization opportunities",
    model="gemini-2.5-flash",
    operation_type="code_generation"  # Optional
)
# Returns: cost estimate with input/output tokens and USD cost
```

### 2. **track_usage** - Post-operation Usage Tracking
```python
result = await token_calc.execute(
    action="track_usage",
    agent_id="my_agent_id",
    operation="code_analysis",
    model="gemini-2.5-flash",
    input_tokens=150,
    output_tokens=300,
    cost_usd=0.00045
)
# Returns: tracking confirmation with daily spend and budget status
```

### 3. **check_budget** - Budget Monitoring
```python
result = await token_calc.execute(action="check_budget")
# Returns: daily/weekly/monthly spend, remaining budget, status
```

### 4. **optimize_prompt** - Cost Optimization
```python
result = await token_calc.execute(
    action="optimize_prompt",
    original_prompt="Your long prompt here...",
    max_tokens=500,
    cost_budget=0.001,
    target_model="gemini-2.5-flash"
)
# Returns: optimization strategies and potential savings
```

### 5. **get_usage_report** - Analytics and Reporting
```python
result = await token_calc.execute(
    action="get_usage_report",
    agent_id="specific_agent",  # Optional - filter by agent
    days_back=7  # Optional - default 7 days
)
# Returns: comprehensive usage statistics and optimization recommendations
```

### 6. **get_cost_breakdown** - Detailed Cost Analysis
```python
result = await token_calc.execute(action="get_cost_breakdown")
# Returns: breakdown by provider, agent, operation, model, and date
```

### 7. **update_pricing** - Pricing Management
```python
result = await token_calc.execute(
    action="update_pricing",
    pricing_updates={
        "google": {
            "gemini-3.0-flash": {
                "input": 0.25,
                "output": 1.0,
                "description": "Next-gen Gemini model"
            }
        }
    }
)
# Returns: confirmation of pricing updates
```

## 🔧 Integration Examples

### Example 1: BDI Agent with Cost Awareness
```python
class CostAwareBDIAgent(BaseBDIAgent):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.token_calc = TokenCalculatorTool(
            memory_agent=self.memory_agent,
            config=self.config
        )
    
    async def execute_with_cost_tracking(self, prompt, model="gemini-2.5-flash"):
        # 1. Estimate cost before operation
        cost_estimate = await self.token_calc.execute(
            action="estimate_cost",
            text=prompt,
            model=model
        )
        
        if cost_estimate[0]:
            estimated_cost = cost_estimate[1]["total_cost_usd"]
            logger.info(f"Estimated cost: ${estimated_cost:.6f}")
        
        # 2. Execute LLM operation (your existing code)
        response = await self.llm_handler.generate_text(prompt, model=model)
        
        # 3. Track actual usage
        await self.token_calc.execute(
            action="track_usage",
            agent_id=self.agent_id,
            operation="text_generation",
            model=model,
            input_tokens=len(prompt) // 4,  # Rough estimate
            output_tokens=len(response) // 4,
            cost_usd=estimated_cost  # Use actual cost if available
        )
        
        return response
```

### Example 2: Coordinator Agent Cost Monitoring
```python
class CostAwareCoordinator(CoordinatorAgent):
    async def monitor_system_costs(self):
        """Monitor costs across all agents."""
        
        # Check budget status
        budget_result = await self.token_calc.execute(action="check_budget")
        if budget_result[0]:
            budget = budget_result[1]
            if budget["status"] == "ALERT":
                await self.handle_budget_alert(budget)
        
        # Get usage report
        report_result = await self.token_calc.execute(
            action="get_usage_report",
            days_back=1  # Daily monitoring
        )
        
        if report_result[0]:
            report = report_result[1]
            await self.process_cost_report(report)
    
    async def optimize_agent_costs(self, agent_id):
        """Optimize costs for a specific agent."""
        
        # Get agent-specific usage
        usage_result = await self.token_calc.execute(
            action="get_usage_report",
            agent_id=agent_id,
            days_back=7
        )
        
        if usage_result[0]:
            usage = usage_result[1]
            recommendations = usage.get("optimization_recommendations", [])
            
            for rec in recommendations:
                if rec["type"] == "model_substitution":
                    await self.suggest_model_change(agent_id, rec)
```

### Example 3: Guardian Agent Budget Enforcement
```python
class CostGuardianAgent(GuardianAgent):
    async def validate_operation_cost(self, agent_id, prompt, model):
        """Validate operation doesn't exceed budget."""
        
        # Estimate cost
        estimate_result = await self.token_calc.execute(
            action="estimate_cost",
            text=prompt,
            model=model
        )
        
        if not estimate_result[0]:
            return False, "Cost estimation failed"
        
        estimated_cost = estimate_result[1]["total_cost_usd"]
        
        # Check budget
        budget_result = await self.token_calc.execute(action="check_budget")
        if budget_result[0]:
            budget = budget_result[1]
            remaining = budget["daily_remaining"]
            
            if estimated_cost > remaining:
                return False, f"Operation cost ${estimated_cost:.6f} exceeds remaining budget ${remaining:.2f}"
        
        return True, "Operation approved"
```

## ⚙️ Configuration

The tool uses several configuration sources:

1. **Main Config**: `config/llm_pricing_config.json` - Comprehensive pricing data
2. **Tool Config**: `data/config/token_calculator_config.json` - Tool-specific settings
3. **Registry**: `data/config/official_tools_registry.json` - Tool registration

### Key Configuration Options
```python
# Via Config object
config = Config()
config.set("token_calculator.daily_budget", 100.0)  # $100/day
config.set("token_calculator.alert_threshold", 0.85)  # 85% alert

# Via tool initialization
token_calc = TokenCalculatorTool(
    memory_agent=memory_agent,
    config=config
)
```

## 📊 Supported Providers & Models

The tool supports comprehensive pricing for:

- **Google**: Gemini 1.5/2.0/2.5 series (Flash, Pro, Lite variants)
- **OpenAI**: GPT-4o, GPT-3.5, O1/O3 series, Embeddings
- **Anthropic**: Claude 3/3.5/4 series (Haiku, Sonnet, Opus)
- **Groq**: Llama 3.x series, Mixtral models
- **Mistral**: Mistral Large, Medium, Small variants

## 🚨 Error Handling

Always check the return status:

```python
success, result = await token_calc.execute(action="estimate_cost", ...)

if success:
    # Use result data
    cost = result["total_cost_usd"]
else:
    # Handle error
    logger.error(f"Token calculation failed: {result}")
```

## 🎯 Best Practices

1. **Pre-estimate** costs for expensive operations
2. **Track actual usage** for all LLM calls
3. **Monitor budgets** regularly
4. **Use optimization** recommendations
5. **Handle errors** gracefully
6. **Configure alerts** for budget thresholds

## 📈 Advanced Features

- **Multi-model cost comparison**
- **Automatic prompt optimization**
- **Usage trend analysis**
- **Cost forecasting**
- **Budget alert systems**
- **Agent-specific cost tracking**

## 🔗 Registry Integration

The tool is registered in the official tools registry with:
- **ID**: `token_calculator`
- **Access**: Universal (`*` - all agents)
- **Module**: `tools.token_calculator_tool`
- **Class**: `TokenCalculatorTool`

## 🧪 Testing

Run the demo script to test functionality:

```bash
python3 scripts/demo_token_calculator.py
```

## 📞 Support

For issues or enhancements:
1. Check tool logs in `data/monitoring/`
2. Verify pricing configuration in `config/llm_pricing_config.json`
3. Review usage logs in `data/monitoring/token_usage.json`

---

**The TokenCalculatorTool is now ready for production use across the entire MindX ecosystem! 🚀** 