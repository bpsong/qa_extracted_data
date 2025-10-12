"""
Schema loader for JSON QA webapp.
Handles loading and validation of YAML/JSON schema definitions based on configuration.
"""

import json
import yaml
from pathlib import Path
from typing import Dict, Any, Optional, List
import logging
import re
import os
import streamlit as st

# Configure logging
logger = logging.getLogger(__name__)

# Configuration and schema directories
CONFIG_FILE = Path("config.yaml")
SCHEMAS_DIR = Path("schemas")

# Supported field types
SUPPORTED_FIELD_TYPES = {
    'string', 'number', 'integer', 'float', 'boolean', 
    'date', 'datetime', 'enum', 'array', 'object'
}

# Global configuration cache
_config_cache = None


def ensure_directories():
    """Ensure required directories exist."""
    SCHEMAS_DIR.mkdir(exist_ok=True)


def load_config() -> Dict[str, Any]:
    """
    Load application configuration from config.yaml.
    
    Returns:
        Configuration dictionary with default values if file not found
    """
    global _config_cache
    
    # Return cached config if available
    if _config_cache is not None:
        return _config_cache
    
    # Default configuration
    default_config = {
        "app": {
            "name": "JSON QA Webapp",
            "version": "1.0.0",
            "debug": False
        },
        "schema": {
            "primary_schema": "default_schema.yaml",
            "fallback_schema": "default_schema.yaml"
        },
        "ui": {
            "page_title": "JSON Quality Assurance",
            "sidebar_title": "Navigation"
        },
        "processing": {
            "lock_timeout": 60,
            "max_file_size": 10
        }
    }
    
    if not CONFIG_FILE.exists():
        logger.warning(f"Configuration file {CONFIG_FILE} not found, using defaults")
        _config_cache = default_config
        return _config_cache
    
    try:
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        # Merge with defaults to ensure all required keys exist
        merged_config = default_config.copy()
        if config:
            for section, values in config.items():
                if section in merged_config and isinstance(values, dict):
                    merged_config[section].update(values)
                else:
                    merged_config[section] = values
        
        _config_cache = merged_config
        logger.info(f"Successfully loaded configuration from {CONFIG_FILE}")
        return _config_cache
        
    except yaml.YAMLError as e:
        logger.error(f"YAML parsing error in {CONFIG_FILE}: {e}")
        logger.info("Using default configuration")
        _config_cache = default_config
        return _config_cache
    except Exception as e:
        logger.error(f"Error loading configuration {CONFIG_FILE}: {e}")
        logger.info("Using default configuration")
        _config_cache = default_config
        return _config_cache


def get_configured_schema() -> Dict[str, Any]:
    """
    Get the schema specified in the configuration.
    
    Returns:
        Schema dictionary (never None - returns fallback if primary not found)
    """
    ensure_directories()
    config = load_config()
    
    # Get schema configuration
    schema_config = config.get("schema", {})
    primary_schema = schema_config.get("primary_schema", "default_schema.yaml")
    fallback_schema = schema_config.get("fallback_schema", "default_schema.yaml")
    
    # Try to load primary schema
    schema = load_schema(primary_schema)
    if schema:
        logger.info(f"Using primary schema: {primary_schema}")
        return schema
    
    # Fall back to fallback schema
    logger.warning(f"Primary schema {primary_schema} not found, trying fallback: {fallback_schema}")
    schema = load_schema(fallback_schema)
    if schema:
        logger.info(f"Using fallback schema: {fallback_schema}")
        return schema
    
    # Create minimal fallback if no schemas found
    logger.error("No valid schemas found, creating minimal fallback")
    return create_fallback_schema()


