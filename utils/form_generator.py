"""
Dynamic form generator for JSON QA webapp.
Creates Streamlit forms based on schema definitions and Pydantic models.
"""

import copy
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
    def _sync_array_to_session(field_name: str, array_value: List[Any]) -> None:
        """
        Synchronize array value to session state and SessionManager form data.
        
        This helper ensures that array modifications are immediately reflected in both
        the session state and the SessionManager's form data, enabling proper diff
        calculation and state management.
        
        Args:
            field_name: Name of the array field
            array_value: Updated array value to synchronize
        """
        # Update session state with the field key
        field_key = f"field_{field_name}"
        array_copy = copy.deepcopy(array_value)
        st.session_state[field_key] = array_copy
        st.session_state[f"scalar_array_{field_name}_size"] = len(array_copy)
        
        # Update form data in SessionManager
        current_form_data = SessionManager.get_form_data()
        current_form_data[field_name] = array_copy
        SessionManager.set_form_data(current_form_data)
        
        logger.debug(f"[_sync_array_to_session] Synchronized {field_name}: {len(array_copy)} items")
    
    @staticmethod
    def _collect_array_data_from_widgets(schema: Dict[str, Any], form_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Collect array data from individual widget keys after form submission.
        
        Inside Streamlit forms, widget values are only available in session_state AFTER
        the form is submitted. This method reads the actual submitted values from individual
        array item widgets and updates the form_data accordingly.
        
        Args:
            schema: Schema definition
            form_data: Form data collected during rendering (may have stale array values)
            
        Returns:
            Updated form data with current array values from widgets
        """
        fields = schema.get('fields', {})
        
        for field_name, field_config in fields.items():
            field_type = field_config.get('type', 'string')
            
            if field_type == 'array':
                items_config = field_config.get('items', {})
                item_type = items_config.get('type', 'string')
                
                # For scalar arrays, collect from individual item widgets
                if item_type != 'object':
                    field_key = f"scalar_array_{field_name}"
                    field_storage_key = f"field_{field_name}"
                    size_key = f"{field_key}_size"
                    
                    # DEBUG: Log what we're looking for
                    logger.info(f"[DEBUG] Looking for array field: {field_name}")
                    logger.info(f"[DEBUG] Size key: {size_key}")
                    logger.info(f"[DEBUG] Size key in session_state: {size_key in st.session_state}")
                    
                    # Get the array size from session state
                    if size_key in st.session_state:
                        array_size = st.session_state[size_key]
                        logger.info(f"[DEBUG] Array size: {array_size}")
                        
                        collected_array: List[Any] = []
                        item_keys_found = False
                        
                        # Collect values from individual item widgets
                        for i in range(array_size):
                            item_key = f"{field_key}_item_{i}"
                            if item_key in st.session_state:
                                item_keys_found = True
                                value = st.session_state[item_key]
                                collected_array.append(value)
                                logger.info(f"[DEBUG] Collected item {i}: {value}")
                            else:
                                logger.warning(f"[DEBUG] Item key not found: {item_key}")

                        if not item_keys_found or len(collected_array) != array_size:
                            stored_value = st.session_state.get(field_storage_key)
                            if isinstance(stored_value, list):
                                collected_array = copy.deepcopy(stored_value)
                                logger.info(f"[DEBUG] Fallback collected array from field state: {collected_array}")
                            else:
                                stored_value = st.session_state.get(field_key)
                                if isinstance(stored_value, list):
                                    collected_array = copy.deepcopy(stored_value)
                                    logger.info(f"[DEBUG] Fallback collected array from legacy scalar key: {collected_array}")
                                else:
                                    collected_array = []
                                    logger.warning(f"[DEBUG] Unable to find scalar array items or field state for {field_name}")
                        
                        # DEBUG: Log before and after
                        logger.info(f"[DEBUG] Original form_data[{field_name}]: {form_data.get(field_name)}")
                        logger.info(f"[DEBUG] Collected array: {collected_array}")
                        
                        # Update form_data with collected array
                        form_data[field_name] = collected_array
                        
                        # Also sync to session state for consistency
                        FormGenerator._sync_array_to_session(field_name, collected_array)
                        
                        logger.info(f"[DEBUG] Updated form_data[{field_name}]: {form_data[field_name]}")
                    else:
                        logger.warning(f"[DEBUG] Size key not found in session_state: {size_key}")
                        logger.info(f"[DEBUG] Available keys: {[k for k in st.session_state.keys() if 'scalar_array' in str(k) or field_name in str(k)]}")
                
                # For object arrays, data_editor handles its own state
                # No additional collection needed
        
        return form_data
    
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
        st.subheader("Extracted Data")
        
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
                validate_submitted = st.form_submit_button("Validate Data")
            
            with col_buttons[1]:
                submit_submitted = st.form_submit_button("Submit Changes", type="primary")
            
            # Handle validation button
            if validate_submitted:
                # CRITICAL: Collect array data from individual item widgets AFTER form submission
                # Inside forms, widget values are only available in session_state after submission
                form_data = FormGenerator._collect_array_data_from_widgets(schema, form_data)
                
                # Always save the form data first
                SessionManager.set_form_data(form_data)
                
                # Validate using comprehensive submission validation
                validation_errors = SubmissionHandler._validate_submission_data(form_data, schema, model_class)
                
                if validation_errors:
                    SessionManager.set_validation_errors(validation_errors)
                    st.error("Please fix the following errors:")
                    for error in validation_errors:
                        st.error(f"  • {error}")
                else:
                    SessionManager.clear_validation_errors()
                    st.success("Data validated successfully")
                
                # Force rerun to update diff section with latest changes
                st.rerun()
                
                # Always return the form_data to preserve changes
                return form_data
            
            # Handle submit button
            if submit_submitted:
                # CRITICAL: Collect array data from individual item widgets AFTER form submission
                form_data = FormGenerator._collect_array_data_from_widgets(schema, form_data)
                
                # Save form data
                SessionManager.set_form_data(form_data)
                
                # Validate first
                validation_errors = SubmissionHandler._validate_submission_data(form_data, schema, model_class)
                
                if validation_errors:
                    SessionManager.set_validation_errors(validation_errors)
                    st.error("Validation failed. Please fix errors before submitting:")
                    for error in validation_errors:
                        st.error(f"  • {error}")
                    return form_data
                else:
                    SessionManager.clear_validation_errors()
                    st.success("Validation passed. Submitting changes...")
                
                # Proceed with submission
                filename = SessionManager.get_current_file()
                original_data = SessionManager.get_original_data()
                user = SessionManager.get_current_user()
                
                if filename is None or original_data is None or user is None:
                    st.error("Missing required information for submission")
                    return form_data
                
                success, errors = SubmissionHandler.validate_and_submit(
                    filename, form_data, original_data, schema, model_class, user
                )
                
                if success:
                    st.success("Changes submitted successfully!")
                    # Clear state and navigate
                    SessionManager._clear_file_state()
                    SessionManager.set_current_page('queue')
                    st.rerun()
                else:
                    st.error("Submission failed:")
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
                st.subheader(f"{group_name}")
            
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
        """
        Collect current form values from session state without rendering the UI.
        
        This method extracts all current widget values from session state, including
        proper handling of array fields (both scalar and object arrays) and edge cases
        like empty arrays and missing keys.
        
        Args:
            schema: Schema definition containing field configurations
            
        Returns:
            Dictionary of current form data with all field values
        """
        form_data = {}
        fields = schema.get('fields', {})
        
        for field_name, field_config in fields.items():
            field_type = field_config.get('type', 'string')
            field_key = f"field_{field_name}"
            
            # Handle array fields with proper extraction logic
            if field_type == 'array':
                items_config = field_config.get('items', {})
                item_type = items_config.get('type', 'string')
                
                # For object arrays, check data_editor key first
                if item_type == 'object':
                    data_editor_key = f"data_editor_{field_name}"
                    if data_editor_key in st.session_state:
                        value = st.session_state[data_editor_key]
                        # Handle pandas DataFrame from data_editor
                        if hasattr(value, 'to_dict'):
                            # Convert DataFrame to list of dicts
                            form_data[field_name] = value.to_dict('records')
                        elif isinstance(value, list):
                            form_data[field_name] = value
                        else:
                            # Fallback to empty array if value is unexpected type
                            form_data[field_name] = []
                        continue
                
                # For scalar arrays, use field_{field_name} key
                if field_key in st.session_state:
                    value = st.session_state[field_key]
                    # Handle empty arrays and None values
                    if value is None:
                        form_data[field_name] = []
                    elif isinstance(value, list):
                        form_data[field_name] = value
                    else:
                        # Single value - wrap in array
                        form_data[field_name] = [value]
                    continue
                
                # Fallback: check legacy array keys for backward compatibility
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
                        form_data[field_name] = []
                else:
                    # No array value found - use empty array
                    form_data[field_name] = []
            
            # Handle object fields
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
                        form_data[field_name] = {}
                elif field_key in st.session_state:
                    value = st.session_state[field_key]
                    form_data[field_name] = value if value is not None else {}
                else:
                    form_data[field_name] = {}
            
            # Handle regular scalar fields
            else:
                if field_key in st.session_state:
                    value = st.session_state[field_key]
                    if value is not None:
                        # Convert date/datetime objects to strings for JSON serialization
                        if field_type == 'date' and isinstance(value, date):
                            form_data[field_name] = value.strftime("%Y-%m-%d")
                        elif field_type == 'datetime' and isinstance(value, datetime):
                            form_data[field_name] = value.isoformat()
                        else:
                            form_data[field_name] = value
        
        logger.debug(f"[collect_current_form_data] Collected {len(form_data)} fields from session state")
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
            
            # Parse date/datetime values if they're strings
            if field_type == 'date' and hydrated_value is not None:
                if isinstance(hydrated_value, str):
                    try:
                        from dateutil import parser
                        hydrated_value = parser.parse(hydrated_value).date()
                    except Exception as e:
                        logger.warning(f"Failed to parse date string '{hydrated_value}': {e}")
                        hydrated_value = None
                elif isinstance(hydrated_value, datetime):
                    hydrated_value = hydrated_value.date()
            elif field_type == 'datetime' and hydrated_value is not None:
                if isinstance(hydrated_value, str):
                    try:
                        from dateutil import parser
                        hydrated_value = parser.parse(hydrated_value)
                    except Exception as e:
                        logger.warning(f"Failed to parse datetime string '{hydrated_value}': {e}")
                        hydrated_value = None
                elif isinstance(hydrated_value, date) and not isinstance(hydrated_value, datetime):
                    hydrated_value = datetime.combine(hydrated_value, datetime.min.time())
                
            # Handle session state
            if widget_key not in st.session_state:
                if isinstance(hydrated_value, list):
                    st.session_state[widget_key] = hydrated_value.copy()
                elif isinstance(hydrated_value, dict):
                    st.session_state[widget_key] = hydrated_value.copy()
                else:
                    st.session_state[widget_key] = hydrated_value
            
            session_value = st.session_state.get(widget_key)
            
            if field_type == 'date' and isinstance(session_value, str):
                try:
                    from dateutil import parser
                    session_value = parser.parse(session_value).date()
                    st.session_state[widget_key] = session_value
                except Exception as e:
                    logger.warning(f"Failed to normalize date string in session state for '{field_name}': {e}")
            elif field_type == 'datetime' and isinstance(session_value, str):
                try:
                    from dateutil import parser
                    session_value = parser.parse(session_value)
                    st.session_state[widget_key] = session_value
                except Exception as e:
                    logger.warning(f"Failed to normalize datetime string in session state for '{field_name}': {e}")
            
            widget_kwargs.pop('value', None)

            value_to_use = session_value
            
            logger.debug(f"[_render_field] Field: {field_name}, Widget Key: {widget_key}, Value to Use: {value_to_use}, Session State Value: {st.session_state.get(widget_key)}")
            
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
            elif field_type == 'date':
                widget_type = 'date_input'
            elif field_type == 'datetime':
                widget_type = 'datetime_input'
            elif field_type == 'enum':
                widget_type = 'selectbox'
            elif field_type == 'number':
                widget_type = 'number_input'
            elif field_type == 'boolean':
                widget_type = 'checkbox'
            elif field_type == 'array':
                widget_type = 'array_editor'
            elif field_type == 'object':
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
            elif widget_type == 'array_editor':
                return FormGenerator._render_array_editor(field_name, field_config, value_to_use or [])
            elif widget_type == 'data_editor':
                return FormGenerator._render_array_editor(field_name, field_config, value_to_use or [])
            elif widget_type == 'json_editor':
                return FormGenerator._render_object_editor(field_name, field_config, value_to_use or {})
            else:
                # Fallback to text input
                return st.text_input(**widget_kwargs)
        
        except Exception as e:
            st.error(f"Error rendering field {field_name}: {str(e)}")
            logger.error(f"Error rendering field {field_name}: {e}", exc_info=True)
            # Show detailed error in expander for debugging
            with st.expander("Error Details"):
                st.code(str(e))
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
                st.error(f"Value doesn't match required pattern: {field_config['pattern']}")
        
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
    def _render_date_input(field_name: str, field_config: Dict[str, Any], kwargs: Dict[str, Any]) -> Optional[str]:
        """Render date input field and return as string."""
        # Handle string to date conversion
        value = kwargs.get('value')
        if value is not None:
            if isinstance(value, str):
                try:
                    from dateutil import parser
                    value = parser.parse(value).date()
                except Exception as e:
                    logger.warning(f"Failed to parse date string '{value}': {e}")
                    value = None
            elif isinstance(value, datetime):
                value = value.date()
            elif not isinstance(value, date):
                logger.warning(f"Unexpected date value type: {type(value)}")
                value = None
        
        # Update kwargs with parsed value
        if value is not None:
            kwargs['value'] = value
        else:
            kwargs.pop('value', None)
        
        result = st.date_input(**kwargs)
        # Convert date object to string for JSON serialization and comparison
        if result is not None and isinstance(result, date):
            return result.strftime("%Y-%m-%d")
        return None
    
    @staticmethod
    def _render_datetime_input(field_name: str, field_config: Dict[str, Any], kwargs: Dict[str, Any]) -> str:
        """Render datetime input field and return as ISO format string."""
        # Streamlit doesn't have native datetime input, use date + time
        col1, col2 = st.columns(2)
        
        current_dt = kwargs.get('value')
        if isinstance(current_dt, str):
            try:
                from dateutil import parser
                current_dt = parser.parse(current_dt)
            except Exception as e:
                logger.warning(f"Failed to parse datetime string '{current_dt}': {e}")
                current_dt = datetime.now()
        elif isinstance(current_dt, date) and not isinstance(current_dt, datetime):
            # Convert date to datetime
            current_dt = datetime.combine(current_dt, datetime.min.time())
        elif not isinstance(current_dt, datetime):
            current_dt = datetime.now()
        
        with col1:
            date_part = st.date_input(
                f"{kwargs.get('label', field_name)} (Date)",
                value=current_dt.date(),
                key=f"{kwargs['key']}_date",
                disabled=kwargs.get('disabled', False)
            )
        
        with col2:
            time_part = st.time_input(
                f"{kwargs.get('label', field_name)} (Time)",
                value=current_dt.time(),
                key=f"{kwargs['key']}_time",
                disabled=kwargs.get('disabled', False)
            )
        
        # Convert datetime to ISO format string for JSON serialization and comparison
        combined_dt = datetime.combine(date_part, time_part)
        return combined_dt.isoformat()
    
    @staticmethod
    def _render_array_editor(field_name: str, field_config: Dict[str, Any], current_value: Any) -> List[Any]:
        """Enhanced array editor that delegates to specialized editors based on array type."""
        # Convert current value to list if needed
        if not current_value or not isinstance(current_value, list):
            current_value = []
        
        # Get item schema
        items_config = field_config.get('items', {})
        item_type = items_config.get('type', 'string')
        
        if item_type == 'object' and 'properties' in items_config:
            # Object array - use enhanced object array editor
            return FormGenerator._render_object_array_editor(field_name, field_config, current_value)
        else:
            # Scalar array - use enhanced scalar array editor
            return FormGenerator._render_scalar_array_editor(field_name, field_config, current_value)
    
    @staticmethod
    def _render_scalar_array_editor(field_name: str, field_config: Dict[str, Any], current_value: List[Any]) -> List[Any]:
        """
        Streamlined scalar array editor using Streamlit's data_editor for in-table editing.
        """
        import pandas as pd

        items_config = field_config.get("items", {})
        item_type = items_config.get("type", "string")

        current_list = list(current_value or [])

        display_values = [
            FormGenerator._prepare_scalar_value_for_editor(item_type, value, items_config)
            for value in current_list
        ]

        column_config = {
            "value": FormGenerator._build_scalar_column_config(field_name, field_config, item_type, items_config)
        }

        data_source = pd.DataFrame({"value": display_values})
        if data_source.empty:
            data_source = pd.DataFrame({"value": pd.Series(dtype="object")})

        st.caption(
            "Edit values directly in the table. Use the '+' icon to add rows and the row menu to delete entries."
        )

        edited_df = st.data_editor(
            data_source,
            column_config=column_config,
            num_rows="dynamic",
            use_container_width=True,
            hide_index=True,
            key=f"scalar_data_editor_{field_name}",
        )

        raw_values = edited_df["value"].tolist() if "value" in edited_df else []

        updated_values: List[Any] = []
        for raw_value in raw_values:
            try:
                if pd.isna(raw_value):
                    continue
            except Exception:
                pass
            updated_values.append(FormGenerator._coerce_scalar_value(item_type, raw_value, items_config))

        FormGenerator._sync_array_to_session(field_name, updated_values)

        validation_errors = FormGenerator._validate_scalar_array(field_name, updated_values, items_config)
        if validation_errors:
            for error in validation_errors:
                st.error(error)
        elif updated_values:
            st.success(f"{len(updated_values)} items valid")
        else:
            st.info("No items in this array yet.")

        return updated_values

    @staticmethod
    def _build_scalar_column_config(
        field_name: str,
        field_config: Dict[str, Any],
        item_type: str,
        items_config: Dict[str, Any],
    ) -> Any:
        """Create column configuration for scalar array editing based on schema metadata."""
        label = field_config.get("label", field_name)
        help_text = field_config.get("help", "")
        required = field_config.get("required", False)

        range_hint: List[str] = []
        min_value = items_config.get("min_value")
        max_value = items_config.get("max_value")
        if min_value is not None:
            range_hint.append(f">= {min_value}")
        if max_value is not None:
            range_hint.append(f"<= {max_value}")
        if range_hint:
            separator = " " if help_text else ""
            help_text = f"{help_text}{separator}(Allowed: {', '.join(range_hint)})"

        if item_type == "string":
            return st.column_config.TextColumn(
                label=label,
                help=help_text,
                required=required,
                max_chars=items_config.get("max_length"),
            )
        if item_type == "number":
            return st.column_config.NumberColumn(
                label=label,
                help=help_text,
                required=required,
                step=items_config.get("step", 0.01),
                format="%.2f",
            )
        if item_type == "integer":
            return st.column_config.NumberColumn(
                label=label,
                help=help_text,
                required=required,
                step=1,
                format="%d",
            )
        if item_type == "boolean":
            return st.column_config.CheckboxColumn(
                label=label,
                help=help_text,
                required=required,
            )
        if item_type == "date":
            return st.column_config.DateColumn(
                label=label,
                help=help_text,
                required=required,
            )
        if item_type == "enum":
            return st.column_config.SelectboxColumn(
                label=label,
                help=help_text,
                required=required,
                options=items_config.get("choices", []),
                default=items_config.get("default"),
            )
        return st.column_config.TextColumn(
            label=label,
            help=help_text,
            required=required,
        )

    @staticmethod
    def _prepare_scalar_value_for_editor(item_type: str, value: Any, items_config: Dict[str, Any]) -> Any:
        """Convert stored scalar array values into editor-friendly representations."""
        if value is None:
            return None

        if item_type == "string":
            return str(value)
        if item_type == "number":
            try:
                return float(value)
            except (TypeError, ValueError):
                logger.debug("Scalar editor: unable to coerce %r to float for display", value)
                return None
        if item_type == "integer":
            try:
                return int(value)
            except (TypeError, ValueError):
                logger.debug("Scalar editor: unable to coerce %r to int for display", value)
                return None
        if item_type == "boolean":
            if isinstance(value, bool):
                return value
            if isinstance(value, str):
                lowered = value.strip().lower()
                if lowered in {"true", "yes", "1"}:
                    return True
                if lowered in {"false", "no", "0"}:
                    return False
            return bool(value)
        if item_type == "date":
            if isinstance(value, datetime):
                return value.date()
            if isinstance(value, date):
                return value
            if isinstance(value, str):
                try:
                    return datetime.strptime(value, "%Y-%m-%d").date()
                except ValueError:
                    logger.debug("Scalar editor: unable to parse date string %r", value)
                    return None
            return None
        if item_type == "enum":
            choices = items_config.get("choices", [])
            return value if not choices or value in choices else items_config.get("default")
        return value

    @staticmethod
    def _coerce_scalar_value(item_type: str, raw_value: Any, items_config: Dict[str, Any]) -> Any:
        """Normalize editor outputs back into schema-compatible scalar values."""
        if raw_value is None:
            return None

        if item_type == "string":
            return str(raw_value)
        if item_type == "number":
            if isinstance(raw_value, (int, float)) and not isinstance(raw_value, bool):
                return float(raw_value)
            if isinstance(raw_value, str):
                stripped = raw_value.strip()
                if not stripped:
                    return ""
                try:
                    return float(stripped)
                except ValueError:
                    return raw_value
            return raw_value
        if item_type == "integer":
            if isinstance(raw_value, bool):
                return int(raw_value)
            if isinstance(raw_value, (int, float)):
                return int(raw_value)
            if isinstance(raw_value, str):
                stripped = raw_value.strip()
                if not stripped:
                    return ""
                try:
                    return int(stripped)
                except ValueError:
                    return raw_value
            return raw_value
        if item_type == "boolean":
            if isinstance(raw_value, bool):
                return raw_value
            if isinstance(raw_value, str):
                lowered = raw_value.strip().lower()
                if lowered in {"true", "yes", "1"}:
                    return True
                if lowered in {"false", "no", "0"}:
                    return False
            return bool(raw_value)
        if item_type == "date":
            if isinstance(raw_value, datetime):
                return raw_value.strftime("%Y-%m-%d")
            if isinstance(raw_value, date):
                return raw_value.strftime("%Y-%m-%d")
            if isinstance(raw_value, str):
                stripped = raw_value.strip()
                if not stripped:
                    return ""
                try:
                    parsed = datetime.strptime(stripped, "%Y-%m-%d")
                    return parsed.strftime("%Y-%m-%d")
                except ValueError:
                    return raw_value
            return str(raw_value)
        if item_type == "enum":
            choices = items_config.get("choices", [])
            if choices and raw_value not in choices:
                default_choice = items_config.get("default")
                return default_choice if default_choice in choices else choices[0]
            return raw_value
        return raw_value
    
    @staticmethod
    def _render_object_array_editor(field_name: str, field_config: Dict[str, Any], current_value: List[Any]) -> List[Any]:
        """
        Enhanced object array editor with manual row operations, NaN cleanup, and integer column config.
        Ported from sandbox with ASCII text labels for production compatibility.
        """
        import pandas as pd
        import numpy as np
        
        items_config = field_config.get("items", {})
        properties = items_config.get("properties", {})
        
        # Initialize array if empty
        if not current_value:
            current_value = []
        
        # Create a copy to work with
        working_array = current_value.copy()
        
        # Generate column configuration for st.data_editor
        column_config = FormGenerator._generate_column_config(properties)
        
        # Container for the object array editor
        with st.container():
            # Instructions for object array editing (ASCII text only)
            st.info("How to edit: Click cells to edit values directly in the table. Use 'Add Row' to add new items. Use the row deletion section below to remove rows.")
            
            col1, col2 = st.columns([3, 1])
            
            with col1:
                st.markdown(f"**{field_config.get('label', field_name)}**")
            
            with col2:
                # Add row button with field-specific key
                if st.button("Add Row", key=f"add_row_{field_name}"):
                    new_object = FormGenerator._create_default_object(properties)
                    working_array.append(new_object)
                    # Synchronize after adding row
                    FormGenerator._sync_array_to_session(field_name, working_array)
                    st.rerun()  # Force immediate rerun to show new row
            
            # Display the data editor if we have data
            if working_array:
                # Convert to DataFrame-like structure for st.data_editor
                df = pd.DataFrame(working_array)
                for column_name, prop_config in properties.items():
                    if prop_config.get("type") == "date" and column_name in df.columns:
                        df[column_name] = pd.to_datetime(df[column_name], errors="coerce")
                
                # Use st.data_editor for table editing with delete capability
                edited_df = st.data_editor(
                    df,
                    column_config=column_config,
                    num_rows="dynamic",
                    use_container_width=True,
                    key=f"data_editor_{field_name}",
                    hide_index=False  # Show index to help with row identification
                )
                
                # Convert back to list of dictionaries
                working_array = edited_df.to_dict('records')
                
                # Clean up any NaN values that pandas might introduce
                working_array = FormGenerator._clean_object_array(working_array, properties)
                
                # Synchronize after data_editor changes (cell edits)
                FormGenerator._sync_array_to_session(field_name, working_array)
                
                # Add manual row deletion interface
                if len(working_array) > 0:
                    st.markdown("#### Manual Row Operations")
                    col1, col2 = st.columns([2, 1])
                    
                    with col1:
                        row_to_delete = st.selectbox(
                            "Select row to delete:",
                            options=list(range(len(working_array))),
                            format_func=lambda x: f"Row {x}: {working_array[x].get(list(working_array[x].keys())[0], 'N/A') if working_array[x] else 'Empty'}",
                            key=f"delete_row_select_{field_name}"
                        )
                    
                    with col2:
                        if st.button("Delete Selected Row", key=f"delete_row_{field_name}"):
                            if 0 <= row_to_delete < len(working_array):
                                working_array.pop(row_to_delete)
                                # Synchronize after deleting row
                                FormGenerator._sync_array_to_session(field_name, working_array)
                                st.success(f"Deleted row {row_to_delete}")
                                st.rerun()
            else:
                st.info("No items in array. Click 'Add Row' to add the first item.")
            
            # Validation feedback
            validation_errors = FormGenerator._validate_object_array(field_name, working_array, items_config)
            if validation_errors:
                for error in validation_errors:
                    st.error(error)
            else:
                if working_array:  # Only show success if array is not empty
                    st.success(f"{len(working_array)} objects valid")
        
        # Ensure final synchronization to session state and SessionManager
        FormGenerator._sync_array_to_session(field_name, working_array)
        
        return working_array
    
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
                st.error("Invalid JSON format")
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
    
    @staticmethod
    def _get_default_value_for_type(item_type: str, items_config: Dict[str, Any]) -> Any:
        """Get appropriate default value for array item type, respecting constraints."""
        if item_type == "string":
            return ""
        elif item_type == "number":
            min_val = items_config.get("min_value")
            if min_val is not None:
                return max(0.0, float(min_val)) if min_val >= 0 else float(min_val)
            return 0.0
        elif item_type == "integer":
            min_val = items_config.get("min_value")
            if min_val is not None:
                return max(0, int(min_val)) if min_val >= 0 else int(min_val)
            return 0
        elif item_type == "boolean":
            return items_config.get("default", False)
        elif item_type == "date":
            return datetime.now().strftime("%Y-%m-%d")
        elif item_type == "enum":
            choices = items_config.get("choices", [])
            return items_config.get("default", choices[0] if choices else "")
        else:
            return ""
    
    @staticmethod
    def _render_scalar_input(field_name: str, item_type: str, current_value: Any, items_config: Dict[str, Any], key: str) -> Any:
        """Render appropriate input widget for scalar array item with enum support."""
        
        if item_type == "string":
            value = st.text_input(
                f"Item {key.split('_')[-1]}",
                value=str(current_value) if current_value is not None else "",
                key=key,
                help=f"String value for {field_name}"
            )
            return value
        
        elif item_type == "number":
            min_val = items_config.get("min_value", None)
            max_val = items_config.get("max_value", None)
            step = items_config.get("step", 0.01)
            
            # Ensure all numeric types are consistent (float)
            min_val = float(min_val) if min_val is not None else None
            max_val = float(max_val) if max_val is not None else None
            step = float(step)
            
            value = st.number_input(
                f"Item {key.split('_')[-1]}",
                value=float(current_value) if current_value is not None else 0.0,
                min_value=min_val,
                max_value=max_val,
                step=step,
                format="%.2f",
                key=key,
                help=f"Number value for {field_name}"
            )
            return round(value, 2)
        
        elif item_type == "integer":
            min_val = items_config.get("min_value", None)
            max_val = items_config.get("max_value", None)
            step = items_config.get("step", 1)
            
            # Ensure all numeric types are consistent (int)
            min_val = int(min_val) if min_val is not None else None
            max_val = int(max_val) if max_val is not None else None
            step = int(step)
            
            value = st.number_input(
                f"Item {key.split('_')[-1]}",
                value=int(current_value) if current_value is not None else 0,
                min_value=min_val,
                max_value=max_val,
                step=step,
                format="%d",
                key=key,
                help=f"Integer value for {field_name}"
            )
            return int(value)
        
        elif item_type == "boolean":
            value = st.checkbox(
                f"Item {key.split('_')[-1]}",
                value=bool(current_value) if current_value is not None else False,
                key=key,
                help=f"Boolean value for {field_name}"
            )
            return value
        
        elif item_type == "date":
            try:
                if isinstance(current_value, str):
                    from dateutil import parser
                    current_date = parser.parse(current_value).date()
                elif isinstance(current_value, datetime):
                    current_date = current_value.date()
                elif isinstance(current_value, date):
                    current_date = current_value
                else:
                    current_date = datetime.now().date()
            except (ValueError, TypeError) as e:
                logger.warning(f"Failed to parse date value '{current_value}': {e}")
                current_date = datetime.now().date()
            
            value = st.date_input(
                f"Item {key.split('_')[-1]}",
                value=current_date,
                key=key,
                help=f"Date value for {field_name}"
            )
            # Ensure value is a date object before calling strftime
            if isinstance(value, date):
                return value.strftime("%Y-%m-%d")
            else:
                logger.warning(f"date_input returned non-date value: {type(value)}")
                return str(value) if value is not None else ""
        
        elif item_type == "enum":
            choices = items_config.get("choices", [])
            if not choices:
                # Fallback to text input if no choices defined
                return st.text_input(
                    f"Item {key.split('_')[-1]}",
                    value=str(current_value) if current_value is not None else "",
                    key=key,
                    help=f"Enum value for {field_name}"
                )
            
            # Find current index
            try:
                current_index = choices.index(current_value) if current_value in choices else 0
            except (ValueError, TypeError):
                current_index = 0
            
            value = st.selectbox(
                f"Item {key.split('_')[-1]}",
                choices,
                index=current_index,
                key=key,
                help=f"Select value for {field_name}"
            )
            return value
        
        else:
            # Fallback to text input
            value = st.text_input(
                f"Item {key.split('_')[-1]}",
                value=str(current_value) if current_value is not None else "",
                key=key,
                help=f"Value for {field_name}"
            )
            return value
    
    @staticmethod
    def _validate_scalar_array(field_name: str, array_value: List[Any], items_config: Dict[str, Any]) -> List[str]:
        """Validate array of scalar values with detailed error reporting."""
        errors = []
        
        if not isinstance(array_value, list):
            errors.append(f"{field_name} must be an array")
            return errors
        
        item_type = items_config.get("type", "string")
        
        for i, item_value in enumerate(array_value):
            item_errors = FormGenerator._validate_scalar_item(f"{field_name}[{i}]", item_value, item_type, items_config)
            errors.extend(item_errors)
        
        return errors
    
    @staticmethod
    def _validate_scalar_item(field_path: str, value: Any, item_type: str, items_config: Dict[str, Any]) -> List[str]:
        """Validate a single scalar array item with contextual error messages."""
        errors = []
        
        # Type validation
        if item_type == "string":
            if not isinstance(value, str):
                errors.append(f"{field_path} must be a string")
                return errors
            
            # Length constraints
            min_length = items_config.get("min_length")
            if min_length is not None and len(value) < min_length:
                errors.append(f"{field_path} must be at least {min_length} characters")
            
            max_length = items_config.get("max_length")
            if max_length is not None and len(value) > max_length:
                errors.append(f"{field_path} must be no more than {max_length} characters")
            
            # Pattern validation
            pattern = items_config.get("pattern")
            if pattern:
                import re
                try:
                    if not re.match(pattern, value):
                        errors.append(f"{field_path} must match pattern: {pattern}")
                except re.error:
                    errors.append(f"{field_path} has invalid pattern: {pattern}")
        
        elif item_type == "number":
            try:
                num_value = float(value)
            except (ValueError, TypeError):
                errors.append(f"{field_path} must be a valid number")
                return errors
            
            min_value = items_config.get("min_value")
            if min_value is not None and num_value < min_value:
                errors.append(f"{field_path} must be at least {min_value}")
            
            max_value = items_config.get("max_value")
            if max_value is not None and num_value > max_value:
                errors.append(f"{field_path} must be no more than {max_value}")
        
        elif item_type == "integer":
            try:
                int_value = int(value)
            except (ValueError, TypeError):
                errors.append(f"{field_path} must be a valid integer")
                return errors
            
            min_value = items_config.get("min_value")
            if min_value is not None and int_value < min_value:
                errors.append(f"{field_path} must be at least {min_value}")
            
            max_value = items_config.get("max_value")
            if max_value is not None and int_value > max_value:
                errors.append(f"{field_path} must be no more than {max_value}")
        
        elif item_type == "boolean":
            if not isinstance(value, bool):
                errors.append(f"{field_path} must be a boolean")
        
        elif item_type == "date":
            if isinstance(value, str):
                try:
                    datetime.strptime(value, "%Y-%m-%d")
                except ValueError:
                    errors.append(f"{field_path} must be a valid date in YYYY-MM-DD format")
            elif not isinstance(value, date):
                errors.append(f"{field_path} must be a valid date")
        
        elif item_type == "enum":
            choices = items_config.get("choices", [])
            if choices and value not in choices:
                errors.append(f"{field_path} must be one of: {', '.join(map(str, choices))}")
        
        return errors
    
    @staticmethod
    def _generate_column_config(properties: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        """Generate column configuration for st.data_editor based on object properties"""
        column_config = {}
        
        for prop_name, prop_config in properties.items():
            prop_type = prop_config.get("type", "string")
            label = prop_config.get("label", prop_name)
            help_text = prop_config.get("help", "")
            required = prop_config.get("required", False)
            
            if prop_type == "string":
                column_config[prop_name] = st.column_config.TextColumn(
                    label=label,
                    help=help_text,
                    required=required,
                    max_chars=prop_config.get("max_length", None)
                )
            elif prop_type == "number":
                column_config[prop_name] = st.column_config.NumberColumn(
                    label=label,
                    help=help_text,
                    required=required,
                    min_value=prop_config.get("min_value", None),
                    max_value=prop_config.get("max_value", None),
                    step=prop_config.get("step", 0.01),
                    format="%.2f"
                )
            elif prop_type == "integer":
                column_config[prop_name] = st.column_config.NumberColumn(
                    label=label,
                    help=help_text,
                    required=required,
                    min_value=prop_config.get("min_value", None),
                    max_value=prop_config.get("max_value", None),
                    step=prop_config.get("step", 1),
                    format="%d"
                )
            elif prop_type == "boolean":
                column_config[prop_name] = st.column_config.CheckboxColumn(
                    label=label,
                    help=help_text,
                    required=required
                )
            elif prop_type == "date":
                column_config[prop_name] = st.column_config.DateColumn(
                    label=label,
                    help=help_text,
                    required=required
                )
            elif prop_type == "enum":
                column_config[prop_name] = st.column_config.SelectboxColumn(
                    label=label,
                    help=help_text,
                    required=required,
                    options=prop_config.get("choices", []),
                    default=prop_config.get("default")
                )
            else:
                # Default to text column
                column_config[prop_name] = st.column_config.TextColumn(
                    label=label,
                    help=help_text,
                    required=required
                )
        
        return column_config
    
    @staticmethod
    def _create_default_object(properties: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        """Create a default object with appropriate default values for each property"""
        default_object = {}
        
        for prop_name, prop_config in properties.items():
            prop_type = prop_config.get("type", "string")
            default_object[prop_name] = FormGenerator._get_default_value_for_type(prop_type, prop_config)
        
        return default_object
    
    @staticmethod
    def _clean_object_array(
        array: List[Dict],
        properties: Optional[Dict[str, Dict[str, Any]]] = None
    ) -> List[Dict]:
        """Clean object array by removing NaN values and normalising types using schema hints."""
        import pandas as pd
        import numpy as np
        
        cleaned_array = []
        properties = properties or {}
        for obj in array:
            cleaned_obj = {}
            for key, value in obj.items():
                prop_config = properties.get(key, {})
                prop_type = prop_config.get("type")
                
                # Handle pandas NaN values
                if pd.isna(value):
                    cleaned_obj[key] = None
                else:
                    normalised_value = value

                    if isinstance(value, np.bool_):
                        normalised_value = bool(value)
                    elif isinstance(value, np.integer):
                        normalised_value = int(value)
                    elif isinstance(value, np.floating):
                        normalised_value = float(value)

                    if prop_type == "number" and normalised_value is not None:
                        try:
                            normalised_value = float(normalised_value)
                        except (TypeError, ValueError):
                            pass
                    elif prop_type == "integer" and normalised_value is not None:
                        try:
                            normalised_value = int(normalised_value)
                        except (TypeError, ValueError):
                            pass
                    elif prop_type == "boolean" and normalised_value is not None:
                        normalised_value = bool(normalised_value)

                    cleaned_obj[key] = normalised_value

            # Ensure all schema-defined properties are present so validation can report omissions
            for prop_name in properties.keys():
                cleaned_obj.setdefault(prop_name, None)
            cleaned_array.append(cleaned_obj)
        
        return cleaned_array
    
    @staticmethod
    def _validate_object_array(field_name: str, array_value: List[Dict], items_config: Dict[str, Any]) -> List[str]:
        """Validate object array according to schema constraints"""
        errors = []
        properties = items_config.get("properties", {})
        
        for i, obj in enumerate(array_value):
            obj_errors = FormGenerator._validate_object_item(f"{field_name}[{i}]", obj, properties)
            errors.extend(obj_errors)
        
        return errors
    
    @staticmethod
    def _validate_object_item(item_path: str, obj: Dict[str, Any], properties: Dict[str, Dict[str, Any]]) -> List[str]:
        """Validate individual object in array"""
        errors = []
        
        # Check required properties
        for prop_name, prop_config in properties.items():
            required = prop_config.get("required", False)
            prop_type = prop_config.get("type", "string")
            
            if required and (prop_name not in obj or obj[prop_name] is None or obj[prop_name] == ""):
                errors.append(f"{item_path}.{prop_name}: is required")
                continue
            
            # Skip validation if property is not present or is None/empty (for optional fields)
            if prop_name not in obj or obj[prop_name] is None:
                continue
            
            value = obj[prop_name]
            
            # Validate property value
            prop_errors = FormGenerator._validate_scalar_item(f"{item_path}.{prop_name}", value, prop_type, prop_config)
            errors.extend(prop_errors)
        
        return errors


# Convenience functions
def render_dynamic_form(schema: Dict[str, Any], current_data: Dict[str, Any]) -> Dict[str, Any]:
    """Render dynamic form."""
    return FormGenerator.render_dynamic_form(schema, current_data)
