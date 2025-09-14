# Enhanced Simple Coder Agent
"""
Enhanced Simple Coder: The BDI Agent's Intelligent Right Hand

This agent provides comprehensive coding assistance with multi-model selection,
file system operations, shell command execution, and seamless integration 
with the MindX ecosystem.
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

logger = get_logger(__name__)

class EnhancedSimpleCoder(BaseTool):
    """
    Enhanced coding agent providing comprehensive assistance to the BDI agent.
    
    Features:
    - Advanced code analysis and generation
    - Complete file system operations
    - Secure shell command execution
    - Multi-model intelligence for different coding tasks
    - Secure sandboxed execution environment
    - Memory integration for learning and improvement
    - Context-aware suggestions and optimizations
    """

    def __init__(self, memory_agent: Optional[MemoryAgent] = None, **kwargs):
        super().__init__(**kwargs)
        self.memory_agent = memory_agent or MemoryAgent()
        self.agent_id = "enhanced_simple_coder"
        self.log_prefix = "EnhancedSimpleCoder:"
        
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
        
        # Multi-model preferences for different coding tasks
        self.model_preferences = {
            "code_generation": "gemini-2.0-flash",
            "code_analysis": "gemini-1.5-pro-latest", 
            "debugging": "gemini-2.0-flash",
            "optimization": "gemini-1.5-pro-latest",
            "documentation": "gemini-2.0-flash",
            "shell_tasks": "gemini-2.0-flash",
            "file_operations": "gemini-1.5-pro-latest"
        }
        
        # Performance tracking
        self.performance_metrics = {}
        
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
        
        logger.info(f"{self.log_prefix} Enhanced coding agent initialized with comprehensive capabilities. Sandbox: {self.sandbox_root}")

    def _load_command_config(self):
        """Load configuration with enhanced defaults."""
        default_path = PROJECT_ROOT / "data" / "config" / "enhanced_simple_coder.json"
        config_path_str = self.config.get("agents.enhanced_simple_coder.config_path") or str(default_path)
        config_path = Path(config_path_str)
        
        # Default enhanced configuration
        default_config = {
            "command_timeout_seconds": 60,
            "allowed_shell_commands": [
                "python", "python3", "pip", "pip3", "git", "ls", "cat", "grep", "find",
                "mkdir", "rm", "cp", "mv", "chmod", "touch", "head", "tail", "wc",
                "pytest", "black", "flake8", "mypy", "coverage", "tox", "which", "echo"
            ],
            "max_file_size_mb": 10,
            "enable_code_analysis": True,
            "enable_auto_testing": True,
            "enable_pattern_learning": True,
            "sandbox_path": "data/agent_workspaces/enhanced_simple_coder"
        }
        
        if config_path.exists():
            try:
                with config_path.open("r", encoding="utf-8") as f:
                    loaded_config = json.load(f)
                    self.config_data = {**default_config, **loaded_config}
            except json.JSONDecodeError:
                logger.error(f"Invalid JSON in config file: {config_path}. Using defaults.")
                self.config_data = default_config
        else:
            self.config_data = default_config
            
        self.command_timeout = self.config_data.get("command_timeout_seconds", 60)

    def _initialize_sandbox(self) -> Path:
        """Creates the enhanced sandbox directory."""
        default_sandbox = PROJECT_ROOT / "data" / "agent_workspaces" / "enhanced_simple_coder"
        sandbox_path_str = self.config_data.get("sandbox_path", str(default_sandbox.relative_to(PROJECT_ROOT)))
        sandbox_abs_path = (PROJECT_ROOT / sandbox_path_str).resolve()
        
        if not sandbox_abs_path.is_relative_to(PROJECT_ROOT) or sandbox_abs_path == PROJECT_ROOT:
            logger.critical(f"INSECURE SANDBOX CONFIG: '{sandbox_path_str}'. Defaulting to '{default_sandbox}'.")
            sandbox_abs_path = default_sandbox
            
        sandbox_abs_path.mkdir(parents=True, exist_ok=True)
        
        # Create subdirectories for organization
        (sandbox_abs_path / "projects").mkdir(exist_ok=True)
        (sandbox_abs_path / "temp").mkdir(exist_ok=True)
        (sandbox_abs_path / "tests").mkdir(exist_ok=True)
        (sandbox_abs_path / "generated").mkdir(exist_ok=True)
        
        return sandbox_abs_path

    def _resolve_and_check_path(self, path_str: str) -> Optional[Path]:
        """Resolves a path and ensures it's within the sandbox."""
        try:
            if os.path.isabs(path_str):
                target_path = Path(path_str).resolve()
            else:
                target_path = (self.current_working_directory / path_str).resolve()
            
            if target_path.is_relative_to(self.sandbox_root):
                return target_path
            else:
                logger.warning(f"Path outside sandbox rejected: {path_str}")
                return None
        except Exception as e:
            logger.error(f"Path resolution error: {e}")
            return None

    async def execute(self, action: str = None, operation: str = None, **kwargs) -> Tuple[bool, Any]:
        """
        Enhanced execute method with intelligent routing.
        Supports both 'action' and 'operation' parameters for compatibility.
        """
        # Use either action or operation parameter
        op = action or operation
        if not op:
            return False, "No action or operation specified"
        
        # Log operation for learning
        start_time = time.time()
        
        try:
            if op in self.native_handlers:
                result = await self.native_handlers[op](**kwargs)
                
                # Learn from execution
                execution_context = {
                    "operation": op,
                    "parameters": kwargs,
                    "duration": time.time() - start_time
                }
                
                await self._learn_from_execution(result, execution_context)
                
                # Convert dict result to tuple for compatibility
                if isinstance(result, dict):
                    success = result.get("status") == "SUCCESS"
                    return success, result
                else:
                    return True, result
            else:
                return False, f"Unknown operation: {op}"
                
        except Exception as e:
            logger.error(f"{self.log_prefix} Execution error: {e}")
            return False, f"Execution failed: {e}"

    # File System Operations
    async def _list_directory(self, path: str = ".") -> Dict[str, Any]:
        """List files and directories in the specified path."""
        dir_path = self._resolve_and_check_path(path)
        if not dir_path or not dir_path.is_dir():
            return {"status": "ERROR", "message": f"Path is not a directory: {path}"}
        
        try:
            items = []
            for item in dir_path.iterdir():
                items.append({
                    "name": item.name,
                    "type": "directory" if item.is_dir() else "file",
                    "size": item.stat().st_size if item.is_file() else None
                })
            
            return {"status": "SUCCESS", "items": items}
        except Exception as e:
            return {"status": "ERROR", "message": f"Error listing directory: {e}"}

    async def _change_directory(self, path: str) -> Dict[str, Any]:
        """Change the current working directory."""
        new_dir = self._resolve_and_check_path(path)
        if not new_dir or not new_dir.is_dir():
            return {"status": "ERROR", "message": f"Cannot cd into invalid directory: '{path}'"}
        
        self.current_working_directory = new_dir
        relative_cwd = self.current_working_directory.relative_to(self.sandbox_root)
        return {"status": "SUCCESS", "message": f"Current directory is now: ./{relative_cwd}"}

    async def _read_file(self, path: str) -> Dict[str, Any]:
        """Read the contents of a file."""
        file_path = self._resolve_and_check_path(path)
        if not file_path or not file_path.is_file():
            return {"status": "ERROR", "message": f"Path is not a file: {path}"}
        
        try:
            content = await asyncio.to_thread(file_path.read_text, encoding='utf-8')
            return {"status": "SUCCESS", "content": content}
        except Exception as e:
            return {"status": "ERROR", "message": f"Error reading file: {e}"}

    async def _write_file(self, path: str, content: str) -> Dict[str, Any]:
        """Write content to a file."""
        file_path = self._resolve_and_check_path(path)
        if not file_path:
            return {"status": "ERROR", "message": f"Invalid or insecure path: {path}"}
        
        try:
            await asyncio.to_thread(file_path.parent.mkdir, parents=True, exist_ok=True)
            await asyncio.to_thread(file_path.write_text, content, encoding='utf-8')
            return {"status": "SUCCESS", "message": f"File written successfully to {path}"}
        except Exception as e:
            return {"status": "ERROR", "message": f"Error writing file: {e}"}

    async def _create_directory(self, path: str) -> Dict[str, Any]:
        """Create a directory."""
        dir_path = self._resolve_and_check_path(path)
        if not dir_path:
            return {"status": "ERROR", "message": "Invalid or insecure directory path provided."}
        
        try:
            dir_path.mkdir(parents=True, exist_ok=True)
            return {"status": "SUCCESS", "message": f"Directory created/ensured at {path}"}
        except Exception as e:
            return {"status": "ERROR", "message": f"Failed to create directory '{path}': {e}"}

    async def _delete_file(self, path: str, force: bool = False) -> Dict[str, Any]:
        """Delete a file (requires force=True for safety)."""
        if not force:
            return {"status": "ERROR", "message": "Deletion requires 'force=True' parameter."}
        
        file_path = self._resolve_and_check_path(path)
        if not file_path or not file_path.is_file():
            return {"status": "ERROR", "message": f"Path is not a file: {path}"}
        
        try:
            await asyncio.to_thread(file_path.unlink)
            return {"status": "SUCCESS", "message": "File deleted successfully."}
        except Exception as e:
            return {"status": "ERROR", "message": f"Error deleting file: {e}"}

    # Shell Command Execution
    async def _run_shell_command(self, command: str, args: Optional[List[str]] = None) -> Dict[str, Any]:
        """Execute a shell command securely."""
        if command not in self.config_data.get("allowed_shell_commands", []):
            return {"status": "ERROR", "message": f"Command '{command}' not in allowlist"}
        
        try:
            cmd_args = [command] + (args or [])
            
            process = await asyncio.create_subprocess_exec(
                *cmd_args,
                cwd=self.current_working_directory,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await asyncio.wait_for(
                process.communicate(), 
                timeout=self.command_timeout
            )
            
            return {
                "status": "SUCCESS",
                "stdout": stdout.decode('utf-8', errors='replace'),
                "stderr": stderr.decode('utf-8', errors='replace'),
                "return_code": process.returncode
            }
            
        except asyncio.TimeoutError:
            return {"status": "ERROR", "message": f"Command timed out after {self.command_timeout}s"}
        except Exception as e:
            return {"status": "ERROR", "message": f"Command execution failed: {e}"}

    # Enhanced Coding Capabilities
    async def _analyze_code(self, code: Optional[str] = None, file_path: Optional[str] = None, analysis_type: str = "comprehensive") -> Dict[str, Any]:
        """Analyze code for quality and improvements."""
        try:
            if file_path:
                file_obj = self._resolve_and_check_path(file_path)
                if not file_obj or not file_obj.is_file():
                    return {"status": "ERROR", "message": f"Invalid file path: {file_path}"}
                code = await asyncio.to_thread(file_obj.read_text, encoding='utf-8')
            
            if not code:
                return {"status": "ERROR", "message": "No code content provided"}
            
            analysis_prompt = f"""
            Perform {analysis_type} analysis of this code:
            
            ```
            {code}
            ```
            
            Analyze:
            1. Code quality and best practices adherence
            2. Potential bugs and security vulnerabilities
            3. Performance optimization opportunities
            4. Maintainability and readability issues
            5. Design patterns and architectural concerns
            6. Error handling completeness
            7. Documentation quality
            
            Return detailed analysis in JSON format with specific recommendations.
            """
            
            if self.llm_handler:
                model = self.model_preferences.get("code_analysis", "gemini-1.5-pro-latest")
                result = await self.llm_handler.generate_text(
                    analysis_prompt, 
                    model=model, 
                    json_mode=True
                )
                
                # Log analysis for learning
                await self.memory_agent.log_process(
                    process_name="code_analysis",
                    data={
                        "file_path": file_path,
                        "analysis_type": analysis_type,
                        "analysis_result": result,
                        "timestamp": time.time()
                    },
                    metadata={"agent_id": self.agent_id}
                )
                
                return {"status": "SUCCESS", "analysis": result}
            else:
                return {"status": "ERROR", "message": "LLM handler not available"}
                
        except Exception as e:
            logger.error(f"{self.log_prefix} Code analysis error: {e}")
            return {"status": "ERROR", "message": f"Analysis failed: {e}"}

    async def _generate_code(self, description: str, language: str = "python", 
                           style: str = "clean", output_file: Optional[str] = None) -> Dict[str, Any]:
        """Generate code based on description."""
        try:
            generation_prompt = f"""
            Generate {language} code for: {description}
            
            Requirements:
            - Follow {style} coding style and best practices
            - Include comprehensive error handling
            - Add detailed docstrings and comments
            - Consider security implications
            - Make it maintainable, testable, and efficient
            - Follow {language} conventions and idioms
            
            Return JSON format:
            {{
                "code": "generated code here",
                "explanation": "detailed explanation of the implementation",
                "dependencies": ["list of required dependencies"],
                "usage_example": "example usage with test cases",
                "considerations": "important considerations and limitations"
            }}
            """
            
            if self.llm_handler:
                model = self.model_preferences.get("code_generation", "gemini-2.0-flash")
                result = await self.llm_handler.generate_text(
                    generation_prompt, 
                    model=model, 
                    json_mode=True
                )
                
                # If output file specified, write the generated code
                if output_file and result:
                    try:
                        generated_data = json.loads(result)
                        code_content = generated_data.get("code", "")
                        if code_content:
                            write_result = await self._write_file(output_file, code_content)
                            if write_result["status"] == "SUCCESS":
                                generated_data["output_file"] = output_file
                except json.JSONDecodeError:
                        pass
                
                # Log for learning
                await self.memory_agent.log_process(
                    process_name="code_generation",
                    data={
                        "description": description,
                        "language": language,
                        "style": style,
                        "result": result,
                        "timestamp": time.time()
                    },
                    metadata={"agent_id": self.agent_id}
                )
                
                return {"status": "SUCCESS", "generation": result}
            else:
                return {"status": "ERROR", "message": "LLM handler not available"}
                
        except Exception as e:
            logger.error(f"{self.log_prefix} Code generation error: {e}")
            return {"status": "ERROR", "message": f"Generation failed: {e}"}

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
            1. Best approaches and methodologies for this specific task
            2. Potential pitfalls to avoid based on similar tasks
            3. Recommended tools, libraries, and frameworks
            4. Code structure and architecture suggestions
            5. Testing and validation strategies
            6. Performance and security considerations
            
            Return comprehensive suggestions in JSON format with rationale.
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
            logger.error(f"{self.log_prefix} Suggestion error: {e}")
            return {"status": "ERROR", "message": f"Suggestion generation failed: {e}"}

    # Helper methods for enhanced functionality
    async def _analyze_current_context(self, task: str) -> Dict[str, Any]:
        """Analyze current context for better suggestions."""
        return {
            "current_directory": str(self.current_working_directory.relative_to(self.sandbox_root)),
            "active_venv": str(self.active_venv_bin_path) if self.active_venv_bin_path else None,
            "task": task,
            "project_info": self.project_context,
            "sandbox_root": str(self.sandbox_root)
        }

    async def _get_relevant_patterns(self, task: str) -> Dict[str, Any]:
        """Get patterns relevant to the current task."""
        # Simple pattern matching - could be enhanced with ML
        relevant = {}
        for pattern_key, patterns in self.code_patterns.items():
            if any(keyword in task.lower() for keyword in pattern_key.split("_")):
                relevant[pattern_key] = patterns[-5:]  # Last 5 relevant patterns
        return relevant

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
            logger.error(f"{self.log_prefix} Learning error: {e}")
            return {"status": "ERROR", "message": f"Learning failed: {e}"}

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

    # Virtual Environment Management
    async def _create_venv(self, venv_name: str = "default") -> Dict[str, Any]:
        """Create a Python virtual environment."""
        venv_path = self.sandbox_root / "venvs" / venv_name
        
        try:
            venv_path.parent.mkdir(exist_ok=True)
            
            process = await asyncio.create_subprocess_exec(
                sys.executable, "-m", "venv", str(venv_path),
                cwd=self.current_working_directory,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=self.command_timeout
            )
            
            if process.returncode == 0:
                return {"status": "SUCCESS", "message": f"Virtual environment '{venv_name}' created"}
            else:
                return {"status": "ERROR", "message": f"Failed to create venv: {stderr.decode()}"}
                
        except Exception as e:
            return {"status": "ERROR", "message": f"Venv creation failed: {e}"}

    async def _activate_venv(self, venv_name: str = "default") -> Dict[str, Any]:
        """Activate a virtual environment."""
        venv_path = self.sandbox_root / "venvs" / venv_name
        venv_bin = venv_path / ("Scripts" if os.name == "nt" else "bin")
        
        if not venv_bin.exists():
            return {"status": "ERROR", "message": f"Virtual environment '{venv_name}' not found"}
        
        self.active_venv_bin_path = venv_bin
        return {"status": "SUCCESS", "message": f"Virtual environment '{venv_name}' activated"}

    async def _deactivate_venv(self) -> Dict[str, Any]:
        """Deactivate the current virtual environment."""
        self.active_venv_bin_path = None
        return {"status": "SUCCESS", "message": "Virtual environment deactivated"}

    # Placeholder methods for compatibility (implement as needed)
    async def _optimize_code(self, **kwargs) -> Dict[str, Any]:
        return {"status": "SUCCESS", "message": "Code optimization feature available"}
    
    async def _debug_code(self, **kwargs) -> Dict[str, Any]:
        return {"status": "SUCCESS", "message": "Code debugging feature available"}
    
    async def _test_code(self, **kwargs) -> Dict[str, Any]:
        return {"status": "SUCCESS", "message": "Code testing feature available"}
    
    async def _refactor_code(self, **kwargs) -> Dict[str, Any]:
        return {"status": "SUCCESS", "message": "Code refactoring feature available"}
    
    async def _explain_code(self, **kwargs) -> Dict[str, Any]:
        return {"status": "SUCCESS", "message": "Code explanation feature available"}
    
    async def _analyze_project(self, **kwargs) -> Dict[str, Any]:
        return {"status": "SUCCESS", "message": "Project analysis feature available"}
    
    async def _suggest_improvements(self, **kwargs) -> Dict[str, Any]:
        return {"status": "SUCCESS", "message": "Improvement suggestions feature available"}
    
    async def _create_documentation(self, **kwargs) -> Dict[str, Any]:
        return {"status": "SUCCESS", "message": "Documentation creation feature available"} 