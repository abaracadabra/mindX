# mindx/agents/simple_coder_agent.py (Version 7.0 - Augmentic Intelligence Enhanced)
"""
SimpleCoderAgent: The BDI Agent's Intelligent Right Hand

Enhanced Philosophy: "Intelligent coding assistance with augmentic intelligence."
This agent provides advanced code analysis, generation, and execution capabilities
with multi-model intelligence and seamless integration with the MindX ecosystem.
"""
import asyncio
import json
import shlex
import sys
import os
import re
import subprocess
import time
from pathlib import Path
from typing import Dict, Any, Optional, List, Callable, Awaitable, TypeAlias, Tuple

from core.bdi_agent import BaseTool
from agents.memory_agent import MemoryAgent
from utils.config import Config, PROJECT_ROOT
from utils.logging_config import get_logger
from llm.llm_interface import LLMHandlerInterface

if sys.version_info >= (3, 10):
    from typing import TypeAlias
else:
    from typing_extensions import TypeAlias

NativeHandler: TypeAlias = Callable[..., Awaitable[Dict[str, Any]]]

class SimpleCoderAgent(BaseTool):
    """
    Enhanced coding agent providing intelligent assistance to the BDI agent.
    
    Features:
    - Advanced code analysis and generation
    - Multi-model intelligence for different coding tasks
    - Secure sandboxed execution environment
    - Memory integration for learning and improvement
    - Context-aware suggestions and optimizations
    """

    def __init__(self, 
                 memory_agent: Optional[MemoryAgent] = None,
                 config: Optional[Config] = None, 
                 llm_handler: Optional[LLMHandlerInterface] = None, 
                 **kwargs):
        super().__init__(config=config, llm_handler=llm_handler, **kwargs)
        
        self.memory_agent = memory_agent or MemoryAgent()
        self.agent_id = "simple_coder_agent"
        self.log_prefix = "SimpleCoderAgent:"
        
        # Configuration and initialization
        self.config_data: Dict[str, Any] = {}
        self.command_timeout: int = 60
        self._load_command_config()

        # Sandbox environment
        self.sandbox_root: Path = self._initialize_sandbox()
        self.current_working_directory: Path = self.sandbox_root
        self.active_venv_bin_path: Optional[Path] = None

        # Enhanced capabilities
        self.coding_history: List[Dict[str, Any]] = []
        self.project_context: Dict[str, Any] = {}
        self.code_patterns: Dict[str, Any] = {}
        
        # Native command handlers
        self.native_handlers: Dict[str, NativeHandler] = {
            # File system operations
            "list_files": self._list_directory,
            "change_directory": self._change_directory,
            "read_file": self._read_file,
            "write_file": self._write_file,
            "create_directory": self._create_directory,
            "delete_file": self._delete_file,
            
            # Execution environment
            "run_shell": self._run_shell_command,
            "create_venv": self._create_venv,
            "activate_venv": self._activate_venv,
            "deactivate_venv": self._deactivate_venv,
            
            # Enhanced coding capabilities
            "analyze_code": self._analyze_code,
            "generate_code": self._generate_code,
            "optimize_code": self._optimize_code,
            "debug_code": self._debug_code,
            "test_code": self._test_code,
            "refactor_code": self._refactor_code,
            "explain_code": self._explain_code,
            
            # Project management
            "analyze_project": self._analyze_project,
            "suggest_improvements": self._suggest_improvements,
            "create_documentation": self._create_documentation,
            
            # Learning and adaptation
            "learn_from_execution": self._learn_from_execution,
            "get_coding_suggestions": self._get_coding_suggestions,
        }
        
        self.logger.info(f"{self.log_prefix} Enhanced coding agent initialized. Sandbox: {self.sandbox_root}")

    def _load_command_config(self):
        """Load configuration with enhanced defaults."""
        default_path = PROJECT_ROOT / "data" / "config" / "simple_coder_agent.json"
        config_path = Path(self.config.get("agents.simple_coder.config_path", default_path))
        
        # Default enhanced configuration
        default_config = {
            "command_timeout_seconds": 60,
            "allowed_shell_commands": [
                "python", "python3", "pip", "pip3", "git", "ls", "cat", "grep", "find",
                "mkdir", "rm", "cp", "mv", "chmod", "touch", "head", "tail", "wc",
                "pytest", "black", "flake8", "mypy", "coverage", "tox"
            ],
            "max_file_size_mb": 10,
            "enable_code_analysis": True,
            "enable_auto_testing": True,
            "enable_pattern_learning": True
        }
        
        if config_path.exists():
            try:
                with config_path.open("r", encoding="utf-8") as f:
                    loaded_config = json.load(f)
                    self.config_data = {**default_config, **loaded_config}
            except json.JSONDecodeError:
                self.logger.error(f"Invalid JSON in config file: {config_path}. Using defaults.")
                self.config_data = default_config
        else:
            self.config_data = default_config
            
        self.command_timeout = self.config_data.get("command_timeout_seconds", 60)

    def _initialize_sandbox(self) -> Path:
        """Creates the enhanced sandbox directory."""
        default_sandbox = PROJECT_ROOT / "data" / "agent_workspaces" / "simple_coder_agent"
        sandbox_path_str = self.config_data.get("sandbox_path", str(default_sandbox.relative_to(PROJECT_ROOT)))
        sandbox_abs_path = (PROJECT_ROOT / sandbox_path_str).resolve()
        
        if not sandbox_abs_path.is_relative_to(PROJECT_ROOT) or sandbox_abs_path == PROJECT_ROOT:
            self.logger.critical(f"INSECURE SANDBOX CONFIG: '{sandbox_path_str}'. Defaulting to '{default_sandbox}'.")
            sandbox_abs_path = default_sandbox
            
        sandbox_abs_path.mkdir(parents=True, exist_ok=True)
        
        # Create subdirectories for organization
        (sandbox_abs_path / "projects").mkdir(exist_ok=True)
        (sandbox_abs_path / "temp").mkdir(exist_ok=True)
        (sandbox_abs_path / "tests").mkdir(exist_ok=True)
        
        return sandbox_abs_path

    def _resolve_and_check_path(self, path_str: str) -> Optional[Path]:
        """Resolves a path relative to the CWD and ensures it's within the sandbox."""
        try:
            # Handle absolute paths within the sandbox by stripping the root
            if Path(path_str).is_absolute():
                # This is a potential security risk if not handled carefully
                # We will treat it as relative to the sandbox root
                path_str = str(Path(path_str).relative_to('/'))
                
            resolved_path = (self.current_working_directory / path_str).resolve()
            
            if not resolved_path.is_relative_to(self.sandbox_root):
                self.logger.error(f"Path Traversal DENIED. Attempt to access '{path_str}' which resolves outside the sandbox.")
                return None
            return resolved_path
        except Exception:
            self.logger.error(f"Path validation failed for '{path_str}'.", exc_info=True)
            return None

    async def _list_directory(self, path: str = ".", detail: bool = False) -> Dict[str, Any]:
        dir_path = self._resolve_and_check_path(path)
        if not dir_path or not dir_path.is_dir(): return {"status": "ERROR", "message": f"Invalid directory: '{path}'"}
        try:
            if not detail:
                items = sorted([f.name + ('/' if f.is_dir() else '') for f in dir_path.iterdir()])
                return {"status": "SUCCESS", "items": items}
            else:
                detailed_items = []
                for f in sorted(dir_path.iterdir()):
                    stat_info = f.stat()
                    detailed_items.append({"name": f.name + ('/' if f.is_dir() else ''), "size_bytes": stat_info.st_size, "modified_time": stat_info.st_mtime})
                return {"status": "SUCCESS", "items": detailed_items}
        except Exception as e:
            return {"status": "ERROR", "message": f"Failed to list directory '{path}': {e}"}
        
    async def _change_directory(self, path: str) -> Dict[str, Any]:
        new_dir = self._resolve_and_check_path(path)
        if not new_dir or not new_dir.is_dir(): return {"status": "ERROR", "message": f"Cannot cd into invalid directory: '{path}'"}
        self.current_working_directory = new_dir
        relative_cwd = self.current_working_directory.relative_to(self.sandbox_root)
        return {"status": "SUCCESS", "message": f"Current directory is now: ./{relative_cwd}"}

    async def _create_directory(self, path: str) -> Dict[str, Any]:
        dir_path = self._resolve_and_check_path(path)
        if not dir_path: return {"status": "ERROR", "message": "Invalid or insecure directory path provided."}
        try:
            dir_path.mkdir(parents=True, exist_ok=True)
            return {"status": "SUCCESS", "message": f"Directory created/ensured at {path}"}
        except Exception as e:
            return {"status": "ERROR", "message": f"Failed to create directory '{path}': {e}"}

    async def _create_venv(self, venv_name: str) -> Dict[str, Any]:
        if not re.match(r'^[a-zA-Z0-9_-]+$', venv_name):
            return {"status": "ERROR", "message": "Invalid venv_name. Use only letters, numbers, underscore, or hyphen."}
        venv_path = self._resolve_and_check_path(venv_name)
        if not venv_path: return {"status": "ERROR", "message": "Invalid or insecure venv path."}
        if venv_path.exists(): return {"status": "ERROR", "message": f"Directory '{venv_name}' already exists."}
        self.logger.info(f"Creating new venv in '{venv_path}'...")
        try:
            await asyncio.to_thread(subprocess.run, [sys.executable, '-m', 'venv', str(venv_path)], check=True, capture_output=True)
            return {"status": "SUCCESS", "message": f"Venv '{venv_name}' created. Activate it with: activate_venv '{venv_name}'"}
        except subprocess.CalledProcessError as e:
            return {"status": "ERROR", "message": f"Failed to create venv: {e.stderr.decode()}"}

    async def _activate_venv(self, venv_name: str) -> Dict[str, Any]:
        venv_path = self._resolve_and_check_path(venv_name)
        if not venv_path or not venv_path.is_dir(): return {"status": "ERROR", "message": f"Venv directory '{venv_name}' not found."}
        bin_path = venv_path / ('Scripts' if sys.platform == 'win32' else 'bin')
        if not (bin_path / 'python').exists() and not (bin_path / 'python.exe').exists(): return {"status": "ERROR", "message": f"'{venv_name}' does not appear to be a valid venv."}
        self.active_venv_bin_path = bin_path
        relative_venv_path = venv_path.relative_to(self.sandbox_root)
        return {"status": "SUCCESS", "message": f"Venv '{relative_venv_path}' is now active."}

    async def _deactivate_venv(self) -> Dict[str, Any]:
        if not self.active_venv_bin_path: return {"status": "SUCCESS", "message": "No venv was active."}
        self.active_venv_bin_path = None
        return {"status": "SUCCESS", "message": "Venv deactivated."}

    async def _run_shell_command(self, command: str) -> Dict[str, Any]:
        try:
            command_parts = shlex.split(command)
            command_name = command_parts[0]
        except (ValueError, IndexError): return {"status": "ERROR", "message": "Invalid command string."}
        if command_name not in self.config_data.get("allowed_shell_commands", []):
            return {"status": "ERROR", "message": f"Command '{command_name}' is not in the allowlist."}
        env = os.environ.copy()
        if self.active_venv_bin_path: env["PATH"] = f"{self.active_venv_bin_path}{os.pathsep}{env.get('PATH', '')}"
        
        self.logger.info(f"Executing in '{self.current_working_directory}': {command_parts}")
        try:
            process = await asyncio.wait_for(asyncio.create_subprocess_exec(*command_parts, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE, cwd=self.current_working_directory, env=env), timeout=self.command_timeout)
            stdout, stderr = await process.communicate()
            result = {"status": "SUCCESS" if process.returncode == 0 else "FAILURE", "return_code": process.returncode, "stdout": stdout.decode('utf-8', 'ignore').strip(), "stderr": stderr.decode('utf-8', 'ignore').strip()}
            if result["status"] == "FAILURE": self.logger.warning(f"Shell command failed. Stderr: {result['stderr']}")
            return result
        except FileNotFoundError: return {"status": "ERROR", "message": f"Shell command not found: '{command_name}'."}
        except Exception as e: return {"status": "ERROR", "message": f"An exception occurred: {str(e)}"}

    async def _read_file(self, path: str) -> Dict[str, Any]:
        file_path = self._resolve_and_check_path(path)
        if not file_path or not file_path.is_file(): return {"status": "ERROR", "message": f"Path is not a file: {path}"}
        try:
            content = await asyncio.to_thread(file_path.read_text, encoding='utf-8')
            return {"status": "SUCCESS", "content": content}
        except Exception as e:
            return {"status": "ERROR", "message": f"Error reading file: {e}"}

    async def _write_file(self, path: str, content: str) -> Dict[str, Any]:
        file_path = self._resolve_and_check_path(path)
        if not file_path: return {"status": "ERROR", "message": f"Invalid or insecure path: {path}"}
        try:
            await asyncio.to_thread(file_path.parent.mkdir, parents=True, exist_ok=True)
            await asyncio.to_thread(file_path.write_text, content, encoding='utf-8')
            return {"status": "SUCCESS", "message": f"File written successfully to {path}."}
        except Exception as e:
            return {"status": "ERROR", "message": f"Error writing file: {e}"}

    async def _delete_file(self, path: str, force: bool = False) -> Dict[str, Any]:
        if not force: return {"status": "ERROR", "message": "Deletion requires 'force=True' parameter."}
        file_path = self._resolve_and_check_path(path)
        if not file_path or not file_path.is_file(): return {"status": "ERROR", "message": f"Path is not a file: {path}"}
        try:
            await asyncio.to_thread(file_path.unlink)
            return {"status": "SUCCESS", "message": "File deleted successfully."}
        except Exception as e:
            return {"status": "ERROR", "message": f"Error deleting file: {e}"}

    async def execute(self, operation: str = None, **kwargs) -> Dict[str, Any]:
        """Enhanced execute method with intelligent routing."""
        if not operation:
            return {"status": "ERROR", "message": "No operation specified"}
        
        # Log operation for learning
        start_time = time.time()
        
        try:
            if operation in self.native_handlers:
                result = await self.native_handlers[operation](**kwargs)
                
                # Learn from execution
                execution_context = {
                    "operation": operation,
                    "parameters": kwargs,
                    "duration": time.time() - start_time
                }
                
                await self._learn_from_execution(result, execution_context)
                
                return result
            else:
                return {"status": "ERROR", "message": f"Unknown operation: {operation}"}
                
        except Exception as e:
            self.logger.error(f"{self.log_prefix} Execution error: {e}")
            return {"status": "ERROR", "message": f"Execution failed: {e}"}

    # Helper methods for enhanced functionality
    async def _get_project_context(self) -> Dict[str, Any]:
        """Get current project context for better code generation."""
        if not self.project_context:
            await self._analyze_project()
        return self.project_context

    async def _get_recent_patterns(self) -> Dict[str, Any]:
        """Get recent coding patterns from memory."""
        # This would query the memory agent for recent patterns
        return self.code_patterns

    async def _update_coding_patterns(self, learning_data: Dict[str, Any]):
        """Update coding patterns based on learning data."""
        # Update internal patterns
        pattern_key = learning_data["context"]["operation"]
        if pattern_key not in self.code_patterns:
            self.code_patterns[pattern_key] = []
        
        self.code_patterns[pattern_key].append({
            "success": learning_data["success"],
            "context": learning_data["context"],
            "timestamp": learning_data["timestamp"]
        })
        
        # Keep only recent patterns (last 100)
        self.code_patterns[pattern_key] = self.code_patterns[pattern_key][-100:]

    async def _analyze_current_context(self, task: str) -> Dict[str, Any]:
        """Analyze current context for better suggestions."""
        return {
            "current_directory": str(self.current_working_directory.relative_to(self.sandbox_root)),
            "active_venv": str(self.active_venv_bin_path) if self.active_venv_bin_path else None,
            "task": task,
            "project_info": self.project_context
        }

    async def _get_relevant_patterns(self, task: str) -> Dict[str, Any]:
        """Get patterns relevant to the current task."""
        # Simple pattern matching - could be enhanced with ML
        relevant = {}
        for pattern_key, patterns in self.code_patterns.items():
            if any(keyword in task.lower() for keyword in pattern_key.split("_")):
                relevant[pattern_key] = patterns[-5:]  # Last 5 relevant patterns
        return relevant

    async def _analyze_code(self, file_path: str = None, code_content: str = None) -> Dict[str, Any]:
        """Analyze code for quality, patterns, and potential improvements."""
        if not self.config_data.get("enable_code_analysis", True):
            return {"status": "DISABLED", "message": "Code analysis is disabled"}
            
        try:
            if file_path:
                file_obj = self._resolve_and_check_path(file_path)
                if not file_obj or not file_obj.is_file():
                    return {"status": "ERROR", "message": f"Invalid file path: {file_path}"}
                code_content = await asyncio.to_thread(file_obj.read_text, encoding='utf-8')
            
            if not code_content:
                return {"status": "ERROR", "message": "No code content provided"}
            
            analysis_prompt = f"""
            Analyze the following code for:
            1. Code quality and best practices
            2. Potential bugs or issues
            3. Performance optimization opportunities
            4. Security considerations
            5. Maintainability and readability
            
            Code to analyze:
            ```
            {code_content}
            ```
            
            Provide a comprehensive analysis in JSON format.
            """
            
            if self.llm_handler:
                analysis_result = await self.llm_handler.generate_text(
                    analysis_prompt, 
                    model=self.llm_handler.model_name_for_api,
                    json_mode=True
                )
                
                # Log analysis for learning
                await self.memory_agent.log_process(
                    process_name="code_analysis",
                    data={
                        "file_path": file_path,
                        "analysis_result": analysis_result,
                        "timestamp": time.time()
                    },
                    metadata={"agent_id": self.agent_id}
                )
                
                return {"status": "SUCCESS", "analysis": analysis_result}
            else:
                return {"status": "ERROR", "message": "LLM handler not available"}
                
        except Exception as e:
            self.logger.error(f"{self.log_prefix} Code analysis error: {e}")
            return {"status": "ERROR", "message": f"Analysis failed: {e}"}

    async def _generate_code(self, description: str, language: str = "python", style: str = "clean") -> Dict[str, Any]:
        """Generate code based on description with intelligent context awareness."""
        try:
            # Get project context for better code generation
            context_info = await self._get_project_context()
            
            generation_prompt = f"""
            Generate {language} code based on the following description:
            {description}
            
            Project Context:
            {json.dumps(context_info, indent=2)}
            
            Requirements:
            - Follow {style} coding style
            - Include appropriate error handling
            - Add docstrings and comments
            - Consider security best practices
            - Make it maintainable and testable
            
            Return the code with explanations in JSON format.
            """
            
            if self.llm_handler:
                generated_code = await self.llm_handler.generate_text(
                    generation_prompt,
                    model=self.llm_handler.model_name_for_api,
                    json_mode=True
                )
                
                # Log generation for learning
                await self.memory_agent.log_process(
                    process_name="code_generation",
                    data={
                        "description": description,
                        "language": language,
                        "generated_code": generated_code,
                        "timestamp": time.time()
                    },
                    metadata={"agent_id": self.agent_id}
                )
                
                return {"status": "SUCCESS", "generated_code": generated_code}
            else:
                return {"status": "ERROR", "message": "LLM handler not available"}
                
        except Exception as e:
            self.logger.error(f"{self.log_prefix} Code generation error: {e}")
            return {"status": "ERROR", "message": f"Generation failed: {e}"}

    async def _optimize_code(self, file_path: str = None, code_content: str = None) -> Dict[str, Any]:
        """Optimize code for performance and efficiency."""
        try:
            if file_path:
                file_obj = self._resolve_and_check_path(file_path)
                if not file_obj or not file_obj.is_file():
                    return {"status": "ERROR", "message": f"Invalid file path: {file_path}"}
                code_content = await asyncio.to_thread(file_obj.read_text, encoding='utf-8')
            
            if not code_content:
                return {"status": "ERROR", "message": "No code content provided"}
            
            optimization_prompt = f"""
            Optimize the following code for:
            1. Performance improvements
            2. Memory efficiency
            3. Algorithmic optimizations
            4. Code simplification
            5. Resource usage reduction
            
            Original code:
            ```
            {code_content}
            ```
            
            Provide optimized version with explanations in JSON format.
            """
            
            if self.llm_handler:
                optimized_result = await self.llm_handler.generate_text(
                    optimization_prompt,
                    model=self.llm_handler.model_name_for_api,
                    json_mode=True
                )
                
                return {"status": "SUCCESS", "optimization": optimized_result}
            else:
                return {"status": "ERROR", "message": "LLM handler not available"}
                
        except Exception as e:
            self.logger.error(f"{self.log_prefix} Code optimization error: {e}")
            return {"status": "ERROR", "message": f"Optimization failed: {e}"}

    async def _debug_code(self, file_path: str = None, code_content: str = None, error_message: str = None) -> Dict[str, Any]:
        """Debug code and provide solutions for issues."""
        try:
            if file_path:
                file_obj = self._resolve_and_check_path(file_path)
                if not file_obj or not file_obj.is_file():
                    return {"status": "ERROR", "message": f"Invalid file path: {file_path}"}
                code_content = await asyncio.to_thread(file_obj.read_text, encoding='utf-8')
            
            if not code_content:
                return {"status": "ERROR", "message": "No code content provided"}
            
            debug_prompt = f"""
            Debug the following code and provide solutions:
            
            Code:
            ```
            {code_content}
            ```
            
            {f"Error message: {error_message}" if error_message else ""}
            
            Provide:
            1. Identified issues
            2. Root cause analysis
            3. Suggested fixes
            4. Prevention strategies
            
            Return analysis in JSON format.
            """
            
            if self.llm_handler:
                debug_result = await self.llm_handler.generate_text(
                    debug_prompt,
                    model=self.llm_handler.model_name_for_api,
                    json_mode=True
                )
                
                return {"status": "SUCCESS", "debug_analysis": debug_result}
            else:
                return {"status": "ERROR", "message": "LLM handler not available"}
                
        except Exception as e:
            self.logger.error(f"{self.log_prefix} Code debugging error: {e}")
            return {"status": "ERROR", "message": f"Debugging failed: {e}"}

    async def _test_code(self, file_path: str, test_type: str = "unit") -> Dict[str, Any]:
        """Generate and run tests for code."""
        if not self.config_data.get("enable_auto_testing", True):
            return {"status": "DISABLED", "message": "Auto testing is disabled"}
            
        try:
            file_obj = self._resolve_and_check_path(file_path)
            if not file_obj or not file_obj.is_file():
                return {"status": "ERROR", "message": f"Invalid file path: {file_path}"}
            
            code_content = await asyncio.to_thread(file_obj.read_text, encoding='utf-8')
            
            test_prompt = f"""
            Generate {test_type} tests for the following code:
            
            ```
            {code_content}
            ```
            
            Create comprehensive tests that cover:
            1. Normal operation cases
            2. Edge cases
            3. Error conditions
            4. Performance considerations
            
            Return test code in JSON format.
            """
            
            if self.llm_handler:
                test_result = await self.llm_handler.generate_text(
                    test_prompt,
                    model=self.llm_handler.model_name_for_api,
                    json_mode=True
                )
                
                return {"status": "SUCCESS", "tests": test_result}
            else:
                return {"status": "ERROR", "message": "LLM handler not available"}
                
        except Exception as e:
            self.logger.error(f"{self.log_prefix} Test generation error: {e}")
            return {"status": "ERROR", "message": f"Test generation failed: {e}"}

    async def _refactor_code(self, file_path: str = None, code_content: str = None, refactor_type: str = "improve") -> Dict[str, Any]:
        """Refactor code for better structure and maintainability."""
        try:
            if file_path:
                file_obj = self._resolve_and_check_path(file_path)
                if not file_obj or not file_obj.is_file():
                    return {"status": "ERROR", "message": f"Invalid file path: {file_path}"}
                code_content = await asyncio.to_thread(file_obj.read_text, encoding='utf-8')
            
            if not code_content:
                return {"status": "ERROR", "message": "No code content provided"}
            
            refactor_prompt = f"""
            Refactor the following code for {refactor_type}:
            
            ```
            {code_content}
            ```
            
            Focus on:
            1. Code structure and organization
            2. Function/class design
            3. Variable naming
            4. Code reusability
            5. Maintainability improvements
            
            Return refactored code with explanations in JSON format.
            """
            
            if self.llm_handler:
                refactor_result = await self.llm_handler.generate_text(
                    refactor_prompt,
                    model=self.llm_handler.model_name_for_api,
                    json_mode=True
                )
                
                return {"status": "SUCCESS", "refactored_code": refactor_result}
            else:
                return {"status": "ERROR", "message": "LLM handler not available"}
                
        except Exception as e:
            self.logger.error(f"{self.log_prefix} Code refactoring error: {e}")
            return {"status": "ERROR", "message": f"Refactoring failed: {e}"}

    async def _explain_code(self, file_path: str = None, code_content: str = None, detail_level: str = "medium") -> Dict[str, Any]:
        """Explain code functionality and structure."""
        try:
            if file_path:
                file_obj = self._resolve_and_check_path(file_path)
                if not file_obj or not file_obj.is_file():
                    return {"status": "ERROR", "message": f"Invalid file path: {file_path}"}
                code_content = await asyncio.to_thread(file_obj.read_text, encoding='utf-8')
            
            if not code_content:
                return {"status": "ERROR", "message": "No code content provided"}
            
            explain_prompt = f"""
            Explain the following code at {detail_level} detail level:
            
            ```
            {code_content}
            ```
            
            Provide:
            1. Overall purpose and functionality
            2. Key components and their roles
            3. Data flow and logic
            4. Important patterns or techniques used
            5. Potential improvements or considerations
            
            Return explanation in JSON format.
            """
            
            if self.llm_handler:
                explanation_result = await self.llm_handler.generate_text(
                    explain_prompt,
                    model=self.llm_handler.model_name_for_api,
                    json_mode=True
                )
                
                return {"status": "SUCCESS", "explanation": explanation_result}
            else:
                return {"status": "ERROR", "message": "LLM handler not available"}
                
        except Exception as e:
            self.logger.error(f"{self.log_prefix} Code explanation error: {e}")
            return {"status": "ERROR", "message": f"Explanation failed: {e}"}

    async def _analyze_project(self, project_path: str = ".") -> Dict[str, Any]:
        """Analyze entire project structure and provide insights."""
        try:
            project_dir = self._resolve_and_check_path(project_path)
            if not project_dir or not project_dir.is_dir():
                return {"status": "ERROR", "message": f"Invalid project path: {project_path}"}
            
            # Collect project information
            project_info = {
                "structure": await self._get_project_structure(project_dir),
                "file_types": await self._analyze_file_types(project_dir),
                "dependencies": await self._analyze_dependencies(project_dir),
                "complexity": await self._analyze_complexity(project_dir)
            }
            
            # Store project context
            self.project_context = project_info
            
            # Log project analysis
            await self.memory_agent.log_process(
                process_name="project_analysis",
                data=project_info,
                metadata={"agent_id": self.agent_id, "project_path": project_path}
            )
            
            return {"status": "SUCCESS", "project_analysis": project_info}
            
        except Exception as e:
            self.logger.error(f"{self.log_prefix} Project analysis error: {e}")
            return {"status": "ERROR", "message": f"Project analysis failed: {e}"}

    async def _suggest_improvements(self, context: str = "general") -> Dict[str, Any]:
        """Suggest improvements based on analysis and learning."""
        try:
            # Get recent coding history
            recent_patterns = await self._get_recent_patterns()
            
            suggestion_prompt = f"""
            Based on the following context and patterns, suggest improvements:
            
            Context: {context}
            Project Context: {json.dumps(self.project_context, indent=2)}
            Recent Patterns: {json.dumps(recent_patterns, indent=2)}
            
            Provide actionable suggestions for:
            1. Code quality improvements
            2. Performance optimizations
            3. Security enhancements
            4. Development workflow improvements
            5. Tool and library recommendations
            
            Return suggestions in JSON format.
            """
            
            if self.llm_handler:
                suggestions = await self.llm_handler.generate_text(
                    suggestion_prompt,
                    model=self.llm_handler.model_name_for_api,
                    json_mode=True
                )
                
                return {"status": "SUCCESS", "suggestions": suggestions}
            else:
                return {"status": "ERROR", "message": "LLM handler not available"}
                
        except Exception as e:
            self.logger.error(f"{self.log_prefix} Suggestion generation error: {e}")
            return {"status": "ERROR", "message": f"Suggestion generation failed: {e}"}

    async def _create_documentation(self, target: str, doc_type: str = "api") -> Dict[str, Any]:
        """Generate documentation for code or projects."""
        try:
            if doc_type == "api":
                # Generate API documentation
                return await self._generate_api_docs(target)
            elif doc_type == "readme":
                # Generate README documentation
                return await self._generate_readme(target)
            elif doc_type == "technical":
                # Generate technical documentation
                return await self._generate_technical_docs(target)
            else:
                return {"status": "ERROR", "message": f"Unknown documentation type: {doc_type}"}
                
        except Exception as e:
            self.logger.error(f"{self.log_prefix} Documentation generation error: {e}")
            return {"status": "ERROR", "message": f"Documentation generation failed: {e}"}

    async def _learn_from_execution(self, execution_result: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Learn from code execution results to improve future suggestions."""
        if not self.config_data.get("enable_pattern_learning", True):
            return {"status": "DISABLED", "message": "Pattern learning is disabled"}
            
        try:
            learning_data = {
                "execution_result": execution_result,
                "context": context,
                "timestamp": time.time(),
                "success": execution_result.get("status") == "SUCCESS"
            }
            
            # Update coding patterns
            await self._update_coding_patterns(learning_data)
            
            # Log learning data
            await self.memory_agent.log_process(
                process_name="coding_learning",
                data=learning_data,
                metadata={"agent_id": self.agent_id}
            )
            
            return {"status": "SUCCESS", "message": "Learning data recorded"}
            
        except Exception as e:
            self.logger.error(f"{self.log_prefix} Learning error: {e}")
            return {"status": "ERROR", "message": f"Learning failed: {e}"}

    async def _get_coding_suggestions(self, current_task: str) -> Dict[str, Any]:
        """Get intelligent coding suggestions based on current task and learned patterns."""
        try:
            # Analyze current context
            context_analysis = await self._analyze_current_context(current_task)
            
            # Get relevant patterns
            relevant_patterns = await self._get_relevant_patterns(current_task)
            
            suggestion_prompt = f"""
            Provide intelligent coding suggestions for the current task:
            
            Task: {current_task}
            Context Analysis: {json.dumps(context_analysis, indent=2)}
            Relevant Patterns: {json.dumps(relevant_patterns, indent=2)}
            
            Suggest:
            1. Best approaches for this task
            2. Potential pitfalls to avoid
            3. Recommended tools and libraries
            4. Code structure suggestions
            5. Testing strategies
            
            Return suggestions in JSON format.
            """
            
            if self.llm_handler:
                suggestions = await self.llm_handler.generate_text(
                    suggestion_prompt,
                    model=self.llm_handler.model_name_for_api,
                    json_mode=True
                )
                
                return {"status": "SUCCESS", "suggestions": suggestions}
            else:
                return {"status": "ERROR", "message": "LLM handler not available"}
                
        except Exception as e:
            self.logger.error(f"{self.log_prefix} Suggestion error: {e}")
            return {"status": "ERROR", "message": f"Suggestion generation failed: {e}"}

    # ... include all the existing file system methods from the original file ...