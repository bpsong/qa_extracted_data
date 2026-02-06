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
        # Get form version for versioned keys
        form_version = st.session_state.get('form_version', 0)
        
        # Update session state with the versioned field key
        field_key = f"field_{field_name}_v{form_version}"
        array_copy = copy.deepcopy(array_value)
        st.session_state[field_key] = array_copy
        st.session_state[f"scalar_array_{field_name}_size_v{form_version}"] = len(array_copy)
        
        # Update form data in SessionManager
        current_form_data = SessionManager.get_form_data()
        current_form_data[field_name] = array_copy
        SessionManager.set_form_data(current_form_data)
        
        logger.info(
            "[SYNC DEBUG] %s -> Synced %d items to field_%s",
            field_name,
            len(array_copy),
            field_name,
        )
        if array_copy:
            logger.info("[SYNC DEBUG] First item: %s", array_copy[0])
        
        logger.debug(
            "[_sync_array_to_session] %s -> %d items; sample=%s",
            field_name,
            len(array_copy),
            array_copy[:2] if array_copy else [],
        )
    
    @staticmethod
    def _extract_data_editor_records(
        editor_state: Any,
        fallback_rows: Optional[List[Dict[str, Any]]] = None,
        editor_key: Optional[str] = None
    ) -> Optional[List[Dict[str, Any]]]:
        """
        Normalize Streamlit data_editor outputs into a list of dictionaries.
        
        Handles:
        - pandas.DataFrame values returned directly by st.data_editor
        - Streamlit DataEditorState objects (use `.value`)
        - Dictionaries with a 'data' payload containing a DataFrame
        - Pre-existing list[dict] structures
        """
        if editor_state is None:
            return []

        logger.debug(
            "[_extract_data_editor_records] Inspecting payload type=%s",
            type(editor_state),
        )

        # Streamlit >=1.50 returns a DataEditorState with a `.value` attribute.
        if hasattr(editor_state, "value"):
            try:
                editor_state = editor_state.value
            except Exception:
                logger.debug("[_extract_data_editor_records] Failed to access DataEditorState.value", exc_info=True)

        if hasattr(editor_state, "to_dict"):
            try:
                records = editor_state.to_dict("records")
            except Exception:
                logger.debug("[_extract_data_editor_records] Failed to convert editor DataFrame to records", exc_info=True)
                records = []
            return FormGenerator._apply_editor_session_diffs(records, editor_key, fallback_rows)

        if isinstance(editor_state, dict):
            logger.debug(
                "[_extract_data_editor_records] Dict payload keys=%s edited_rows=%s added_rows=%s deleted_rows=%s",
                list(editor_state.keys()),
                editor_state.get("edited_rows"),
                editor_state.get("added_rows"),
                editor_state.get("deleted_rows"),
            )
            records: List[Dict[str, Any]] = []

            data_frame = editor_state.get("data")
            if data_frame is not None and hasattr(data_frame, "to_dict"):
                try:
                    records = data_frame.to_dict("records")
                except Exception:
                    logger.debug("[_extract_data_editor_records] Failed to convert editor['data'] to records", exc_info=True)
            elif isinstance(data_frame, list):
                records = copy.deepcopy(data_frame)
            elif isinstance(fallback_rows, list):
                records = copy.deepcopy(fallback_rows)

            records = FormGenerator._apply_editor_dict_diffs(
                records,
                editor_state.get("edited_rows") or {},
                editor_state.get("added_rows") or [],
                editor_state.get("deleted_rows") or []
            )

            return FormGenerator._apply_editor_session_diffs(records, editor_key, fallback_rows)

        if isinstance(editor_state, list):
            return FormGenerator._apply_editor_session_diffs(editor_state, editor_key, fallback_rows)

        logger.debug("[_extract_data_editor_records] Unsupported editor payload type: %s", type(editor_state))
        return None
    
    @staticmethod
    def _display_data_editor_debug(field_name: str, editor_state: Any) -> None:
        """Render session state details for the Streamlit data editor when debugging is enabled."""
        if not st.session_state.get("show_array_debug"):
            return

        try:
            container = st.sidebar.expander(f"Array Debug · {field_name}", expanded=True)
        except Exception:
            return

        with container:
            container.markdown(f"**State Type:** `{type(editor_state).__name__}`")
            container.markdown(f"**State Repr:** `{editor_state}`")

            related_keys = {
                key: st.session_state.get(key)
                for key in st.session_state.keys()
                if isinstance(key, str) and key.startswith(f"data_editor_{field_name}")
            }
            container.markdown("**Related session_state keys:**")

            def _safe_value(value: Any) -> Any:
                if hasattr(value, "to_dict"):
                    try:
                        return value.to_dict()
                    except Exception:
                        return repr(value)
                if isinstance(value, (list, dict, str, int, float, bool)) or value is None:
                    return value
                return repr(value)

            safe_related = {key: _safe_value(val) for key, val in related_keys.items()}
            container.json(safe_related)

    @staticmethod
    def _apply_editor_dict_diffs(
        records: List[Dict[str, Any]],
        edited_rows: Dict[str, Dict[str, Any]],
        added_rows: List[Dict[str, Any]],
        deleted_rows: List[Any],
    ) -> List[Dict[str, Any]]:
        """Apply diff dictionaries provided by Streamlit data_editor state."""
        working = copy.deepcopy(records)

        for row_key, updates in (edited_rows or {}).items():
            try:
                idx = int(row_key)
            except (TypeError, ValueError):
                logger.debug("[_apply_editor_dict_diffs] Non-numeric row key %s", row_key)
                continue

            while idx >= len(working):
                working.append({})
            working[idx].update(updates or {})

        for row in added_rows or []:
            working.append(dict(row))

        for row_key in sorted(
            deleted_rows or [],
            key=lambda x: int(x) if isinstance(x, (int, str)) and str(x).isdigit() else -1,
            reverse=True,
        ):
            try:
                idx = int(row_key)
            except (TypeError, ValueError):
                logger.debug("[_apply_editor_dict_diffs] Non-numeric delete key %s", row_key)
                continue
            if 0 <= idx < len(working):
                working.pop(idx)

        return working

    @staticmethod
    def _apply_editor_session_diffs(
        records: Optional[List[Dict[str, Any]]],
        editor_key: Optional[str],
        fallback_rows: Optional[List[Dict[str, Any]]] = None
    ) -> List[Dict[str, Any]]:
        """Merge Streamlit's __edited_rows/__added_rows/__deleted_rows session keys into records."""
        base = copy.deepcopy(records) if records is not None else []
        if not base and isinstance(fallback_rows, list):
            base = copy.deepcopy(fallback_rows)

        if not editor_key:
            return base

        edited_rows = st.session_state.get(f"{editor_key}__edited_rows") or {}
        added_rows = st.session_state.get(f"{editor_key}__added_rows") or []
        deleted_rows = st.session_state.get(f"{editor_key}__deleted_rows") or []

        logger.debug(
            "[_apply_editor_session_diffs] editor=%s edited=%s added=%s deleted=%s",
            editor_key,
            edited_rows,
            added_rows,
            deleted_rows,
        )

        return FormGenerator._apply_editor_dict_diffs(base, edited_rows, added_rows, deleted_rows)
    
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
        
        logger.info("[DEBUG _collect_array_data_from_widgets] === COLLECTING ARRAY DATA ===")
        
        for field_name, field_config in fields.items():
            field_type = field_config.get('type', 'string')
            
            if field_type == 'array':
                items_config = field_config.get('items', {})
                item_type = items_config.get('type', 'string')
                properties = items_config.get('properties', {})

                logger.info(f"[DEBUG _collect_array_data_from_widgets] Processing array field: {field_name}, item_type: {item_type}")

                if item_type == 'object':
                    # CRITICAL FIX: Prioritize field_{field_name} which is synced during rendering
                    field_key = f"field_{field_name}"
                    if field_key in st.session_state and isinstance(st.session_state[field_key], list):
                        value = st.session_state[field_key]
                        cleaned_records = FormGenerator._clean_object_array(value, properties)
                        logger.info(f"[DEBUG _collect_array_data_from_widgets] Using field_{field_name} (synced): {len(cleaned_records)} rows")
                        if cleaned_records:
                            logger.info(f"[DEBUG _collect_array_data_from_widgets] First record from field_{field_name}: {cleaned_records[0]}")
                        form_data[field_name] = cleaned_records
                        FormGenerator._sync_array_to_session(field_name, cleaned_records)
                        continue
                    
                    # Fallback to data_editor key
                    data_editor_key = f"data_editor_{field_name}"
                    logger.info(f"[DEBUG _collect_array_data_from_widgets] field_{field_name} not found, trying data_editor key: {data_editor_key}")
                    logger.info(f"[DEBUG _collect_array_data_from_widgets] Key exists in session_state: {data_editor_key in st.session_state}")
                    
                    if data_editor_key in st.session_state:
                        editor_state = st.session_state.get(data_editor_key)
                        logger.info(f"[DEBUG _collect_array_data_from_widgets] Editor state type: {type(editor_state)}")
                        logger.debug(
                            "[_collect_array_data_from_widgets] raw editor state for %s: type=%s repr=%r attrs=%s",
                            field_name,
                            type(editor_state),
                            editor_state,
                            [attr for attr in dir(editor_state) if not attr.startswith('_')],
                        )
                        FormGenerator._display_data_editor_debug(field_name, editor_state)
                        records = FormGenerator._extract_data_editor_records(
                            editor_state,
                            fallback_rows=form_data.get(field_name) if isinstance(form_data.get(field_name), list) else None,
                            editor_key=data_editor_key,
                        )
                        logger.info(f"[DEBUG _collect_array_data_from_widgets] Extracted records: {records is not None}, count: {len(records) if records else 0}")
                        if records is not None:
                            cleaned_records = FormGenerator._clean_object_array(records, properties)
                            logger.info(f"[DEBUG _collect_array_data_from_widgets] Cleaned records count: {len(cleaned_records)}")
                            if cleaned_records:
                                logger.info(f"[DEBUG _collect_array_data_from_widgets] First cleaned record: {cleaned_records[0]}")
                            logger.debug(
                                "[_collect_array_data_from_widgets] Collected %s rows for %s (validate)",
                                len(cleaned_records),
                                field_name,
                            )
                            form_data[field_name] = cleaned_records
                            FormGenerator._sync_array_to_session(field_name, cleaned_records)
                            continue
                
                # For scalar arrays, collect from individual item widgets
                if item_type != 'object':
                    form_version = st.session_state.get('form_version', 0)
                    array_state_key = f"array_{field_name}_v{form_version}"
                    legacy_array_state_key = f"scalar_array_{field_name}"
                    versioned_field_key = f"field_{field_name}_v{form_version}"
                    legacy_field_key = f"field_{field_name}"
                    size_keys = [
                        f"scalar_array_{field_name}_size_v{form_version}",
                        f"scalar_array_{field_name}_size"
                    ]
                    
                    logger.info(f"[DEBUG] Looking for array field: {field_name}")
                    logger.info(f"[DEBUG] Array state key: {array_state_key} present: {array_state_key in st.session_state}")
                    
                    collected_array: List[Any] = []
                    
                    if array_state_key in st.session_state and isinstance(st.session_state[array_state_key], list):
                        collected_array = [
                            FormGenerator._coerce_scalar_value(item_type, value, items_config)
                            for value in st.session_state[array_state_key]
                        ]
                        logger.info(f"[DEBUG] Collected {len(collected_array)} items from {array_state_key}")
                    elif versioned_field_key in st.session_state and isinstance(st.session_state[versioned_field_key], list):
                        collected_array = [
                            FormGenerator._coerce_scalar_value(item_type, value, items_config)
                            for value in st.session_state[versioned_field_key]
                        ]
                        logger.info(f"[DEBUG] Collected {len(collected_array)} items from {versioned_field_key}")
                    elif legacy_field_key in st.session_state and isinstance(st.session_state[legacy_field_key], list):
                        collected_array = [
                            FormGenerator._coerce_scalar_value(item_type, value, items_config)
                            for value in st.session_state[legacy_field_key]
                        ]
                        logger.info(f"[DEBUG] Collected {len(collected_array)} items from legacy {legacy_field_key}")
                    elif legacy_array_state_key in st.session_state and isinstance(st.session_state[legacy_array_state_key], list):
                        collected_array = [
                            FormGenerator._coerce_scalar_value(item_type, value, items_config)
                            for value in st.session_state[legacy_array_state_key]
                        ]
                        logger.info(f"[DEBUG] Collected {len(collected_array)} items from legacy {legacy_array_state_key}")
                    else:
                        size_hint = None
                        for size_key in size_keys:
                            if size_key in st.session_state:
                                size_hint = st.session_state[size_key]
                                break
                        if size_hint is None and array_state_key in st.session_state and isinstance(st.session_state[array_state_key], list):
                            size_hint = len(st.session_state[array_state_key])
                        logger.info(f"[DEBUG] Size hint for {field_name}: {size_hint}")
                        
                        if size_hint is not None:
                            collected_candidates: List[Any] = []
                            key_prefixes = [
                                f"{array_state_key}_item_",
                                f"{legacy_array_state_key}_item_"
                            ]
                            for i in range(int(size_hint)):
                                value_found = False
                                for prefix in key_prefixes:
                                    widget_key = f"{prefix}{i}"
                                    if widget_key in st.session_state:
                                        collected_candidates.append(
                                            FormGenerator._coerce_scalar_value(
                                                item_type,
                                                st.session_state[widget_key],
                                                items_config
                                            )
                                        )
                                        value_found = True
                                        break
                                if not value_found:
                                    logger.debug(f"[DEBUG] Item key not found for {field_name} at index {i} with prefixes {key_prefixes}")
                                    break
                            if collected_candidates:
                                collected_array = collected_candidates
                                logger.info(f"[DEBUG] Collected {len(collected_array)} items from widget prefixes for {field_name}")
                        else:
                            logger.warning(f"[DEBUG] No size hint available for {field_name}; session_state keys: {[k for k in st.session_state.keys() if field_name in str(k)]}")
                    
                    logger.info(f"[DEBUG] Final collected array for {field_name}: {collected_array}")
                    form_data[field_name] = collected_array
                    
                    # Also sync to session state for consistency
                    FormGenerator._sync_array_to_session(field_name, collected_array)
                    
                    logger.info(f"[DEBUG] Updated form_data[{field_name}]: {form_data[field_name]}")
                
                # For object arrays, data_editor handles its own state
                # No additional collection needed
        
        return form_data
    
    @staticmethod
    def render_dynamic_form(schema: Dict[str, Any], current_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Render a dynamic form based on schema and return form data.
        
        CRITICAL: data_editor widgets are rendered OUTSIDE the form to capture edits.
        Only buttons are inside the form.
        
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
        
        # Render fields OUTSIDE form (so data_editor can capture changes)
        fields = schema['fields']
        form_data = FormGenerator._render_form_fields(fields, current_data)
        
        # Create form with ONLY buttons
        with st.form("json_edit_form", clear_on_submit=False):
            
            # Get model class for validation
            model_class = SessionManager.get_model_class()
            
            # Form submission buttons (ONLY buttons in form)
            st.markdown("---")
            col_buttons = st.columns(2)
            
            with col_buttons[0]:
                validate_submitted = st.form_submit_button("🔍 Validate Data", use_container_width=True)
            
            with col_buttons[1]:
                submit_submitted = st.form_submit_button("✅ Submit Changes", type="primary", use_container_width=True)
            
            # Handle validation button
            if validate_submitted:
                # DEBUG: Check what's in data_editor session state AFTER form submission
                for key in st.session_state.keys():
                    if 'data_editor' in str(key) or 'Items' in str(key):
                        value = st.session_state[key]
                        logger.info(f"[DEBUG VALIDATE] {key}: type={type(value)}, value={value if not isinstance(value, (list, dict)) or len(str(value)) < 200 else f'{type(value)} with {len(value)} items'}")
                
                # SIMPLIFIED: Collect ALL form data from widgets
                from utils.form_data_collector import collect_all_form_data
                form_data = collect_all_form_data(schema)
                
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
                # SIMPLIFIED: Collect ALL form data from widgets
                from utils.form_data_collector import collect_all_form_data
                form_data = collect_all_form_data(schema)
                
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
                is_object_array = (
                    field_config.get("type") == "array"
                    and isinstance(field_config.get("items"), dict)
                    and field_config.get("items", {}).get("type") == "object"
                )

                if is_object_array:
                    with st.container():
                        field_value = FormGenerator._render_field(
                            field_name,
                            field_config,
                            current_data.get(field_name)
                        )
                        form_data[field_name] = field_value

                    # restart the two-column flow after the full-width field
                    cols = st.columns(2)
                    col_index = 0
                    continue

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
        Collect current form values from ALL widgets in session state.
        
        SIMPLIFIED APPROACH:
        - For ALL fields: Read from field_{field_name} in session_state
        - This key is set by widgets during rendering and synced by _sync_array_to_session
        - No complex extraction logic needed - just read the values directly
        
        Args:
            schema: Schema definition containing field configurations
            
        Returns:
            Dictionary of current form data with all field values
        """
        form_data = {}
        fields = schema.get('fields', {})
        
        logger.info("[DEBUG collect_current_form_data] === COLLECTING FORM DATA (SIMPLIFIED) ===")
        
        for field_name, field_config in fields.items():
            field_type = field_config.get('type', 'string')
            field_key = f"field_{field_name}"
            
            # Handle array fields with proper extraction logic
            if field_type == 'array':
                items_config = field_config.get('items', {})
                item_type = items_config.get('type', 'string')
                properties = items_config.get("properties", {})

                logger.info(f"[DEBUG collect_current_form_data] Processing array field: {field_name}, item_type: {item_type}")

                # CRITICAL FIX: For object arrays, prioritize field_{field_name} which is synced during rendering
                # The data_editor session state dict has empty edited_rows when read outside rendering context
                if item_type == 'object':
                    # First try field_{field_name} which gets synced by _sync_array_to_session during rendering
                    if field_key in st.session_state and isinstance(st.session_state[field_key], list):
                        value = st.session_state[field_key]
                        cleaned = FormGenerator._clean_object_array(value, properties)
                        logger.info(
                            f"[DEBUG collect_current_form_data] Using field_{field_name} (synced during render): {len(cleaned)} rows"
                        )
                        if cleaned:
                            logger.info(f"[DEBUG collect_current_form_data] First item from field_{field_name}: {cleaned[0]}")
                        form_data[field_name] = cleaned
                        continue
                    
                    # Fallback to data_editor key (legacy path)
                    data_editor_key = f"data_editor_{field_name}"
                    logger.info(f"[DEBUG collect_current_form_data] field_{field_name} not found, trying data_editor key: {data_editor_key}")
                    logger.info(f"[DEBUG collect_current_form_data] Key exists: {data_editor_key in st.session_state}")
                    
                    # DEBUG: Check for the actual DataFrame value that data_editor returns
                    logger.info(f"[DEBUG collect_current_form_data] All session keys with '{field_name}': {[k for k in st.session_state.keys() if field_name in str(k)]}")
                    
                    if data_editor_key in st.session_state:
                        editor_state = st.session_state.get(data_editor_key)
                        logger.info(f"[DEBUG collect_current_form_data] Editor state type: {type(editor_state)}")
                        
                        # Check if it's a DataFrame directly
                        if hasattr(editor_state, 'to_dict'):
                            editor_shape = editor_state.shape if editor_state is not None and hasattr(editor_state, 'shape') else 'unknown'
                            logger.info(f"[DEBUG collect_current_form_data] Editor state is a DataFrame with shape: {editor_shape}")
                            try:
                                df_dict = editor_state.to_dict('records') if editor_state is not None else []
                                logger.info(f"[DEBUG collect_current_form_data] DataFrame records count: {len(df_dict)}")
                                if df_dict:
                                    logger.info(f"[DEBUG collect_current_form_data] First DataFrame record: {df_dict[0]}")
                            except Exception as e:
                                logger.error(f"[DEBUG collect_current_form_data] Error converting DataFrame: {e}")
                        
                        logger.debug(
                            "[collect_current_form_data] raw editor state for %s: type=%s repr=%r attrs=%s",
                            field_name,
                            type(editor_state),
                            editor_state,
                            [attr for attr in dir(editor_state) if not attr.startswith('_')],
                        )
                        FormGenerator._display_data_editor_debug(field_name, editor_state)
                        records = FormGenerator._extract_data_editor_records(
                            editor_state,
                            fallback_rows=st.session_state.get(field_key) if isinstance(st.session_state.get(field_key), list) else None,
                            editor_key=data_editor_key,
                        )
                        logger.info(f"[DEBUG collect_current_form_data] Extracted records: {records is not None}, count: {len(records) if records else 0}")
                        if records is not None:
                            cleaned_records = FormGenerator._clean_object_array(records, properties)
                            logger.info(f"[DEBUG collect_current_form_data] Cleaned records count: {len(cleaned_records)}")
                            if cleaned_records:
                                logger.info(f"[DEBUG collect_current_form_data] First cleaned record: {cleaned_records[0]}")
                            logger.debug(
                                "[collect_current_form_data] Using data_editor state for %s (%d rows)",
                                field_name,
                                len(cleaned_records),
                            )
                            form_data[field_name] = cleaned_records
                            continue

                if field_key in st.session_state and isinstance(st.session_state[field_key], list):
                    value = st.session_state[field_key]
                    cleaned = (
                        FormGenerator._clean_object_array(value, properties)
                        if item_type == 'object'
                        else value
                    )
                    logger.info(
                        f"[DEBUG collect_current_form_data] Using field_{field_name} directly (len={len(cleaned)})"
                    )
                    if cleaned:
                        logger.info(f"[DEBUG collect_current_form_data] First item from field_{field_name}: {cleaned[0]}")
                    logger.debug(
                        "[collect_current_form_data] Using field_%s (len=%d)",
                        field_name,
                        len(cleaned),
                    )
                    form_data[field_name] = cleaned
                    continue

                # For scalar arrays or unexpected types, use field_{field_name} when possible
                if field_key in st.session_state:
                    value = st.session_state[field_key]
                    if value is None:
                        form_data[field_name] = []
                    elif isinstance(value, list):
                        form_data[field_name] = (
                            FormGenerator._clean_object_array(value, properties)
                            if item_type == 'object'
                            else value
                        )
                    else:
                        form_data[field_name] = [value]
                    continue
                
                # Fallback: check legacy array keys for backward compatibility
                array_key = f"array_{field_name}"
                json_array_key = f"json_array_{field_name}"
                
                if array_key in st.session_state and st.session_state[array_key] is not None:
                    fallback_value = st.session_state[array_key]
                    if item_type == 'object' and isinstance(fallback_value, list):
                        form_data[field_name] = FormGenerator._clean_object_array(fallback_value, properties)
                    else:
                        form_data[field_name] = fallback_value
                elif json_array_key in st.session_state and st.session_state[json_array_key] is not None:
                    try:
                        value = st.session_state[json_array_key]
                        if isinstance(value, str):
                            parsed = json.loads(value)
                            if item_type == 'object' and isinstance(parsed, list):
                                form_data[field_name] = FormGenerator._clean_object_array(parsed, properties)
                            else:
                                form_data[field_name] = parsed
                        else:
                            if item_type == 'object' and isinstance(value, list):
                                form_data[field_name] = FormGenerator._clean_object_array(value, properties)
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
            
            # Get form version for reset functionality
            form_version = st.session_state.get('form_version', 0)
            widget_key = f"field_{field_name}_v{form_version}"
            
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
        Render array of scalars with individual input fields and delete icons.
        Uses the Option A pattern: individual fields with delete buttons.
        """
        # Get form version for reset functionality
        form_version = st.session_state.get('form_version', 0)
        array_key = f'array_{field_name}_v{form_version}'
        
        items_config = field_config.get("items", {})
        item_type = items_config.get("type", "string")
        
        # Initialize if needed
        if array_key not in st.session_state:
            st.session_state[array_key] = [
                FormGenerator._coerce_scalar_value(item_type, item, items_config)
                for item in list(current_value or [])
            ]
        else:
            st.session_state[array_key] = [
                FormGenerator._coerce_scalar_value(item_type, item, items_config)
                for item in st.session_state[array_key]
            ]
        
        # Display field label
        label = field_config.get('label', field_name)
        help_text = field_config.get('help', '')
        st.markdown(f"**{label}**")
        if help_text:
            st.caption(help_text)
        
        # Display current items
        items = st.session_state[array_key]
        normalized_values: List[Any] = []
        
        # Render each item with its own input field and delete button
        for i, item in enumerate(items):
            col1, col2 = st.columns([5, 1])
            with col1:
                item_key = f'{array_key}_item_{i}'
                logger.debug(
                    "[_render_scalar_array_editor] pre-render | field=%s array_key=%s item_index=%s item_key=%s key_exists=%s incoming_item=%r",
                    field_name,
                    array_key,
                    i,
                    item_key,
                    item_key in st.session_state,
                    item,
                )
                if item_key not in st.session_state:
                    st.session_state[item_key] = FormGenerator._coerce_scalar_value(item_type, item, items_config)
                    logger.debug(
                        "[_render_scalar_array_editor] initialized item key | item_key=%s initialized_value=%r",
                        item_key,
                        st.session_state[item_key],
                    )
                
                widget_value = FormGenerator._render_scalar_input(
                    field_name,
                    item_type,
                    st.session_state[item_key],
                    items_config,
                    item_key
                )
                logger.debug(
                    "[_render_scalar_array_editor] post-widget | item_key=%s widget_value=%r session_state_value=%r",
                    item_key,
                    widget_value,
                    st.session_state.get(item_key),
                )
                coerced_value = FormGenerator._coerce_scalar_value(item_type, widget_value, items_config)
                logger.debug(
                    "[_render_scalar_array_editor] pre-session-write | item_key=%s coerced_value=%r existing_session_state_value=%r",
                    item_key,
                    coerced_value,
                    st.session_state.get(item_key),
                )
                logger.debug(
                    "[_render_scalar_array_editor] skip-session-write | item_key=%s using_widget_value=%r session_state_stays=%r",
                    item_key,
                    coerced_value,
                    st.session_state.get(item_key),
                )
                normalized_values.append(coerced_value)
            
            with col2:
                if st.button("🗑️", key=f'delete_{array_key}_{i}'):
                    # Delete this item and reindex remaining items
                    
                    # First, collect current values from all existing keys
                    current_values = []
                    for j in range(len(items)):
                        key_j = f'{array_key}_item_{j}'
                        if key_j in st.session_state:
                            current_values.append(
                                FormGenerator._coerce_scalar_value(
                                    item_type,
                                    st.session_state[key_j],
                                    items_config
                                )
                            )
                        else:
                            current_values.append(
                                FormGenerator._coerce_scalar_value(
                                    item_type,
                                    items[j] if j < len(items) else "",
                                    items_config
                                )
                            )
                    
                    # Remove the item at position i
                    if 0 <= i < len(current_values):
                        current_values.pop(i)
                    st.session_state[array_key] = current_values
                    logger.debug(
                        "[_render_scalar_array_editor] delete-item | field=%s array_key=%s deleted_index=%s remaining_count=%s",
                        field_name,
                        array_key,
                        i,
                        len(current_values),
                    )
                    
                    # Clear all existing item keys
                    keys_to_delete = [
                        key for key in list(st.session_state.keys())
                        if str(key).startswith(f'{array_key}_item_')
                    ]
                    logger.debug(
                        "[_render_scalar_array_editor] reindex-cleanup | array_key=%s keys_to_delete=%s",
                        array_key,
                        keys_to_delete,
                    )
                    for key in keys_to_delete:
                        del st.session_state[key]
                    logger.debug(
                        "[_render_scalar_array_editor] reindex-cleanup-complete | array_key=%s",
                        array_key,
                    )
                    
                    st.rerun()
        
        st.session_state[array_key] = normalized_values

        # Add button
        if st.button(f"➕ Add Item", key=f'add_{array_key}'):
            # Add default value based on type
            default_value = FormGenerator._get_default_value_for_type(item_type, items_config)
            st.session_state[array_key].append(default_value)
            st.rerun()
        
        # Collect current values from individual item keys for validation and sync
        updated_values = [
            FormGenerator._coerce_scalar_value(item_type, value, items_config)
            for value in st.session_state[array_key]
        ]
        
        # Sync to session state for data collection
        FormGenerator._sync_array_to_session(field_name, updated_values)
        
        # Validation
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
        Streamlined object array editor that relies on Streamlit's native data_editor controls
        for adding and removing rows while preserving production validation and state sync.
        """
        import pandas as pd
        
        # Get form version for reset functionality
        form_version = st.session_state.get('form_version', 0)
        
        items_config = field_config.get("items", {})
        properties = items_config.get("properties", {})
        
        working_array = list(current_value or [])

        # Prepare DataFrame for data_editor, ensuring consistent column ordering
        column_order: List[str] = list(properties.keys())
        for obj in working_array:
            for key in obj.keys():
                if key not in column_order:
                    column_order.append(key)

        if working_array:
            df = pd.DataFrame(working_array)
            if column_order:
                df = df.reindex(columns=column_order)
        else:
            df = pd.DataFrame(columns=column_order)

        for column_name, prop_config in properties.items():
            if prop_config.get("type") == "date" and column_name in df.columns:
                df[column_name] = pd.to_datetime(df[column_name], errors="coerce")

        column_config = FormGenerator._generate_column_config(properties)
        
        # Initialize versioned array in session state if needed
        array_key = f'array_{field_name}_v{form_version}'
        if array_key not in st.session_state:
            st.session_state[array_key] = working_array.copy()
        
        # Get current items from session state
        current_items = st.session_state[array_key]
        
        # Default row for adding new items
        default_row = {}
        for prop_name, prop_config in properties.items():
            prop_type = prop_config.get('type', 'string')
            if prop_type == 'string':
                default_row[prop_name] = "New Item"
            elif prop_type in ['number', 'integer']:
                default_row[prop_name] = 1
            elif prop_type == 'boolean':
                default_row[prop_name] = False
            else:
                default_row[prop_name] = None

        with st.container():
            label = field_config.get('label', field_name)
            help_text = field_config.get('help', '')
            st.markdown(f"**{label}**")
            if help_text:
                st.caption(help_text)
            
            # Add/Delete buttons (manual control)
            col1, col2 = st.columns([1, 1])
            with col1:
                if st.button("➕ Add Row", key=f'add_{array_key}'):
                    st.session_state[array_key].append(default_row.copy())
                    st.rerun()
            with col2:
                if len(current_items) > 0:
                    if st.button("🗑️ Delete Last Row", key=f'delete_{array_key}'):
                        st.session_state[array_key].pop()
                        st.rerun()
            
            st.caption("Edit cells directly. Use the buttons above to add/remove rows.")

            # Create DataFrame from current items
            if current_items:
                df = pd.DataFrame(current_items)
                if column_order:
                    df = df.reindex(columns=column_order)
            else:
                df = pd.DataFrame(columns=column_order)

            edited_df = st.data_editor(
                df,
                column_config=column_config,
                num_rows="fixed",  # Use manual buttons instead of dynamic
                width='stretch',
                key=f"data_editor_{field_name}_v{form_version}",
                hide_index=True
            )
            try:
                first_quantity = edited_df.iloc[0]["Quantity"] if not edited_df.empty else None
            except Exception:
                first_quantity = None
            logger.debug(
                "[_render_object_array_editor] data_editor df first quantity=%s",
                first_quantity,
            )
            FormGenerator._display_data_editor_debug(field_name, edited_df)

            # CRITICAL: Store edited DataFrame in a separate key for data collection
            # This is read during data collection, NOT used to update the source array
            st.session_state[f'{array_key}_current'] = edited_df
            
            # Convert DataFrame to records for validation display
            if hasattr(edited_df, 'to_dict'):
                try:
                    # Convert DataFrame directly to records - this contains the edited values
                    editor_records = edited_df.to_dict('records')
                    logger.info(f"[DEBUG _render_object_array_editor] Converted DataFrame: {len(editor_records)} records")
                    if editor_records:
                        logger.info(f"[DEBUG _render_object_array_editor] First record: {editor_records[0]}")
                    
                    # Clean the records for validation
                    working_array = FormGenerator._clean_object_array(editor_records, properties)
                    
                    logger.info(
                        "[DEBUG _render_object_array_editor] Cleaned %s: %d rows; first=%s",
                        field_name,
                        len(working_array),
                        working_array[0] if working_array else None,
                    )
                except Exception as e:
                    logger.error(f"[DEBUG _render_object_array_editor] Error converting DataFrame: {e}")
                    working_array = list(current_items or [])
            else:
                logger.warning(f"[DEBUG _render_object_array_editor] edited_df is not a DataFrame: {type(edited_df)}")
                working_array = list(current_items or [])

            validation_errors = FormGenerator._validate_object_array(field_name, working_array, items_config)
            if validation_errors:
                for error in validation_errors:
                    st.error(error)
            elif working_array:
                st.success(f"{len(working_array)} objects valid")

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
                key=key,
                help=f"Select value for {field_name}"
            )
            return value
        
        else:
            # Fallback to text input
            value = st.text_input(
                f"Item {key.split('_')[-1]}",
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
