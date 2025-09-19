#!/usr/bin/env python3
"""
Simple Coder Agent - Streamlined and Audited Version
====================================================

A comprehensive coding agent providing intelligent assistance to the BDI agent.
This is an improved, audited version of the enhanced_simple_coder with better
error handling, security, and performance optimizations.

Features:
- Advanced code analysis and generation
- Secure file system operations
- Shell command execution with safety checks
- Multi-model intelligence for different coding tasks
- Memory integration for learning and improvement
- Context-aware suggestions and optimizations
- Virtual environment management
- Comprehensive error handling and logging
"""

import asyncio
import json
import shlex
import sys
import os
import re
import subprocess
import time
import hashlib
from pathlib import Path
from typing import Dict, Any, Optional, List, Callable, Awaitable, TypeAlias, Tuple
from dataclasses import dataclass
from enum import Enum

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

class OperationType(Enum):
    """Enumeration of supported operation types."""
    FILE_READ = "read_file"
    FILE_WRITE = "write_file"
    FILE_DELETE = "delete_file"
    DIR_LIST = "list_directory"
    DIR_CREATE = "create_directory"
    SHELL_COMMAND = "run_shell_command"
    CODE_ANALYZE = "analyze_code"
    CODE_GENERATE = "generate_code"
    CODE_SUGGEST = "get_coding_suggestions"
    VENV_CREATE = "create_venv"
    VENV_ACTIVATE = "activate_venv"
    VENV_DEACTIVATE = "deactivate_venv"

@dataclass
class SecurityConfig:
    """Security configuration for the agent."""
    max_file_size_mb: int = 10
    allowed_commands: List[str] = None
    sandbox_enabled: bool = True
    max_execution_time: int = 60
    
    def __post_init__(self):
        if self.allowed_commands is None:
            self.allowed_commands = [
                "python", "python3", "pip", "pip3", "git", "ls", "cat", "grep", 
                "find", "mkdir", "rm", "cp", "mv", "chmod", "touch", "head", 
                "tail", "wc", "pytest", "black", "flake8", "mypy", "coverage", 
                "tox", "which", "echo", "grep", "sed", "awk"
            ]

