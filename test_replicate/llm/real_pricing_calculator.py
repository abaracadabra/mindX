"""
Real LLM Pricing Calculator with Actual Current Prices (January 2025)
Based on actual provider pricing pages and web search data
"""

import json
from dataclasses import dataclass
from typing import Dict, Optional, Union, Tuple
from enum import Enum

class Provider(Enum):
    OPENAI = "openai"
    GOOGLE = "google" 
    ANTHROPIC = "anthropic"
    GROQ = "groq"
    MISTRAL = "mistral"
    COHERE = "cohere"
    DEEPSEEK = "deepseek"

@dataclass
class TokenUsage:
    input_tokens: int
    output_tokens: int
    context_length: Optional[int] = None
    uses_cache: bool = False
    is_batch: bool = False

@dataclass
class CostBreakdown:
    input_cost: float
    output_cost: float
    total_cost: float
    provider: str
    model: str
    notes: str = ""

class RealLLMPricingCalculator:
    """
    Real-world LLM pricing calculator with actual current prices
    Updated January 2025 based on provider pricing pages
    """
    
    def __init__(self):
        self.pricing_data = self._load_pricing_data()
    
    def _load_pricing_data(self) -> Dict:
        """Load actual pricing data from providers"""
        return {
            "openai": {
                "o3": {"input": 1.00, "output": 4.00, "context": 200000},
                "o3-mini": {"input": 1.10, "output": 4.40, "context": 200000},
                "o1": {"input": 15.00, "output": 60.00, "context": 200000},
                "o1-mini": {"input": 1.10, "output": 4.40, "context": 128000},
                "gpt-4o": {"input": 2.50, "output": 10.00, "context": 128000},
                "gpt-4o-mini": {"input": 0.15, "output": 0.60, "context": 128000},
                "gpt-4.1": {"input": 2.00, "output": 8.00, "context": 1000000},
                "gpt-4.1-mini": {"input": 0.40, "output": 1.60, "context": 1000000},
                "gpt-4.1-nano": {"input": 0.10, "output": 0.40, "context": 1000000},
                "gpt-4-turbo": {"input": 10.00, "output": 30.00, "context": 128000},
                "gpt-3.5-turbo": {"input": 0.50, "output": 1.50, "context": 16000},
                "batch_discount": 0.50,  # 50% discount for batch API
            },
            "google": {
                "gemini-2.5-pro": {
                    "input": 1.25, "input_long": 2.50,
                    "output": 10.00, "output_long": 15.00,
                    "context": 200000, "long_threshold": 200000
                },
                "gemini-2.5-flash": {"input": 0.30, "output": 2.50, "context": 1000000},
                "gemini-2.5-flash-lite": {"input": 0.10, "output": 0.40, "context": 1000000},
                "gemini-2.0-flash": {"input": 0.10, "input_audio": 0.70, "output": 0.40, "context": 1000000},
                "gemini-2.0-flash-lite": {"input": 0.075, "output": 0.30, "context": 1000000},
                "gemini-1.5-pro": {
                    "input": 1.25, "input_long": 2.50,
                    "output": 5.00, "output_long": 10.00,
                    "context": 2000000, "long_threshold": 128000
                },
                "gemini-1.5-flash": {
                    "input": 0.075, "input_long": 0.15,
                    "output": 0.30, "output_long": 0.60,
                    "context": 1000000, "long_threshold": 128000
                },
                "gemini-1.5-flash-8b": {
                    "input": 0.0375, "input_long": 0.075,
                    "output": 0.15, "output_long": 0.30,
                    "context": 1000000, "long_threshold": 128000
                },
                "batch_discount": 0.50,
            },
            "anthropic": {
                "claude-4-opus": {"input": 15.00, "output": 75.00, "context": 200000},
                "claude-4-sonnet": {"input": 3.00, "output": 15.00, "context": 200000},
                "claude-3.7-sonnet": {"input": 3.00, "output": 15.00, "context": 200000},
                "claude-3.5-sonnet": {"input": 3.00, "output": 15.00, "context": 200000},
                "claude-3.5-haiku": {"input": 0.80, "output": 4.00, "context": 200000},
                "claude-3-opus": {"input": 15.00, "output": 75.00, "context": 200000},
                "claude-3-sonnet": {"input": 3.00, "output": 15.00, "context": 200000},
                "claude-3-haiku": {"input": 0.25, "output": 1.25, "context": 200000},
                "batch_discount": 0.50,
                "cache_write_multiplier": 1.25,  # 25% extra to write to cache
                "cache_read_multiplier": 0.10,   # 90% discount to read from cache
            },
            "groq": {
                "llama-3.3-70b": {"input": 0.59, "output": 0.79, "context": 128000},
                "llama-3.1-405b": {"input": 1.79, "output": 1.79, "context": 128000},
                "llama-3.1-70b": {"input": 0.59, "output": 0.79, "context": 128000},
                "llama-3.2-90b-vision": {"input": 0.90, "output": 0.90, "context": 128000},
                "mixtral-8x7b": {"input": 0.50, "output": 0.50, "context": 32000},
            },
            "mistral": {
                "mistral-large-2": {"input": 2.00, "output": 6.00, "context": 128000},
                "mistral-small-24.09": {"input": 0.20, "output": 0.60, "context": 128000},
                "mistral-nemo": {"input": 0.15, "output": 0.15, "context": 128000},
            },
            "cohere": {
                "command-r-plus": {"input": 3.00, "output": 15.00, "context": 128000},
                "command-r": {"input": 0.50, "output": 1.50, "context": 128000},
                "command": {"input": 10.00, "output": 20.00, "context": 4000},
            },
            "deepseek": {
                "deepseek-v3": {"input": 0.14, "output": 0.28, "context": 128000},
                "deepseek-r1": {"input": 0.55, "output": 2.19, "context": 128000},
            }
        }
    
    def calculate_cost(self, 
                      provider: Union[str, Provider], 
                      model: str, 
                      usage: TokenUsage) -> CostBreakdown:
        """
        Calculate cost for given provider, model and usage
        """
        if isinstance(provider, Provider):
            provider = provider.value
        
        if provider not in self.pricing_data:
            raise ValueError(f"Provider {provider} not supported")
        
        provider_data = self.pricing_data[provider]
        if model not in provider_data:
            raise ValueError(f"Model {model} not found for provider {provider}")
        
        model_data = provider_data[model]
        
        # Calculate base costs
        input_cost, output_cost, notes = self._calculate_base_costs(
            provider, model_data, usage
        )
        
        # Apply discounts
        if usage.is_batch and "batch_discount" in provider_data:
            discount = provider_data["batch_discount"]
            input_cost *= discount
            output_cost *= discount
            notes += f" | Batch discount: {(1-discount)*100:.0f}%"
        
        # Apply caching (Anthropic)
        if usage.uses_cache and provider == "anthropic":
            cache_read_multiplier = provider_data["cache_read_multiplier"]
            input_cost *= cache_read_multiplier
            notes += f" | Cache read discount: {(1-cache_read_multiplier)*100:.0f}%"
        
        total_cost = input_cost + output_cost
        
        return CostBreakdown(
            input_cost=input_cost,
            output_cost=output_cost,
            total_cost=total_cost,
            provider=provider,
            model=model,
            notes=notes
        )
    
    def _calculate_base_costs(self, provider: str, model_data: Dict, usage: TokenUsage) -> Tuple[float, float, str]:
        """Calculate base input and output costs"""
        notes = ""
        
        # Handle Google's long context pricing
        if provider == "google" and "long_threshold" in model_data:
            threshold = model_data["long_threshold"]
            if usage.context_length and usage.context_length > threshold:
                input_price = model_data.get("input_long", model_data["input"])
                output_price = model_data.get("output_long", model_data["output"])
                notes += f" | Long context pricing (>{threshold:,} tokens)"
            else:
                input_price = model_data["input"]
                output_price = model_data["output"]
        else:
            input_price = model_data["input"]
            output_price = model_data["output"]
        
        input_cost = (usage.input_tokens / 1_000_000) * input_price
        output_cost = (usage.output_tokens / 1_000_000) * output_price
        
        return input_cost, output_cost, notes
    
    def compare_providers(self, model_mapping: Dict[str, str], usage: TokenUsage) -> Dict[str, CostBreakdown]:
        """
        Compare costs across multiple providers for equivalent models
        model_mapping: {"provider": "model_name"}
        """
        results = {}
        
        for provider, model in model_mapping.items():
            try:
                cost = self.calculate_cost(provider, model, usage)
                results[f"{provider}:{model}"] = cost
            except ValueError as e:
                results[f"{provider}:{model}"] = f"Error: {str(e)}"
        
        return results
    
    def get_cheapest_option(self, model_mapping: Dict[str, str], usage: TokenUsage) -> Tuple[str, CostBreakdown]:
        """Find the cheapest option among given models"""
        comparisons = self.compare_providers(model_mapping, usage)
        
        valid_options = {k: v for k, v in comparisons.items() if isinstance(v, CostBreakdown)}
        
        if not valid_options:
            raise ValueError("No valid options found")
        
        cheapest = min(valid_options.items(), key=lambda x: x[1].total_cost)
        return cheapest
    
    def estimate_monthly_cost(self, 
                            provider: str, 
                            model: str, 
                            daily_requests: int,
                            avg_input_tokens: int,
                            avg_output_tokens: int,
                            context_length: Optional[int] = None,
                            batch_percentage: float = 0.0,
                            cache_percentage: float = 0.0) -> Dict:
        """
        Estimate monthly costs with usage patterns
        """
        # Calculate base usage per request
        base_usage = TokenUsage(
            input_tokens=avg_input_tokens,
            output_tokens=avg_output_tokens,
            context_length=context_length,
            uses_cache=False,
            is_batch=False
        )
        
        base_cost = self.calculate_cost(provider, model, base_usage)
        
        # Calculate costs for different usage patterns
        regular_requests = int(daily_requests * (1 - batch_percentage - cache_percentage))
        batch_requests = int(daily_requests * batch_percentage)
        cached_requests = int(daily_requests * cache_percentage)
        
        monthly_regular = regular_requests * 30 * base_cost.total_cost
        
        # Batch cost
        batch_usage = TokenUsage(
            input_tokens=avg_input_tokens,
            output_tokens=avg_output_tokens,
            context_length=context_length,
            uses_cache=False,
            is_batch=True
        )
        batch_cost = self.calculate_cost(provider, model, batch_usage)
        monthly_batch = batch_requests * 30 * batch_cost.total_cost
        
        # Cached cost (if supported)
        monthly_cached = 0
        if cache_percentage > 0 and provider == "anthropic":
            cached_usage = TokenUsage(
                input_tokens=avg_input_tokens,
                output_tokens=avg_output_tokens,
                context_length=context_length,
                uses_cache=True,
                is_batch=False
            )
            cached_cost = self.calculate_cost(provider, model, cached_usage)
            monthly_cached = cached_requests * 30 * cached_cost.total_cost
        
        total_monthly = monthly_regular + monthly_batch + monthly_cached
        
        return {
            "provider": provider,
            "model": model,
            "monthly_cost": total_monthly,
            "breakdown": {
                "regular_requests": {"count": regular_requests * 30, "cost": monthly_regular},
                "batch_requests": {"count": batch_requests * 30, "cost": monthly_batch},
                "cached_requests": {"count": cached_requests * 30, "cost": monthly_cached}
            },
            "per_request_costs": {
                "regular": base_cost.total_cost,
                "batch": batch_cost.total_cost,
                "cached": cached_cost.total_cost if cache_percentage > 0 and provider == "anthropic" else 0
            }
        }
    
    def get_supported_models(self, provider: Optional[str] = None) -> Dict:
        """Get all supported models, optionally filtered by provider"""
        if provider:
            if provider not in self.pricing_data:
                return {}
            return {provider: list(self.pricing_data[provider].keys())}
        
        return {
            provider: [model for model in models.keys() if not model.endswith("_discount") and not model.endswith("_multiplier")]
            for provider, models in self.pricing_data.items()
        }
    
    def get_model_info(self, provider: str, model: str) -> Dict:
        """Get detailed information about a specific model"""
        if provider not in self.pricing_data or model not in self.pricing_data[provider]:
            return {}
        
        model_data = self.pricing_data[provider][model].copy()
        
        # Add derived information
        model_data["provider"] = provider
        model_data["model"] = model
        model_data["cost_per_1k_input"] = model_data["input"] / 1000
        model_data["cost_per_1k_output"] = model_data["output"] / 1000
        
        # Calculate example costs
        example_usage = TokenUsage(input_tokens=1000, output_tokens=1000)
        example_cost = self.calculate_cost(provider, model, example_usage)
        model_data["example_cost_1k_tokens"] = example_cost.total_cost
        
        return model_data


