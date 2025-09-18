# tttools/base_gen_agent.py
"""
BaseGenAgent (Codebase Documentation Generator): Generates Markdown
documentation from a codebase directory.
"""
import argparse
import fnmatch
import pathlib # Keep this for using pathlib.Path if preferred
from pathlib import Path # Explicitly import Path for direct use
import sys
import os
import json
from typing import List, Optional, Dict, Tuple, Any
from datetime import datetime
import copy

# Requires: pip install pathspec
try:
    import pathspec
except ImportError: # pragma: no cover
    print("CRITICAL ERROR: 'pathspec' library not found. Please run 'pip install pathspec'", file=sys.stderr)
    pathspec = None


# Import from sibling top-level package 'utils'
# This assumes 'tools' and 'utils' are sibling directories under PROJECT_ROOT
# and PROJECT_ROOT is in sys.path
try:
    from utils.config import Config, PROJECT_ROOT
    from utils.logging_config import get_logger
    from core.belief_system import BeliefSystem, BeliefSource
    from agents.memory_agent import MemoryAgent
    logger = get_logger(__name__)
except ImportError as e: # pragma: no cover
    # Fallback if run standalone or utils not found, very basic logging
    import logging
    logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(name)s: %(message)s')
    logger = logging.getLogger(__name__)
    logger.warning(f"Could not import from 'utils' package ({e}). Using fallback PROJECT_ROOT and basic Config.")
    # Try to determine PROJECT_ROOT assuming this file is in /tools/
    # This makes it /home/luvai/mindX if structure is mindX/tools/base_gen_agent.py
    PROJECT_ROOT = Path(__file__).resolve().parent.parent
    class Config:
        def get(self, key, default=None):
            # Provide minimal defaults if global Config is not available
            if key == "base_gen_agent.config_file_path": return None
            return default