class SimpleCoder(BaseTool):
    """
    Streamlined coding agent providing intelligent assistance to the BDI agent.
    
    This is an improved, audited version with:
    - Better error handling and validation
    - Enhanced security measures
    - Optimized performance
    - Cleaner code structure
    - Comprehensive logging
    """

    def __init__(self, 
                 memory_agent: Optional[MemoryAgent] = None,
                 config: Optional[Config] = None,
                 llm_handler: Optional[LLMHandlerInterface] = None,
                 **kwargs):
        super().__init__(config=config, llm_handler=llm_handler, **kwargs)
        
        # Core components
        self.memory_agent = memory_agent or MemoryAgent()
        self.config_data = {}
        self.security_config = SecurityConfig()
        
        # Working environment
        self.sandbox_root = None
        self.current_working_directory = None
        self.active_venv_bin_path = None
        
        # Learning and patterns
        self.code_patterns = {}
        self.execution_history = []
        
        # Model preferences for different tasks
        self.model_preferences = {
            "code_analysis": "gemini-1.5-pro-latest",
            "code_generation": "gemini-2.0-flash",
            "suggestions": "gemini-1.5-pro-latest",
            "debugging": "gemini-1.5-pro-latest"
        }
        
        # Initialize the agent
        self._load_configuration()
        self._initialize_sandbox()
        self._register_handlers()
        
        logger.info(f"SimpleCoder initialized with sandbox: {self.sandbox_root}")

    def _load_configuration(self):
        """Load configuration with enhanced defaults and validation."""
        default_config = {
            "command_timeout_seconds": 60,
            "max_file_size_mb": 10,
            "enable_code_analysis": True,
            "enable_auto_testing": True,
            "enable_pattern_learning": True,
            "sandbox_path": "data/agent_workspaces/simple_coder",
            "security": {
                "max_file_size_mb": 10,
                "allowed_commands": self.security_config.allowed_commands,
                "sandbox_enabled": True,
                "max_execution_time": 60
            }
        }
        
        # Load from config file if available
        config_path = PROJECT_ROOT / "data" / "config" / "simple_coder.json"
        if config_path.exists():
            try:
                with config_path.open("r", encoding="utf-8") as f:
                    loaded_config = json.load(f)
                    self.config_data = {**default_config, **loaded_config}
            except (json.JSONDecodeError, IOError) as e:
                logger.warning(f"Failed to load config: {e}. Using defaults.")
                self.config_data = default_config
        else:
            self.config_data = default_config
        
        # Update security config
        if "security" in self.config_data:
            security_data = self.config_data["security"]
            self.security_config = SecurityConfig(**security_data)

    def _initialize_sandbox(self) -> Path:
        """Create and initialize the secure sandbox directory."""
        default_sandbox = PROJECT_ROOT / "data" / "agent_workspaces" / "simple_coder"
        sandbox_path_str = self.config_data.get("sandbox_path", str(default_sandbox.relative_to(PROJECT_ROOT)))
        sandbox_abs_path = (PROJECT_ROOT / sandbox_path_str).resolve()
        
        # Security check: ensure sandbox is within project root
        if not sandbox_abs_path.is_relative_to(PROJECT_ROOT) or sandbox_abs_path == PROJECT_ROOT:
            logger.critical(f"INSECURE SANDBOX CONFIG: '{sandbox_path_str}'. Using default.")
            sandbox_abs_path = default_sandbox
        
        # Create sandbox structure
        sandbox_abs_path.mkdir(parents=True, exist_ok=True)
        (sandbox_abs_path / "projects").mkdir(exist_ok=True)
        (sandbox_abs_path / "temp").mkdir(exist_ok=True)
        (sandbox_abs_path / "tests").mkdir(exist_ok=True)
        (sandbox_abs_path / "generated").mkdir(exist_ok=True)
        (sandbox_abs_path / "venvs").mkdir(exist_ok=True)
        
        self.sandbox_root = sandbox_abs_path
        self.current_working_directory = sandbox_abs_path
        
        return sandbox_abs_path

    def _register_handlers(self):
        """Register all operation handlers."""
        self.native_handlers = {
            OperationType.FILE_READ.value: self._read_file,
            OperationType.FILE_WRITE.value: self._write_file,
            OperationType.FILE_DELETE.value: self._delete_file,
            OperationType.DIR_LIST.value: self._list_directory,
            OperationType.DIR_CREATE.value: self._create_directory,
            OperationType.SHELL_COMMAND.value: self._run_shell_command,
            OperationType.CODE_ANALYZE.value: self._analyze_code,
            OperationType.CODE_GENERATE.value: self._generate_code,
            OperationType.CODE_SUGGEST.value: self._get_coding_suggestions,
            OperationType.VENV_CREATE.value: self._create_venv,
            OperationType.VENV_ACTIVATE.value: self._activate_venv,
            OperationType.VENV_DEACTIVATE.value: self._deactivate_venv,
        }

    def _resolve_and_check_path(self, path_str: str) -> Optional[Path]:
        """Resolve a path and ensure it's within the sandbox for security."""
        try:
            if os.path.isabs(path_str):
                target_path = Path(path_str).resolve()
            else:
                target_path = (self.current_working_directory / path_str).resolve()
            
            # Security check: ensure path is within sandbox
            if target_path.is_relative_to(self.sandbox_root):
                return target_path
            else:
                logger.warning(f"Path outside sandbox rejected: {path_str}")
                return None
        except Exception as e:
            logger.error(f"Path resolution error: {e}")
            return None

    def _validate_file_size(self, file_path: Path) -> bool:
        """Validate file size against security limits."""
        try:
            file_size_mb = file_path.stat().st_size / (1024 * 1024)
            return file_size_mb <= self.security_config.max_file_size_mb
        except OSError:
            return False

    async def execute(self, action: str = None, operation: str = None, **kwargs) -> Tuple[bool, Any]:
        """
        Enhanced execute method with intelligent routing and validation.
        Supports both 'action' and 'operation' parameters for compatibility.
        """
        op = action or operation
        if not op:
            return False, "No action or operation specified"
        
        # Validate operation
        if op not in self.native_handlers:
            return False, f"Unknown operation: {op}"
        
        start_time = time.time()
        
        try:
            # Execute the operation
            result = await self.native_handlers[op](**kwargs)
            
            # Log execution for learning
            execution_context = {
                "operation": op,
                "parameters": kwargs,
                "duration": time.time() - start_time,
                "timestamp": time.time()
            }
            
            await self._learn_from_execution(result, execution_context)
            
            # Convert dict result to tuple for compatibility
            if isinstance(result, dict):
                success = result.get("status") == "SUCCESS"
                return success, result
            else:
                return True, result
                
        except Exception as e:
            logger.error(f"SimpleCoder execution error: {e}")
            return False, f"Execution failed: {e}"

    # File System Operations
    async def _read_file(self, path: str) -> Dict[str, Any]:
        """Read file contents with security validation."""
        file_path = self._resolve_and_check_path(path)
        if not file_path or not file_path.is_file():
            return {"status": "ERROR", "message": f"File not found or invalid: {path}"}
        
        # Validate file size
        if not self._validate_file_size(file_path):
            return {"status": "ERROR", "message": f"File too large: {path}"}
        
        try:
            content = await asyncio.to_thread(file_path.read_text, encoding='utf-8')
            return {
                "status": "SUCCESS", 
                "content": content,
                "file_path": str(file_path),
                "size": len(content)
            }
        except Exception as e:
            return {"status": "ERROR", "message": f"Error reading file: {e}"}

    async def _write_file(self, path: str, content: str, create_dirs: bool = True) -> Dict[str, Any]:
        """Write content to file with security validation."""
        file_path = self._resolve_and_check_path(path)
        if not file_path:
            return {"status": "ERROR", "message": f"Invalid or insecure path: {path}"}
        
        # Validate content size
        content_size_mb = len(content.encode('utf-8')) / (1024 * 1024)
        if content_size_mb > self.security_config.max_file_size_mb:
            return {"status": "ERROR", "message": f"Content too large: {content_size_mb:.2f}MB"}
        
        try:
            if create_dirs:
                await asyncio.to_thread(file_path.parent.mkdir, parents=True, exist_ok=True)
            
            await asyncio.to_thread(file_path.write_text, content, encoding='utf-8')
            return {
                "status": "SUCCESS", 
                "message": f"File written successfully to {path}",
                "file_path": str(file_path),
                "size": len(content)
            }
        except Exception as e:
            return {"status": "ERROR", "message": f"Error writing file: {e}"}

    async def _delete_file(self, path: str, force: bool = False) -> Dict[str, Any]:
        """Delete file with safety checks."""
        if not force:
            return {"status": "ERROR", "message": "Deletion requires 'force=True' parameter"}
        
        file_path = self._resolve_and_check_path(path)
        if not file_path or not file_path.is_file():
            return {"status": "ERROR", "message": f"File not found: {path}"}
        
        try:
            await asyncio.to_thread(file_path.unlink)
            return {"status": "SUCCESS", "message": f"File deleted: {path}"}
        except Exception as e:
            return {"status": "ERROR", "message": f"Error deleting file: {e}"}

    async def _list_directory(self, path: str = ".") -> Dict[str, Any]:
        """List directory contents with security validation."""
        dir_path = self._resolve_and_check_path(path)
        if not dir_path or not dir_path.is_dir():
            return {"status": "ERROR", "message": f"Directory not found: {path}"}
        
        try:
            items = []
            for item in dir_path.iterdir():
                try:
                    stat_info = item.stat()
                    items.append({
                        "name": item.name,
                        "type": "directory" if item.is_dir() else "file",
                        "size": stat_info.st_size if item.is_file() else None,
                        "modified": stat_info.st_mtime
                    })
                except OSError:
                    # Skip items we can't access
                    continue
            
            return {"status": "SUCCESS", "items": items}
        except Exception as e:
            return {"status": "ERROR", "message": f"Error listing directory: {e}"}

    async def _create_directory(self, path: str) -> Dict[str, Any]:
        """Create directory with security validation."""
        dir_path = self._resolve_and_check_path(path)
        if not dir_path:
            return {"status": "ERROR", "message": "Invalid or insecure directory path"}
        
        try:
            await asyncio.to_thread(dir_path.mkdir, parents=True, exist_ok=True)
            return {"status": "SUCCESS", "message": f"Directory created: {path}"}
        except Exception as e:
            return {"status": "ERROR", "message": f"Failed to create directory: {e}"}

    # Shell Command Execution
    async def _run_shell_command(self, command: str, args: Optional[List[str]] = None) -> Dict[str, Any]:
        """Execute shell command with security validation."""
        # Validate command against allowlist
        if command not in self.security_config.allowed_commands:
            return {"status": "ERROR", "message": f"Command '{command}' not allowed"}
        
        try:
            cmd_args = [command] + (args or [])
            
            # Create subprocess with timeout
            process = await asyncio.create_subprocess_exec(
                *cmd_args,
                cwd=self.current_working_directory,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            # Wait for completion with timeout
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=self.security_config.max_execution_time
            )
            
            return {
                "status": "SUCCESS",
                "stdout": stdout.decode('utf-8', errors='replace'),
                "stderr": stderr.decode('utf-8', errors='replace'),
                "return_code": process.returncode,
                "command": " ".join(cmd_args)
            }
            
        except asyncio.TimeoutError:
            return {"status": "ERROR", "message": f"Command timed out after {self.security_config.max_execution_time}s"}
        except Exception as e:
            return {"status": "ERROR", "message": f"Command execution failed: {e}"}

    # Code Analysis and Generation
    async def _analyze_code(self, code: Optional[str] = None, file_path: Optional[str] = None, 
                          analysis_type: str = "comprehensive") -> Dict[str, Any]:
        """Analyze code for quality and improvements."""
        try:
            # Get code content
            if file_path:
                file_obj = self._resolve_and_check_path(file_path)
                if not file_obj or not file_obj.is_file():
                    return {"status": "ERROR", "message": f"Invalid file path: {file_path}"}
                code = await asyncio.to_thread(file_obj.read_text, encoding='utf-8')
            
            if not code:
                return {"status": "ERROR", "message": "No code content provided"}
            
            # Create analysis prompt
            analysis_prompt = f"""
            Perform {analysis_type} analysis of this code:
            
            ```python
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
            logger.error(f"Code analysis error: {e}")
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
                
                # Write to file if specified
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
            logger.error(f"Code generation error: {e}")
            return {"status": "ERROR", "message": f"Generation failed: {e}"}

    async def _get_coding_suggestions(self, current_task: str) -> Dict[str, Any]:
        """Get intelligent coding suggestions based on current task."""
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
                    model=self.model_preferences.get("suggestions", "gemini-1.5-pro-latest"),
                    json_mode=True
                )
                
                return {"status": "SUCCESS", "suggestions": suggestions}
            else:
                return {"status": "ERROR", "message": "LLM handler not available"}
                
        except Exception as e:
            logger.error(f"Suggestion error: {e}")
            return {"status": "ERROR", "message": f"Suggestion generation failed: {e}"}

    # Virtual Environment Management
    async def _create_venv(self, venv_name: str = "default") -> Dict[str, Any]:
        """Create a Python virtual environment."""
        venv_path = self.sandbox_root / "venvs" / venv_name
        
        try:
            await asyncio.to_thread(venv_path.parent.mkdir, exist_ok=True)
            
            process = await asyncio.create_subprocess_exec(
                sys.executable, "-m", "venv", str(venv_path),
                cwd=self.current_working_directory,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=self.security_config.max_execution_time
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

    # Helper methods
    async def _analyze_current_context(self, task: str) -> Dict[str, Any]:
        """Analyze current context for better suggestions."""
        return {
            "current_directory": str(self.current_working_directory.relative_to(self.sandbox_root)),
            "active_venv": str(self.active_venv_bin_path) if self.active_venv_bin_path else None,
            "task": task,
            "sandbox_root": str(self.sandbox_root),
            "available_operations": list(self.native_handlers.keys())
        }

    async def _get_relevant_patterns(self, task: str) -> Dict[str, Any]:
        """Get patterns relevant to the current task."""
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
            logger.error(f"Learning error: {e}")
            return {"status": "ERROR", "message": f"Learning failed: {e}"}

    async def _update_coding_patterns(self, learning_data: Dict[str, Any]):
        """Update coding patterns based on learning data."""
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

    # Additional utility methods
    async def get_status(self) -> Dict[str, Any]:
        """Get current agent status and capabilities."""
        return {
            "status": "active",
            "agent_type": "SimpleCoder",
            "sandbox_root": str(self.sandbox_root),
            "current_directory": str(self.current_working_directory.relative_to(self.sandbox_root)),
            "active_venv": str(self.active_venv_bin_path) if self.active_venv_bin_path else None,
            "available_operations": list(self.native_handlers.keys()),
            "security_config": {
                "max_file_size_mb": self.security_config.max_file_size_mb,
                "allowed_commands": self.security_config.allowed_commands,
                "sandbox_enabled": self.security_config.sandbox_enabled,
                "max_execution_time": self.security_config.max_execution_time
            },
            "learning_enabled": self.config_data.get("enable_pattern_learning", True),
            "pattern_count": sum(len(patterns) for patterns in self.code_patterns.values())
        }

    async def cleanup(self) -> Dict[str, Any]:
        """Cleanup resources and save learning data."""
        try:
            # Save learning data
            if self.code_patterns:
                patterns_file = self.sandbox_root / "learned_patterns.json"
                await asyncio.to_thread(
                    patterns_file.write_text,
                    json.dumps(self.code_patterns, indent=2),
                    encoding='utf-8'
                )
            
            return {"status": "SUCCESS", "message": "Cleanup completed"}
        except Exception as e:
            logger.error(f"Cleanup error: {e}")
            return {"status": "ERROR", "message": f"Cleanup failed: {e}"}

# Factory function for easy instantiation
def create_simple_coder(memory_agent: Optional[MemoryAgent] = None, 
                       config: Optional[Config] = None,
                       llm_handler: Optional[LLMHandlerInterface] = None) -> SimpleCoder:
    """Create a SimpleCoder instance with optional dependencies."""
    return SimpleCoder(
        memory_agent=memory_agent,
        config=config,
        llm_handler=llm_handler
    )

# Export the main class
__all__ = ['SimpleCoder', 'create_simple_coder', 'OperationType', 'SecurityConfig']
