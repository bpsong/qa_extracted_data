"""
ArrayFieldManager for Schema Editor

Provides array field configuration interfaces for both scalar and object arrays.
Integrates with the existing SchemaEditorView field type system.
"""

import streamlit as st
import logging
from typing import Dict, Any, List, Optional
from utils.ui_feedback import Notify

logger = logging.getLogger(__name__)


class ArrayFieldManager:
    """Manager for array field configuration in Schema Editor"""
    
    @staticmethod
    def render_array_field_config(field_id: str, field: Dict[str, Any]) -> None:
        """
        Render array field configuration interface
        
        Args:
            field_id: Unique identifier for the field
            field: Field configuration dictionary
        """
        st.subheader("Array Field Configuration")
        
        # Initialize items config if not present
        if 'items' not in field:
            field['items'] = {'type': 'string'}
        
        # Array type selection (scalar vs object)
        array_type_key = f"array_type_{field_id}"
        current_item_type = field['items'].get('type', 'string')
        
        # Determine if this is a scalar or object array
        is_object_array = current_item_type == 'object'
        array_type = 'object' if is_object_array else 'scalar'
        
        array_type = st.selectbox(
            "Array Type",
            options=['scalar', 'object'],
            index=1 if is_object_array else 0,
            help="Choose whether this array contains simple values (scalar) or complex objects",
            key=array_type_key
        )
        
        # Update field type based on selection
        if array_type == 'object':
            field['items'] = ArrayFieldManager._sanitize_object_items(field['items'])
            ArrayFieldManager._render_object_array_config(field_id, field)
        else:
            # Render scalar array configuration
            scalar_type = current_item_type if current_item_type in ['string', 'integer', 'number', 'boolean', 'date', 'enum'] else 'string'
            field['items'] = ArrayFieldManager._sanitize_scalar_items(field['items'], scalar_type)
            ArrayFieldManager._render_scalar_array_config(field_id, field)

    @staticmethod
    def _sanitize_scalar_items(items_config: Dict[str, Any], item_type: str) -> Dict[str, Any]:
        """
        Normalize scalar item configuration, removing incompatible keys when switching types.
        """
        supported_scalar_types = ['string', 'integer', 'number', 'boolean', 'date', 'enum']
        normalized_type = item_type if item_type in supported_scalar_types else 'string'
        
        type_specific_keys = {
            'string': {'min_length', 'max_length', 'pattern'},
            'number': {'min_value', 'max_value', 'step'},
            'integer': {'min_value', 'max_value', 'step'},
            'boolean': set(),
            'date': set(),
            'enum': {'choices'}
        }
        
        allowed_keys = {'type', 'default'}
        allowed_keys.update(type_specific_keys.get(normalized_type, set()))
        if normalized_type == 'enum':
            allowed_keys.add('choices')
        
        sanitized: Dict[str, Any] = {}
        for key in allowed_keys:
            if key == 'type':
                continue
            if key in items_config:
                sanitized[key] = items_config[key]
        
        sanitized['type'] = normalized_type
        return sanitized

    @staticmethod
    def _sanitize_object_items(items_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalize object item configuration, ensuring properties dict and removing scalar-only keys.
        """
        scalar_only_keys = {
            'min_length', 'max_length', 'pattern', 'min_value', 'max_value', 'step',
            'choices', 'default'
        }
        
        sanitized: Dict[str, Any] = {
            key: value for key, value in items_config.items()
            if key not in scalar_only_keys
        }
        sanitized['type'] = 'object'
        
        properties = sanitized.get('properties')
        if not isinstance(properties, dict):
            sanitized['properties'] = {}
        
        return sanitized
    
    @staticmethod
    def _render_scalar_array_config(field_id: str, field: Dict[str, Any]) -> None:
        """
        Render configuration interface for scalar arrays
        
        Args:
            field_id: Unique identifier for the field
            field: Field configuration dictionary
        """
        st.markdown("**Scalar Array Configuration**")
        
        # Item type selection
        item_type_key = f"scalar_array_item_type_{field_id}"
        supported_scalar_types = ['string', 'integer', 'number', 'boolean', 'date', 'enum']
        
        current_type = field['items'].get('type', 'string')
        if current_type not in supported_scalar_types:
            current_type = 'string'
        
        item_type = st.selectbox(
            "Item Type",
            options=supported_scalar_types,
            index=supported_scalar_types.index(current_type),
            help="Type of values stored in this array",
            key=item_type_key
        )
        
        field['items'] = ArrayFieldManager._sanitize_scalar_items(field['items'], item_type)
        
        # Type-specific constraints
        ArrayFieldManager._render_scalar_constraints(field_id, field, item_type)
    
    @staticmethod
    def _render_scalar_constraints(field_id: str, field: Dict[str, Any], item_type: str) -> None:
        """
        Render type-specific constraints for scalar array items
        
        Args:
            field_id: Unique identifier for the field
            field: Field configuration dictionary
            item_type: Type of scalar items
        """
        items_config = field['items']
        
        if item_type == 'string':
            col1, col2 = st.columns(2)
            
            with col1:
                min_length = st.number_input(
                    "Min Length",
                    min_value=0,
                    value=items_config.get('min_length', 0),
                    help="Minimum length for string items",
                    key=f"string_min_length_{field_id}"
                )
                if min_length > 0:
                    items_config['min_length'] = min_length
                elif 'min_length' in items_config:
                    del items_config['min_length']
            
            with col2:
                max_length = st.number_input(
                    "Max Length",
                    min_value=1,
                    value=items_config.get('max_length', 100),
                    help="Maximum length for string items",
                    key=f"string_max_length_{field_id}"
                )
                items_config['max_length'] = max_length
            
            # Pattern validation
            pattern = st.text_input(
                "Pattern (Regex)",
                value=items_config.get('pattern', ''),
                help="Regular expression pattern for validation",
                key=f"string_pattern_{field_id}"
            )
            if pattern:
                items_config['pattern'] = pattern
            elif 'pattern' in items_config:
                del items_config['pattern']
        
        elif item_type in ['integer', 'number']:
            col1, col2 = st.columns(2)
            
            with col1:
                min_value = st.number_input(
                    "Min Value",
                    value=items_config.get('min_value', 0),
                    help="Minimum value for numeric items",
                    key=f"numeric_min_value_{field_id}"
                )
                items_config['min_value'] = min_value
            
            with col2:
                max_value = st.number_input(
                    "Max Value",
                    value=items_config.get('max_value', 1000),
                    help="Maximum value for numeric items",
                    key=f"numeric_max_value_{field_id}"
                )
                items_config['max_value'] = max_value
            
            if item_type == 'number':
                step = st.number_input(
                    "Step",
                    min_value=0.01,
                    value=items_config.get('step', 0.01),
                    help="Step size for number inputs",
                    key=f"number_step_{field_id}"
                )
                items_config['step'] = step
        
        elif item_type == 'boolean':
            default_value = st.checkbox(
                "Default Value",
                value=items_config.get('default', False),
                help="Default value for new boolean items",
                key=f"boolean_default_{field_id}"
            )
            items_config['default'] = default_value
        
        elif item_type == 'enum':
            ArrayFieldManager._render_enum_config(field_id, field)
    
    @staticmethod
    def _render_enum_config(field_id: str, field: Dict[str, Any]) -> None:
        """
        Render enum configuration for scalar arrays
        
        Args:
            field_id: Unique identifier for the field
            field: Field configuration dictionary
        """
        items_config = field['items']
        
        st.markdown("**Enum Options**")
        
        # Get current choices
        current_choices = items_config.get('choices', [])
        
        # Text area for choices (one per line)
        choices_text = st.text_area(
            "Enum Choices (one per line)",
            value='\n'.join(current_choices),
            help="Enter each enum option on a separate line",
            key=f"enum_choices_{field_id}"
        )
        
        # Parse choices from text
        if choices_text.strip():
            choices = [line.strip() for line in choices_text.split('\n') if line.strip()]
            items_config['choices'] = choices
            
            # Default value selection
            if choices:
                current_default = items_config.get('default', choices[0] if choices else '')
                default_index = 0
                if current_default in choices:
                    default_index = choices.index(current_default)
                
                default_choice = st.selectbox(
                    "Default Choice",
                    options=choices,
                    index=default_index,
                    help="Default value for new enum items",
                    key=f"enum_default_{field_id}"
                )
                items_config['default'] = default_choice
        else:
            items_config['choices'] = []
            if 'default' in items_config:
                del items_config['default']
    
    @staticmethod
    def _render_object_array_config(field_id: str, field: Dict[str, Any]) -> None:
        """
        Render configuration interface for object arrays
        
        Args:
            field_id: Unique identifier for the field
            field: Field configuration dictionary
        """
        st.markdown("**Object Array Configuration**")
        
        # Initialize properties if not present
        if 'properties' not in field['items']:
            field['items']['properties'] = {}
        
        properties = field['items']['properties']
        
        # Property management
        st.markdown("**Object Properties**")
        
        # Add new property
        col1, col2 = st.columns([3, 1])
        with col1:
            new_prop_name = st.text_input(
                "New Property Name",
                placeholder="Enter property name",
                key=f"new_prop_name_{field_id}"
            )
        with col2:
            if st.button("Add Property", key=f"add_prop_{field_id}"):
                if new_prop_name and new_prop_name not in properties:
                    properties[new_prop_name] = {
                        'type': 'string',
                        'label': new_prop_name.replace('_', ' ').title(),
                        'required': False
                    }
                    st.rerun()
                elif new_prop_name in properties:
                    Notify.warn(f"Property '{new_prop_name}' already exists")
                elif not new_prop_name:
                    Notify.warn("Property name cannot be empty")
        
        # Display existing properties
        if properties:
            # Use list() to avoid modification during iteration
            for prop_name in list(properties.keys()):
                if prop_name in properties:  # Check if property still exists (might have been deleted)
                    ArrayFieldManager._render_property_config(field_id, prop_name, properties[prop_name], properties)
        else:
            st.info("No properties defined. Add a property to get started.")
    
    @staticmethod
    def _render_property_config(field_id: str, prop_name: str, prop_config: Dict[str, Any], properties_dict: Dict[str, Any]) -> bool:
        """
        Render configuration for a single object property
        
        Args:
            field_id: Unique identifier for the field
            prop_name: Name of the property
            prop_config: Property configuration dictionary
            properties_dict: Parent properties dictionary for deletion
            
        Returns:
            True if property should be deleted, False otherwise
        """
        with st.expander(f"Property: {prop_name}", expanded=True):
            col1, col2 = st.columns([4, 1])
            
            with col1:
                # Property label
                label = st.text_input(
                    "Label",
                    value=prop_config.get('label', prop_name.replace('_', ' ').title()),
                    key=f"prop_label_{field_id}_{prop_name}"
                )
                prop_config['label'] = label
                
                # Property type
                supported_types = ['string', 'integer', 'number', 'boolean', 'date', 'enum']
                current_type = prop_config.get('type', 'string')
                if current_type not in supported_types:
                    current_type = 'string'
                
                prop_type = st.selectbox(
                    "Type",
                    options=supported_types,
                    index=supported_types.index(current_type),
                    key=f"prop_type_{field_id}_{prop_name}"
                )
                prop_config['type'] = prop_type
                
                # Required checkbox
                required = st.checkbox(
                    "Required",
                    value=prop_config.get('required', False),
                    key=f"prop_required_{field_id}_{prop_name}"
                )
                prop_config['required'] = required
                
                # Type-specific constraints
                ArrayFieldManager._render_property_constraints(field_id, prop_name, prop_config, prop_type)
            
            with col2:
                # Delete property button
                confirm_key = f"delete_prop_confirm_{field_id}_{prop_name}"
                
                if confirm_key in st.session_state and st.session_state[confirm_key]:
                    # Show confirmation dialog
                    st.warning(f"Delete property '{prop_name}'?")
                    col_yes, col_no = st.columns(2)
                    
                    with col_yes:
                        if st.button("Delete", key=f"confirm_delete_{field_id}_{prop_name}"):
                            # Actually delete the property
                            if prop_name in properties_dict:
                                del properties_dict[prop_name]
                            # Clear confirmation state
                            del st.session_state[confirm_key]
                            st.rerun()
                    
                    with col_no:
                        if st.button("Cancel", key=f"cancel_delete_{field_id}_{prop_name}"):
                            # Cancel deletion
                            del st.session_state[confirm_key]
                            st.rerun()
                else:
                    # Show delete button
                    if st.button("Delete", key=f"delete_prop_{field_id}_{prop_name}", help="Delete property"):
                        st.session_state[confirm_key] = True
                        st.rerun()
        
        return False  # Property not deleted in this render
    
    @staticmethod
    def _render_property_constraints(field_id: str, prop_name: str, prop_config: Dict[str, Any], prop_type: str) -> None:
        """
        Render type-specific constraints for object properties
        
        Args:
            field_id: Unique identifier for the field
            prop_name: Name of the property
            prop_config: Property configuration dictionary
            prop_type: Type of the property
        """
        if prop_type == 'string':
            col1, col2 = st.columns(2)
            
            with col1:
                min_length = st.number_input(
                    "Min Length",
                    min_value=0,
                    value=prop_config.get('min_length', 0),
                    key=f"prop_string_min_{field_id}_{prop_name}"
                )
                if min_length > 0:
                    prop_config['min_length'] = min_length
                elif 'min_length' in prop_config:
                    del prop_config['min_length']
            
            with col2:
                max_length = st.number_input(
                    "Max Length",
                    min_value=1,
                    value=prop_config.get('max_length', 100),
                    key=f"prop_string_max_{field_id}_{prop_name}"
                )
                prop_config['max_length'] = max_length
        
        elif prop_type in ['integer', 'number']:
            col1, col2 = st.columns(2)
            
            # Determine step and default values based on type
            if prop_type == 'integer':
                step = 1
                default_min = 0
                default_max = 1000
            else:  # number
                step = 0.01
                default_min = 0.0
                default_max = 1000.0
            
            with col1:
                current_min = prop_config.get('min_value')
                if current_min is not None:
                    # Preserve existing value with correct type
                    min_value = int(current_min) if prop_type == 'integer' else float(current_min)
                else:
                    min_value = default_min
                
                min_value = st.number_input(
                    "Min Value",
                    value=min_value,
                    step=step,
                    key=f"prop_numeric_min_{field_id}_{prop_name}"
                )
                prop_config['min_value'] = min_value
            
            with col2:
                current_max = prop_config.get('max_value')
                if current_max is not None:
                    # Preserve existing value with correct type
                    max_value = int(current_max) if prop_type == 'integer' else float(current_max)
                else:
                    max_value = default_max
                
                max_value = st.number_input(
                    "Max Value",
                    value=max_value,
                    step=step,
                    key=f"prop_numeric_max_{field_id}_{prop_name}"
                )
                prop_config['max_value'] = max_value
        
        elif prop_type == 'enum':
            # Enum choices for property
            current_choices = prop_config.get('choices', [])
            choices_text = st.text_area(
                "Enum Choices (one per line)",
                value='\n'.join(current_choices),
                key=f"prop_enum_choices_{field_id}_{prop_name}"
            )
            
            if choices_text.strip():
                choices = [line.strip() for line in choices_text.split('\n') if line.strip()]
                prop_config['choices'] = choices
            else:
                prop_config['choices'] = []
    
    @staticmethod
    def validate_array_config(field_config: Dict[str, Any]) -> List[str]:
        """
        Validate array field configuration
        
        Args:
            field_config: Field configuration dictionary
            
        Returns:
            List of validation error messages
        """
        errors = []
        
        if 'items' not in field_config:
            errors.append("Array field must have 'items' configuration")
            return errors
        
        items_config = field_config['items']
        item_type = items_config.get('type')
        
        if not item_type:
            errors.append("Array items must have a type specified")
            return errors
        
        supported_scalar_types = {'string', 'integer', 'number', 'boolean', 'date', 'enum'}
        
        if item_type == 'object':
            # Validate object array
            properties = items_config.get('properties', {})
            if not properties:
                errors.append("Object arrays must have at least one property defined")
            
            for prop_name, prop_config in properties.items():
                if not prop_config.get('type'):
                    errors.append(f"Property '{prop_name}' must have a type specified")
                
                # Validate enum choices
                if prop_config.get('type') == 'enum':
                    choices = prop_config.get('choices', [])
                    if not choices:
                        errors.append(f"Enum property '{prop_name}' must have at least one choice")
        
        elif item_type in supported_scalar_types:
            if 'properties' in items_config:
                errors.append("Scalar arrays cannot include 'properties'; switch to object array to configure nested fields")
            
            if item_type == 'enum':
                choices = items_config.get('choices', [])
                if not choices:
                    errors.append("Enum arrays must have at least one choice defined")
            elif items_config.get('choices'):
                errors.append(f"Array items of type '{item_type}' cannot define 'choices'")
            
            if item_type != 'string':
                for key in ('min_length', 'max_length', 'pattern'):
                    if key in items_config:
                        errors.append(f"Only string arrays may include '{key}' constraints")
            
            if item_type not in {'number', 'integer'}:
                for key in ('min_value', 'max_value', 'step'):
                    if key in items_config:
                        errors.append(f"Only numeric arrays may include '{key}' constraints")
        else:
            errors.append(f"Array items have unsupported type '{item_type}'")
        
        return errors
    
    @staticmethod
    def generate_array_yaml(field_name: str, field_config: Dict[str, Any]) -> str:
        """
        Generate YAML representation of array field configuration
        
        Args:
            field_name: Name of the field
            field_config: Field configuration dictionary
            
        Returns:
            YAML string representation
        """
        import yaml
        
        # Create a clean config for YAML generation
        yaml_config = {
            'type': 'array',
            'label': field_config.get('label', field_name.replace('_', ' ').title()),
            'required': field_config.get('required', False),
            'items': field_config['items'].copy()
        }
        
        # Add help text if present
        if field_config.get('help'):
            yaml_config['help'] = field_config['help']
        
        # Clean up empty values
        def clean_dict(d):
            if isinstance(d, dict):
                return {k: clean_dict(v) for k, v in d.items() if v is not None and v != ''}
            return d
        
        yaml_config = clean_dict(yaml_config)
        
        # Generate YAML
        return yaml.dump({field_name: yaml_config}, default_flow_style=False, sort_keys=False)
