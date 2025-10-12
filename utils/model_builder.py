"""
Dynamic Pydantic model builder for JSON QA webapp.
Creates Pydantic models from schema definitions for validation and form generation.
"""

from typing import Dict, Any, Type, Optional, List, Union, Tuple, Set
from datetime import datetime, date
from pydantic import BaseModel, Field, field_validator, create_model, ValidationError
# Detect pydantic v2 ConfigDict if available; fallback to v1 behaviour
try:
    from pydantic import ConfigDict  # type: ignore
    _PYDANTIC_V2 = True
except Exception:
    ConfigDict = None  # type: ignore
    _PYDANTIC_V2 = False
import re
import logging

logger = logging.getLogger(__name__)


def create_model_from_schema(schema: Dict[str, Any], model_name: str = "DynamicModel") -> Type[BaseModel]:
    """
    Create a Pydantic model from a schema definition.
    
    Args:
        schema: Schema dictionary containing field definitions
        model_name: Name for the generated model class
        
    Returns:
        Pydantic model class
    """
    if 'fields' not in schema:
        raise ValueError("Schema must contain 'fields' key")
    
    fields = schema['fields']
    model_fields = {}
    validators_dict = {}
    
    # Process each field in the schema
    for field_name, field_config in fields.items():
        field_type, field_info = create_field_from_config(field_name, field_config)
        model_fields[field_name] = (field_type, field_info)
        
        # Add custom validators if needed
        field_validators = create_validators_for_field(field_name, field_config)
        validators_dict.update(field_validators)
    
    # Create the dynamic model
    try:
        # Create model normally
        dynamic_model = create_model(
            model_name,
            **model_fields,
            __validators__=validators_dict
        )

        # Apply extra='ignore' in a guarded, compatible way for both pydantic v2 and v1.
        # Try pydantic v2 approach first (model_config with ConfigDict), fall back to v1 inner Config.
        try:
            if ConfigDict is not None:
                # pydantic v2
                dynamic_model.model_config = ConfigDict(extra='ignore')
            else:
                # ConfigDict not present -> treat as v1
                raise RuntimeError("ConfigDict not available")
        except Exception:
            # Fallback to pydantic v1 behaviour: add inner Config with extra='ignore'
            try:
                Config = type("Config", (), {"extra": "ignore"})
                setattr(dynamic_model, "Config", Config)
            except Exception:
                # best-effort: silently ignore failures to avoid breaking environments
                pass

        logger.info(f"Created dynamic model '{model_name}' with {len(fields)} fields")
        return dynamic_model

    except Exception as e:
        logger.error(f"Failed to create model '{model_name}': {e}")
        raise


def create_field_from_config(field_name: str, field_config: Dict[str, Any]) -> tuple:
    """
    Create a Pydantic field from schema field configuration.
    
    Args:
        field_name: Name of the field
        field_config: Field configuration from schema
        
    Returns:
        Tuple of (field_type, FieldInfo)
    """
    field_type = get_field_type(field_config)
    
    # Create field info with constraints and metadata
    field_kwargs = {}
    
    # Handle default values
    if 'default' in field_config:
        field_kwargs['default'] = field_config['default']
    elif not field_config.get('required', False):
        field_kwargs['default'] = None
    # For required fields, don't set default (Pydantic V2 handles this automatically)
    
    # Add description/label
    if 'label' in field_config:
        field_kwargs['description'] = field_config['label']
    elif 'description' in field_config:
        field_kwargs['description'] = field_config['description']
    
    # Add type-specific constraints
    field_type_name = field_config.get('type', 'string')
    
    if field_type_name == 'string':
        if 'min_length' in field_config:
            field_kwargs['min_length'] = field_config['min_length']
        if 'max_length' in field_config:
            field_kwargs['max_length'] = field_config['max_length']
    
    elif field_type_name in ['number', 'integer', 'float']:
        if 'min_value' in field_config:
            field_kwargs['ge'] = field_config['min_value']  # greater than or equal
        if 'max_value' in field_config:
            field_kwargs['le'] = field_config['max_value']  # less than or equal
    
    # Create FieldInfo
    field_info = Field(**field_kwargs)
    
    return field_type, field_info


