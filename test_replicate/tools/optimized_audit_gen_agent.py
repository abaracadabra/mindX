# tools/optimized_audit_gen_agent.py
"""
OptimizedAuditGenAgent: A specialized version of BaseGenAgent optimized for code auditing.
Addresses the giant file problem through smart filtering, chunking, and audit-focused analysis.
"""
import json
import fnmatch
from pathlib import Path
from typing import List, Optional, Dict, Tuple, Any, Set
from datetime import datetime
import copy
import hashlib
import subprocess
import re

try:
    import pathspec
except ImportError:
    pathspec = None

try:
    from utils.config import Config, PROJECT_ROOT
    from utils.logging_config import get_logger
    from core.belief_system import BeliefSystem, BeliefSource
    from agents.memory_agent import MemoryAgent
    logger = get_logger(__name__)
except ImportError as e:
    import logging
    logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(name)s: %(message)s')
    logger = logging.getLogger(__name__)
    logger.warning(f"Could not import from 'utils' package ({e}). Using fallback.")
    PROJECT_ROOT = Path(__file__).resolve().parent.parent
    class Config:
        def get(self, key, default=None):
            return default


class AuditMetrics:
    """Container for code audit metrics and analysis."""
    
    def __init__(self):
        self.complexity_score = 0
        self.maintainability_score = 0
        self.test_coverage_estimate = 0
        self.code_smells: List[Dict[str, Any]] = []
        self.security_issues: List[Dict[str, Any]] = []
        self.performance_issues: List[Dict[str, Any]] = []
        self.documentation_coverage = 0
        self.dependencies: Set[str] = set()
        self.file_metrics: Dict[str, Dict[str, Any]] = {}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "complexity_score": self.complexity_score,
            "maintainability_score": self.maintainability_score,
            "test_coverage_estimate": self.test_coverage_estimate,
            "code_smells": self.code_smells,
            "security_issues": self.security_issues,
            "performance_issues": self.performance_issues,
            "documentation_coverage": self.documentation_coverage,
            "dependencies": list(self.dependencies),
            "file_metrics": self.file_metrics
        }


