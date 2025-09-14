# Gemini LLM Handler & Discovery Tool

**File:** `mindx/llm/gemini_handler.py` <br />
**Component Type:** Cognitive Resource Handler & System Utility

---

###  Introduction

The `gemini_handler.py` module is a critical component of the MindX cognitive architecture, serving a sophisticated dual purpose.

  **As a Runtime Handler (`GeminiHandler` class):** When imported by the `ModelRegistry`, it functions as a standardized, resilient interface to the Google Gemini family of Large Language Models. It translates abstract requests from the agent's core logic into concrete, rate-limited, and error-handled API calls.

  **As a Discovery Utility (Script Mode):** When executed directly as a script, it transforms into a powerful tool for **active introspection**. It queries the live Gemini API, discovers all available models, probes their capabilities, and automatically generates a detailed `gemini.yaml` configuration file. This allows the MindX system to dynamically update its own knowledge about its available cognitive resources.

This module embodies the core MindX philosophies of **Resilience** (through robust error handling and rate limiting) and **Augmentic Intelligence** (automating the tedious task of discovery while relying on human expertise for high-level knowledge like pricing).

---

###  Explanation of Core Functionality

#### **The `GeminiHandler` Class (Runtime Operation)**

When the MindX system is running, the `ModelRegistry` instantiates the `GeminiHandler` class. Its job is to be a reliable conduit to the Gemini API.

*   **Standardized Interface:** It implements the `LLMHandlerInterface`, ensuring it has a predictable `generate_text` method that the rest of the system can call without needing to know the specific details of the Gemini API.
*   **Resilience through Rate Limiting:** The handler is initialized with our custom `RateLimiter` instance. Before making any API call, it `await`s this limiter, which automatically pauses execution if the request rate exceeds the configured limits (e.g., 15 requests/minute). This prevents the agent from crashing due to `429 Too Many Requests` errors.
*   **Robust Error Handling:** The `generate_text` method is wrapped in a comprehensive `try...except` block. It gracefully catches specific API errors (like `ResourceExhausted` or `PermissionDenied`) and returns a structured JSON error object (e.g., `{"error": "ResourceExhausted", ...}`). This prevents the agent's cognitive loop from crashing and allows the `AGInt` to understand *why* a call failed and adapt its strategy (e.g., by trying a fallback model).

#### **The `GeminiModelDiscoverer` (Script-Mode Operation)**

When you run `python -m mindx.llm.gemini_handler`, you activate the `GeminiModelDiscoverer` tool. This is the "self-awareness" function for the Gemini provider.

*   **Live Discovery:** It makes an initial API call to `genai.list_models` to get a raw list of all models associated with the API key.
*   **Intelligent Filtering:** It performs a crucial filtering step, discarding models that are unsuitable for text-generation tasks (like vision, embedding, or TTS models) based on their API metadata. This focuses the subsequent, more expensive, probing step on relevant models only.
*   **Capability Probing:** For each relevant model, it sends a carefully crafted prompt asking the model to self-evaluate its own skills across a standardized set of `TaskType`s (e.g., `reasoning`, `code_generation`). This automates the tedious process of benchmarking.
*   **Graceful Degradation:** If a model probe fails (due to a rate limit, a deprecation error, or the model not understanding the request), the script logs the error and inserts a set of reasonable `DEFAULT_CAPABILITIES` for that model. The mission to generate a complete configuration file always succeeds.
*   **Knowledge Integration:** It combines the live API data (token limits), the self-assessed capabilities, and a hardcoded dictionary of known pricing data (`KNOWN_GEMINI_COSTS`) into a single, comprehensive profile for each model.

---

###  Technical Details

*   **Dual-Purpose Execution:** The `if __name__ == "__main__"` block at the end of the file is the standard Python mechanism that allows the file to have two distinct behaviors: one when imported as a module, and another when executed as a standalone script.
*   **Dependencies:**
    *   **Runtime:** `google-generativeai`, `utils`, `llm.llm_interface`, `llm.rate_limiter`.
    *   **Script Mode:** Also requires `PyYAML` for generating the `.yaml` configuration file.
*   **Configuration:**
    *   The `GeminiHandler` is configured at runtime by the `ModelRegistry` and the main `Config` object.
    *   The `GeminiModelDiscoverer` is configured via command-line arguments and the `GEMINI_API_KEY` environment variable.

---

# Prerequisites:
Your GEMINI_API_KEY must be set in your .env file or as a system environment variable<br />
Required packages must be installed: pip install google-generativeai pyyaml python-dotenv<br /><br />

The gemini_handler.py module is a prime example of the MindX design philosophy. It provides a resilient, abstracted interface for a core cognitive resource while also embedding the tools for the system to perform its own introspection and self-configuration. By consolidating the runtime handler and the discovery script, we create a cohesive, maintainable, and highly capable component that is essential for the mindX journey towards operational Augmentic Intelligence<br /><br />

###  Usage

#### **As a Runtime Component**

This is handled automatically by the `ModelRegistry`. No direct interaction is typically needed. The registry creates the handler, and agents like `AGInt` use the registry to access it.

#### **As a Standalone Discovery Tool**

This script should be run whenever you want to update the system's knowledge of available Gemini models, for example, after Google announces new models or if you change your API key to one with a different access tier.

**Command:**
From the project root (`mindX/`), run the following command in your terminal:

```bash
python3 -m mindx.llm.gemini_handler --update-config
```

