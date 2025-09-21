#!/usr/bin/env python3
"""
Enhanced Simple Coder Agent - Integrated with UI Refresh and Update Functionality
Part of the mindX autonomous digital civilization system.

This enhanced version integrates features from:
- simple_coder.py (base functionality)
- simple_coder_agent.py (BDI integration)
- enhanced_simple_coder.py (advanced capabilities)

Features:
- Sandbox mode with automatic file backups
- Autonomous mode with infinite cycle iterations
- File update request mechanism with UI integration
- Enhanced security and validation
- Pattern learning and adaptation
- Memory integration
- UI refresh and approve functionality
"""

import os
import shutil
import time
import json
import logging
import hashlib
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
from pathlib import Path
import asyncio

# Memory integration
try:
    from agents.memory_agent import MemoryAgent, MemoryType, MemoryImportance
    MEMORY_AVAILABLE = True
except ImportError:
    MEMORY_AVAILABLE = False
    MemoryAgent = None
    MemoryType = None
    MemoryImportance = None

import aiofiles

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SimpleCoder:
    """
    Enhanced Simple Coder Agent with sandbox mode, autonomous operation capabilities,
    and full UI integration for refresh and update functionality.
    """
    
    def __init__(self, sandbox_mode: bool = True, autonomous_mode: bool = False):
        self.sandbox_mode = sandbox_mode
        self.autonomous_mode = autonomous_mode
        self.backup_dir = Path("simple_coder_backups")
        self.sandbox_dir = Path("simple_coder_sandbox")
        self.update_requests_file = self.sandbox_dir / "update_requests.json"
        self.update_requests = self._load_update_requests()
        self.cycle_count = 0
        # Set infinite cycles for autonomous mode
        self.max_cycles = float('inf') if autonomous_mode else 10
        
        # Initialize directories
        self._initialize_directories()
        
        # Pattern learning storage
        self.patterns = self._load_patterns()

        # Memory agent integration
        self.memory_agent = None
        if MEMORY_AVAILABLE:
            try:
                self.memory_agent = MemoryAgent()
                logger.info("Memory agent initialized for simple_coder")
            except Exception as e:
                logger.warning(f"Failed to initialize memory agent: {e}")
                self.memory_agent = None

    def _load_update_requests(self) -> List[Dict[str, Any]]:
        """Load update requests from persistent storage."""
        try:
            if self.update_requests_file.exists():
                with open(self.update_requests_file, 'r') as f:
                    return json.load(f)
        except Exception as e:
            logger.warning(f"Failed to load update requests: {e}")
        return []
    
    def _save_update_requests(self):
        """Save update requests to persistent storage."""
        try:
            with open(self.update_requests_file, 'w') as f:
                json.dump(self.update_requests, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save update requests: {e}")
    
    def _initialize_directories(self):
        """Initialize backup and sandbox directories."""
        self.backup_dir.mkdir(exist_ok=True)
        self.sandbox_dir.mkdir(exist_ok=True)
        
        # Create subdirectories for organization
        (self.backup_dir / "by_date").mkdir(exist_ok=True)
        (self.backup_dir / "by_file").mkdir(exist_ok=True)
        (self.sandbox_dir / "working").mkdir(exist_ok=True)
        (self.sandbox_dir / "completed").mkdir(exist_ok=True)
        
    def _load_patterns(self) -> Dict[str, Any]:
        """Load learned patterns from storage."""
        patterns_file = self.sandbox_dir / "patterns.json"
        if patterns_file.exists():
            try:
                with open(patterns_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Failed to load patterns: {e}")
        return {"file_patterns": {}, "code_patterns": {}, "success_rates": {}}
    
    def _save_patterns(self):
        """Save learned patterns to storage."""
        patterns_file = self.sandbox_dir / "patterns.json"
        try:
            with open(patterns_file, 'w') as f:
                json.dump(self.patterns, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save patterns: {e}")
    
    def _create_backup(self, file_path: str) -> str:
        """Create a backup of the file before modification."""
        if not os.path.exists(file_path):
            return None
            
        # Generate unique backup filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_hash = hashlib.md5(file_path.encode()).hexdigest()[:8]
        backup_name = f"{Path(file_path).stem}_{timestamp}_{file_hash}.bak"
        
        # Create date-based backup
        date_dir = self.backup_dir / "by_date" / datetime.now().strftime("%Y-%m-%d")
        date_dir.mkdir(exist_ok=True)
        backup_path = date_dir / backup_name
        
        # Create file-specific backup
        file_backup_dir = self.backup_dir / "by_file" / Path(file_path).stem
        file_backup_dir.mkdir(exist_ok=True)
        file_backup_path = file_backup_dir / backup_name
        
        try:
            # Copy to both locations
            shutil.copy2(file_path, backup_path)
            shutil.copy2(file_path, file_backup_path)
            
            logger.info(f"Backup created: {backup_path}")
            return str(backup_path)
        except Exception as e:
            logger.error(f"Failed to create backup: {e}")
            return None
    
    def _get_sandbox_path(self, original_path: str) -> str:
        """Get the sandbox path for a file."""
        if not self.sandbox_mode:
            return original_path
            
        # Create sandbox version
        sandbox_path = self.sandbox_dir / "working" / Path(original_path).name
        
        # Copy original to sandbox if it exists
        if os.path.exists(original_path) and not sandbox_path.exists():
            shutil.copy2(original_path, sandbox_path)
        elif not sandbox_path.exists():
            # Create empty file if original doesn't exist
            sandbox_path.touch()
            
        return str(sandbox_path)
    
    def _validate_file_operation(self, file_path: str, operation: str) -> bool:
        """Validate if file operation is safe and allowed."""
        # Security checks
        if not file_path or not isinstance(file_path, str):
            return False
            
        # Prevent operations on system files
        dangerous_paths = ['/etc/', '/sys/', '/proc/', '/dev/', '/boot/']
        if any(file_path.startswith(path) for path in dangerous_paths):
            logger.warning(f"Blocked operation on system path: {file_path}")
            return False
            
        # Check file extension for safety
        allowed_extensions = ['.py', '.js', '.html', '.css', '.json', '.md', '.txt', '.yml', '.yaml']                                                                                         
        if not any(file_path.endswith(ext) for ext in allowed_extensions):
            logger.warning(f"Blocked operation on non-allowed file type: {file_path}")
            return False
            
        return True
    
    async def process_directive(self, directive: str, target_file: Optional[str] = None) -> Dict[str, Any]:                                                                                   
        """
        Process a directive with enhanced simple_coder capabilities.
        
        Args:
            directive: The directive to process
            target_file: Optional target file to work on
            
        Returns:
            Dictionary containing results and changes
        """
        self.cycle_count += 1
        logger.info(f"Simple Coder Cycle {self.cycle_count}: Processing directive: {directive}")                                                                                              
        
        results = {
            "cycle": self.cycle_count,
            "directive": directive,
            "target_file": target_file,
            "sandbox_mode": self.sandbox_mode,
            "autonomous_mode": self.autonomous_mode,
            "changes": [],
            "backups": [],
            "update_requests": [],
            "timestamp": datetime.now().isoformat()
        }
        
        try:
            # Determine target file
            if not target_file:
                target_file = self._extract_target_file(directive)
            
            if not target_file:
                # Fallback to test file
                target_file = "test_simple_coder.py"
                logger.info(f"No target file specified, using: {target_file}")
            
            # Validate file operation
            if not self._validate_file_operation(target_file, "modify"):
                results["error"] = f"File operation not allowed: {target_file}"
                return results
            
            # Create backup if in sandbox mode
            if self.sandbox_mode and os.path.exists(target_file):
                backup_path = self._create_backup(target_file)
                if backup_path:
                    results["backups"].append(backup_path)
            
            # Get working file path (sandbox or original)
            working_file = self._get_sandbox_path(target_file)
            
            # Process the directive
            changes = await self._apply_directive(directive, working_file, target_file)
            results["changes"] = changes
            
            # Learn from this operation
            self._learn_from_operation(directive, target_file, changes)
            
            # If in sandbox mode, create update request
            if self.sandbox_mode and changes:
                update_request = self._create_update_request(target_file, working_file, changes)                                                                                              
                results["update_requests"].append(update_request)
                self.update_requests.append(update_request)
                self._save_update_requests()
            
            # Check if should continue (autonomous mode)
            if self.autonomous_mode:
                if self.max_cycles == float('inf'):
                    logger.info("Autonomous mode: Infinite cycles enabled - continuing")
                    results["continue_autonomous"] = True
                    results["infinite_mode"] = True
                elif self.cycle_count < self.max_cycles:
                    logger.info(f"Autonomous mode: Continuing to next cycle ({self.cycle_count}/{self.max_cycles})")                                                                          
                    results["continue_autonomous"] = True
                else:
                    logger.info("Autonomous mode: Max cycles reached")
                    results["continue_autonomous"] = False
            
        except Exception as e:
            logger.error(f"Error in process_directive: {e}")
            results["error"] = str(e)
        
        return results
    
    def _extract_target_file(self, directive: str) -> Optional[str]:
        """Extract target file from directive."""
        # Look for file patterns in directive
        import re
        
        # Common file patterns
        patterns = [
            r'evolve\s+(\w+\.py)',
            r'update\s+(\w+\.py)',
            r'modify\s+(\w+\.py)',
            r'(\w+\.py)',
            r'(\w+\.js)',
            r'(\w+\.html)',
            r'(\w+\.css)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, directive, re.IGNORECASE)
            if match:
                return match.group(1)
        
        return None
    
    async def _apply_directive(self, directive: str, working_file: str, original_file: str) -> List[Dict[str, Any]]:                                                                          
        """Apply the directive to the working file."""
        changes = []
        
        try:
            # Read current content
            if os.path.exists(working_file):
                with open(working_file, 'r', encoding='utf-8') as f:
                    content = f.read()
            else:
                content = ""
            
            # Generate enhanced code based on directive
            enhanced_code = self._generate_enhanced_code(directive, self.cycle_count)
            
            # Apply changes
            if "def test_function():" in content:
                # Modify existing function
                new_content = content.replace(
                    "def test_function():\n    return 'original'",
                    f"def test_function():\n    # Enhanced by Simple Coder cycle {self.cycle_count}\n    return f'simple_coder_{self.cycle_count}'"                                           
                )
            else:
                # Add new content
                new_content = content + "\n" + enhanced_code
            
            # Write changes
            with open(working_file, 'w', encoding='utf-8') as f:
                f.write(new_content)
            
            # Record changes
            changes.append({
                "file": working_file,
                "type": "modification" if os.path.exists(working_file) else "creation",
                "changes": [
                    {
                        "line": len(content.split('\n')) + 1,
                        "old": "",
                        "new": enhanced_code.strip()
                    }
                ]
            })
            
        except Exception as e:
            logger.error(f"Error applying directive: {e}")
            changes.append({
                "file": f"simple_coder_error_{self.cycle_count}.txt",
                "type": "error",
                "changes": [
                    {
                        "line": 1,
                        "old": "",
                        "new": f"Simple Coder Error Cycle {self.cycle_count}: {str(e)}"
                    }
                ]
            })
        
        return changes
    
    def _generate_enhanced_code(self, directive: str, cycle: int) -> str:
        """Generate enhanced code based on directive and cycle."""
        return f'''
def simple_coder_cycle_{cycle}_function():
    """Enhanced function added by Simple Coder cycle {cycle}"""
    return {{
        'cycle': {cycle},
        'directive': '{directive}',
        'approach': 'simple_coder_enhanced',
        'timestamp': time.time(),
        'sandbox_mode': {self.sandbox_mode},
        'autonomous_mode': {self.autonomous_mode}
    }}

def enhanced_processing_v{cycle}():
    """Enhanced processing with improved error handling and logging"""
    try:
        result = f'Enhanced processing completed for cycle {cycle}'
        logger.info(f"Enhanced processing successful: {{result}}")
        return result
    except Exception as e:
        logger.error(f"Enhanced processing failed: {{e}}")
        return f'Error: {{e}}'

# Simple Coder Pattern Learning
def learn_pattern_{cycle}():
    """Pattern learning function for cycle {cycle}"""
    patterns = {{
        'directive_pattern': '{directive}',
        'cycle': {cycle},
        'success_rate': 0.0,
        'learned_at': time.time()
    }}
    return patterns
'''
    
    def _learn_from_operation(self, directive: str, target_file: str, changes: List[Dict[str, Any]]):                                                                                         
        """Learn patterns from successful operations."""
        if not changes:
            return
            
        # Update success rates
        file_key = Path(target_file).stem
        if file_key not in self.patterns["success_rates"]:
            self.patterns["success_rates"][file_key] = []
        
        self.patterns["success_rates"][file_key].append({
            "cycle": self.cycle_count,
            "success": True,
            "changes_count": len(changes),
            "timestamp": time.time()
        })
        
        # Update file patterns
        if file_key not in self.patterns["file_patterns"]:
            self.patterns["file_patterns"][file_key] = []
        
        self.patterns["file_patterns"][file_key].append({
            "directive": directive,
            "cycle": self.cycle_count,
            "timestamp": time.time()
        })
        
        # Save patterns
        self._save_patterns()
    
    def _create_update_request(self, original_file: str, sandbox_file: str, changes: List[Dict[str, Any]]) -> Dict[str, Any]:                                                                 
        """Create an update request for applying sandbox changes to original file."""
        return {
            "request_id": f"update_{int(time.time())}_{self.cycle_count}",
            "original_file": original_file,
            "sandbox_file": sandbox_file,
            "changes": changes,
            "cycle": self.cycle_count,
            "timestamp": datetime.now().isoformat(),
            "status": "pending",
            "backup_created": len(self.update_requests) > 0
        }
    
    def get_update_requests(self) -> List[Dict[str, Any]]:
        """Get all pending update requests."""
        return self.update_requests
    
    def approve_update_request(self, request_id: str) -> bool:
        """Approve and apply an update request."""
        for request in self.update_requests:
            if request["request_id"] == request_id:
                try:
                    # Apply changes to original file
                    shutil.copy2(request["sandbox_file"], request["original_file"])
                    request["status"] = "approved"
                    self._save_update_requests()
                    request["applied_at"] = datetime.now().isoformat()
                    logger.info(f"Update request {request_id} approved and applied")
                    return True
                except Exception as e:
                    logger.error(f"Failed to apply update request {request_id}: {e}")
                    request["status"] = "failed"
                    request["error"] = str(e)
                    return False
        return False
    
    def reject_update_request(self, request_id: str) -> bool:
        """Reject an update request."""
        for request in self.update_requests:
            if request["request_id"] == request_id:
                request["status"] = "rejected"
                self._save_update_requests()
                request["rejected_at"] = datetime.now().isoformat()
                logger.info(f"Update request {request_id} rejected")
                return True
        return False
    
    def update_mode(self, autonomous_mode: bool = None, max_cycles: int = None):
        """Update autonomous mode and max cycles from UI."""
        if autonomous_mode is not None:
            self.autonomous_mode = autonomous_mode
            # Update max_cycles based on autonomous mode
            if autonomous_mode:
                self.max_cycles = float('inf')
                logger.info("Autonomous mode enabled - setting infinite cycles")
            else:
                self.max_cycles = max_cycles if max_cycles is not None else 10
                logger.info(f"Autonomous mode disabled - setting max cycles to {self.max_cycles}")                                                                                            
        elif max_cycles is not None and not self.autonomous_mode:
            self.max_cycles = max_cycles
            logger.info(f"Updated max cycles to {self.max_cycles}")
    
    def get_status(self) -> Dict[str, Any]:
        """Get current status of the Simple Coder - Enhanced for UI integration."""
        return {
            "status": "active",
            "sandbox_mode": self.sandbox_mode,
            "autonomous_mode": self.autonomous_mode,
            "pending_updates": len([r for r in self.update_requests if r["status"] == "pending"]),
            "total_updates": len(self.update_requests),
            "working_directory": str(self.sandbox_dir / "working"),
            "last_activity": time.time(),
            "cycle_count": self.cycle_count,
            "max_cycles": self.max_cycles,
            "infinite_mode": self.max_cycles == float('inf'),
            "patterns_learned": len(self.patterns.get("file_patterns", {})),
            "backup_dir": str(self.backup_dir),
            "sandbox_dir": str(self.sandbox_dir)
        }

    async def _log_to_memory(self, memory_type: str, category: str, data: Dict[str, Any], metadata: Dict[str, Any] = None) -> Optional[Path]:                                                 
        """Log information to memory agent if available."""
        if not self.memory_agent:
            return None
        
        try:
            if metadata is None:
                metadata = {}
            
            # Add simple_coder specific metadata
            metadata.update({
                "agent": "simple_coder",
                "sandbox_mode": self.sandbox_mode,
                "autonomous_mode": self.autonomous_mode,
                "cycle_count": self.cycle_count
            })
            
            # Use the memory agent's save_memory method
            return await self.memory_agent.save_memory(memory_type, f"simple_coder/{category}", data, metadata)                                                                               
        except Exception as e:
            logger.error(f"Failed to log to memory: {e}")
            return None
    
    async def _log_cycle_start(self, cycle: int, directive: str) -> None:
        """Log cycle start to memory."""
        data = {
            "cycle": cycle,
            "directive": directive,
            "timestamp": datetime.now().isoformat(),
            "status": "started"
        }
        await self._log_to_memory("STM", "cycles", data)
    
    async def _log_cycle_completion(self, cycle: int, directive: str, results: Dict[str, Any]) -> None:                                                                                       
        """Log cycle completion to memory."""
        data = {
            "cycle": cycle,
            "directive": directive,
            "timestamp": datetime.now().isoformat(),
            "status": "completed",
            "results": {
                "changes_made": len(results.get("changes", [])),
                "update_requests": len(results.get("update_requests", [])),
                "success": results.get("success", False)
            }
        }
        await self._log_to_memory("STM", "cycles", data)
    
    async def _log_file_operation(self, operation: str, file_path: str, success: bool, details: Dict[str, Any] = None) -> None:                                                               
        """Log file operations to memory."""
        data = {
            "operation": operation,
            "file_path": file_path,
            "success": success,
            "timestamp": datetime.now().isoformat(),
            "details": details or {}
        }
        await self._log_to_memory("STM", "file_operations", data)
    
    async def _log_update_request(self, request: Dict[str, Any]) -> None:
        """Log update request creation to memory."""
        data = {
            "request_id": request.get("request_id"),
            "original_file": request.get("original_file"),
            "sandbox_file": request.get("sandbox_file"),
            "timestamp": request.get("timestamp"),
            "status": request.get("status"),
            "changes_count": len(request.get("changes", []))
        }
        await self._log_to_memory("STM", "update_requests", data)
    
    async def _log_error(self, error_type: str, error_message: str, context: Dict[str, Any] = None) -> None:                                                                                  
        """Log errors to memory."""
        data = {
            "error_type": error_type,
            "error_message": error_message,
            "timestamp": datetime.now().isoformat(),
            "context": context or {}
        }
        await self._log_to_memory("STM", "errors", data)

    def cleanup(self):
        """Clean up temporary files and directories."""
        try:
            # Move completed sandbox files
            if self.sandbox_dir.exists():
                completed_dir = self.sandbox_dir / "completed"
                completed_dir.mkdir(exist_ok=True)
                
                for file in (self.sandbox_dir / "working").glob("*"):
                    if file.is_file():
                        shutil.move(str(file), str(completed_dir / file.name))
            
            logger.info("Simple Coder cleanup completed")
        except Exception as e:
            logger.error(f"Cleanup failed: {e}")


# Standalone functions for backward compatibility
async def execute_simple_coder_changes(directive: str, cycle: int, sandbox_mode: bool = True, autonomous_mode: bool = False) -> List[Dict[str, Any]]:                                         
    """
    Execute changes using simple_coder approach with enhanced features.
    This function maintains backward compatibility with the existing system.
    """
    simple_coder = SimpleCoder(sandbox_mode=sandbox_mode, autonomous_mode=autonomous_mode)
    results = await simple_coder.process_directive(directive)
    
    # Convert to expected format
    changes = []
    for change in results.get("changes", []):
        changes.append({
            "file": change["file"],
            "type": change["type"],
            "changes": change["changes"]
        })
    
    return changes


# Example usage and testing
if __name__ == "__main__":
    async def main():
        # Test the Simple Coder
        simple_coder = SimpleCoder(sandbox_mode=True, autonomous_mode=False)
        
        # Process a test directive
        results = await simple_coder.process_directive("evolve test_file.py")
        print("Results:", json.dumps(results, indent=2))
        
        # Show status
        status = simple_coder.get_status()
        print("Status:", json.dumps(status, indent=2))
        
        # Show update requests
        requests = simple_coder.get_update_requests()
        print("Update Requests:", json.dumps(requests, indent=2))
    
    # Run the test
    asyncio.run(main())