def get_field_type(field_config: Dict[str, Any]) -> Type:
    """
    Map schema field type to Python/Pydantic type.
    
    Args:
        field_config: Field configuration from schema
        
    Returns:
        Python type for the field
    """
    field_type = field_config.get('type', 'string')
    
    if field_type == 'string':
        return str
    
    elif field_type == 'integer':
        return int
    
    elif field_type in ['number', 'float']:
        return float
    
    elif field_type == 'boolean':
        return bool
    
    elif field_type == 'date':
        return date
    
    elif field_type == 'datetime':
        return datetime
    
    elif field_type == 'enum':
        # Create a literal type from choices
        choices = field_config.get('choices', [])
        if not choices:
            logger.warning(f"Enum field has no choices, defaulting to str")
            return str
        
        # For Pydantic, we'll use str with validation
        return str
    
    elif field_type == 'array':
        # Get the item type
        items_config = field_config.get('items', {'type': 'string'})
        item_type = get_field_type(items_config)
        return List[item_type]
    
    elif field_type == 'object':
        # For nested objects, create a nested model
        properties = field_config.get('properties', {})
        if properties:
            nested_model = create_nested_model(properties, f"NestedModel_{id(field_config)}")
            return nested_model
        else:
            # Generic dict if no properties defined
            return Dict[str, Any]
    
    else:
        logger.warning(f"Unknown field type '{field_type}', defaulting to str")
        return str


def create_nested_model(properties: Dict[str, Any], model_name: str) -> Type[BaseModel]:
    """
    Create a nested Pydantic model for object fields.
    
    Args:
        properties: Dictionary of property definitions
        model_name: Name for the nested model
        
    Returns:
        Pydantic model class for the nested object
    """
    nested_fields = {}
    nested_validators = {}
    
    for prop_name, prop_config in properties.items():
        field_type, field_info = create_field_from_config(prop_name, prop_config)
        nested_fields[prop_name] = (field_type, field_info)
        
        # Add validators for nested fields
        prop_validators = create_validators_for_field(prop_name, prop_config)
        nested_validators.update(prop_validators)
    
    nested_model = create_model(
        model_name,
        **nested_fields,
        __validators__=nested_validators
    )

    # Apply same extra='ignore' behaviour to nested models
    # Try pydantic v2 approach first (ConfigDict), fall back to v1 inner Config class.
    try:
        if ConfigDict is not None:
            nested_model.model_config = ConfigDict(extra='ignore')
        else:
            raise RuntimeError("ConfigDict not available")
    except Exception:
        try:
            Config = type("Config", (), {"extra": "ignore"})
            setattr(nested_model, "Config", Config)
        except Exception:
            pass

    return nested_model


