"""
API routes for inference discovery and provider management.
Exposes InferenceDiscovery status, probing, and fallback decision endpoints.
"""

from fastapi import APIRouter

from llm.inference_discovery import InferenceDiscovery

router = APIRouter(prefix="/inference", tags=["inference-discovery"])


@router.get("/status")
async def inference_status():
    """Current inference source status — which providers are available."""
    discovery = await InferenceDiscovery.get_instance()
    return discovery.status_summary()


@router.post("/probe")
async def probe_all():
    """Force probe all inference sources and return results."""
    discovery = await InferenceDiscovery.get_instance()
    results = await discovery.probe_all()
    return {
        "probed": len(results),
        "results": {k: v.value for k, v in results.items()},
        "summary": discovery.status_summary(),
    }


@router.get("/best")
async def get_best_provider():
    """Get the best currently available inference provider."""
    discovery = await InferenceDiscovery.get_instance()
    result = await discovery.get_best_provider()
    if result:
        name, src = result
        return {
            "provider": name,
            "type": src.provider_type,
            "base_url": src.base_url,
            "models": src.models[:5],
            "score": round(src.score, 3),
            "latency_ms": round(src.latency_ms, 1),
        }
    return {"provider": None, "message": "No inference sources available"}


@router.post("/discover")
async def discover_network(subnet: str = "10.0.0"):
    """Scan local network for Ollama/vLLM instances."""
    discovery = await InferenceDiscovery.get_instance()
    found = await discovery.discover_network(subnet=subnet)
    return {
        "discovered": len(found),
        "sources": [
            {
                "name": s.name,
                "type": s.provider_type,
                "url": s.base_url,
                "models": s.models,
            }
            for s in found
        ],
    }


@router.post("/self-improve")
async def self_improve():
    """Run self-improvement evaluation on inference sources."""
    discovery = await InferenceDiscovery.get_instance()
    return await discovery.self_improve()


@router.get("/improvement-history")
async def improvement_history():
    """Get recent self-improvement evaluation history."""
    discovery = await InferenceDiscovery.get_instance()
    history = discovery.get_improvement_history()
    return {"entries": len(history), "history": history[-10:]}


@router.post("/fallback-decide")
async def fallback_decide(context: str, options: list[str], criteria: str = ""):
    """
    Make a rule-based decision without LLM inference.
    Used when all inference sources are down.
    """
    discovery = await InferenceDiscovery.get_instance()
    return discovery.fallback_decide(context, options, criteria)
