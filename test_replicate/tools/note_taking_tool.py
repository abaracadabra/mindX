# mindx/tools/note_taking_tool.py
"""
NoteTakingTool for MindX agents.
Allows agents to create, read, update, and delete textual notes.
"""
import asyncio
import re
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional

import aiofiles

from core.bdi_agent import BaseTool
from utils.config import Config, PROJECT_ROOT
from utils.logging_config import get_logger
from agents.memory_agent import MemoryAgent

logger = get_logger(__name__)

class NoteTakingTool(BaseTool):
    """Tool for taking and managing textual notes, stored as files."""
    
    def __init__(self, 
                 memory_agent: MemoryAgent,
                 config: Optional[Config] = None,
                 **kwargs: Any):
        """
        Initializes the NoteTakingTool.
        
        Args:
            memory_agent: The memory agent for getting data directories.
            config: Optional Config instance.
            **kwargs: Catches any other arguments from the BDI agent.
        """
        super().__init__(config=config, **kwargs)
        self.memory_agent = memory_agent
        
        # The notes directory is now determined by the calling agent's workspace
        if self.bdi_agent_ref and hasattr(self.bdi_agent_ref, 'agent_id'):
            calling_agent_id = self.bdi_agent_ref.agent_id
            self.notes_dir = self.memory_agent.get_agent_data_directory(calling_agent_id) / "notes"
        else:
            # Fallback to a general notes directory if the tool is somehow used without a BDI agent context
            self.notes_dir = self.memory_agent.get_agent_data_directory("general_note_taking_tool") / "notes"

        try:
            self.notes_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"NoteTakingTool initialized. Notes directory: {self.notes_dir}")
        except Exception as e:
            logger.error(f"NoteTakingTool: Failed to create notes directory {self.notes_dir}: {e}", exc_info=True)
            raise

    def _sanitize_filename(self, name: str) -> str:
        """Sanitizes a string into a safe filename."""
        if not name or not isinstance(name, str):
            raise ValueError("Filename base must be a non-empty string.")
        
        sanitized = re.sub(r'[^\w\-\.]', '_', name)
        sanitized = re.sub(r'_+', '_', sanitized)
        sanitized = sanitized.strip('_.')
        
        if not sanitized:
            return f"note_{str(uuid.uuid4())[:8]}"
        
        return sanitized[:100] # Limit length

    def _get_note_path(self, topic: Optional[str] = None, file_name: Optional[str] = None) -> Path:
        """
        Constructs the full path for a note file, creating subdirectories from topic.
        """
        target_dir = self.notes_dir
        note_name = ""

        if topic:
            # Treat topic as a potential path
            path_parts = [self._sanitize_filename(part) for part in re.split(r'[\\/]', topic)]
            
            # Limit directory depth
            if len(path_parts) > 10:
                logger.warning(f"Topic path depth exceeds 10, truncating: {topic}")
                path_parts = path_parts[:10]

            if len(path_parts) > 1:
                target_dir = self.notes_dir.joinpath(*path_parts[:-1])
            
            note_name = path_parts[-1]

        if file_name:
            # file_name overrides the note name part of the topic
            note_name = self._sanitize_filename(Path(file_name).stem)
        
        if not note_name:
            # Fallback if topic and file_name are empty or just slashes
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            note_name = f"note_{timestamp}"

        # Create the directory structure if it doesn't exist
        target_dir.mkdir(parents=True, exist_ok=True)

        return target_dir / f"{note_name}.md"

    async def execute(self, **kwargs) -> Dict[str, Any]:
        """
        Executes a note-taking action based on provided parameters.

        Args (from kwargs):
            action (str): The action to perform. Supported: 'add', 'update', 'read', 'delete', 'list'.
            content (str): The content of the note (required for 'add', 'update').
            topic (Optional[str]): A topic to derive the filename from if 'file_name' is not provided.
            file_name (Optional[str]): The specific filename for the note.
        """
        action = kwargs.get("action")
        content = kwargs.get("content")
        topic = kwargs.get("topic")
        file_name = kwargs.get("file_name")

        if not action:
            return {"status": "error", "message": "Missing required parameter: 'action'."}
        
        action = action.lower()
        
        try:
            if action in ["add", "update", "read", "delete"]:
                if not topic and not file_name:
                    return {"status": "error", "message": "Either 'topic' or 'file_name' is required for this action."}
            
            file_path = self._get_note_path(topic=topic, file_name=file_name)

            if action == "add" or action == "update":
                if content is None:
                    return {"status": "error", "message": f"Missing 'content' parameter for '{action}' action."}
                
                async with aiofiles.open(file_path, "w", encoding="utf-8") as f:
                    await f.write(content)
                
                message = f"Note '{file_path.name}' created." if action == "add" else f"Note '{file_path.name}' updated."
                return {"status": "success", "message": message, "file_path": str(file_path)}

            elif action == "read":
                if not file_path.exists():
                    return {"status": "error", "message": f"Note '{file_path.name}' not found."}
                async with aiofiles.open(file_path, "r", encoding="utf-8") as f:
                    read_content = await f.read()
                return {"status": "success", "file_path": str(file_path), "content": read_content}

            elif action == "delete":
                if not file_path.exists():
                    return {"status": "error", "message": f"Note '{file_path.name}' not found for deletion."}
                file_path.unlink()
                return {"status": "success", "message": f"Note '{file_path.name}' deleted."}

            elif action == "list":
                # Recursively list all markdown files in the notes directory
                notes_files = [str(p.relative_to(self.notes_dir)) for p in self.notes_dir.rglob('*.md')]
                if not notes_files:
                    return {"status": "success", "notes": [], "message": "No notes found."}
                return {"status": "success", "notes": sorted(notes_files)}
            
            else:
                return {"status": "error", "message": f"Unknown action: '{action}'. Supported: add, update, read, delete, list."}

        except Exception as e:
            logger.error(f"NoteTakingTool: Error during action '{action}': {e}", exc_info=True)
            return {"status": "error", "message": f"An unexpected error occurred: {e}"}
