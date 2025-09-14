import asyncio
import json
import logging
from typing import Dict, Any, Optional, TypedDict

# --- Configuration ---
# The command used to invoke the Gemini CLI. Can be an absolute path if needed.
GEMINI_COMMAND = "gemini"
# Default timeout in seconds to prevent agents from hanging on a stalled process.
DEFAULT_TIMEOUT_SECONDS = 120

# --- Module-level logger ---
# It's best practice to get the logger at the module level.
# The final application's logging config will determine its output level and format.
logger = logging.getLogger(__name__)


# --- Data Structure for Responses ---
class CLIResponse(TypedDict):
    """
    A structured dictionary for the output of the Gemini CLI invocation.
    This provides a consistent and predictable return format for agent interaction.

    Attributes:
        success: Boolean indicating if the CLI call succeeded AND returned valid JSON.
        data: The JSON-parsed dictionary from the CLI's stdout, if successful.
        error: A string describing the precise error, if any occurred.
        raw_output: The raw, decoded stdout from the CLI. Always populated on success,
                    and may be populated on failure for debugging purposes.
        exit_code: The integer exit code of the subprocess. 0 typically means success.
    """
    success: bool
    data: Optional[Dict[str, Any]]
    error: Optional[str]
    raw_output: Optional[str]
    exit_code: Optional[int]


async def invoke_gemini_cli(prompt: str, timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS) -> CLIResponse:
    """
    Invokes the Gemini CLI as a non-blocking subprocess to perform inference.

    This function is the core integration point for using the user-authenticated
    Gemini CLI as a cost-free inference engine. It is hardened with timeout
    and error handling to be safely used within an agentic framework like MindX.

    The "contract" for using this function is that the prompt should explicitly
    instruct the Gemini model to return its response in a valid JSON format.
    This function's success state depends on its ability to parse this JSON.

    Args:
        prompt: The full prompt string to be sent to the Gemini CLI.
        timeout_seconds: The maximum time to wait for the CLI to complete.

    Returns:
        A CLIResponse dictionary containing the structured outcome of the invocation.
    """
    command = [GEMINI_COMMAND, prompt]
    prompt_prefix = prompt[:150] + "..." if len(prompt) > 150 else prompt

    try:
        process = await asyncio.create_subprocess_exec(
            *command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

        # Wait for the subprocess to finish with a crucial timeout
        stdout, stderr = await asyncio.wait_for(
            process.communicate(),
            timeout=timeout_seconds
        )

        stdout_str = stdout.decode('utf-8').strip()
        stderr_str = stderr.decode('utf-8').strip()
        exit_code = process.returncode

        if exit_code != 0:
            error_message = (
                f"Gemini CLI process failed with exit code {exit_code}. "
                f"Stderr: '{stderr_str}'"
            )
            logger.error(f"{error_message} | Prompt Prefix: '{prompt_prefix}'")
            return CLIResponse(
                success=False, data=None, error=error_message,
                raw_output=stdout_str, exit_code=exit_code
            )

        try:
            parsed_data = json.loads(stdout_str)
            logger.info(f"Successfully invoked Gemini CLI and parsed JSON response for prompt prefix: '{prompt_prefix}'")
            return CLIResponse(
                success=True, data=parsed_data, error=None,
                raw_output=stdout_str, exit_code=exit_code
            )
        except json.JSONDecodeError:
            error_message = "Contract Violation: Failed to decode JSON from Gemini CLI response."
            logger.warning(f"{error_message} | Raw Output: '{stdout_str}'")
            return CLIResponse(
                success=False, data=None, error=error_message,
                raw_output=stdout_str, exit_code=exit_code
            )

    except FileNotFoundError:
        error_message = f"Critical Error: '{GEMINI_COMMAND}' command not found. Ensure the Gemini CLI is installed and in the system's PATH."
        logger.critical(error_message)
        return CLIResponse(success=False, data=None, error=error_message, raw_output=None, exit_code=None)

    except asyncio.TimeoutError:
        # Best practice: try to kill the lingering process if it times out.
        if 'process' in locals() and process.returncode is None:
            try:
                process.kill()
                await process.wait()
            except ProcessLookupError:
                pass # Process already finished
        error_message = f"Gemini CLI invocation timed out after {timeout_seconds} seconds."
        logger.error(f"{error_message} | Prompt Prefix: '{prompt_prefix}'")
        return CLIResponse(success=False, data=None, error=error_message, raw_output=None, exit_code=None)

    except Exception as e:
        error_message = f"An unexpected exception occurred while invoking Gemini CLI: {e}"
        logger.critical(error_message, exc_info=True)
        return CLIResponse(success=False, data=None, error=error_message, raw_output=None, exit_code=None)


# --- Standalone Self-Test Suite ---
async def _test_successful_json_parsing():
    """Tests the ideal case: CLI runs and returns valid JSON."""
    print("\n--- [1/3] Testing: Successful JSON Parsing ---")
    prompt = (
        "Analyze the user's request: 'What is the capital of France?'. "
        "Your final output must be a single, valid JSON object and nothing else. "
        "The JSON object must contain two keys: 'capital' and 'country'."
    )
    response = await invoke_gemini_cli(prompt)
    print(f"Response: {json.dumps(response, indent=2)}")
    assert response["success"] is True
    assert response["data"] is not None
    assert response["data"].get("capital") == "Paris"
    print("✅ PASSED")


async def _test_non_json_output():
    """Tests the contract violation case: CLI runs but returns plain text."""
    print("\n--- [2/3] Testing: Non-JSON Output Handling ---")
    prompt = "Tell me a very short, one-sentence poem about the moon."
    response = await invoke_gemini_cli(prompt)
    print(f"Response: {json.dumps(response, indent=2)}")
    assert response["success"] is False
    assert response["error"] and "Failed to decode JSON" in response["error"]
    assert response["raw_output"] is not None and len(response["raw_output"]) > 0
    print("✅ PASSED")


async def _test_command_not_found():
    """Tests the environment failure case: the gemini command does not exist."""
    print("\n--- [3/3] Testing: Command Not Found Handling ---")
    global GEMINI_COMMAND
    original_command = GEMINI_COMMAND
    GEMINI_COMMAND = "gemini-command-that-does-not-exist"  # Simulate missing command
    prompt = "This prompt will not be sent."
    response = await invoke_gemini_cli(prompt)
    print(f"Response: {json.dumps(response, indent=2)}")
    assert response["success"] is False
    assert response["error"] and "command not found" in response["error"]
    GEMINI_COMMAND = original_command  # Restore original command
    print("✅ PASSED")


if __name__ == "__main__":
    # To run this test suite directly: `python path/to/cli_subprocess.py`
    # You must have the Gemini CLI installed and authenticated for tests to pass.
    # Note: If tests fail, check if you are logged in: `gemini auth login`
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s'
    )

    async def run_all_tests():
        try:
            await _test_successful_json_parsing()
        except Exception as e:
            print(f"❌ FAILED: _test_successful_json_parsing | Error: {e}")
            print("Note: This test requires internet access and a valid Gemini CLI login.")

        try:
            await _test_non_json_output()
        except Exception as e:
            print(f"❌ FAILED: _test_non_json_output | Error: {e}")
            print("Note: This test requires internet access and a valid Gemini CLI login.")

        try:
            await _test_command_not_found()
        except Exception as e:
            print(f"❌ FAILED: _test_command_not_found | Error: {e}")

    asyncio.run(run_all_tests())
