# tools/web_search_tool.py
"""
WebSearchTool for mindX agents.
Utilizes Google Custom Search JSON API to perform web searches.
"""
import os
# import logging # Use get_logger
import json
import asyncio
from typing import Dict, Any, List, Optional, Coroutine

# httpx is an async-capable HTTP client
try:
    import httpx # Requires: pip install httpx
except ImportError: # pragma: no cover
    httpx = None
    print("CRITICAL: httpx library not found for WebSearchTool. Please 'pip install httpx'.", file=sys.stderr)


from utils.config import Config
from utils.logging_config import get_logger
from core.bdi_agent import BaseTool # Import BaseTool from the core package

logger = get_logger(__name__)

class WebSearchTool(BaseTool): # Inherit from BaseTool
    """
    Tool for searching the web using Google Custom Search JSON API.
    Requires GOOGLE_SEARCH_API_KEY and GOOGLE_SEARCH_ENGINE_ID to be configured.
    Gracefully falls back to mock results if keys are missing.
    """

    def __init__(self,
                 config: Optional[Config] = None,
                 api_key_override: Optional[str] = None,
                 search_engine_id_override: Optional[str] = None,
                 bdi_agent_ref: Optional[Any] = None, # From BaseTool
                 llm_handler: Optional[Any] = None): # From BaseTool, if needed for mocks
        """
        Initialize the web search tool.
        """
        super().__init__(config=config, llm_handler=llm_handler, bdi_agent_ref=bdi_agent_ref)
        # self.config is now set by BaseTool's __init__
        # self.logger is now set by BaseTool's __init__ to f"tool.WebSearchTool"

        self.api_key: Optional[str] = api_key_override or \
                                     self.config.get("tools.web_search.google_api_key",
                                                     os.environ.get("GOOGLE_SEARCH_API_KEY"))
        self.search_engine_id: Optional[str] = search_engine_id_override or \
                                               self.config.get("tools.web_search.google_search_engine_id",
                                                               os.environ.get("GOOGLE_SEARCH_ENGINE_ID"))

        self.http_client: Optional[httpx.AsyncClient] = None
        if httpx:
            self.http_client = httpx.AsyncClient(
                timeout=self.config.get("tools.web_search.timeout_seconds", 20.0),
                follow_redirects=True
            )
        else: # pragma: no cover
            self.logger.error("httpx library is not installed. Real web searches will fail. Only mock results available.")


        if not self.api_key or not self.search_engine_id: # pragma: no cover
            self.logger.warning(
                f"Google Search API key or Search Engine ID not configured. "
                "Web search will use mock results."
            )
        self.logger.info(f"WebSearchTool initialized. API Key Configured: {bool(self.api_key)}, SE ID Configured: {bool(self.search_engine_id)}, httpx available: {bool(httpx)}")

    async def execute(self, query: str, num_results: int = 5, **kwargs) -> str: # Added **kwargs for BaseTool compatibility
        """
        Executes a web search using Google Custom Search API.
        """
        tool_name = self.__class__.__name__ # Use class name for tool name
        self.logger.info(f"Executing web search. Query: '{query}', NumResults: {num_results}")

        if not query or not isinstance(query, str): # pragma: no cover
            self.logger.warning(f"Invalid query provided: {query}")
            return "Error: Invalid or empty query provided for web search."

        if not self.api_key or not self.search_engine_id or not self.http_client: # pragma: no cover
            self.logger.warning(f"API key, Search Engine ID, or HTTP client missing. Generating mock results.")
            return self._generate_mock_results(query, num_results)

        actual_num_results = min(max(1, num_results), 10)

        search_url = "https://www.googleapis.com/customsearch/v1"
        params = {
            "key": self.api_key,
            "cx": self.search_engine_id,
            "q": query,
            "num": actual_num_results
        }

        try:
            response = await self.http_client.get(search_url, params=params)
            response.raise_for_status()
            results_json = response.json()
            return self._format_google_search_results(results_json, query)

        except httpx.TimeoutException as e_timeout: # pragma: no cover
            self.logger.error(f"Web search request timed out for query '{query}': {e_timeout}")
            return f"Error: Web search request timed out. ({e_timeout})"
        except httpx.HTTPStatusError as e_http: # pragma: no cover
            error_detail = "Unknown API error."
            try: error_detail = e_http.response.json().get("error", {}).get("message", str(e_http))
            except: pass
            self.logger.error(f"HTTP error during web search for '{query}': {e_http.response.status_code} - {error_detail}", exc_info=True)
            return f"Error: Web search API request failed with status {e_http.response.status_code}. Detail: {error_detail}"
        except Exception as e_general: # pragma: no cover
            self.logger.error(f"Unexpected error during web search for '{query}': {e_general}", exc_info=True)
            return f"Error: Unexpected error during web search - {type(e_general).__name__}: {e_general}"

    def _format_google_search_results(self, results_json: Dict[str, Any], query: str) -> str: # pragma: no cover
        original_query = query
        search_info = results_json.get("searchInformation", {})
        formatted_time = search_info.get("formattedSearchTime", "N/A")
        total_results = search_info.get("formattedTotalResults", "N/A")
        output_parts = [f"Search Results for: \"{original_query}\" (Time: {formatted_time}s, Approx. Total: {total_results})\n"]
        items = results_json.get("items")
        if not items:
            output_parts.append("\nNo results found for this query.")
            return "".join(output_parts)
        for i, item in enumerate(items, 1):
            title = item.get("title", "No Title")
            link = item.get("link", "No Link")
            snippet = item.get("snippet", "No Snippet").replace("\n", " ").strip()
            output_parts.append(f"\nResult {i}:")
            output_parts.append(f"  Title: {title}")
            output_parts.append(f"  Link: {link}")
            output_parts.append(f"  Snippet: {snippet}")
        return "\n".join(output_parts)

    def _generate_mock_results(self, query: str, num_results: int) -> str: # pragma: no cover
        self.logger.info(f"Generating mock search results for query '{query}'.")
        output_parts = [f"Mock Search Results for: \"{query}\" (API Key/ID Not Configured or httpx missing)\n"]
        for i in range(1, num_results + 1):
            output_parts.append(f"\nResult {i}:")
            output_parts.append(f"  Title: Mock Result {i} - {query[:50]}")
            output_parts.append(f"  Link: https://example.com/mocksearch?q={query.replace(' ','+')}&result={i}")
            output_parts.append(f"  Snippet: This is mock search result number {i} for the query '{query}'. It demonstrates the expected format of real search results, which would contain relevant information from the web.")
        return "\n".join(output_parts)

    async def shutdown(self): # pragma: no cover
        if self.http_client and not self.http_client.is_closed:
            await self.http_client.aclose()
            self.logger.info(f"WebSearchTool's HTTP client closed.")

# Example usage section can be kept for direct testing of this file
async def _web_search_tool_example(): # pragma: no cover
    # Ensure .env is loaded if running this file directly for testing API keys
    # PROJECT_ROOT here would be tools/, so .env is ../.env
    env_path = Path(__file__).resolve().parent.parent / ".env"
    if env_path.exists():
        from dotenv import load_dotenv
        print(f"Loading .env from {env_path}")
        load_dotenv(dotenv_path=env_path, override=True)
    else:
        print(f"Example: .env not found at {env_path}", file=sys.stderr)

    # Need to init Config for the tool to use it
    config = Config()
    search_tool = WebSearchTool(config=config) # bdi_agent_ref is optional

    query1 = "latest advancements in Augmentic Intelligence"
    print(f"\n--- Searching for: '{query1}' ---")
    results1 = await search_tool.execute(query=query1, num_results=3)
    print(results1)
    await search_tool.shutdown()

if __name__ == "__main__": # pragma: no cover
    # Setup basic logging if run standalone
    logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(name)s - %(module)s.%(funcName)s:%(lineno)d - %(message)s')
    if httpx is None:
        logger.critical("httpx is not installed. WebSearchTool example cannot run effectively.")
    else:
        asyncio.run(_web_search_tool_example())