def load_schema(schema_path: str) -> Optional[Dict[str, Any]]:
    """
    Load a schema from YAML or JSON file.
    
    Args:
        schema_path: Path to schema file (relative to schemas directory)
        
    Returns:
        Schema dictionary or None if loading fails
    """
    ensure_directories()
    
    full_path = SCHEMAS_DIR / schema_path
    
    if not full_path.exists():
        logger.error(f"Schema file not found: {full_path}")
        return None
    
    try:
        with open(full_path, 'r', encoding='utf-8') as f:
            if full_path.suffix.lower() in ['.yaml', '.yml']:
                schema = yaml.safe_load(f)
            elif full_path.suffix.lower() == '.json':
                schema = json.load(f)
            else:
                logger.error(f"Unsupported schema file format: {full_path.suffix}")
                return None
        
        # Validate schema structure
        if not validate_schema(schema):
            logger.error(f"Invalid schema structure in {schema_path}")
            return None
        
        logger.info(f"Successfully loaded schema: {schema_path}")
        return schema
        
    except yaml.YAMLError as e:
        logger.error(f"YAML parsing error in {schema_path}: {e}")
        return None
    except json.JSONDecodeError as e:
        logger.error(f"JSON parsing error in {schema_path}: {e}")
        return None
    except Exception as e:
        logger.error(f"Error loading schema {schema_path}: {e}")
        return None


def get_schema_for_file(filename: str) -> Dict[str, Any]:
    """
    Get the configured schema for any JSON file.
    
    This function is maintained for backward compatibility but now simply
    returns the configured schema regardless of filename.
    
    Args:
        filename: Name of the JSON file (ignored in new implementation)
        
    Returns:
        Schema dictionary from configuration
    """
    return get_configured_schema()


def validate_schema(schema: Dict[str, Any]) -> bool:
    """
    Validate schema structure and field definitions.
    
    Args:
        schema: Schema dictionary to validate
        
    Returns:
        True if schema is valid, False otherwise
    """
    if not isinstance(schema, dict):
        logger.error("Schema must be a dictionary")
        return False
    
    # Check for required top-level keys
    if 'fields' not in schema:
        logger.error("Schema must contain 'fields' key")
        return False
    
    fields = schema['fields']
    if not isinstance(fields, dict):
        logger.error("Schema 'fields' must be a dictionary")
        return False
    
    # Validate each field definition
    for field_name, field_config in fields.items():
        if not validate_field_config(field_name, field_config):
            return False
    
    return True


def validate_field_config(field_name: str, field_config: Dict[str, Any]) -> bool:
    """
    Validate individual field configuration.
    
    Args:
        field_name: Name of the field
        field_config: Field configuration dictionary
        
    Returns:
        True if field config is valid, False otherwise
    """
    if not isinstance(field_config, dict):
        logger.error(f"Field '{field_name}' config must be a dictionary")
        return False
    
    # Check required 'type' field
    if 'type' not in field_config:
        logger.error(f"Field '{field_name}' must have a 'type'")
        return False
    
    field_type = field_config['type']
    if field_type not in SUPPORTED_FIELD_TYPES:
        logger.error(f"Field '{field_name}' has unsupported type '{field_type}'. "
                    f"Supported types: {SUPPORTED_FIELD_TYPES}")
        return False
    
    # Validate type-specific configurations
    if field_type == 'enum':
        if 'choices' not in field_config:
            logger.error(f"Enum field '{field_name}' must have 'choices'")
            return False
        
        choices = field_config['choices']
        if not isinstance(choices, list) or len(choices) == 0:
            logger.error(f"Enum field '{field_name}' choices must be a non-empty list")
            return False
    
    if field_type == 'array':
        if 'items' not in field_config:
            logger.error(f"Array field '{field_name}' must have 'items' definition")
            return False
        
        # Recursively validate array item schema
        items_config = field_config['items']
        if isinstance(items_config, dict) and 'type' in items_config:
            if not validate_field_config(f"{field_name}[items]", items_config):
                return False
    
    if field_type == 'object':
        if 'properties' not in field_config:
            logger.error(f"Object field '{field_name}' must have 'properties'")
            return False
        
        # Recursively validate object properties
        properties = field_config['properties']
        if not isinstance(properties, dict):
            logger.error(f"Object field '{field_name}' properties must be a dictionary")
            return False
        
        for prop_name, prop_config in properties.items():
            if not validate_field_config(f"{field_name}.{prop_name}", prop_config):
                return False
    
    # Validate numeric constraints
    if field_type in ['number', 'integer', 'float']:
        for constraint in ['min_value', 'max_value']:
            if constraint in field_config:
                value = field_config[constraint]
                if not isinstance(value, (int, float)):
                    logger.error(f"Field '{field_name}' {constraint} must be a number")
                    return False
    
    # Validate string constraints
    if field_type == 'string':
        for constraint in ['min_length', 'max_length']:
            if constraint in field_config:
                value = field_config[constraint]
                if not isinstance(value, int) or value < 0:
                    logger.error(f"Field '{field_name}' {constraint} must be a non-negative integer")
                    return False
        
        if 'pattern' in field_config:
            try:
                re.compile(field_config['pattern'])
            except re.error as e:
                logger.error(f"Field '{field_name}' has invalid regex pattern: {e}")
                return False
    
    return True