def demo_pricing_calculator():
    """Demonstrate the real pricing calculator"""
    calculator = RealLLMPricingCalculator()
    
    print("🎯 Real LLM Pricing Calculator Demo")
    print("=" * 50)
    
    # Example usage scenario
    usage = TokenUsage(
        input_tokens=10000,  # 10K input tokens (~7500 words)
        output_tokens=2000,  # 2K output tokens (~1500 words)
        context_length=50000,
        uses_cache=False,
        is_batch=False
    )
    
    print(f"\n📊 Usage Scenario:")
    print(f"  Input: {usage.input_tokens:,} tokens (~{usage.input_tokens//1.33:.0f} words)")
    print(f"  Output: {usage.output_tokens:,} tokens (~{usage.output_tokens//1.33:.0f} words)")
    print(f"  Context: {usage.context_length:,} tokens")
    
    # Compare flagship models
    flagship_models = {
        "openai": "gpt-4o",
        "google": "gemini-2.5-pro", 
        "anthropic": "claude-4-sonnet",
        "groq": "llama-3.1-70b"
    }
    
    print(f"\n💰 Cost Comparison (Flagship Models):")
    comparisons = calculator.compare_providers(flagship_models, usage)
    
    for model_key, result in comparisons.items():
        if isinstance(result, CostBreakdown):
            print(f"  {model_key:25} ${result.total_cost:.4f} (In: ${result.input_cost:.4f}, Out: ${result.output_cost:.4f}){result.notes}")
        else:
            print(f"  {model_key:25} {result}")
    
    # Find cheapest option
    cheapest_key, cheapest_cost = calculator.get_cheapest_option(flagship_models, usage)
    print(f"\n🏆 Cheapest Option: {cheapest_key} - ${cheapest_cost.total_cost:.4f}")
    
    # Monthly cost estimation
    print(f"\n📅 Monthly Cost Estimation (1000 requests/day):")
    monthly_est = calculator.estimate_monthly_cost(
        provider="openai",
        model="gpt-4o",
        daily_requests=1000,
        avg_input_tokens=usage.input_tokens,
        avg_output_tokens=usage.output_tokens,
        context_length=usage.context_length,
        batch_percentage=0.3,  # 30% batch processing
        cache_percentage=0.0   # No caching for OpenAI
    )
    
    print(f"  Provider: {monthly_est['provider']} {monthly_est['model']}")
    print(f"  Total Monthly Cost: ${monthly_est['monthly_cost']:.2f}")
    print(f"  Regular requests: {monthly_est['breakdown']['regular_requests']['count']:,} @ ${monthly_est['per_request_costs']['regular']:.4f} = ${monthly_est['breakdown']['regular_requests']['cost']:.2f}")
    print(f"  Batch requests: {monthly_est['breakdown']['batch_requests']['count']:,} @ ${monthly_est['per_request_costs']['batch']:.4f} = ${monthly_est['breakdown']['batch_requests']['cost']:.2f}")
    
    # Show supported models
    print(f"\n📋 Available Models by Provider:")
    models = calculator.get_supported_models()
    for provider, model_list in models.items():
        print(f"  {provider}: {len(model_list)} models")
        for model in model_list[:3]:  # Show first 3
            info = calculator.get_model_info(provider, model)
            print(f"    - {model}: ${info.get('input', 0):.2f}/${info.get('output', 0):.2f} per 1M tokens")
        if len(model_list) > 3:
            print(f"    ... and {len(model_list) - 3} more")


if __name__ == "__main__":
    demo_pricing_calculator() 