class BaseGenAgent:
    # Default path if no override is given AND the global Config doesn't specify one for it.
    # This should align with where your main basegen_config.json is.
    DEFAULT_AGENT_CONFIG_FILE_PATH_RELATIVE = Path("data") / "config" / "basegen_config.json"

    INTERNAL_FALLBACK_CONFIG_DATA: Dict[str, Any] = {
        "HARD_CODED_EXCLUDES": [
            "*.md", "*.txt", "*.pdf", "*.doc", "*.docx", "*.odt", "*.rtf",
            "*.png", "*.jpg", "*.jpeg", "*.gif", "*.bmp", "*.tiff", "*.svg", "*.ico", "*.webp",
            "*.mp3", "*.wav", "*.ogg", "*.flac", "*.aac", "*.mp4", "*.mov", "*.avi", "*.mkv", "*.webm", "*.flv",
            "*.zip", "*.tar", "*.tar.gz", "*.tar.bz2", "*.rar", "*.7z", "*.gz", "*.bz2", "*.xz",
            "*.o", "*.so", "*.a", "*.dylib", "*.dll", "*.exe", "*.com", "*.msi", "*.deb", "*.rpm", "*.app",
            "*.class", "*.jar", "*.war", "*.ear", "*.pyc", "*.pyo", "*.pyd",
            "__pycache__/", ".pytest_cache/", ".mypy_cache/", ".ruff_cache/", "build/", "dist/", "target/",
            "package-lock.json", "yarn.lock", "poetry.lock", "Pipfile.lock", "composer.lock",
            "node_modules/", "bower_components/", "vendor/", "vendors/",
            "venv/", ".venv/", "env/", ".env", ".env.*",
            "output/", "out/", "bin/", "obj/", ".git/", ".hg/", ".svn/", ".bzr/",
            ".DS_Store", "Thumbs.db", "*.log", "*.log.*", "*.tmp", "*.temp", "*.swp", "*.swo",
            ".idea/", ".vscode/", "*.sublime-project", "*.sublime-workspace",
            "coverage.xml", ".coverage", "nosetests.xml", "pytestdebug.log",
            "*.bak", "*.old", "*.orig", ".gitattributes", ".gitmodules",
            "LICENSE", "LICENSE.*", "CONTRIBUTING.md", "CODE_OF_CONDUCT.md", "SECURITY.md",
            "poetry.toml", "setup.cfg", "MANIFEST.in", "mkdocs.yml"
        ],
        "LANGUAGE_MAPPING": {
            ".py": "python", ".js": "javascript", ".jsx": "javascript", ".ts": "typescript", ".tsx": "typescript",
            ".java": "java", ".kt": "kotlin", ".swift": "swift", ".c": "c", ".h": "c", ".cpp": "cpp", ".hpp": "cpp",
            ".cs": "csharp", ".go": "go", ".rs": "rust", ".rb": "ruby", ".php": "php", ".sh": "bash",
            ".html": "html", ".css": "css", ".scss": "scss", ".json": "json", ".yaml": "yaml", ".yml": "yaml",
            ".xml": "xml", ".sql": "sql", ".dockerfile": "dockerfile", "dockerfile": "dockerfile",
            ".md": "markdown", ".rst": "rst", ".gitignore":"gitignore",
        },
        "base_gen_agent_settings": {
            "max_file_size_kb_for_inclusion": 1024,
            "default_output_filename_stem": "codebase_snapshot",
            "output_subdir_relative_to_project": "mindX/memory/generated_docs/codebase_snapshots"
        }
    }

    def __init__(self, memory_agent: MemoryAgent, config_file_path_override_str: Optional[str] = None, agent_id: str = "base_gen_agent_v1.1", belief_system: Optional[BeliefSystem] = None):
        self.agent_id = agent_id
        self.belief_system = belief_system
        self.memory_agent = memory_agent
        self.log_prefix = f"[{self.agent_id}]"

        # Ensure the agent's data directory exists upon initialization
        self.data_dir = self.memory_agent.get_agent_data_directory(self.agent_id)

        global_cfg = Config()

        if config_file_path_override_str:
            self.agent_config_file_path = Path(config_file_path_override_str).resolve()
            logger.info(f"{self.log_prefix} Using specified config file: '{self.agent_config_file_path}'")
        else:
            default_path_from_global_cfg = global_cfg.get("base_gen_agent.config_file_path")
            if default_path_from_global_cfg:
                self.agent_config_file_path = (PROJECT_ROOT / default_path_from_global_cfg).resolve()
            else:
                self.agent_config_file_path = (PROJECT_ROOT / self.DEFAULT_AGENT_CONFIG_FILE_PATH_RELATIVE).resolve()
            logger.info(f"{self.log_prefix} Using resolved config file path: '{self.agent_config_file_path}'")

        self.config_data = self._load_and_merge_config_from_file()
        max_file_kb = self.get_agent_setting('max_file_size_kb_for_inclusion', 1024)
        logger.info(f"{self.log_prefix} Initialized. Config source: '{self.agent_config_file_path}'. Max file size: {max_file_kb}KB.")

    def get_agent_setting(self, key: str, default_value: Any = None) -> Any:
        return self.config_data.get("base_gen_agent_settings", {}).get(key, default_value)

    def _load_and_merge_config_from_file(self) -> Dict[str, Any]:
        current_config = copy.deepcopy(self.INTERNAL_FALLBACK_CONFIG_DATA)
        if self.agent_config_file_path.exists() and self.agent_config_file_path.is_file():
            try:
                with self.agent_config_file_path.open("r", encoding="utf-8") as f:
                    loaded_config_from_file = json.load(f)
                self._deep_update_dict(current_config, loaded_config_from_file)
                logger.info(f"{self.log_prefix} Loaded and merged agent config from '{self.agent_config_file_path}'")
            except Exception as e: # pragma: no cover
                logger.error(f"{self.log_prefix} Error reading/parsing config file '{self.agent_config_file_path}': {e}. Using internal fallback defaults only.")
                current_config = copy.deepcopy(self.INTERNAL_FALLBACK_CONFIG_DATA)
        else:
             logger.warning(f"{self.log_prefix} Agent config file '{self.agent_config_file_path}' not found. Using internal fallback defaults. Consider creating the file with desired settings.")
        return current_config

    def _save_agent_config_to_file(self) -> bool: # pragma: no cover
        try:
            self.memory_agent.save_memory(
                memory_type="config",
                category="bdi_agent",
                data=self.config_data,
                metadata={"agent_id": self.agent_id}
            )
            logger.info(f"{self.log_prefix} Agent configuration saved to '{self.agent_config_file_path}'")
            return True
        except Exception as e:
            logger.error(f"{self.log_prefix} Error saving agent configuration to '{self.agent_config_file_path}': {e}", exc_info=True)
            return False

    def _deep_update_dict(self, target: Dict, source: Dict): # pragma: no cover
        for key, value in source.items():
            if isinstance(value, dict) and key in target and isinstance(target[key], dict):
                self._deep_update_dict(target[key], value)
            elif isinstance(value, list) and key in target and isinstance(target[key], list) and key == "HARD_CODED_EXCLUDES":
                existing_set = set(target[key])
                for item in value:
                    if item not in existing_set: target[key].append(item)
                target[key] = sorted(list(set(target[key])))
            else:
                target[key] = value

    def update_config_setting(self, key_path: str, new_value: Any, save_after: bool = True) -> bool: # pragma: no cover
        logger.info(f"{self.log_prefix} Attempting to update config: '{key_path}' with value (type: {type(new_value).__name__})")
        try:
            keys = key_path.split('.')
            d = self.config_data
            for key_part in keys[:-1]:
                d = d.setdefault(key_part, {})
                if not isinstance(d, dict):
                    logger.error(f"{self.log_prefix} Config update failed: Path part '{key_part}' in '{key_path}' is not a dictionary."); return False
            final_key = keys[-1]
            if final_key == "HARD_CODED_EXCLUDES" and isinstance(new_value, list) and \
               new_value and isinstance(new_value[0], dict) and "_LIST_OP_" in new_value[0]:
                op_dict = new_value.pop(0)
                operation = op_dict["_LIST_OP_"]
                items_to_operate = new_value
                current_list = d.get(final_key, [])
                if not isinstance(current_list, list): current_list = []
                if operation == "APPEND_UNIQUE":
                    for item in items_to_operate:
                        if item not in current_list: current_list.append(item)
                    d[final_key] = sorted(list(set(current_list)))
                elif operation == "REMOVE":
                    d[final_key] = [item for item in current_list if item not in items_to_operate]
                else:
                    logger.warning(f"{self.log_prefix} Unknown list op '{operation}' for '{key_path}'. Replacing list.")
                    d[final_key] = items_to_operate
            elif isinstance(new_value, dict) and final_key in d and isinstance(d[final_key], dict) and new_value.get("_MERGE_DEEP_", False):
                new_value_copy = new_value.copy(); new_value_copy.pop("_MERGE_DEEP_")
                self._deep_update_dict(d[final_key], new_value_copy)
            else:
                d[final_key] = new_value
            logger.info(f"{self.log_prefix} Config setting '{key_path}' updated in memory.")
            if save_after:
                return self._save_agent_config_to_file()
            return True
        except Exception as e:
            logger.error(f"{self.log_prefix} Failed to update config setting '{key_path}': {e}", exc_info=True)
            return False

    def _guess_language(self, file_extension: str) -> str: # pragma: no cover
        ext = file_extension.lower()
        if not ext.startswith('.'): ext = '.' + ext
        mapping = self.config_data.get("LANGUAGE_MAPPING", self.INTERNAL_FALLBACK_CONFIG_DATA["LANGUAGE_MAPPING"])
        return mapping.get(ext, '')

    def _load_gitignore_specs(self, root_path: Path):
        if pathspec is None:
            logger.error(f"{self.log_prefix} 'pathspec' library not available. Cannot process .gitignore files.")
            return None
        all_patterns: List[str] = []
        try:
            for gitignore_file_path in root_path.rglob(".gitignore"):
                try: lines = gitignore_file_path.read_text(encoding="utf-8").splitlines()
                except Exception as e_read: logger.warning(f"{self.log_prefix} Could not read {gitignore_file_path}: {e_read}"); continue
                try: gitignore_dir_relative_to_root = gitignore_file_path.parent.relative_to(root_path)
                except ValueError: gitignore_dir_relative_to_root = Path(".")

                for line in lines:
                    line = line.strip()
                    if not line or line.startswith("#"): continue
                    if gitignore_dir_relative_to_root != Path("."):
                        if line.startswith('/'):
                            all_patterns.append((gitignore_dir_relative_to_root / line.lstrip('/')).as_posix())
                        else:
                            all_patterns.append((gitignore_dir_relative_to_root / line).as_posix())
                    else:
                         all_patterns.append(line)

            if (root_path / ".git").is_dir(): all_patterns.append("/.git/")
            if all_patterns:
                logger.debug(f"{self.log_prefix} Loaded {len(all_patterns)} patterns from .gitignore files under {root_path}.")
                return pathspec.PathSpec.from_lines(pathspec.patterns.GitWildMatchPattern, all_patterns)
            else: logger.debug(f"{self.log_prefix} No .gitignore patterns found or loaded for {root_path}."); return None
        except Exception as e: logger.error(f"{self.log_prefix} Error loading .gitignore for {root_path}: {e}", exc_info=True); return None

    def _should_include_file( self, file_abs_path: Path, root_path: Path,
        include_glob_patterns: Optional[List[str]], user_exclude_glob_patterns: Optional[List[str]],
        gitignore_spec: Optional[Any], use_gitignore_rules: bool = True ) -> bool: # pragma: no cover
        try: relative_file_path_for_match = file_abs_path.relative_to(root_path)
        except ValueError: logger.warning(f"{self.log_prefix} File {file_abs_path} not under root {root_path}. Excluding."); return False

        path_for_gitignore_match = relative_file_path_for_match.as_posix()

        if use_gitignore_rules and gitignore_spec and gitignore_spec.match_file(path_for_gitignore_match):
            logger.debug(f"{self.log_prefix} Excluding '{path_for_gitignore_match}' by .gitignore.")
            return False

        hardcoded_excludes = self.config_data.get("HARD_CODED_EXCLUDES", self.INTERNAL_FALLBACK_CONFIG_DATA["HARD_CODED_EXCLUDES"])
        all_exclude_glob_patterns = list(set((user_exclude_glob_patterns or []) + hardcoded_excludes))

        if any(fnmatch.fnmatch(file_abs_path.name, pattern) or \
               fnmatch.fnmatch(path_for_gitignore_match, pattern) or \
               any(fnmatch.fnmatch(part, pattern.strip('/')) for part in relative_file_path_for_match.parts if pattern.endswith('/') or pattern.startswith('/'))
               for pattern in all_exclude_glob_patterns):
            logger.debug(f"{self.log_prefix} Excluding '{path_for_gitignore_match}' by custom/hardcoded exclude pattern.")
            return False

        if include_glob_patterns is not None:
            if not any(fnmatch.fnmatch(path_for_gitignore_match, pattern) or fnmatch.fnmatch(file_abs_path.name, pattern) for pattern in include_glob_patterns):
                logger.debug(f"{self.log_prefix} Excluding '{path_for_gitignore_match}' as it does not match any include pattern.")
                return False
        return True

    def _build_tree_dict(self, root_scan_path: Path, relative_file_paths_to_include: List[Path]) -> Dict[str, Any]: # pragma: no cover
        tree: Dict[str, Any] = {}
        for rel_path in sorted(relative_file_paths_to_include):
            parts = rel_path.parts; current_level = tree
            for part in parts[:-1]: current_level = current_level.setdefault(part, {})
            current_level[parts[-1]] = {}
        return tree

    def _format_tree_lines(self, tree_dict: Dict[str, Any], indent_str: str = "", is_root_level: bool = True) -> List[str]: # pragma: no cover
        lines = []
        sorted_keys = sorted(tree_dict.keys(), key=lambda k: (not isinstance(tree_dict[k], dict) or not tree_dict[k], k.lower()))
        for i, key in enumerate(sorted_keys):
            is_last_item_in_level = (i == len(sorted_keys) - 1)
            connector = "" if is_root_level else ("└── " if is_last_item_in_level else "├── ")
            new_indent_for_children = indent_str + ("    " if (is_root_level or is_last_item_in_level) else "│   ")
            is_directory_node = bool(tree_dict[key])
            lines.append(f"{indent_str}{connector}{key}{'/' if is_directory_node else ''}")
            if is_directory_node:
                lines.extend(self._format_tree_lines(tree_dict[key], new_indent_for_children, is_root_level=False))
        return lines

    def execute(
        self, root_path_str: str, output_file_str: Optional[str] = None,
        include_patterns: Optional[List[str]] = None, user_exclude_patterns: Optional[List[str]] = None,
        use_gitignore: bool = True ) -> Tuple[bool, Dict[str, Any]]: # pragma: no cover
        return self.generate_markdown_summary(
            root_path_str=root_path_str,
            output_file_str=output_file_str,
            include_patterns=include_patterns,
            user_exclude_patterns=user_exclude_patterns,
            use_gitignore=use_gitignore
        )

    def generate_markdown_summary(
        self, root_path_str: str, output_file_str: Optional[str] = None,
        include_patterns: Optional[List[str]] = None, user_exclude_patterns: Optional[List[str]] = None,
        use_gitignore: bool = True ) -> Tuple[bool, Dict[str, Any]]: # pragma: no cover

        root_path = Path(root_path_str)
        if not root_path.is_absolute():
            if root_path_str.startswith('mindx/'):
                root_path = (PROJECT_ROOT / root_path_str).resolve()
            else:
                root_path = (PROJECT_ROOT / root_path_str).resolve()
        else:
            root_path = root_path.resolve()
        effective_output_file: Path
        if output_file_str:
            effective_output_file = Path(output_file_str)
            if not effective_output_file.is_absolute():
                 effective_output_file = (PROJECT_ROOT / effective_output_file).resolve()
        else:
            # Use the agent's data_dir which was ensured at init
            output_subdir = self.data_dir / "generated_docs"
            input_dir_name_slug = root_path.name.replace(" ", "_").replace("/", "_")
            default_stem = self.get_agent_setting("default_output_filename_stem", "codebase_snapshot")
            effective_output_file = output_subdir / f"{input_dir_name_slug}_{default_stem}.md"

        logger.info(f"{self.log_prefix} Documentation generation: Input='{root_path}', Output='{effective_output_file}'")
        if not root_path.is_dir(): err_msg = f"Input path '{root_path}' is not a valid directory."; logger.error(f"{self.log_prefix} {err_msg}"); return False, {"status": "ERROR", "message": err_msg, "output_file": None, "files_included": 0}

        gitignore_spec = self._load_gitignore_specs(root_path) if use_gitignore else None
        included_files_rel: List[Path] = []
        try:
            for item_abs in sorted(root_path.rglob("*")):
                if item_abs.is_file() and self._should_include_file(item_abs, root_path, include_patterns, user_exclude_patterns, gitignore_spec, use_gitignore):
                    included_files_rel.append(item_abs.relative_to(root_path))
        except Exception as e_scan: err_msg = f"Error scanning directory '{root_path}': {e_scan}"; logger.error(f"{self.log_prefix} {err_msg}", exc_info=True); return False, {"status": "ERROR", "message": err_msg, "output_file": None, "files_included": 0}

        if not included_files_rel: logger.warning(f"{self.log_prefix} No files matched criteria in '{root_path}'. Output will be minimal.")

        tree_str = "[No files included to generate tree]"
        if included_files_rel:
            try:
                tree_dict = self._build_tree_dict(root_path, included_files_rel)
                tree_lines = self._format_tree_lines(tree_dict, indent_str="  ", is_root_level=True)
                tree_str = "\n".join([root_path.name + "/"] + tree_lines) if tree_lines else root_path.name + "/"
            except Exception as e_tree: err_msg = f"Error building directory tree: {e_tree}"; logger.error(f"{self.log_prefix} {err_msg}", exc_info=True); return False, {"status": "ERROR", "message": err_msg, "output_file": None, "files_included": 0}

        md_lines = [f"# Codebase Snapshot: {root_path.name}", f"Generated by: {self.agent_id} on {datetime.now().strftime('%Y-%m-%d %H:%M:%S %Z')}", f"Source Directory (resolved): `{root_path}`", "", "## Directory Structure", "", "```text", tree_str, "```", "", "## File Contents", ""]
        max_fsize_bytes = self.get_agent_setting("max_file_size_kb_for_inclusion", 1024) * 1024
        num_processed = 0
        for rel_p in included_files_rel:
            file_abs = root_path / rel_p; num_processed +=1
            lang_guess = self._guess_language(file_abs.suffix)
            md_lines.append(f"### `{rel_p.as_posix()}`\n\n```{lang_guess if lang_guess else ''}")
            try:
                file_size = file_abs.stat().st_size
                if file_size > max_fsize_bytes:
                    content = f"[File content omitted: Size ({file_size // 1024:,}KB) exceeds limit ({max_fsize_bytes // 1024:,}KB)]"
                    logger.warning(f"{self.log_prefix} Omitting content of '{rel_p.as_posix()}' due to size ({file_size} bytes).")
                else: content = file_abs.read_text(encoding="utf-8", errors="replace")
            except Exception as e_rc: content = f"[Error reading file '{rel_p.as_posix()}': {e_rc}]"; logger.warning(f"{self.log_prefix} {content}")
            md_lines.append(content.strip()); md_lines.append("```\n")

        try:
            effective_output_file.parent.mkdir(parents=True, exist_ok=True)
            with effective_output_file.open("w", encoding="utf-8") as f: f.write("\n".join(md_lines))
            msg = f"Markdown documentation generated successfully: {effective_output_file}"
            logger.info(f"{self.log_prefix} {msg}")
            
            if self.belief_system:
                belief_key = f"basegen.snapshot.{root_path.name}.{datetime.now().strftime('%Y%m%d%H%M%S')}"
                belief_value = {
                    "output_file": str(effective_output_file),
                    "files_included": num_processed,
                    "timestamp": time.time()
                }
                asyncio.create_task(self.belief_system.add_belief(belief_key, belief_value, 0.9, BeliefSource.DERIVED))

            return True, {"status": "SUCCESS", "message": msg, "output_file": str(effective_output_file), "files_included": num_processed}
        except Exception as e_w:
            err_msg = f"Error writing output Markdown to '{effective_output_file}': {e_w}"
            logger.error(f"{self.log_prefix} {err_msg}", exc_info=True)
            return False, {"status": "ERROR", "message": err_msg, "output_file": str(effective_output_file), "files_included": num_processed}