def create_fallback_schema() -> Dict[str, Any]:
    """
    Create a minimal fallback schema for unknown document types.
    
    Returns:
        Basic schema that accepts common field types with validation
    """
    return {
        "title": "Fallback Schema",
        "description": "Generic schema for unknown document types with basic validation",
        "fields": {
            "supplier_name": {
                "type": "string",
                "label": "Supplier Name",
                "required": True,
                "min_length": 1,
                "max_length": 200
            },
            "invoice_amount": {
                "type": "number",
                "label": "Invoice Amount",
                "required": True,
                "min_value": 0.01
            },
            "invoice_date": {
                "type": "date",
                "label": "Invoice Date",
                "required": False
            },
            "document_type": {
                "type": "string",
                "label": "Document Type",
                "required": False,
                "default": "unknown"
            },
            "content": {
                "type": "object",
                "label": "Document Content",
                "required": False,
                "properties": {}
            }
        }
    }


def list_available_schemas() -> List[str]:
    """
    List all available schema files in the schemas directory.
    
    Returns:
        List of schema filenames
    """
    ensure_directories()
    
    schema_files = []
    
    for pattern in ['*.yaml', '*.yml', '*.json']:
        schema_files.extend([f.name for f in SCHEMAS_DIR.glob(pattern)])
    
    return sorted(schema_files)


def get_schema_info(schema_path: str) -> Optional[Dict[str, Any]]:
    """
    Get metadata information about a schema.
    
    Args:
        schema_path: Path to schema file
        
    Returns:
        Dictionary with schema metadata or None if schema not found
    """
    schema = load_schema(schema_path)
    if not schema:
        return None
    
    fields = schema.get('fields', {})
    
    info = {
        "title": schema.get('title', 'Untitled Schema'),
        "description": schema.get('description', ''),
        "field_count": len(fields),
        "required_fields": [
            name for name, config in fields.items() 
            if config.get('required', False)
        ],
        "field_types": {
            name: config.get('type', 'unknown') 
            for name, config in fields.items()
        }
    }
    
    return info


def validate_data_against_schema(data: Dict[str, Any], schema: Dict[str, Any]) -> List[str]:
    """
    Validate data against schema and return list of validation errors.
    
    Args:
        data: Data to validate
        schema: Schema to validate against
        
    Returns:
        List of validation error messages (empty if valid)
    """
    errors = []
    fields = schema.get('fields', {})
    
    # Check required fields
    for field_name, field_config in fields.items():
        if field_config.get('required', False):
            if field_name not in data or data[field_name] is None:
                errors.append(f"Required field '{field_name}' is missing or null")
    
    # Validate field types and constraints
    for field_name, value in data.items():
        if field_name not in fields:
            continue  # Skip unknown fields (could be extra data)
        
        field_config = fields[field_name]
        field_errors = validate_field_value(field_name, value, field_config)
        errors.extend(field_errors)
    
    return errors


def reload_config():
    """
    Force reload of configuration from file.
    Useful for testing or when configuration changes.
    """
    global _config_cache
    _config_cache = None
    return load_config()


def get_config_value(section: str, key: str, default: Any = None) -> Any:
    """
    Get a specific configuration value.
    
    Args:
        section: Configuration section (e.g., 'schema', 'ui')
        key: Configuration key within section
        default: Default value if not found
        
    Returns:
        Configuration value or default
    """
    config = load_config()
    return config.get(section, {}).get(key, default)


