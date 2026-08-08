"""
Tree Agent for mindX - Secure directory navigation and file system exploration.

Provides sandboxed directory navigation capabilities with command whitelisting
and comprehensive logging for security and auditing.

Containment model
-----------------
The root path is a **boundary**, not a suffix. Every path-shaped argument is
resolved (following symlinks and ``..``) and must land inside the root, or the
command is refused before it reaches a shell. Commands then run with the root as
the working directory and their paths rewritten relative to it.

An earlier revision appended the root as an extra argument, which enforced
nothing: ``ls -1 /etc/ssl`` simply became ``ls -1 /etc/ssl <root>`` and listed
``/etc/ssl`` quite happily. Appending a path does not constrain the paths that
are already there.
"""
import os
import shlex
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from tools.core.shell_command_tool import ShellCommandTool
from agents.core.bdi_agent import BaseTool
from utils.logging_config import get_logger

logger = get_logger(__name__)

class TreeAgent(BaseTool):
    """
    Secure directory navigation tool with a sandboxed root path.

    Features:
    - Command whitelisting (ls, find only), matched on the exact first token
    - Path containment: every path argument must resolve inside the root
    - Shell-metacharacter refusal, so no second command can be chained on
    - Read-only: find predicates that execute or write are rejected
    - Comprehensive operation logging
    """

    ALLOWED_COMMANDS = ["ls", "find"]

    #: Refused outright. A navigation tool that can run programs or write files
    #: is not a navigation tool. `-delete` writes; the `-exec` family and
    #: `-ok`/`-okdir` run arbitrary binaries; `-fprint`/`-fls` write to an
    #: attacker-chosen path, escaping the root through the *output* side even
    #: when every input path is properly contained.
    FORBIDDEN_FIND_PREDICATES = frozenset({
        "-exec", "-execdir", "-ok", "-okdir", "-delete",
        "-fprint", "-fprint0", "-fprintf", "-fls",
    })

    #: `find -L` / `-follow` resolve symlinks *during traversal*, which walks out
    #: of the root through a link that validated as being inside it.
    FORBIDDEN_OPTIONS = frozenset({"-L", "-follow"})

    #: Options whose *next* token is a value (a pattern, size, depth…), not a
    #: path. Without this, `find . -name '*.py'` would treat `*.py` as a path.
    VALUE_TAKING_OPTIONS = frozenset({
        "-name", "-iname", "-path", "-ipath", "-wholename", "-iwholename",
        "-lname", "-ilname", "-regex", "-iregex", "-regextype",
        "-type", "-xtype", "-size", "-perm", "-user", "-group", "-uid", "-gid",
        "-links", "-inum", "-printf", "-format",
        "-maxdepth", "-mindepth",
        "-mtime", "-mmin", "-atime", "-amin", "-ctime", "-cmin",
        "-newer", "-newermt", "-anewer", "-cnewer", "-samefile",
        "--time-style", "--block-size", "--format", "--color", "--sort",
    })

    #: Anything that lets a shell see a second command, a redirect, or a
    #: substitution. Refused in the raw string, before tokenising.
    SHELL_METACHARACTERS = frozenset(";&|<>`$()\n\r")

    #: Glob characters are handled per-token rather than banned outright: as a
    #: *pattern* for `-name` they are the whole point (`find . -name '*.py'`),
    #: and the rewritten command is shlex-quoted so the shell never expands
    #: them. As a *path* they cannot be resolved or contained, so they are
    #: refused there — see `_resolve_argument`.
    GLOB_CHARACTERS = frozenset("*?[]{}")

    def __init__(self, root_path: str, config=None, **kwargs: Any):
        super().__init__(config=config, **kwargs)
        self.root_path = Path(root_path).resolve()

        # Validate root path exists
        if not self.root_path.exists():
            raise ValueError(f"Root path does not exist: {self.root_path}")
        if not self.root_path.is_dir():
            raise ValueError(f"Root path is not a directory: {self.root_path}")

        # Initialize shell command tool
        self.shell = ShellCommandTool(config=self.config)

        self.logger.info(f"TreeAgent initialized with root path: {self.root_path}")

    # ------------------------------------------------------------- containment

    def _is_within_root(self, candidate: Path) -> bool:
        """True if `candidate` resolves inside the root (the root itself counts)."""
        try:
            resolved = candidate.resolve()
        except (OSError, RuntimeError):  # RuntimeError: symlink loop
            return False
        return resolved == self.root_path or self.root_path in resolved.parents

    def _resolve_argument(self, token: str) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Resolve one path-shaped token against the root.

        Returns (ok, relative_path, error). Relative tokens are interpreted
        against the root; absolute ones must already be inside it. The path is
        returned relative so the command can run with the root as its cwd.
        """
        glob_chars = sorted(set(token) & self.GLOB_CHARACTERS)
        if glob_chars:
            # A glob cannot be resolved, so it cannot be contained. Refusing it
            # as a path is not a limitation — `find -name '<pattern>'` is the
            # supported way to match, and patterns are allowed there.
            return False, None, (
                f"path argument may not contain glob characters ({' '.join(glob_chars)}): {token}. "
                "Use `find <dir> -name '<pattern>'` to match by name."
            )

        raw = Path(token)
        candidate = raw if raw.is_absolute() else (self.root_path / raw)

        if not self._is_within_root(candidate):
            return False, None, f"path escapes sandbox root: {token}"

        resolved = candidate.resolve()
        if resolved == self.root_path:
            return True, ".", None
        return True, str(resolved.relative_to(self.root_path)), None

    # -------------------------------------------------------------- validation

    def _validate_command(self, command: str) -> Tuple[bool, Optional[str]]:
        """
        Validate command against the whitelist and the containment rules.

        Returns:
            Tuple of (is_valid, error_message)
        """
        if not command or not isinstance(command, str):
            return False, "Command must be a non-empty string"

        stripped = command.strip()

        bad = sorted(set(stripped) & self.SHELL_METACHARACTERS)
        if bad:
            # Globs and braces are refused too: the shell expands them before the
            # command runs, so they can name paths this validator never saw.
            # `find -name '<pattern>'` is the supported way to match.
            return False, f"Command contains disallowed shell characters: {' '.join(bad)}"

        try:
            tokens = shlex.split(stripped)
        except ValueError as exc:
            return False, f"Command could not be parsed: {exc}"

        if not tokens:
            return False, "Command must be a non-empty string"

        # Exact match on the first token. `startswith` would admit `lsblk`,
        # `lscpu`, `findmnt` — different programs that merely share a prefix.
        if tokens[0] not in self.ALLOWED_COMMANDS:
            return False, (
                f"Only '{', '.join(self.ALLOWED_COMMANDS)}' commands are allowed. "
                f"Got: {tokens[0][:50]}"
            )

        ok, _, error = self._analyse_tokens(tokens)
        return (True, None) if ok else (False, error)

    def _analyse_tokens(self, tokens: List[str]) -> Tuple[bool, List[str], Optional[str]]:
        """
        Walk the token list, rejecting dangerous options and containing every
        path argument.

        Returns (ok, rewritten_tokens, error).
        """
        rewritten: List[str] = [tokens[0]]
        paths_seen = 0
        index = 1

        while index < len(tokens):
            token = tokens[index]

            if token in self.FORBIDDEN_FIND_PREDICATES:
                return False, [], f"predicate '{token}' is not permitted (executes or writes)"
            if token in self.FORBIDDEN_OPTIONS:
                return False, [], f"option '{token}' is not permitted (follows symlinks out of the root)"

            if token in self.VALUE_TAKING_OPTIONS:
                rewritten.append(token)
                if index + 1 < len(tokens):
                    rewritten.append(tokens[index + 1])  # a value, never a path
                    index += 2
                else:
                    index += 1
                continue

            if token.startswith("-"):
                rewritten.append(token)
                index += 1
                continue

            ok, relative, error = self._resolve_argument(token)
            if not ok:
                return False, [], error
            rewritten.append(relative)
            paths_seen += 1
            index += 1

        if paths_seen == 0:
            rewritten.append(".")  # default to the root itself

        return True, rewritten, None

    def _construct_sandboxed_command(self, command: str) -> str:
        """
        Build the contained command: every path rewritten relative to the root,
        which is supplied separately as the working directory.

        Raises ValueError if the command does not validate. Callers run
        `_validate_command` first; this is a backstop so the method can never
        emit something unvalidated.
        """
        tokens = shlex.split(command.strip())
        ok, rewritten, error = self._analyse_tokens(tokens)
        if not ok:
            raise ValueError(error)
        return " ".join(shlex.quote(part) for part in rewritten)

    # ---------------------------------------------------------------- execution

    async def execute(self, command: str) -> Optional[str]:
        """
        Execute a directory navigation command.

        Args:
            command: Command to execute (must start with 'ls' or 'find')

        Returns:
            Command output on success, error message on failure
        """
        self.logger.info(f"TreeAgent executing command: {command[:100]}")

        # Validate command
        is_valid, validation_error = self._validate_command(command)
        if not is_valid:
            error_msg = f"Command validation failed: {validation_error}"
            self.logger.error(error_msg)
            return error_msg

        # Construct sandboxed command
        try:
            full_command = self._construct_sandboxed_command(command)
        except ValueError as exc:
            error_msg = f"Command validation failed: {exc}"
            self.logger.error(error_msg)
            return error_msg
        self.logger.debug(f"Sandboxed command: {full_command}")

        try:
            # Execute via shell tool, rooted at the sandbox
            success, result = await self.shell.execute(command=full_command, working_dir=str(self.root_path))

            # Log operation
            if hasattr(self, 'memory_agent') and self.memory_agent and self.bdi_agent_ref:
                try:
                    await self.memory_agent.log_process(
                        process_name='tree_agent_execution',
                        data={
                            'command': command,
                            'full_command': full_command,
                            'success': success,
                            'result_preview': str(result)[:500] if result else None
                        },
                        metadata={
                            'agent_id': self.bdi_agent_ref.agent_id,
                            'tool_id': 'tree_agent',
                            'root_path': str(self.root_path)
                        }
                    )
                except Exception as log_error:
                    self.logger.warning(f"Failed to log tree agent operation: {log_error}")

            if success:
                self.logger.info(f"TreeAgent command executed successfully")
                return result
            else:
                error_msg = f"Command execution failed: {result}"
                self.logger.error(error_msg)
                return error_msg

        except Exception as e:
            error_msg = f"Exception during command execution: {e}"
            self.logger.error(error_msg, exc_info=True)
            return error_msg

    def get_root_path(self) -> Path:
        """Get the sandboxed root path."""
        return self.root_path

    def get_allowed_commands(self) -> List[str]:
        """Get list of allowed commands."""
        return self.ALLOWED_COMMANDS.copy()