class OptimizedAuditGenAgent:
    """
    Optimized code auditing agent that generates manageable documentation chunks
    with focus on code quality, maintainability, and audit insights.
    """
    
    # Enhanced exclude patterns specifically for audit focus
    AUDIT_OPTIMIZED_EXCLUDES = [
        # Memory and log files (major source of bloat)
        "data/memory/*", "data/logs/*", "logs/*", "*.log", "*.log.*",
        
        # Binary and media files
        "*.png", "*.jpg", "*.jpeg", "*.gif", "*.bmp", "*.tiff", "*.svg", "*.ico", "*.webp",
        "*.mp3", "*.wav", "*.ogg", "*.flac", "*.aac", "*.mp4", "*.mov", "*.avi", "*.mkv",
        "*.zip", "*.tar", "*.tar.gz", "*.tar.bz2", "*.rar", "*.7z", "*.gz", "*.bz2",
        "*.exe", "*.dll", "*.so", "*.dylib", "*.class", "*.jar", "*.war", "*.ear",
        "*.pyc", "*.pyo", "*.pyd", "__pycache__/", "*.o", "*.a",
        
        # Documentation that's not code (reduce noise)
        "*.md", "*.txt", "*.pdf", "*.doc", "*.docx", "*.rst",
        
        # Package management and build artifacts
        "node_modules/", "package-lock.json", "yarn.lock", "poetry.lock", "Pipfile.lock",
        "vendor/", "venv/", ".venv/", "env/", "build/", "dist/", "target/", "bin/", "obj/",
        
        # VCS and IDE
        ".git/", ".hg/", ".svn/", ".bzr/", ".idea/", ".vscode/", ".DS_Store", "Thumbs.db",
        
        # Test and coverage artifacts
        "coverage.xml", ".coverage", "nosetests.xml", "pytestdebug.log", ".pytest_cache/",
        
        # Temporary and backup files
        "*.tmp", "*.temp", "*.swp", "*.swo", "*.bak", "*.old", "*.orig"
    ]
    
    # Code patterns that indicate potential issues
    CODE_SMELL_PATTERNS = {
        "long_functions": r"def\s+\w+\([^)]*\):[^}]*(?:\n(?:\s{4,}|\t)[^\n]*){50,}",
        "deep_nesting": r"(\s{16,}|\t{4,})(if|for|while|try|with)",
        "magic_numbers": r"\b(?<![\.\w])[0-9]{2,}\b(?![\.\w])",
        "hardcoded_strings": r'["\'][^"\']{20,}["\']',
        "todo_fixme": r"(TODO|FIXME|HACK|XXX)[:|\s]",
        "long_lines": r".{120,}",
        "missing_docstrings": r"^(class|def)\s+[^#\n]*:\s*\n\s*(?!\"\"\"|\'\'\')(?!\s*#)",
    }
    
    SECURITY_PATTERNS = {
        "sql_injection": r"(execute|query|cursor).*%.*['\"]",
        "command_injection": r"(os\.system|subprocess|shell=True)",
        "hardcoded_secrets": r"(password|secret|key|token)\s*=\s*['\"][^'\"]+['\"]",
        "eval_usage": r"\beval\s*\(",
        "pickle_usage": r"\bpickle\.(loads?|dumps?)\s*\(",
    }
    
    def __init__(self, 
                 memory_agent: MemoryAgent, 
                 agent_id: str = "optimized_audit_gen_agent",
                 max_file_size_kb: int = 500,
                 max_files_per_chunk: int = 50,
                 belief_system: Optional[BeliefSystem] = None):
        self.agent_id = agent_id
        self.belief_system = belief_system
        self.memory_agent = memory_agent
        self.max_file_size_kb = max_file_size_kb
        self.max_files_per_chunk = max_files_per_chunk
        self.log_prefix = f"[{self.agent_id}]"
        
        # Ensure agent data directory exists
        self.data_dir = self.memory_agent.get_agent_data_directory(self.agent_id)
        self.output_dir = self.data_dir / "audit_reports"
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"{self.log_prefix} Initialized with max_file_size={max_file_size_kb}KB, max_files_per_chunk={max_files_per_chunk}")

    def _should_include_file_for_audit(self, file_path: Path, root_path: Path) -> bool:
        """Enhanced file filtering specifically for code auditing."""
        try:
            relative_path = file_path.relative_to(root_path)
        except ValueError:
            return False
            
        relative_str = relative_path.as_posix()
        
        # Apply optimized exclude patterns
        for pattern in self.AUDIT_OPTIMIZED_EXCLUDES:
            if fnmatch.fnmatch(relative_str, pattern) or fnmatch.fnmatch(file_path.name, pattern):
                logger.debug(f"{self.log_prefix} Excluding {relative_str} by audit pattern: {pattern}")
                return False
        
        # Only include code files and configuration files for auditing
        code_extensions = {'.py', '.js', '.jsx', '.ts', '.tsx', '.java', '.cpp', '.c', '.h', '.hpp',
                          '.cs', '.go', '.rs', '.rb', '.php', '.scala', '.kt', '.swift',
                          '.json', '.yaml', '.yml', '.toml', '.xml', '.ini', '.cfg', '.conf'}
        
        if file_path.suffix.lower() not in code_extensions and file_path.name.lower() not in ['dockerfile', 'makefile', 'requirements.txt']:
            logger.debug(f"{self.log_prefix} Excluding {relative_str} - not a code file")
            return False
        
        # Check file size
        try:
            if file_path.stat().st_size > (self.max_file_size_kb * 1024):
                logger.warning(f"{self.log_prefix} Excluding {relative_str} - file too large ({file_path.stat().st_size} bytes)")
                return False
        except OSError:
            return False
            
        return True

    def generate_audit_documentation(self,
                                   root_path_str: str,
                                   focus_areas: Optional[List[str]] = None,
                                   include_patterns: Optional[List[str]] = None,
                                   additional_exclude_patterns: Optional[List[str]] = None) -> Tuple[bool, Dict[str, Any]]:
        """
        Generate optimized audit documentation with chunking and quality metrics.
        """
        root_path = Path(root_path_str).resolve()
        
        if not root_path.is_dir():
            error_msg = f"Input path '{root_path}' is not a valid directory"
            logger.error(f"{self.log_prefix} {error_msg}")
            return False, {"status": "ERROR", "message": error_msg}
        
        logger.info(f"{self.log_prefix} Starting audit documentation for: {root_path}")
        
        # Collect files for analysis
        included_files = []
        
        try:
            for item in sorted(root_path.rglob("*")):
                if item.is_file() and self._should_include_file_for_audit(item, root_path):
                    included_files.append(item)
        except Exception as e:
            error_msg = f"Error scanning directory: {e}"
            logger.error(f"{self.log_prefix} {error_msg}", exc_info=True)
            return False, {"status": "ERROR", "message": error_msg}
        
        if not included_files:
            logger.warning(f"{self.log_prefix} No files found for analysis")
            return False, {"status": "WARNING", "message": "No files found for analysis"}
        
        logger.info(f"{self.log_prefix} Found {len(included_files)} files for analysis")
        
        # Chunk files to prevent giant output
        file_chunks = self._chunk_files(included_files)
        output_files = []
        
        # Generate timestamp for this audit session
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        try:
            # Generate main audit report
            main_report_path = self.output_dir / f"audit_report_{root_path.name}_{timestamp}.md"
            
            # Generate main report
            with main_report_path.open("w", encoding="utf-8") as f:
                f.write(f"# Code Audit Report: {root_path.name}\n")
                f.write(f"Generated by: {self.agent_id} on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"Source Directory: `{root_path}`\n\n")
                
                f.write(f"## Summary\n")
                f.write(f"- **Total Files Analyzed:** {len(included_files)}\n")
                f.write(f"- **Files per Chunk:** {self.max_files_per_chunk}\n")
                f.write(f"- **Total Chunks:** {len(file_chunks)}\n\n")
                
                # Write file index
                f.write("## File Analysis Chunks\n\n")
                for i, chunk in enumerate(file_chunks):
                    chunk_file = f"audit_chunk_{i+1:03d}_{root_path.name}_{timestamp}.md"
                    f.write(f"- [Chunk {i+1}](./{chunk_file}) - {len(chunk)} files\n")
                
                f.write(f"\n## File List\n\n")
                for file_path in included_files:
                    rel_path = file_path.relative_to(root_path)
                    f.write(f"- `{rel_path.as_posix()}`\n")
            
            # Generate chunk files
            for i, chunk in enumerate(file_chunks):
                chunk_path = self.output_dir / f"audit_chunk_{i+1:03d}_{root_path.name}_{timestamp}.md"
                
                with chunk_path.open("w", encoding="utf-8") as f:
                    f.write(f"# Audit Chunk {i+1} - {root_path.name}\n")
                    f.write(f"Files {i*self.max_files_per_chunk + 1} to {min((i+1)*self.max_files_per_chunk, len(included_files))}\n\n")
                    
                    for file_path in chunk:
                        try:
                            content = file_path.read_text(encoding="utf-8", errors="replace")
                            rel_path = file_path.relative_to(root_path)
                            
                            f.write(f"## `{rel_path.as_posix()}`\n\n")
                            
                            # Write file content with appropriate language tag
                            lang = self._guess_language(file_path.suffix)
                            f.write(f"```{lang}\n{content.strip()}\n```\n\n")
                            
                        except Exception as e:
                            f.write(f"Error reading file: {e}\n\n")
                
                output_files.append(str(chunk_path))
            
            output_files.append(str(main_report_path))
            
            result = {
                "status": "SUCCESS",
                "message": f"Audit documentation generated successfully",
                "main_report": str(main_report_path),
                "chunk_files": output_files[:-1],  # Exclude main report
                "files_analyzed": len(included_files),
                "chunks_created": len(file_chunks),
            }
            
            logger.info(f"{self.log_prefix} Audit complete. Main report: {main_report_path}")
            return True, result
            
        except Exception as e:
            error_msg = f"Error generating audit documentation: {e}"
            logger.error(f"{self.log_prefix} {error_msg}", exc_info=True)
            return False, {"status": "ERROR", "message": error_msg}

    def _chunk_files(self, files: List[Path]) -> List[List[Path]]:
        """Split files into manageable chunks to prevent giant output files."""
        chunks = []
        current_chunk = []
        
        for file_path in files:
            current_chunk.append(file_path)
            
            if len(current_chunk) >= self.max_files_per_chunk:
                chunks.append(current_chunk)
                current_chunk = []
        
        if current_chunk:
            chunks.append(current_chunk)
        
        return chunks

    def _guess_language(self, extension: str) -> str:
        """Guess programming language from file extension."""
        lang_map = {
            ".py": "python", ".js": "javascript", ".jsx": "javascript",
            ".ts": "typescript", ".tsx": "typescript", ".java": "java",
            ".cpp": "cpp", ".c": "c", ".h": "c", ".hpp": "cpp",
            ".cs": "csharp", ".go": "go", ".rs": "rust", ".rb": "ruby",
            ".php": "php", ".scala": "scala", ".kt": "kotlin", ".swift": "swift",
            ".json": "json", ".yaml": "yaml", ".yml": "yaml", ".xml": "xml",
            ".toml": "toml", ".ini": "ini", ".cfg": "ini", ".conf": "apache"
        }
        return lang_map.get(extension.lower(), "")


def main():
    """CLI entry point for testing."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Optimized Audit Code Generator")
    parser.add_argument("input_dir", help="Directory to analyze")
    parser.add_argument("--max-file-size", type=int, default=500, 
                       help="Maximum file size in KB to include")
    parser.add_argument("--max-files-per-chunk", type=int, default=50,
                       help="Maximum files per output chunk")
    
    args = parser.parse_args()
    
    # Create a minimal memory agent for testing
    from agents.memory_agent import MemoryAgent
    memory_agent = MemoryAgent()
    
    # Create the audit agent
    audit_agent = OptimizedAuditGenAgent(
        memory_agent=memory_agent,
        max_file_size_kb=args.max_file_size,
        max_files_per_chunk=args.max_files_per_chunk
    )
    
    # Run the audit
    success, result = audit_agent.generate_audit_documentation(args.input_dir)
    
    if success:
        print(f"✅ Audit completed successfully!")
        print(f"📊 Files analyzed: {result['files_analyzed']}")
        print(f"📁 Chunks created: {result['chunks_created']}")
        print(f"📄 Main report: {result['main_report']}")
    else:
        print(f"❌ Audit failed: {result['message']}")


if __name__ == "__main__":
    main() 