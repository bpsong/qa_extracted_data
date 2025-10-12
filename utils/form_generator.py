"""
Dynamic form generator for JSON QA webapp.
Creates Streamlit forms based on schema definitions and Pydantic models.
"""

import streamlit as st
import json
from datetime import datetime, date
from typing import Dict, Any, List, Optional, Union
import logging

from .model_builder import get_streamlit_widget_type, get_widget_kwargs
from .session_manager import SessionManager
from .submission_handler import SubmissionHandler

logger = logging.getLogger(__name__)


class FormGenerator:
    """Generates dynamic forms based on schemas and handles form data."""
    
    @staticmethod
    def render_dynamic_form(schema: Dict[str, Any], current_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Render a dynamic form based on schema and return form data.
        
        Args:
            schema: Schema definition
            current_data: Current form data
            
        Returns:
            Updated form data from the form
        """
        st.subheader("📝 Extracted Data")
        
        if not schema or 'fields' not in schema:
            st.error("Invalid schema provided")
            return current_data
        
        # Create form
        with st.form("json_edit_form", clear_on_submit=False):
            fields = schema['fields']
            form_data = FormGenerator._render_form_fields(fields, current_data)
            
            # Get model class for validation
            model_class = SessionManager.get_model_class()
            
            # Form submission buttons
            col_buttons = st.columns(2)
            
            with col_buttons[0]:
                validate_submitted = st.form_submit_button("🔍 Validate Data")
            
            with col_buttons[1]:
                submit_submitted = st.form_submit_button("💾 Submit Changes", type="primary")
            
            # Handle validation button
            if validate_submitted:
                # Always save the form data first
                SessionManager.set_form_data(form_data)
                
                # Validate using comprehensive submission validation
                validation_errors = SubmissionHandler._validate_submission_data(form_data, schema, model_class)
                
                if validation_errors:
                    SessionManager.set_validation_errors(validation_errors)
                    st.error("❌ Please fix the following errors:")
                    for error in validation_errors:
                        st.error(f"  • {error}")
                else:
                    SessionManager.clear_validation_errors()
                    st.success("✅ Data validated successfully")
                
                # Always return the form_data to preserve changes
                return form_data
            
            # Handle submit button
            if submit_submitted:
                # Save form data
                SessionManager.set_form_data(form_data)
                
                # Validate first
                validation_errors = SubmissionHandler._validate_submission_data(form_data, schema, model_class)
                
                if validation_errors:
                    SessionManager.set_validation_errors(validation_errors)
                    st.error("❌ Validation failed. Please fix errors before submitting:")
                    for error in validation_errors:
                        st.error(f"  • {error}")
                    return form_data
                else:
                    SessionManager.clear_validation_errors()
                    st.success("✅ Validation passed. Submitting changes...")
                
                # Proceed with submission
                filename = SessionManager.get_current_file()
                original_data = SessionManager.get_original_data()
                user = SessionManager.get_current_user()
                
                if filename is None or original_data is None or user is None:
                    st.error("❌ Missing required information for submission")
                    return form_data
                
                success, errors = SubmissionHandler.validate_and_submit(
                    filename, form_data, original_data, schema, model_class, user
                )
                
                if success:
                    st.success("✅ Changes submitted successfully!")
                    # Clear state and navigate
                    SessionManager._clear_file_state()
                    SessionManager.set_current_page('queue')
                    st.rerun()
                else:
                    st.error("❌ Submission failed:")
                    for error in errors:
                        st.error(f"  • {error}")
                    SessionManager.set_validation_errors(errors)
                
                return form_data
            
            # If not submitted, return the built form_data to ensure latest widget values are used
            return form_data
    
    @staticmethod
    def _render_form_fields(fields: Dict[str, Any], current_data: Dict[str, Any]) -> Dict[str, Any]:
        """Render form fields based on schema definition."""
        form_data = {}
        
        # Group fields by category if possible
        grouped_fields = FormGenerator._group_fields(fields)
        for group_name, group_fields in grouped_fields.items():
            if group_name != "General":
                st.subheader(f"📋 {group_name}")
            
            # Render fields in columns for better layout
            cols = st.columns(2)
            col_index = 0
            
            for field_name, field_config in group_fields.items():
                with cols[col_index % 2]:
                    field_value = FormGenerator._render_field(
                        field_name,
                        field_config,
                        current_data.get(field_name)
                    )
                    form_data[field_name] = field_value
                col_index += 1
        
        return form_data

    @staticmethod
    def collect_current_form_data(schema: Dict[str, Any]) -> Dict[str, Any]:
        """Collect current form values from session state without rendering the UI."""
        form_data = {}
        fields = schema.get('fields', {})
        for field_name, field_config in fields.items():
            field_type = field_config.get('type', 'string')
            field_key = f"field_{field_name}"
            
            # Get regular field value
            if field_key in st.session_state:
                value = st.session_state[field_key]
                if value is not None:
                    form_data[field_name] = value
            
            # Override for array fields if applicable
            if field_type == 'array':
                array_key = f"array_{field_name}"
                json_array_key = f"json_array_{field_name}"
                
                if array_key in st.session_state and st.session_state[array_key] is not None:
                    form_data[field_name] = st.session_state[array_key]
                elif json_array_key in st.session_state and st.session_state[json_array_key] is not None:
                    try:
                        value = st.session_state[json_array_key]
                        if isinstance(value, str):
                            form_data[field_name] = json.loads(value)
                        else:
                            form_data[field_name] = value
                    except json.JSONDecodeError as e:
                        logger.warning(f"Invalid JSON for array {field_name}: {e}")
            
            # Override for object fields if applicable
            elif field_type == 'object':
                object_key = f"json_object_{field_name}"
                if object_key in st.session_state and st.session_state[object_key] is not None:
                    try:
                        value = st.session_state[object_key]
                        if isinstance(value, str):
                            form_data[field_name] = json.loads(value)
                        else:
                            form_data[field_name] = value
                    except json.JSONDecodeError as e:
                        logger.warning(f"Invalid JSON for object {field_name}: {e}")
        
        return form_data

    @staticmethod
    def _group_fields(fields: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
        """Group fields by category for better organization."""
        groups = {
            "General": {},
            "Financial": {},
            "Address": {},
            "Metadata": {},
            "Other": {}
        }
        
        # Define field categories
        financial_fields = ['amount', 'price', 'cost', 'tax', 'total', 'subtotal', 'currency', 'payment']
        address_fields = ['address', 'street', 'city', 'state', 'zip', 'postal', 'country']
        metadata_fields = ['confidence', 'timestamp', 'created', 'modified', 'extraction', 'processing']
        
        for field_name, field_config in fields.items():
            field_lower = field_name.lower()
            if any(fin in field_lower for fin in financial_fields):
                groups["Financial"][field_name] = field_config
            elif any(addr in field_lower for addr in address_fields):
                groups["Address"][field_name] = field_config
            elif any(meta in field_lower for meta in metadata_fields):
                groups["Metadata"][field_name] = field_config
            elif field_config.get('readonly', False):
                groups["Metadata"][field_name] = field_config
            else:
                groups["General"][field_name] = field_config
        
        return {k: v for k, v in groups.items() if v}
    
    @staticmethod
    def _render_field(field_name: str, field_config: Dict[str, Any], current_value: Any) -> Any:
        """Render a single form field based on its configuration."""
        try:
            field_type = field_config.get('type', 'string')
            widget_key = f"field_{field_name}"
            
            # Initialize widget kwargs
            widget_kwargs = {
                'key': widget_key,
                'label': field_config.get('label', field_name),
                'help': field_config.get('help', None),
                'disabled': field_config.get('readonly', False)
            }
            
            # First determine hydrated value from data or schema default
            
            if current_value is not None:
                hydrated_value = current_value
            elif 'default' in field_config:
                hydrated_value = field_config['default']
            elif field_config.get('required', False):
                # Set type-specific defaults for required fields
                if field_type == 'string':
                    hydrated_value = ''
                elif field_type in ['number', 'integer']:
                    hydrated_value = 0
                elif field_type == 'boolean':
                    hydrated_value = False
                elif field_type == 'enum' and 'choices' in field_config and field_config['choices']:
                    hydrated_value = field_config['choices'][0]  # Use first enum choice as default
                elif field_type == 'array':
                    hydrated_value = []
                elif field_type == 'object':
                    hydrated_value = {}
                else:
                    hydrated_value = None
            else:
                hydrated_value = None
                
            # Handle session state
            if widget_key in st.session_state:
                value_to_use = st.session_state[widget_key]
            else:
                value_to_use = hydrated_value
                st.session_state[widget_key] = value_to_use
            
            logger.debug(f"[_render_field] Field: {field_name}, Widget Key: {widget_key}, Value to Use: {value_to_use}, Session State Value: {st.session_state.get(widget_key)}")
            
            widget_kwargs['value'] = value_to_use
            
            # Determine widget type
            if field_type == 'string':
                if field_config.get('format') == 'date':
                    widget_type = 'date_input'
                elif field_config.get('format') == 'date-time':
                    widget_type = 'datetime_input'
                elif field_config.get('maxLength', 0) > 100:
                    widget_type = 'text_area'
                else:
                    widget_type = 'text_input'
            elif field_type == 'enum':
                widget_type = 'selectbox'
            elif field_type == 'number':
                widget_type = 'number_input'
            elif field_type == 'boolean':
                widget_type = 'checkbox'
            elif field_type in ['array', 'object']:
                if field_config.get('format') == 'data-grid':
                    widget_type = 'data_editor'
                else:
                    widget_type = 'json_editor'
            else:
                widget_type = 'text_input'
            
            # Render based on widget type
            if widget_type == 'text_input':
                return FormGenerator._render_text_input(field_name, field_config, widget_kwargs)
            elif widget_type == 'text_area':
                return FormGenerator._render_text_area(field_name, field_config, widget_kwargs)
            elif widget_type == 'number_input':
                return FormGenerator._render_number_input(field_name, field_config, widget_kwargs)
            elif widget_type == 'selectbox':
                return FormGenerator._render_selectbox(field_name, field_config, widget_kwargs)
            elif widget_type == 'checkbox':
                return FormGenerator._render_checkbox(field_name, field_config, widget_kwargs)
            elif widget_type == 'date_input':
                return FormGenerator._render_date_input(field_name, field_config, widget_kwargs)
            elif widget_type == 'datetime_input':
                return FormGenerator._render_datetime_input(field_name, field_config, widget_kwargs)
            elif widget_type == 'data_editor':
                return FormGenerator._render_array_editor(field_name, field_config, value_to_use or [])
            elif widget_type == 'json_editor':
                return FormGenerator._render_object_editor(field_name, field_config, value_to_use or {})
            else:
                # Fallback to text input
                return st.text_input(**widget_kwargs)
        
        except Exception as e:
            st.error(f"Error rendering field {field_name}")
            return current_value
    
    @staticmethod
    def _render_text_input(field_name: str, field_config: Dict[str, Any], kwargs: Dict[str, Any]) -> str:
        """Render text input field."""
        # Handle pattern validation display
        if 'pattern' in field_config:
            pattern = field_config['pattern']
            if 'help' not in kwargs:
                kwargs['help'] = f"Pattern: {pattern}"
            else:
                kwargs['help'] += f" | Pattern: {pattern}"
        
        # Remove value from kwargs since it's handled by session state
        kwargs.pop('value', None)
        
        value = st.text_input(**kwargs)
        
        # Show validation feedback
        if value and 'pattern' in field_config:
            import re
            if not re.match(field_config['pattern'], value):
                st.error(f"❌ Value doesn't match required pattern: {field_config['pattern']}")
        
        return value if value is not None else ""
    
    @staticmethod
    def _render_text_area(field_name: str, field_config: Dict[str, Any], kwargs: Dict[str, Any]) -> str:
        """Render text area field."""
        kwargs['height'] = 100  # Default height
        
        # Remove value from kwargs since it's handled by session state
        kwargs.pop('value', None)
            
        value = st.text_area(**kwargs)
        return value if value is not None else ""
    
    @staticmethod
    def _render_number_input(field_name: str, field_config: Dict[str, Any], kwargs: Dict[str, Any]) -> Union[int, float]:
        """Render number input field."""
        field_type = field_config.get('type', 'number')
        
        # Ensure all numeric parameters are of the same type
        if field_type == 'integer':
            kwargs['step'] = 1
            kwargs['format'] = "%d"
            # Convert min/max values to int if present
            if 'min_value' in kwargs and kwargs['min_value'] is not None:
                kwargs['min_value'] = int(kwargs['min_value'])
            if 'max_value' in kwargs and kwargs['max_value'] is not None:
                kwargs['max_value'] = int(kwargs['max_value'])
            if 'value' in kwargs and kwargs['value'] is not None:
                kwargs['value'] = int(kwargs['value'])
        else:
            if 'step' not in kwargs:
                kwargs['step'] = 0.01
            kwargs['format'] = "%.2f"
            # Convert min/max values to float if present
            if 'min_value' in kwargs and kwargs['min_value'] is not None:
                kwargs['min_value'] = float(kwargs['min_value'])
            if 'max_value' in kwargs and kwargs['max_value'] is not None:
                kwargs['max_value'] = float(kwargs['max_value'])
            if 'value' in kwargs and kwargs['value'] is not None:
                kwargs['value'] = float(kwargs['value'])
            if 'step' in kwargs:
                kwargs['step'] = float(kwargs['step'])
        
        # Remove value from kwargs since it's handled by session state
        kwargs.pop('value', None)
        
        return st.number_input(**kwargs)
    
    @staticmethod
    def _render_selectbox(field_name: str, field_config: Dict[str, Any], kwargs: Dict[str, Any]) -> Any:
        """Render selectbox field."""
        if field_config.get('type') == 'enum' and 'choices' in field_config:
            kwargs['options'] = field_config['choices']
            
            # Handle optional enums
            if not field_config.get('required', False):
                kwargs['options'] = [None] + list(kwargs['options'])
                kwargs['format_func'] = lambda x: "-- Select --" if x is None else str(x)
        
        # Remove value from kwargs since it's handled by session state
        kwargs.pop('value', None)
        
        return st.selectbox(**kwargs)
    
    @staticmethod
    def _render_checkbox(field_name: str, field_config: Dict[str, Any], kwargs: Dict[str, Any]) -> bool:
        """Render checkbox field."""
        # Convert value to boolean if needed
        if 'value' in kwargs and not isinstance(kwargs['value'], bool):
            kwargs['value'] = bool(kwargs['value'])
        
        # Remove value from kwargs since it's handled by session state
        kwargs.pop('value', None)
        
        return st.checkbox(**kwargs)
    
    @staticmethod
    def _render_date_input(field_name: str, field_config: Dict[str, Any], kwargs: Dict[str, Any]) -> Optional[date]:
        """Render date input field."""
        # Remove value from kwargs since it's handled by session state
        kwargs.pop('value', None)
        result = st.date_input(**kwargs)
        return result if result is not None else None
    
    @staticmethod
    def _render_datetime_input(field_name: str, field_config: Dict[str, Any], kwargs: Dict[str, Any]) -> datetime:
        """Render datetime input field."""
        # Streamlit doesn't have native datetime input, use date + time
        col1, col2 = st.columns(2)
        
        current_dt = kwargs.get('value')
        if isinstance(current_dt, str):
            try:
                current_dt = datetime.fromisoformat(current_dt)
            except:
                current_dt = datetime.now()
        elif not isinstance(current_dt, datetime):
            current_dt = datetime.now()
        
        with col1:
            date_part = st.date_input(
                f"{kwargs.get('label', field_name)} (Date)",
                value=current_dt.date(),
                key=f"{kwargs['key']}_date"
            )
        
        with col2:
            time_part = st.time_input(
                f"{kwargs.get('label', field_name)} (Time)",
                value=current_dt.time(),
                key=f"{kwargs['key']}_time"
            )
        
        return datetime.combine(date_part, time_part)
    
    @staticmethod
    def _render_array_editor(field_name: str, field_config: Dict[str, Any], current_value: Any) -> List[Any]:
        """Render array editor using st.data_editor."""
        import pandas as pd
        
        st.write(f"**{field_config.get('label', field_name)}**")
        
        # Convert current value to DataFrame
        if not current_value or not isinstance(current_value, list):
            current_value = []
        
        # Get item schema
        items_config = field_config.get('items', {})
        
        if items_config.get('type') == 'object' and 'properties' in items_config:
            # Object array - use data editor
            properties = items_config['properties']
            
            # Create DataFrame
            if current_value:
                df = pd.DataFrame(current_value)
            else:
                # Create empty DataFrame with correct columns
                columns = list(properties.keys())
                df = pd.DataFrame(columns=columns)
            
            # Configure column types
            column_config = {}
            for prop_name, prop_config in properties.items():
                prop_type = prop_config.get('type', 'string')
                if prop_type == 'number':
                    column_config[prop_name] = st.column_config.NumberColumn(
                        prop_config.get('label', prop_name),
                        help=prop_config.get('help', ''),
                        min_value=prop_config.get('min_value'),
                        max_value=prop_config.get('max_value'),
                        step=prop_config.get('step', 0.01)
                    )
                elif prop_type == 'boolean':
                    column_config[prop_name] = st.column_config.CheckboxColumn(
                        prop_config.get('label', prop_name),
                        help=prop_config.get('help', '')
                    )
                else:
                    column_config[prop_name] = st.column_config.TextColumn(
                        prop_config.get('label', prop_name),
                        help=prop_config.get('help', ''),
                        max_chars=prop_config.get('max_length')
                    )
            
            # Render data editor
            edited_df = st.data_editor(
                df,
                column_config=column_config,
                num_rows="dynamic",
                use_container_width=True,
                key=f"array_{field_name}"
            )
            
            return edited_df.to_dict('records')
        
        else:
            # Simple array - use text area with JSON
            st.write("Edit as JSON array:")
            json_str = st.text_area(
                f"JSON for {field_name}",
                value=json.dumps(current_value, indent=2),
                height=150,
                key=f"json_array_{field_name}"
            )
            
            try:
                return json.loads(json_str)
            except json.JSONDecodeError:
                st.error("❌ Invalid JSON format")
                return current_value
    
    @staticmethod
    def _render_object_editor(field_name: str, field_config: Dict[str, Any], current_value: Any) -> Dict[str, Any]:
        """Render object editor for nested objects."""
        st.write(f"**{field_config.get('label', field_name)}**")
        
        properties = field_config.get('properties', {})
        
        if properties:
            # Render nested form
            if not current_value or not isinstance(current_value, dict):
                current_value = {}
            
            nested_data = {}
            
            with st.container():
                for prop_name, prop_config in properties.items():
                    prop_value = FormGenerator._render_field(
                        f"{field_name}_{prop_name}",
                        prop_config,
                        current_value.get(prop_name)
                    )
                    nested_data[prop_name] = prop_value
            
            return nested_data
        
        else:
            # Generic object - use JSON editor
            json_str = st.text_area(
                f"JSON for {field_name}",
                value=json.dumps(current_value or {}, indent=2),
                height=150,
                key=f"json_object_{field_name}"
            )
            
            try:
                return json.loads(json_str)
            except json.JSONDecodeError:
                st.error("❌ Invalid JSON format")
                return current_value or {}
    
    # Removed _validate_form_data as validation now uses SubmissionHandler._validate_submission_data
    
    @staticmethod
    def _validate_field_value(field_name: str, value: Any, field_config: Dict[str, Any]) -> List[str]:
        """Validate a single field value."""
        errors = []
        
        # Check required fields
        if field_config.get('required', False) and (value is None or value == ''):
            errors.append(f"Field '{field_config.get('label', field_name)}' is required")
            return errors
        
        # Skip validation for empty optional fields
        if value is None or value == '':
            return errors
        
        field_type = field_config.get('type', 'string')
        
        # Type-specific validation
        if field_type == 'string':
            if not isinstance(value, str):
                errors.append(f"Field '{field_name}' must be text")
            else:
                # Length validation
                min_length = field_config.get('min_length')
                max_length = field_config.get('max_length')
                
                if min_length and len(value) < min_length:
                    errors.append(f"Field '{field_name}' must be at least {min_length} characters")
                
                if max_length and len(value) > max_length:
                    errors.append(f"Field '{field_name}' must be at most {max_length} characters")
                
                # Pattern validation
                pattern = field_config.get('pattern')
                if pattern:
                    import re
                    if not re.match(pattern, value):
                        errors.append(f"Field '{field_name}' format is invalid")
        
        elif field_type in ['number', 'integer', 'float']:
            if not isinstance(value, (int, float)):
                errors.append(f"Field '{field_name}' must be a number")
            else:
                min_value = field_config.get('min_value')
                max_value = field_config.get('max_value')
                
                if min_value is not None and value < min_value:
                    errors.append(f"Field '{field_name}' must be at least {min_value}")
                
                if max_value is not None and value > max_value:
                    errors.append(f"Field '{field_name}' must be at most {max_value}")
        
        elif field_type == 'enum':
            choices = field_config.get('choices', [])
            if value not in choices:
                errors.append(f"Field '{field_name}' must be one of: {', '.join(map(str, choices))}")
        
        return errors


# Convenience functions
def render_dynamic_form(schema: Dict[str, Any], current_data: Dict[str, Any]) -> Dict[str, Any]:
    """Render dynamic form."""
    return FormGenerator.render_dynamic_form(schema, current_data)