def validate_field_value(field_name: str, value: Any, field_config: Dict[str, Any]) -> List[str]:
    """
    Validate a single field value against its configuration.
    
    Args:
        field_name: Name of the field
        value: Value to validate
        field_config: Field configuration from schema
        
    Returns:
        List of validation error messages
    """
    errors = []
    field_type = field_config.get('type', 'string')
    
    # Skip validation for null values if field is not required
    if value is None and not field_config.get('required', False):
        return errors
    
    # Type-specific validation
    if field_type == 'string':
        if not isinstance(value, str):
            errors.append(f"Field '{field_name}' must be a string")
        else:
            # Length constraints
            min_length = field_config.get('min_length')
            max_length = field_config.get('max_length')
            
            if min_length is not None and len(value) < min_length:
                errors.append(f"Field '{field_name}' must be at least {min_length} characters")
            
            if max_length is not None and len(value) > max_length:
                errors.append(f"Field '{field_name}' must be at most {max_length} characters")
            
            # Pattern validation
            pattern = field_config.get('pattern')
            if pattern and not re.match(pattern, value):
                errors.append(f"Field '{field_name}' does not match required pattern")
    
    elif field_type in ['number', 'integer', 'float']:
        if not isinstance(value, (int, float)):
            errors.append(f"Field '{field_name}' must be a number")
        else:
            # Range constraints
            min_value = field_config.get('min_value')
            max_value = field_config.get('max_value')
            
            if min_value is not None and value < min_value:
                errors.append(f"Field '{field_name}' must be at least {min_value}")
            
            if max_value is not None and value > max_value:
                errors.append(f"Field '{field_name}' must be at most {max_value}")
    
    elif field_type == 'boolean':
        if not isinstance(value, bool):
            errors.append(f"Field '{field_name}' must be a boolean")
    
    elif field_type == 'enum':
        choices = field_config.get('choices', [])
        if value not in choices:
            errors.append(f"Field '{field_name}' must be one of: {choices}")
    
    elif field_type == 'array':
        if not isinstance(value, list):
            errors.append(f"Field '{field_name}' must be an array")
        else:
            # Validate array items if items schema is provided
            items_config = field_config.get('items')
            if items_config:
                for i, item in enumerate(value):
                    item_errors = validate_field_value(f"{field_name}[{i}]", item, items_config)
                    errors.extend(item_errors)
    
    elif field_type == 'object':
        if not isinstance(value, dict):
            errors.append(f"Field '{field_name}' must be an object")
        else:
            # Validate object properties
            properties = field_config.get('properties', {})
            for prop_name, prop_config in properties.items():
                prop_value = value.get(prop_name)
                prop_errors = validate_field_value(f"{field_name}.{prop_name}", prop_value, prop_config)
                errors.extend(prop_errors)
    
    return errors


def extract_field_names(schema: Dict[str, Any]) -> set[str]:
    """
    Extract field names from schema as a set.
    
    Args:
        schema: Schema dictionary
        
    Returns:
        Set of field names
    """
    if not isinstance(schema, dict) or 'fields' not in schema:
        return set()
    return set(schema['fields'].keys())


@st.cache_data(show_spinner=False)
def _load_schema_with_mtime(path: str, mtime: float) -> Optional[Dict[str, Any]]:
    """
    Load schema with mtime as cache key for hot-reload.
    
    Args:
        path: Schema path relative to schemas directory
        mtime: Modification time of the file
        
    Returns:
        Schema dictionary or None if loading fails
    """
    return load_schema(path)


def load_active_schema(path: str) -> Optional[Dict[str, Any]]:
    """
    Load active schema with hot-reload using file mtime.
    Updates session state with schema, mtime, fields, and version.
    
    Args:
        path: Schema path relative to schemas directory
        
    Returns:
        Schema dictionary or None if loading fails
    """
    full_path = SCHEMAS_DIR / path
    
    if not full_path.exists():
        logger.error(f"Schema file not found: {full_path}")
        return None
    
    mtime = os.path.getmtime(full_path)
    schema = _load_schema_with_mtime(path, mtime)
    
    if schema:
        st.session_state['active_schema'] = schema
        st.session_state['active_schema_mtime'] = mtime
        st.session_state['schema_fields'] = extract_field_names(schema)
        # Preserve explicit schema version if present in the schema; fall back to file mtime
        st.session_state['schema_version'] = schema.get("schema_version", mtime)
        logger.info(f"Loaded active schema: {path} (mtime: {mtime})")
    
    return schema