def create_validators_for_field(field_name: str, field_config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Create custom validators for a field based on its configuration.
    
    Args:
        field_name: Name of the field
        field_config: Field configuration from schema
        
    Returns:
        Dictionary of validator functions
    """
    validators = {}
    field_type = field_config.get('type', 'string')
    
    # String pattern validation
    if field_type == 'string' and 'pattern' in field_config:
        pattern = field_config['pattern']
        
        def pattern_validator(cls, v):
            if v is not None and not re.match(pattern, str(v)):
                raise ValueError(f'Field must match pattern: {pattern}')
            return v
        
        @field_validator(field_name)
        @classmethod
        def pattern_validator_func(cls, v):
            if v is not None and not re.match(pattern, str(v)):
                raise ValueError(f'Field must match pattern: {pattern}')
            return v
        validators[f'validate_{field_name}_pattern'] = pattern_validator_func
    
    # Enum validation
    if field_type == 'enum':
        choices = field_config.get('choices', [])
        
        def enum_validator(cls, v):
            if v is not None and v not in choices:
                raise ValueError(f'Value must be one of: {choices}')
            return v
        
        @field_validator(field_name)
        @classmethod
        def enum_validator_func(cls, v):
            if v is not None and v not in choices:
                raise ValueError(f'Value must be one of: {choices}')
            return v
        validators[f'validate_{field_name}_enum'] = enum_validator_func
    
    # Custom validation rules
    if 'validation' in field_config:
        validation_rules = field_config['validation']
        
        def custom_validator(cls, v):
            # Apply custom validation logic here
            # This is extensible for future custom validation needs
            return v
        
        @field_validator(field_name)
        @classmethod
        def custom_validator_func(cls, v):
            # Apply custom validation logic here
            # This is extensible for future custom validation needs
            return v
        validators[f'validate_{field_name}_custom'] = custom_validator_func
    
    return validators


def get_streamlit_widget_type(field_config: Dict[str, Any]) -> str:
    """
    Determine the appropriate Streamlit widget type for a field.
    
    Args:
        field_config: Field configuration from schema
        
    Returns:
        Streamlit widget type name
    """
    field_type = field_config.get('type', 'string')
    
    if field_type == 'string':
        if 'choices' in field_config:
            return 'selectbox'
        elif field_config.get('multiline', False):
            return 'text_area'
        else:
            return 'text_input'
    
    elif field_type in ['integer', 'number', 'float']:
        return 'number_input'
    
    elif field_type == 'boolean':
        return 'checkbox'
    
    elif field_type == 'date':
        return 'date_input'
    
    elif field_type == 'datetime':
        return 'datetime_input'
    
    elif field_type == 'enum':
        return 'selectbox'
    
    elif field_type == 'array':
        return 'data_editor'
    
    elif field_type == 'object':
        return 'json_editor'  # Custom widget for nested objects
    
    else:
        return 'text_input'


def get_widget_kwargs(field_config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Get keyword arguments for Streamlit widgets based on field configuration.
    
    Args:
        field_config: Field configuration from schema
        
    Returns:
        Dictionary of widget kwargs
    """
    kwargs = {}
    field_type = field_config.get('type', 'string')
    
    # Common properties
    if 'label' in field_config:
        kwargs['label'] = field_config['label']
    
    if 'help' in field_config:
        kwargs['help'] = field_config['help']
    elif 'description' in field_config:
        kwargs['help'] = field_config['description']
    
    if 'default' in field_config:
        kwargs['value'] = field_config['default']
    
    if field_config.get('readonly', False):
        kwargs['disabled'] = True
    
    # Type-specific properties
    if field_type == 'string':
        if 'max_length' in field_config:
            kwargs['max_chars'] = field_config['max_length']
        
        if 'placeholder' in field_config:
            kwargs['placeholder'] = field_config['placeholder']
    
    elif field_type in ['integer', 'number', 'float']:
        if 'min_value' in field_config:
            kwargs['min_value'] = field_config['min_value']
        
        if 'max_value' in field_config:
            kwargs['max_value'] = field_config['max_value']
        
        if 'step' in field_config:
            kwargs['step'] = field_config['step']
        elif field_type == 'integer':
            kwargs['step'] = 1
        else:
            kwargs['step'] = 0.01
    
    elif field_type == 'enum':
        if 'choices' in field_config:
            kwargs['options'] = field_config['choices']
        
        # Don't set index here, let the form generator handle it
    
    return kwargs


def model_to_dict(model_instance: BaseModel, exclude_none: bool = True) -> Dict[str, Any]:
    """
    Convert a Pydantic model instance to a dictionary.
    
    Args:
        model_instance: Pydantic model instance
        exclude_none: Whether to exclude None values
        
    Returns:
        Dictionary representation of the model
    """
    return model_instance.model_dump(exclude_none=exclude_none)


def dict_to_model(data: Dict[str, Any], model_class: Type[BaseModel]) -> BaseModel:
    """
    Create a model instance from a dictionary.
    
    Args:
        data: Dictionary data
        model_class: Pydantic model class
        
    Returns:
        Model instance
    """
    try:
        return model_class(**data)
    except Exception as e:
        logger.error(f"Failed to create model instance: {e}")
        raise


def get_model_fields_info(model_class: Type[BaseModel]) -> Dict[str, Dict[str, Any]]:
    """
    Get information about all fields in a Pydantic model.
    
    Args:
        model_class: Pydantic model class
        
    Returns:
        Dictionary with field information
    """
    fields_info = {}
    
    for field_name, field in model_class.model_fields.items():
        field_info = {
            'type': field.annotation,
            'required': field.is_required(),
            'default': field.default if field.default is not ... else None,
            'description': field.description,
            'constraints': {}
        }
        
        # Extract constraints from field metadata
        constraints = getattr(field, 'constraints', [])
        for constraint in constraints:
            if hasattr(constraint, 'min_length'):
                field_info['constraints']['min_length'] = constraint.min_length
            if hasattr(constraint, 'max_length'):
                field_info['constraints']['max_length'] = constraint.max_length
            if hasattr(constraint, 'ge'):
                field_info['constraints']['min_value'] = constraint.ge
            if hasattr(constraint, 'le'):
                field_info['constraints']['max_value'] = constraint.le
        
        fields_info[field_name] = field_info
    
    return fields_info


def validate_model_data(data: Dict[str, Any], model_class: Type[BaseModel]) -> List[str]:
    """
    Validate data against a Pydantic model and return validation errors.
    
    Args:
        data: Data to validate
        model_class: Pydantic model class
        
    Returns:
        List of validation error messages
    """
    try:
        model_class(**data)
        return []  # No errors
    except ValidationError as e:
        # Pydantic validation errors: construct readable messages
        error_messages = []
        for error in e.errors():
            field_path = ' -> '.join(str(loc) for loc in error.get('loc', []))
            message = f"{field_path}: {error.get('msg')}"
            error_messages.append(message)
        return error_messages
    except Exception as e:
        return [str(e)]


def create_form_schema(model_class: Type[BaseModel]) -> Dict[str, Any]:
    """
    Create a form schema from a Pydantic model for UI generation.
    
    Args:
        model_class: Pydantic model class
        
    Returns:
        Form schema dictionary
    """
    form_schema = {
        'title': getattr(model_class, '__title__', model_class.__name__),
        'fields': {}
    }
    
    fields_info = get_model_fields_info(model_class)
    
    for field_name, field_info in fields_info.items():
        # Convert Pydantic field info to form field config
        field_config = {
            'type': _python_type_to_schema_type(field_info['type']),
            'label': field_info.get('description', field_name.replace('_', ' ').title()),
            'required': field_info['required'],
            'default': field_info['default']
        }
        
        # Add constraints
        constraints = field_info.get('constraints', {})
        field_config.update(constraints)
        
        form_schema['fields'][field_name] = field_config
    
    return form_schema


def _python_type_to_schema_type(python_type: Type) -> str:
    """
    Convert Python type to schema type string.
    
    Args:
        python_type: Python type
        
    Returns:
        Schema type string
    """
    if python_type == str:
        return 'string'
    elif python_type == int:
        return 'integer'
    elif python_type == float:
        return 'number'
    elif python_type == bool:
        return 'boolean'
    elif python_type == date:
        return 'date'
    elif python_type == datetime:
        return 'datetime'
    elif hasattr(python_type, '__origin__'):
        if python_type.__origin__ == list:
            return 'array'
        elif python_type.__origin__ == dict:
            return 'object'
    
    return 'string'  # Default fallback


def filter_to_schema_fields(data: Dict[str, Any], schema_fields: Set[str]) -> Tuple[Dict[str, Any], List[str]]:
    """
    Filter a data dict to only keys present in schema_fields and return extras.

    Args:
        data: input data dictionary
        schema_fields: set of allowed schema field names

    Returns:
        Tuple of (filtered_dict, extras_list)
        - filtered_dict: {k: v for k in schema_fields if k in data}
        - extras_list: sorted list of keys present in data but not in schema_fields
    """
    if not isinstance(data, dict):
        return {}, []

    filtered = {k: v for k, v in data.items() if k in schema_fields}
    extras = sorted(list(set(data.keys()) - set(schema_fields)))
    return filtered, extras