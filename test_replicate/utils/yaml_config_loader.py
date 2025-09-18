# mindx/utils/yaml_config_loader.py
"""
Utility for loading and parsing YAML configuration files.
"""
import yaml
from pathlib import Path
from typing import Dict, Any, Optional
from .logging_config import get_logger

logger = get_logger(__name__)

def load_yaml_file(file_path: Path) -> Optional[Dict[str, Any]]:
    """
    Loads a single YAML file and returns its content as a dictionary.

    Args:
        file_path: The Path object pointing to the YAML file.

    Returns:
        A dictionary with the parsed YAML content, or None if an error occurs.
    """
    if not file_path.is_file():
        logger.warning(f"YAML file not found at: {file_path}")
        return None
    
    try:
        with file_path.open("r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        logger.info(f"Successfully loaded YAML configuration from {file_path.name}")
        return data
    except yaml.YAMLError as e:
        logger.error(f"Error parsing YAML file {file_path}: {e}", exc_info=True)
    except Exception as e:
        logger.error(f"Failed to read or process YAML file {file_path}: {e}", exc_info=True)
    
    return None
