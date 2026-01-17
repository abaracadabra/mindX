# mindx/tools/github_feedback_tool.py
"""
GitHub Feedback Tool for MindX.

This tool automates collection of AI code review feedback from GitHub,
particularly from the Gemini bot, and processes it for mindX to fix.

Zero-cost AI debugging loop:
1. Gemini bot reviews code on GitHub (free)
2. This tool collects the error comments
3. mindX processes and generates fixes
4. Fixes are applied and committed

Supported bots:
- Gemini Code Assist (gemini-code-assist[bot])
- GitHub Copilot
- Other AI review bots

Usage:
    feedback_tool = GitHubFeedbackTool(memory_agent=memory_agent)

    # Collect all Gemini feedback
    result = await feedback_tool.execute(
        operation="collect_feedback",
        repo="owner/repo"
    )

    # Process errors for fixing
    result = await feedback_tool.execute(
        operation="process_errors",
        auto_fix=True
    )
"""

import json
import subprocess
import re
import asyncio
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime
from dataclasses import dataclass, asdict
from enum import Enum

from agents.core.bdi_agent import BaseTool
from agents.memory_agent import MemoryAgent
from utils.config import Config, PROJECT_ROOT
from utils.logging_config import get_logger

logger = get_logger(__name__)


class FeedbackSource(Enum):
    """Sources of AI feedback on GitHub."""
    GEMINI = "gemini-code-assist[bot]"
    GEMINI_ALT = "gemini-code-assist"
    COPILOT = "github-copilot[bot]"
    CODERABBIT = "coderabbitai[bot]"
    CODACY = "codacy-production[bot]"
    SONARCLOUD = "sonarcloud[bot]"
    CUSTOM = "custom"


