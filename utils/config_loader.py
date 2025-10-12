"""
Configuration loading utilities for the JSON QA webapp.

This module provides functionality to load and validate application
configuration including directory paths with fallback to defaults.
"""

import yaml
from pathlib import Path
from typing import Dict, Any, Optional
import logging
from copy import deepcopy

from .directory_config import DirectoryConfig
from .directory_exceptions import ConfigurationLoadError

logger = logging.getLogger(__name__)


def deep_merge(base_dict: Dict[str, Any], update_dict: Dict[str, Any]) -> Dict[str, Any]:
    """
    Deep merge two dictionaries, with update_dict taking precedence.
    
    Args:
        base_dict: Base dictionary (defaults)
        update_dict: Dictionary to merge in (user config)
        
    Returns:
        Merged dictionary
    """
    result = deepcopy(base_dict)
    
    for key, value in update_dict.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = deepcopy(value)
    
    return result


def get_default_config() -> Dict[str, Any]:
    """
    Get default configuration with current hardcoded values.
    
    Returns:
        Dictionary with default configuration
    """
    return {
        'app': {
            'name': 'JSON QA Webapp',
            'version': '1.0.0',
            'debug': False
        },
        'schema': {
            'primary_schema': 'invoice_schema.yaml',
            'fallback_schema': 'default_schema.yaml'
        },
        'directories': {
            'json_docs': 'json_docs',
            'corrected': 'corrected',
            'audits': 'audits',
            'pdf_docs': 'pdf_docs',
            'locks': 'locks'
        },
        'ui': {
            'page_title': 'JSON Quality Assurance',
            'sidebar_title': 'Navigation'
        },
        'processing': {
            'lock_timeout': 60,
            'max_file_size': 10
        }
    }


def load_config(config_path: Optional[Path] = None) -> Dict[str, Any]:
    """
    Load application configuration with directory support.
    
    Args:
        config_path: Optional path to config file (defaults to config.yaml)
        
    Returns:
        Complete configuration dictionary
        
    Raises:
        ConfigurationLoadError: If configuration loading fails critically
    """
    if config_path is None:
        config_path = Path("config.yaml")
    
    # Get default configuration
    default_config = get_default_config()
    
    # If config file doesn't exist, use defaults
    if not config_path.exists():
        logger.warning(f"Configuration file not found: {config_path}")
        logger.info("Using default configuration")
        return default_config
    
    try:
        # Load user configuration
        with open(config_path, 'r', encoding='utf-8') as f:
            user_config = yaml.safe_load(f)
        
        if user_config is None:
            logger.warning(f"Configuration file is empty: {config_path}")
            return default_config
        
        if not isinstance(user_config, dict):
            logger.error(f"Configuration file is not a valid dictionary: {config_path}")
            logger.info("Using default configuration")
            return default_config
        
        # Merge user config with defaults
        config = deep_merge(default_config, user_config)
        
        logger.info(f"Successfully loaded configuration from {config_path}")
        return config
        
    except yaml.YAMLError as e:
        logger.error(f"YAML parsing error in {config_path}: {e}")
        logger.info("Using default configuration")
        return default_config
        
    except (IOError, OSError) as e:
        logger.error(f"Failed to read configuration file {config_path}: {e}")
        logger.info("Using default configuration")
        return default_config
        
    except Exception as e:
        logger.error(f"Unexpected error loading configuration from {config_path}: {e}")
        logger.info("Using default configuration")
        return default_config


def validate_config(config: Dict[str, Any]) -> bool:
    """
    Validate configuration structure and required fields.
    
    Args:
        config: Configuration dictionary to validate
        
    Returns:
        True if configuration is valid, False otherwise
    """
    required_sections = ['app', 'schema', 'directories', 'ui', 'processing']
    
    try:
        # Check for required top-level sections
        for section in required_sections:
            if section not in config:
                logger.warning(f"Missing required configuration section: {section}")
                return False
        
        # Validate directories section
        directories = config.get('directories', {})
        required_dirs = ['json_docs', 'corrected', 'audits', 'pdf_docs', 'locks']
        
        for dir_name in required_dirs:
            if dir_name not in directories:
                logger.warning(f"Missing required directory configuration: {dir_name}")
                return False
            
            if not isinstance(directories[dir_name], str):
                logger.warning(f"Directory path must be string: {dir_name}")
                return False
        
        # Validate app section
        app = config.get('app', {})
        if 'name' not in app or 'version' not in app:
            logger.warning("Missing required app configuration (name or version)")
            return False
        
        # Validate processing section
        processing = config.get('processing', {})
        if 'lock_timeout' in processing:
            try:
                timeout = int(processing['lock_timeout'])
                if timeout <= 0:
                    logger.warning("lock_timeout must be positive")
                    return False
            except (ValueError, TypeError):
                logger.warning("lock_timeout must be a valid integer")
                return False
        
        if 'max_file_size' in processing:
            try:
                size = float(processing['max_file_size'])
                if size <= 0:
                    logger.warning("max_file_size must be positive")
                    return False
            except (ValueError, TypeError):
                logger.warning("max_file_size must be a valid number")
                return False
        
        return True
        
    except Exception as e:
        logger.error(f"Error during configuration validation: {e}")
        return False


def get_directory_config(config: Dict[str, Any]) -> DirectoryConfig:
    """
    Extract directory configuration from complete config.
    
    Args:
        config: Complete configuration dictionary
        
    Returns:
        DirectoryConfig instance
    """
    try:
        return DirectoryConfig.from_config(config)
    except Exception as e:
        logger.error(f"Failed to create DirectoryConfig: {e}")
        logger.info("Using default directory configuration")
        return DirectoryConfig.from_config(get_default_config())


def save_config(config: Dict[str, Any], config_path: Optional[Path] = None) -> bool:
    """
    Save configuration to YAML file.
    
    Args:
        config: Configuration dictionary to save
        config_path: Optional path to save to (defaults to config.yaml)
        
    Returns:
        True if save was successful, False otherwise
    """
    if config_path is None:
        config_path = Path("config.yaml")
    
    try:
        with open(config_path, 'w', encoding='utf-8') as f:
            yaml.dump(config, f, default_flow_style=False, indent=2, sort_keys=False)
        
        logger.info(f"Configuration saved to {config_path}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to save configuration to {config_path}: {e}")
        return False


def get_config_summary(config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Get a summary of the current configuration.
    
    Args:
        config: Configuration dictionary
        
    Returns:
        Dictionary with configuration summary
    """
    summary = {
        'app_name': config.get('app', {}).get('name', 'Unknown'),
        'app_version': config.get('app', {}).get('version', 'Unknown'),
        'debug_mode': config.get('app', {}).get('debug', False),
        'primary_schema': config.get('schema', {}).get('primary_schema', 'Unknown'),
        'directories': {},
        'lock_timeout': config.get('processing', {}).get('lock_timeout', 60),
        'max_file_size': config.get('processing', {}).get('max_file_size', 10)
    }
    
    # Add directory information
    directories = config.get('directories', {})
    for name, path in directories.items():
        summary['directories'][name] = str(path)
    
    return summary