def main_cli(): # pragma: no cover
    parser = argparse.ArgumentParser(
        description="Generate Markdown documentation for a codebase directory.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter )
    parser.add_argument("input_dir", help="Path to the codebase root directory to document.")
    parser.add_argument("-o", "--output", default=None, help="Output Markdown file path. If None, a default name is generated.")
    parser.add_argument("--include", nargs="+", default=None, help="Glob pattern(s) for files to explicitly include.")
    parser.add_argument("--exclude", nargs="+", default=None, help="Glob pattern(s) for files/directories to explicitly exclude.")
    parser.add_argument("--no-gitignore", action="store_true", help="Disable applying .gitignore file exclusions.")
    parser.add_argument("--config-file", default=None, help=f"Path to a custom agent JSON configuration file. Overrides default config path resolution.")
    parser.add_argument("--update-config", default=None, help="JSON string of settings to update in the agent's used config file. Example: '{\"base_gen_agent_settings.max_file_size_kb_for_inclusion\": 512}'")

    args = parser.parse_args()
    Config()

    try:
        # Create a MemoryAgent instance for standalone CLI usage
        memory_agent = MemoryAgent()
        agent = BaseGenAgent(memory_agent=memory_agent, config_file_path_override_str=args.config_file)
        if args.update_config:
            try:
                updates_dict = json.loads(args.update_config)
                if not isinstance(updates_dict, dict): raise ValueError("Update data must be a JSON object string.")
                all_ok = True
                for key_path, new_val in updates_dict.items():
                    if not agent.update_config_setting(key_path, new_val, save_after=False):
                        all_ok = False; logger.error(f"{agent.log_prefix} CLI: Failed to stage config update for key: {key_path}")
                if all_ok:
                    if agent._save_agent_config_to_file(): print(json.dumps({"status": "SUCCESS", "message": f"Agent configuration '{agent.agent_config_file_path}' updated successfully."}))
                    else: print(json.dumps({"status": "FAILURE", "message": f"Agent configuration updated in memory, but FAILED to save to '{agent.agent_config_file_path}'."})); sys.exit(1)
                else: print(json.dumps({"status": "FAILURE", "message": "One or more configuration updates failed in memory. Config file not saved."})); sys.exit(1)
                sys.exit(0)
            except Exception as e_cfg_update: print(json.dumps({"status": "ERROR", "message": f"Error processing --update-config: {e_cfg_update}"}), file=sys.stderr); sys.exit(2)

        output_file_path_str_for_gen: Optional[str] = args.output

        result = agent.generate_markdown_summary(
            root_path_str=args.input_dir, output_file_str=output_file_path_str_for_gen,
            include_patterns=args.include, user_exclude_patterns=args.exclude,
            use_gitignore=not args.no_gitignore,
        )
        print(json.dumps(result, indent=2)); sys.exit(0 if result["status"] == "SUCCESS" else 1)
    except SystemExit: raise
    except Exception as e:
        print(json.dumps({"status": "FATAL_ERROR", "message": str(e), "error_type": type(e).__name__}), file=sys.stderr)
        logger.critical(f"Fatal error in BaseGenAgent CLI: {e}", exc_info=True); sys.exit(2)

if __name__ == "__main__": # pragma: no cover
    Config()
    main_cli()