class ErrorSeverity(Enum):
    """Severity levels for detected errors."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class ErrorCategory(Enum):
    """Categories of errors detected."""
    SYNTAX = "syntax"
    TYPE = "type"
    LOGIC = "logic"
    SECURITY = "security"
    PERFORMANCE = "performance"
    STYLE = "style"
    DEPRECATED = "deprecated"
    IMPORT = "import"
    UNDEFINED = "undefined"
    OTHER = "other"


@dataclass
class CodeError:
    """Represents a code error from AI feedback."""
    id: str
    file_path: str
    line_number: Optional[int]
    column: Optional[int]
    message: str
    severity: str
    category: str
    source: str
    suggestion: Optional[str]
    code_snippet: Optional[str]
    pr_number: Optional[int]
    comment_id: Optional[int]
    created_at: str
    status: str = "pending"  # pending, processing, fixed, ignored
    fix_applied: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class GitHubFeedbackTool(BaseTool):
    """
    GitHub Feedback Tool - Collects and processes AI code review feedback.

    This tool enables zero-cost AI debugging by:
    1. Collecting feedback from Gemini and other AI bots on GitHub
    2. Parsing and categorizing errors
    3. Generating fix suggestions for mindX to process
    4. Tracking fix status and results
    """

    def __init__(self,
                 memory_agent: MemoryAgent,
                 config: Optional[Config] = None,
                 **kwargs):
        super().__init__(config=config, **kwargs)
        self.memory_agent = memory_agent
        self.config = config or Config()
        self.project_root = PROJECT_ROOT

        # Feedback storage
        self.feedback_path = self.project_root / "data" / "github_feedback"
        self.feedback_path.mkdir(parents=True, exist_ok=True)
        self.errors_path = self.feedback_path / "errors.json"
        self.processed_path = self.feedback_path / "processed.json"
        self.fixes_path = self.feedback_path / "fixes.json"

        # Load existing data
        self.errors: List[CodeError] = self._load_errors()
        self.processed_comments: List[str] = self._load_json(self.processed_path, [])
        self.fixes: List[Dict[str, Any]] = self._load_json(self.fixes_path, [])

        # Bot identifiers to look for
        self.bot_identifiers = [
            "gemini-code-assist[bot]",
            "gemini-code-assist",
            "github-copilot[bot]",
            "coderabbitai[bot]",
        ]

        # Error patterns for parsing
        self.error_patterns = self._compile_error_patterns()

        self.log_prefix = "GitHubFeedbackTool:"
        logger.info(f"{self.log_prefix} Initialized - Zero-cost AI debugging ready")

    def _load_json(self, path: Path, default: Any) -> Any:
        """Safely load JSON file."""
        try:
            if path.exists():
                with path.open("r", encoding="utf-8") as f:
                    return json.load(f)
        except Exception as e:
            logger.warning(f"{self.log_prefix} Failed to load {path}: {e}")
        return default

    def _save_json(self, path: Path, data: Any):
        """Safely save JSON file."""
        try:
            with path.open("w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, default=str)
        except Exception as e:
            logger.error(f"{self.log_prefix} Failed to save {path}: {e}")

    def _load_errors(self) -> List[CodeError]:
        """Load errors from disk."""
        data = self._load_json(self.errors_path, [])
        errors = []
        for item in data:
            try:
                errors.append(CodeError(**item))
            except Exception as e:
                logger.warning(f"Failed to load error: {e}")
        return errors

    def _save_errors(self):
        """Save errors to disk."""
        data = [e.to_dict() for e in self.errors]
        self._save_json(self.errors_path, data)

    def _compile_error_patterns(self) -> Dict[str, re.Pattern]:
        """Compile regex patterns for error detection."""
        return {
            "file_line": re.compile(r"(?:in\s+)?[`'\"]?([^`'\":\s]+\.\w+)[`'\"]?\s*(?:line\s+|:)(\d+)", re.IGNORECASE),
            "error_keyword": re.compile(r"\b(error|warning|issue|bug|problem|vulnerability|deprecated)\b", re.IGNORECASE),
            "severity": re.compile(r"\b(critical|high|medium|low|info|warning|error)\b", re.IGNORECASE),
            "suggestion": re.compile(r"(?:suggest|should|consider|recommend|fix|change|use|replace|instead)[:\s]+(.+?)(?:\.|$)", re.IGNORECASE),
            "code_block": re.compile(r"```[\w]*\n(.*?)```", re.DOTALL),
            "undefined": re.compile(r"(?:undefined|not defined|unknown|unresolved)\s+(?:variable|function|method|class|module|name)\s+[`'\"]?(\w+)[`'\"]?", re.IGNORECASE),
            "import_error": re.compile(r"(?:import|module)\s+[`'\"]?(\w+)[`'\"]?\s+(?:not found|missing|failed)", re.IGNORECASE),
            "type_error": re.compile(r"(?:type|expected)\s+[`'\"]?(\w+)[`'\"]?\s+(?:but|got|instead)", re.IGNORECASE),
        }

    async def execute(self, operation: str, **kwargs) -> Dict[str, Any]:
        """
        Execute GitHub feedback operations.

        Operations:
        - collect_feedback: Collect AI feedback from GitHub PRs/issues
        - list_errors: List all collected errors
        - process_errors: Process errors and generate fixes
        - apply_fix: Apply a specific fix
        - mark_fixed: Mark an error as fixed
        - mark_ignored: Mark an error as ignored
        - get_stats: Get feedback statistics
        - clear_processed: Clear processed feedback
        - export_errors: Export errors for external processing
        """
        try:
            if operation == "collect_feedback":
                return await self._collect_feedback(**kwargs)
            elif operation == "list_errors":
                return await self._list_errors(**kwargs)
            elif operation == "process_errors":
                return await self._process_errors(**kwargs)
            elif operation == "apply_fix":
                return await self._apply_fix(**kwargs)
            elif operation == "mark_fixed":
                return await self._mark_fixed(**kwargs)
            elif operation == "mark_ignored":
                return await self._mark_ignored(**kwargs)
            elif operation == "get_stats":
                return await self._get_stats(**kwargs)
            elif operation == "clear_processed":
                return await self._clear_processed(**kwargs)
            elif operation == "export_errors":
                return await self._export_errors(**kwargs)
            elif operation == "fetch_pr_comments":
                return await self._fetch_pr_comments(**kwargs)
            elif operation == "fetch_repo_issues":
                return await self._fetch_repo_issues(**kwargs)
            else:
                return {"success": False, "error": f"Unknown operation: {operation}"}
        except Exception as e:
            logger.error(f"{self.log_prefix} Error in {operation}: {e}", exc_info=True)
            return {"success": False, "error": str(e)}

    async def _run_gh_command(self, args: List[str], check: bool = True) -> Tuple[bool, str]:
        """Run a GitHub CLI command."""
        try:
            result = subprocess.run(
                ["gh"] + args,
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=60
            )
            if check and result.returncode != 0:
                return False, result.stderr or result.stdout
            return True, result.stdout.strip()
        except subprocess.TimeoutExpired:
            return False, "GitHub CLI command timed out"
        except FileNotFoundError:
            return False, "GitHub CLI (gh) not found. Install from https://cli.github.com/"
        except Exception as e:
            return False, str(e)

    async def _collect_feedback(self,
                                 repo: Optional[str] = None,
                                 pr_number: Optional[int] = None,
                                 since: Optional[str] = None,
                                 bot_filter: Optional[List[str]] = None,
                                 **kwargs) -> Dict[str, Any]:
        """
        Collect AI feedback from GitHub.

        Args:
            repo: Repository in owner/repo format (default: current repo)
            pr_number: Specific PR number to check (default: all open PRs)
            since: Only collect feedback since this date (ISO format)
            bot_filter: List of bot names to filter (default: all known bots)
        """
        logger.info(f"{self.log_prefix} Collecting feedback from GitHub")

        collected_errors = []
        bots = bot_filter or self.bot_identifiers

        # Get repo info if not provided
        if not repo:
            success, output = await self._run_gh_command(
                ["repo", "view", "--json", "nameWithOwner", "-q", ".nameWithOwner"],
                check=False
            )
            if success and output:
                repo = output
            else:
                return {"success": False, "error": "Could not determine repository"}

        # Collect from PR comments
        if pr_number:
            pr_errors = await self._collect_pr_feedback(repo, pr_number, bots)
            collected_errors.extend(pr_errors)
        else:
            # Get all open PRs
            success, output = await self._run_gh_command(
                ["pr", "list", "--json", "number", "-q", ".[].number"],
                check=False
            )
            if success and output:
                pr_numbers = [int(n) for n in output.strip().split('\n') if n.strip()]
                for pn in pr_numbers[:10]:  # Limit to 10 PRs
                    pr_errors = await self._collect_pr_feedback(repo, pn, bots)
                    collected_errors.extend(pr_errors)

        # Collect from issues (bot-created issues)
        issue_errors = await self._collect_issue_feedback(repo, bots)
        collected_errors.extend(issue_errors)

        # Add new errors (avoid duplicates)
        new_count = 0
        for error in collected_errors:
            if error.id not in [e.id for e in self.errors]:
                self.errors.append(error)
                new_count += 1

        self._save_errors()

        # Log to memory
        await self.memory_agent.store_memory(
            agent_id="github_feedback_tool",
            memory_type="system_state",
            content={
                "action": "feedback_collected",
                "repo": repo,
                "total_errors": len(collected_errors),
                "new_errors": new_count,
                "sources": list(set(e.source for e in collected_errors))
            },
            importance="high"
        )

        logger.info(f"{self.log_prefix} Collected {new_count} new errors from {len(collected_errors)} total")

        return {
            "success": True,
            "repo": repo,
            "total_collected": len(collected_errors),
            "new_errors": new_count,
            "total_errors": len(self.errors),
            "errors": [e.to_dict() for e in collected_errors[:20]]  # Return first 20
        }

    async def _collect_pr_feedback(self,
                                    repo: str,
                                    pr_number: int,
                                    bots: List[str]) -> List[CodeError]:
        """Collect feedback from a specific PR."""
        errors = []

        # Get PR review comments
        success, output = await self._run_gh_command([
            "api", f"repos/{repo}/pulls/{pr_number}/comments",
            "--paginate", "-q", "."
        ], check=False)

        if success and output:
            try:
                comments = json.loads(output)
                for comment in comments:
                    author = comment.get("user", {}).get("login", "")
                    if any(bot in author.lower() for bot in [b.lower() for b in bots]):
                        error = self._parse_comment_to_error(comment, pr_number, "pr_review")
                        if error:
                            errors.append(error)
                            if comment.get("id"):
                                self.processed_comments.append(str(comment["id"]))
            except json.JSONDecodeError:
                logger.warning(f"Failed to parse PR {pr_number} comments")

        # Get PR issue comments
        success, output = await self._run_gh_command([
            "api", f"repos/{repo}/issues/{pr_number}/comments",
            "--paginate", "-q", "."
        ], check=False)

        if success and output:
            try:
                comments = json.loads(output)
                for comment in comments:
                    author = comment.get("user", {}).get("login", "")
                    if any(bot in author.lower() for bot in [b.lower() for b in bots]):
                        error = self._parse_comment_to_error(comment, pr_number, "issue_comment")
                        if error:
                            errors.append(error)
            except json.JSONDecodeError:
                pass

        return errors

    async def _collect_issue_feedback(self,
                                       repo: str,
                                       bots: List[str]) -> List[CodeError]:
        """Collect feedback from issues created by bots."""
        errors = []

        for bot in bots:
            success, output = await self._run_gh_command([
                "issue", "list", "--author", bot, "--json",
                "number,title,body,createdAt", "-q", "."
            ], check=False)

            if success and output:
                try:
                    issues = json.loads(output)
                    for issue in issues:
                        error = self._parse_issue_to_error(issue, bot)
                        if error:
                            errors.append(error)
                except json.JSONDecodeError:
                    pass

        return errors

    def _parse_comment_to_error(self,
                                 comment: Dict[str, Any],
                                 pr_number: int,
                                 source_type: str) -> Optional[CodeError]:
        """Parse a GitHub comment into a CodeError."""
        body = comment.get("body", "")
        if not body or len(body) < 10:
            return None

        # Check if it contains error-like content
        if not self.error_patterns["error_keyword"].search(body):
            # Still might be useful feedback
            pass

        # Extract file and line info
        file_path = comment.get("path", "")
        line_number = comment.get("line") or comment.get("original_line")

        # Try to extract from body if not in metadata
        if not file_path:
            match = self.error_patterns["file_line"].search(body)
            if match:
                file_path = match.group(1)
                line_number = int(match.group(2))

        # Determine severity
        severity = ErrorSeverity.MEDIUM.value
        sev_match = self.error_patterns["severity"].search(body)
        if sev_match:
            sev_text = sev_match.group(1).lower()
            if sev_text in ["critical", "high"]:
                severity = ErrorSeverity.HIGH.value
            elif sev_text in ["low", "info"]:
                severity = ErrorSeverity.LOW.value

        # Categorize error
        category = self._categorize_error(body)

        # Extract suggestion
        suggestion = None
        sug_match = self.error_patterns["suggestion"].search(body)
        if sug_match:
            suggestion = sug_match.group(1).strip()

        # Extract code snippet
        code_snippet = None
        code_match = self.error_patterns["code_block"].search(body)
        if code_match:
            code_snippet = code_match.group(1).strip()

        author = comment.get("user", {}).get("login", "unknown")

        return CodeError(
            id=f"gh_{comment.get('id', hash(body))}",
            file_path=file_path or "unknown",
            line_number=line_number,
            column=None,
            message=body[:500],  # Truncate long messages
            severity=severity,
            category=category,
            source=author,
            suggestion=suggestion,
            code_snippet=code_snippet,
            pr_number=pr_number,
            comment_id=comment.get("id"),
            created_at=comment.get("created_at", datetime.utcnow().isoformat()),
            status="pending"
        )

    def _parse_issue_to_error(self,
                               issue: Dict[str, Any],
                               bot: str) -> Optional[CodeError]:
        """Parse a GitHub issue into a CodeError."""
        body = issue.get("body", "") or ""
        title = issue.get("title", "")

        if not body and not title:
            return None

        full_text = f"{title}\n{body}"

        # Extract file info
        file_path = "unknown"
        line_number = None
        match = self.error_patterns["file_line"].search(full_text)
        if match:
            file_path = match.group(1)
            line_number = int(match.group(2))

        category = self._categorize_error(full_text)

        return CodeError(
            id=f"issue_{issue.get('number', hash(body))}",
            file_path=file_path,
            line_number=line_number,
            column=None,
            message=title or body[:200],
            severity=ErrorSeverity.MEDIUM.value,
            category=category,
            source=bot,
            suggestion=None,
            code_snippet=None,
            pr_number=None,
            comment_id=None,
            created_at=issue.get("createdAt", datetime.utcnow().isoformat()),
            status="pending"
        )

    def _categorize_error(self, text: str) -> str:
        """Categorize an error based on its content."""
        text_lower = text.lower()

        if self.error_patterns["undefined"].search(text):
            return ErrorCategory.UNDEFINED.value
        if self.error_patterns["import_error"].search(text):
            return ErrorCategory.IMPORT.value
        if self.error_patterns["type_error"].search(text):
            return ErrorCategory.TYPE.value
        if "syntax" in text_lower:
            return ErrorCategory.SYNTAX.value
        if "security" in text_lower or "vulnerability" in text_lower:
            return ErrorCategory.SECURITY.value
        if "performance" in text_lower or "slow" in text_lower:
            return ErrorCategory.PERFORMANCE.value
        if "style" in text_lower or "format" in text_lower or "lint" in text_lower:
            return ErrorCategory.STYLE.value
        if "deprecated" in text_lower:
            return ErrorCategory.DEPRECATED.value
        if "logic" in text_lower or "bug" in text_lower:
            return ErrorCategory.LOGIC.value

        return ErrorCategory.OTHER.value

    async def _list_errors(self,
                           status: Optional[str] = None,
                           severity: Optional[str] = None,
                           category: Optional[str] = None,
                           limit: int = 50,
                           **kwargs) -> Dict[str, Any]:
        """List collected errors with optional filters."""
        filtered = self.errors

        if status:
            filtered = [e for e in filtered if e.status == status]
        if severity:
            filtered = [e for e in filtered if e.severity == severity]
        if category:
            filtered = [e for e in filtered if e.category == category]

        return {
            "success": True,
            "total": len(filtered),
            "errors": [e.to_dict() for e in filtered[:limit]],
            "status_counts": {
                "pending": len([e for e in self.errors if e.status == "pending"]),
                "processing": len([e for e in self.errors if e.status == "processing"]),
                "fixed": len([e for e in self.errors if e.status == "fixed"]),
                "ignored": len([e for e in self.errors if e.status == "ignored"])
            }
        }

    async def _process_errors(self,
                               auto_fix: bool = False,
                               category_filter: Optional[str] = None,
                               limit: int = 10,
                               **kwargs) -> Dict[str, Any]:
        """
        Process pending errors and generate fix suggestions.

        This creates a structured format that mindX agents can process.
        """
        pending = [e for e in self.errors if e.status == "pending"]

        if category_filter:
            pending = [e for e in pending if e.category == category_filter]

        pending = pending[:limit]

        processed_results = []

        for error in pending:
            error.status = "processing"

            # Generate fix context for mindX
            fix_context = {
                "error_id": error.id,
                "file_path": error.file_path,
                "line_number": error.line_number,
                "message": error.message,
                "category": error.category,
                "severity": error.severity,
                "suggestion": error.suggestion,
                "code_snippet": error.code_snippet,
                "action_required": self._determine_action(error),
                "auto_fixable": self._is_auto_fixable(error)
            }

            processed_results.append(fix_context)

            # Log to memory for mindX processing
            await self.memory_agent.store_memory(
                agent_id="github_feedback_tool",
                memory_type="task",
                content={
                    "action": "error_ready_for_fix",
                    "error": error.to_dict(),
                    "fix_context": fix_context
                },
                importance="high"
            )

        self._save_errors()

        return {
            "success": True,
            "processed_count": len(processed_results),
            "errors_to_fix": processed_results,
            "message": f"Processed {len(processed_results)} errors for mindX to fix"
        }

    def _determine_action(self, error: CodeError) -> str:
        """Determine the action required to fix an error."""
        category = error.category

        if category == ErrorCategory.IMPORT.value:
            return "Add missing import or install package"
        elif category == ErrorCategory.UNDEFINED.value:
            return "Define the missing variable/function or fix typo"
        elif category == ErrorCategory.TYPE.value:
            return "Fix type annotation or conversion"
        elif category == ErrorCategory.SYNTAX.value:
            return "Fix syntax error"
        elif category == ErrorCategory.SECURITY.value:
            return "Apply security fix - review carefully"
        elif category == ErrorCategory.DEPRECATED.value:
            return "Update to non-deprecated alternative"
        elif category == ErrorCategory.STYLE.value:
            return "Apply code style fix"
        else:
            return "Review and apply appropriate fix"

    def _is_auto_fixable(self, error: CodeError) -> bool:
        """Determine if an error can be auto-fixed safely."""
        # Style issues are usually safe to auto-fix
        if error.category == ErrorCategory.STYLE.value:
            return True
        # Import errors with clear suggestions
        if error.category == ErrorCategory.IMPORT.value and error.suggestion:
            return True
        # Don't auto-fix security or logic issues
        if error.category in [ErrorCategory.SECURITY.value, ErrorCategory.LOGIC.value]:
            return False
        return False

    async def _apply_fix(self,
                          error_id: str,
                          fix_content: str,
                          **kwargs) -> Dict[str, Any]:
        """Apply a fix for a specific error."""
        error = next((e for e in self.errors if e.id == error_id), None)
        if not error:
            return {"success": False, "error": f"Error not found: {error_id}"}

        error.status = "fixed"
        error.fix_applied = fix_content

        self.fixes.append({
            "error_id": error_id,
            "file_path": error.file_path,
            "fix_content": fix_content,
            "applied_at": datetime.utcnow().isoformat()
        })

        self._save_errors()
        self._save_json(self.fixes_path, self.fixes)

        return {
            "success": True,
            "error_id": error_id,
            "status": "fixed",
            "message": f"Fix applied to {error.file_path}"
        }

    async def _mark_fixed(self, error_id: str, **kwargs) -> Dict[str, Any]:
        """Mark an error as fixed."""
        error = next((e for e in self.errors if e.id == error_id), None)
        if not error:
            return {"success": False, "error": f"Error not found: {error_id}"}

        error.status = "fixed"
        self._save_errors()
        return {"success": True, "error_id": error_id, "status": "fixed"}

    async def _mark_ignored(self, error_id: str, reason: str = "", **kwargs) -> Dict[str, Any]:
        """Mark an error as ignored."""
        error = next((e for e in self.errors if e.id == error_id), None)
        if not error:
            return {"success": False, "error": f"Error not found: {error_id}"}

        error.status = "ignored"
        error.fix_applied = f"Ignored: {reason}"
        self._save_errors()
        return {"success": True, "error_id": error_id, "status": "ignored", "reason": reason}

    async def _get_stats(self, **kwargs) -> Dict[str, Any]:
        """Get feedback statistics."""
        return {
            "success": True,
            "total_errors": len(self.errors),
            "by_status": {
                "pending": len([e for e in self.errors if e.status == "pending"]),
                "processing": len([e for e in self.errors if e.status == "processing"]),
                "fixed": len([e for e in self.errors if e.status == "fixed"]),
                "ignored": len([e for e in self.errors if e.status == "ignored"])
            },
            "by_severity": {
                "critical": len([e for e in self.errors if e.severity == "critical"]),
                "high": len([e for e in self.errors if e.severity == "high"]),
                "medium": len([e for e in self.errors if e.severity == "medium"]),
                "low": len([e for e in self.errors if e.severity == "low"]),
                "info": len([e for e in self.errors if e.severity == "info"])
            },
            "by_category": {
                cat.value: len([e for e in self.errors if e.category == cat.value])
                for cat in ErrorCategory
            },
            "by_source": self._group_by_source(),
            "total_fixes_applied": len(self.fixes),
            "processed_comments": len(self.processed_comments)
        }

    def _group_by_source(self) -> Dict[str, int]:
        """Group errors by source."""
        sources = {}
        for error in self.errors:
            sources[error.source] = sources.get(error.source, 0) + 1
        return sources

    async def _clear_processed(self, **kwargs) -> Dict[str, Any]:
        """Clear all processed feedback."""
        cleared_count = len(self.processed_comments)
        self.processed_comments = []
        self._save_json(self.processed_path, self.processed_comments)
        return {"success": True, "cleared": cleared_count}

    async def _export_errors(self,
                              format: str = "json",
                              status_filter: Optional[str] = None,
                              **kwargs) -> Dict[str, Any]:
        """Export errors for external processing."""
        errors = self.errors
        if status_filter:
            errors = [e for e in errors if e.status == status_filter]

        export_data = {
            "exported_at": datetime.utcnow().isoformat(),
            "total_errors": len(errors),
            "errors": [e.to_dict() for e in errors]
        }

        export_path = self.feedback_path / f"export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        self._save_json(export_path, export_data)

        return {
            "success": True,
            "export_path": str(export_path),
            "error_count": len(errors),
            "format": format
        }

    async def _fetch_pr_comments(self,
                                  pr_number: int,
                                  repo: Optional[str] = None,
                                  **kwargs) -> Dict[str, Any]:
        """Fetch all comments from a specific PR."""
        if not repo:
            success, repo = await self._run_gh_command(
                ["repo", "view", "--json", "nameWithOwner", "-q", ".nameWithOwner"],
                check=False
            )
            if not success:
                return {"success": False, "error": "Could not determine repository"}

        # Fetch review comments
        success, output = await self._run_gh_command([
            "api", f"repos/{repo}/pulls/{pr_number}/comments",
            "-q", "."
        ], check=False)

        review_comments = []
        if success and output:
            try:
                review_comments = json.loads(output)
            except json.JSONDecodeError:
                pass

        # Fetch issue comments
        success, output = await self._run_gh_command([
            "api", f"repos/{repo}/issues/{pr_number}/comments",
            "-q", "."
        ], check=False)

        issue_comments = []
        if success and output:
            try:
                issue_comments = json.loads(output)
            except json.JSONDecodeError:
                pass

        # Filter for bot comments
        bot_review_comments = [
            c for c in review_comments
            if any(bot in c.get("user", {}).get("login", "").lower()
                   for bot in self.bot_identifiers)
        ]
        bot_issue_comments = [
            c for c in issue_comments
            if any(bot in c.get("user", {}).get("login", "").lower()
                   for bot in self.bot_identifiers)
        ]

        return {
            "success": True,
            "pr_number": pr_number,
            "repo": repo,
            "total_review_comments": len(review_comments),
            "total_issue_comments": len(issue_comments),
            "bot_review_comments": len(bot_review_comments),
            "bot_issue_comments": len(bot_issue_comments),
            "bot_comments": bot_review_comments + bot_issue_comments
        }

    async def _fetch_repo_issues(self,
                                  repo: Optional[str] = None,
                                  state: str = "open",
                                  **kwargs) -> Dict[str, Any]:
        """Fetch issues from the repository."""
        if not repo:
            success, repo = await self._run_gh_command(
                ["repo", "view", "--json", "nameWithOwner", "-q", ".nameWithOwner"],
                check=False
            )
            if not success:
                return {"success": False, "error": "Could not determine repository"}

        success, output = await self._run_gh_command([
            "issue", "list", "--state", state, "--json",
            "number,title,body,author,createdAt,labels", "-q", "."
        ], check=False)

        issues = []
        if success and output:
            try:
                issues = json.loads(output)
            except json.JSONDecodeError:
                pass

        # Filter for bot-created issues
        bot_issues = [
            i for i in issues
            if any(bot in i.get("author", {}).get("login", "").lower()
                   for bot in self.bot_identifiers)
        ]

        return {
            "success": True,
            "repo": repo,
            "state": state,
            "total_issues": len(issues),
            "bot_issues": len(bot_issues),
            "issues": bot_issues
        }

    def get_schema(self) -> Dict[str, Any]:
        """Return the tool schema for LLM integration."""
        return {
            "name": "github_feedback_tool",
            "description": "Collect and process AI code review feedback from GitHub for zero-cost debugging",
            "parameters": {
                "type": "object",
                "properties": {
                    "operation": {
                        "type": "string",
                        "description": "The operation to perform",
                        "enum": [
                            "collect_feedback",
                            "list_errors",
                            "process_errors",
                            "apply_fix",
                            "mark_fixed",
                            "mark_ignored",
                            "get_stats",
                            "clear_processed",
                            "export_errors",
                            "fetch_pr_comments",
                            "fetch_repo_issues"
                        ]
                    }
                },
                "required": ["operation"]
            },
            "supported_bots": self.bot_identifiers
        }
