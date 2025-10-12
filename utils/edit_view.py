"""
Edit view utilities for JSON QA webapp.
Handles the side-by-side layout with PDF preview and form editing.
"""

import streamlit as st
from typing import Dict, Any, Optional
import logging
import json

from .session_manager import SessionManager
from .file_utils import load_json_file, save_corrected_json, release_file, append_audit_log
from .schema_loader import get_schema_for_file
from .model_builder import create_model_from_schema, validate_model_data
from .pdf_viewer import PDFViewer
from .form_generator import FormGenerator
from .diff_utils import calculate_diff, format_diff_for_display, has_changes, create_audit_diff_entry
from .submission_handler import SubmissionHandler
from datetime import datetime
from utils.ui_feedback import Notify

logger = logging.getLogger(__name__)


class EditView:
    """Manages the edit view interface for validating and correcting JSON data."""
    
    
    @staticmethod
    def render(cancel_callback=None):
        """Render the complete edit view."""
        
        current_file = SessionManager.get_current_file()
        
        if not current_file:
            EditView._render_no_file_selected()
            return
        
        st.header(f"✏️ Editing: {current_file}")
        
        try:
            # Initialize data if needed
            if not EditView._initialize_edit_data(current_file):
                return
            
            # Render the side-by-side layout
            EditView._render_side_by_side_layout()
            
            # Render diff section
            st.divider()
            EditView._render_diff_section()
            
            # Render action buttons
            EditView._render_action_buttons(cancel_callback=cancel_callback)
            
            
        except Exception as e:
            Notify.error("Operation failed")
            with st.expander("Details"):
                st.error(str(e))
            logger.error(f"Error in edit view for {current_file}: {e}", exc_info=True)
    
    @staticmethod
    def _render_no_file_selected():
        """Render message when no file is selected."""
        if not st.session_state.get("edit_view_no_file_notified"):
            Notify.info("No document selected. Please go to Queue View and claim a file.")
            st.session_state["edit_view_no_file_notified"] = True
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("📋 Go to Queue", type="primary", help="Go to Queue view", key="go_to_queue_btn"):
                SessionManager.set_current_page('queue')
                st.rerun()
        
        with col2:
            if st.button("📊 View Audit Log", help="Go to Audit view", key="go_to_audit_btn"):
                SessionManager.set_current_page('audit')
                st.rerun()
        
        # Show helpful information
        with st.expander("ℹ️ How to start editing"):
            st.markdown("""
            **To begin editing a file:**
            
            1. **Go to Queue View** - Click the "Go to Queue" button above
            2. **Select a file** - Choose an unverified JSON file from the list
            3. **Claim the file** - Click the "Claim" button to lock it for editing
            4. **Edit and validate** - You'll be automatically redirected here to edit
            
            **What you can do in Edit View:**
            - View the original PDF document side-by-side with extracted data
            - Edit JSON data using schema-driven forms
            - See real-time differences between original and modified data
            - Validate changes before submitting
            - Submit corrections or cancel to release the file
            """)
    
    @staticmethod
    def _filter_to_schema_fields(data: dict, schema_fields: set) -> tuple[dict, dict]:
        """Filter data to schema fields and extract extras."""
        filtered_data = {k: v for k, v in data.items() if k in schema_fields}
        extras = {k: v for k, v in data.items() if k not in schema_fields}
        return filtered_data, extras

    @staticmethod
    def _initialize_edit_data(filename: str) -> bool:
        """Initialize edit data for the current file."""
        from .error_handler import ErrorHandler, ErrorType
        from .ui_feedback import show_loading, show_progress
        from .schema_loader import load_config, extract_field_names, load_active_schema, get_schema_for_file
        from .model_builder import filter_to_schema_fields as mb_filter_to_schema_fields
        
        try:
            with show_progress(4, "Initializing edit session") as progress:
                # Step 1: Load original data
                progress.update(1, "Loading JSON data")
                original_data = load_json_file(filename)
                if not original_data:
                    raise FileNotFoundError(f"Could not load JSON file: {filename}")
                
                # Step 2: Load primary active schema from config (hot-reloadable)
                progress.update(2, "Loading active schema")
                schema_config = load_config()['schema']
                schema_path = schema_config['primary_schema']
                schema = load_active_schema(schema_path)
                
                # Ensure we have a schema for this file: prefer schema for file if available
                progress.update(3, "Ensuring schema for file")
                if not SessionManager.get_schema():
                    # Try to get schema for this file (fallback to get_schema_for_file)
                    schema = st.session_state.get('active_schema', get_schema_for_file(filename))
                    # Attempt to hot-reload latest schema for this specific file path
                    latest_schema = None
                    try:
                        latest_schema = load_active_schema(filename)
                    except Exception:
                        pass
                    if latest_schema:
                        schema = latest_schema
                    
                    if schema:
                        SessionManager.set_schema(schema)
                        if not st.session_state.get(f"edit_view_schema_loaded_{filename}"):
                            Notify.success(f"Loaded schema for: {filename}")
                            st.session_state[f"edit_view_schema_loaded_{filename}"] = True
                    else:
                        raise ValueError(f"Could not load schema for file: {filename}")
                
                # Determine schema fields (prefer session override if present)
                schema_fields = st.session_state.get("schema_fields") or (extract_field_names(SessionManager.get_schema()) if SessionManager.get_schema() else None)
                if not schema_fields:
                    schema_fields = set()
                
                # Filter data to schema fields using model_builder utility (returns (filtered, extras_list))
                try:
                    filtered_data, extras = mb_filter_to_schema_fields(original_data, set(schema_fields))
                except Exception:
                    # Fallback to local filter if model_builder.filter_to_schema_fields fails
                    filtered_data, extras = EditView._filter_to_schema_fields(original_data, set(schema_fields))
                
                if extras:
                    # Persist deprecated extras for UI and show a non-blocking notice
                    st.session_state["deprecated_fields_current_doc"] = extras
                    # extras may be a list (model_builder) or dict (local impl)
                    if isinstance(extras, dict):
                        extras_list = list(extras.keys())
                    else:
                        extras_list = list(extras)
                    ignored_preview = extras_list[:5]
                    msg = f"Ignored {len(extras_list)} deprecated fields: {', '.join(ignored_preview)}{'...' if len(extras_list) > 5 else ''}"
                    try:
                        Notify.warn(msg)
                    except Exception:
                        # streamlit may not have Notify available in some contexts; use toast as fallback
                        st.toast(msg, icon="⚠️")
                
                # Update session manager with filtered data (do not mutate on-disk JSON)
                SessionManager.set_original_data(filtered_data)
                SessionManager.set_form_data(filtered_data.copy())
                Notify.success(f"Loaded: {filename}")
                
                # Step 4: Create model
                progress.update(4, "Creating validation model")
                if not SessionManager.get_model_class():
                    try:
                        model_class = create_model_from_schema(
                            SessionManager.get_schema(),
                            f"Model_{filename.replace('.', '_')}"
                        )
                        SessionManager.set_model_class(model_class)
                    except Exception as e:
                       logger.error(f"Failed to create model: {e}")
                       Notify.warn("Schema validation may be limited due to model creation error")
                
                progress.complete("Edit session ready")
            
            return True
            
        except Exception as e:
            # Notify user of failure in load path, preserve existing ErrorHandler flow and expanders
            Notify.error("Failed to load document")
            ErrorHandler.handle_error(
                e,
                f"initializing edit data for {filename}",
                ErrorType.FILE_SYSTEM if isinstance(e, FileNotFoundError) else ErrorType.SCHEMA,
                recovery_options=ErrorHandler.create_recovery_options("file schema")
            )
            return False
    
    @staticmethod
    def _render_side_by_side_layout():
        """Render the side-by-side layout with PDF and form."""
        # Create two equal-width columns
        col1, col2 = st.columns([1, 1], gap="medium")
        
        with col1:
            EditView._render_pdf_column()
        
        with col2:
            EditView._render_form_column()
    
    @staticmethod
    def _render_pdf_column():
        """Render the PDF preview column."""
        try:
            current_file = SessionManager.get_current_file()
            # SessionManager may return None; PDFViewer.render_pdf_preview expects str.
            # If no file is selected, pass an empty string so the PDFViewer's own
            # falsy-check (if not filename) will handle the "no file" UI path.
            if current_file is None:
                PDFViewer.render_pdf_preview("")
            else:
                PDFViewer.render_pdf_preview(current_file)
        
        except Exception as e:
            Notify.error("Operation failed")
            with st.expander("Details"):
                st.error(str(e))
            logger.error(f"Error in PDF column: {e}", exc_info=True)
    
    @staticmethod
    def _render_form_column():
        """Render the form editing column."""
        try:
            schema = SessionManager.get_schema()
            current_data = SessionManager.get_form_data()
            
            if not schema:
                if not st.session_state.get("edit_view_schema_required_warned"):
                    Notify.warn("Schema required to validate")
                    st.session_state["edit_view_schema_required_warned"] = True
                return
            
            # Render the dynamic form
            updated_data = FormGenerator.render_dynamic_form(schema, current_data)
            
            # Always update form data to ensure changes are captured
            SessionManager.set_form_data(updated_data)
        
        except Exception as e:
            Notify.error("Operation failed")
            with st.expander("Details"):
                st.error(str(e))
            logger.error(f"Error in form column: {e}", exc_info=True)
    
    @staticmethod
    def _render_diff_section():
        """Render the diff section showing changes."""
        st.subheader("🔍 Changes Preview")
        
        try:
            original_data = SessionManager.get_original_data()
            form_data = SessionManager.get_form_data()

            current_file = SessionManager.get_current_file()
            # Reload original data from JSON file to ensure fresh data
            original_data = load_json_file(current_file) if current_file else None
            form_data = SessionManager.get_form_data()
            
            if not original_data or not form_data:
                Notify.info("No data to compare")
                return
            
            # Calculate diff
            diff = calculate_diff(original_data, form_data)
            
            if has_changes(diff):
                # Show summary metrics
                from .diff_utils import get_change_summary
                summary = get_change_summary(diff)
                
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("Total Changes", summary['total'])
                with col2:
                    st.metric("Modified", summary['modified'])
                with col3:
                    st.metric("Added", summary['added'])
                with col4:
                    st.metric("Removed", summary['removed'])
                
                # Show detailed diff
                # Get data from SessionManager to ensure we have the latest state
                # Use the freshly loaded data for consistent display
                formatted_diff = format_diff_for_display(diff, original_data, form_data)
                st.markdown(formatted_diff)
                
                # Store diff in session for submission
                st.session_state.current_diff = diff
            else:
                st.success("✅ No changes detected")
                st.session_state.current_diff = {}
        
        except Exception as e:
            Notify.error("Operation failed")
            with st.expander("Details"):
                st.error(str(e))
            logger.error(f"Error in diff section: {e}", exc_info=True)
    
    @staticmethod
    def _show_cancel_dialog(cancel_callback=None):
        """Show cancel confirmation as a popup dialog."""
        @st.dialog("Confirm Discard Changes", width="large")  # type: ignore[reportArgumentType]
        def cancel_dialog():
            """Dialog to confirm discarding changes."""
            st.warning("⚠️ You have unsaved changes. Are you sure you want to discard them and return to the queue?")
            
            col1, col2 = st.columns([1, 1])
            with col1:
                if st.button("❌ Discard Changes", type="primary"):
                    if cancel_callback:
                        cancel_callback()
                    else:
                        EditView._handle_cancel()  # Fallback
                    st.rerun()  # Close dialog and rerun app
            with col2:
                if st.button("✏️ Continue Editing"):
                    st.rerun()  # Close dialog and continue editing
        
        cancel_dialog()
 
    @staticmethod
    def _render_action_buttons(cancel_callback=None):
        """Render action buttons for reset and status."""
        st.divider()
        
        col1, col2 = st.columns([3, 2])
        
        with col1:
            if st.button("🔄 Reset to Original", help="Reset form to original data"):
                EditView._handle_reset()
        
        with col2:
            # Show validation status
            validation_errors = SessionManager.get_validation_errors()
            if validation_errors:
                Notify.warn("field(s) need attention")
            elif SessionManager.has_unsaved_changes():
                st.warning("⚠️ Unsaved changes")
            else:
                Notify.success("All fields valid")
    
    # _handle_submit removed - submission now handled within FormGenerator form context
    
    @staticmethod
    def _handle_cancel():
        """Handle editing cancellation."""
        from .submission_handler import SubmissionHandler
        
        try:
            success = SubmissionHandler.handle_cancel_submission()
            if success:
                st.rerun()
        
        except Exception as e:
            Notify.error("Operation failed")
            with st.expander("Details"):
                st.error(str(e))
            logger.error(f"Error cancelling: {e}", exc_info=True)

    @staticmethod
    def _render_cancel_confirmation(cancel_callback=None):
        """Render persistent cancel confirmation modal."""
        if st.session_state.get('show_cancel_confirm', False):
            # Check for unsaved changes (this should be true if we got here)
            if SessionManager.has_unsaved_changes():
                st.warning("⚠️ You have unsaved changes. Are you sure you want to discard them and return to the queue?")
                
                col1, col2 = st.columns([1, 1])
                with col1:
                    if st.button("❌ Discard Changes", type="primary", key="discard_confirm"):
                        st.session_state.show_cancel_confirm = False
                        if cancel_callback:
                            cancel_callback()
                        else:
                            EditView._handle_cancel()  # Fallback
                with col2:
                    if st.button("✏️ Continue Editing", key="continue_editing"):
                        st.session_state.show_cancel_confirm = False
                        st.rerun()
            else:
                # No changes, just cancel
                st.session_state.show_cancel_confirm = False
                if cancel_callback:
                    cancel_callback()
                else:
                    EditView._handle_cancel()
    

    @staticmethod
    def _handle_reset():
        """Handle form reset to original data."""
        try:
            # Initialize schema
            schema = SessionManager.get_schema()
            if not schema:
                Notify.warn("Schema required to reset form")
                return 

            current_file = SessionManager.get_current_file()
            
            # Reload original data from JSON file to ensure fresh data
            original_data = load_json_file(current_file) if current_file else None
            
            if original_data:
                # First update the session manager state
                SessionManager.set_original_data(original_data)
                SessionManager.set_form_data(original_data.copy())
                SessionManager.clear_validation_errors()
                
                # Clear all existing field_ prefixed keys from session state
                for key in list(st.session_state.keys()):
                    if str(key).startswith('field_'):
                        del st.session_state[key]
                
                # For array fields, also clear array_ and json_array_ prefixed keys
                for key in list(st.session_state.keys()):
                    if str(key).startswith('array_') or str(key).startswith('json_array_'):
                        del st.session_state[key]
                
                # Update widget-level session state keys with original values
                def update_widget_keys(data, schema, prefix=''):
                    if isinstance(data, dict):
                        for key, value in data.items():
                            widget_key = f"field_{prefix}{key}" if prefix else f"field_{key}"
                            try:
                                # Get field type from schema
                                field_type = schema.get('fields', {}).get(key, {}).get('type', 'string')
                                
                                if isinstance(value, (dict, list)):
                                    # For complex types, store them as is
                                    st.session_state[widget_key] = value
                                    # Recursively handle nested dictionaries
                                    if isinstance(value, dict):
                                        update_widget_keys(value, schema, f"{prefix}{key}.")
                                else:
                                    # Special handling for date fields
                                    if field_type == 'date':
                                        from datetime import datetime
                                        # If value is string, try to parse it
                                        if isinstance(value, str):
                                            try:
                                                parsed_date = datetime.strptime(value, "%Y/%m/%d").date()
                                                st.session_state[widget_key] = parsed_date
                                            except ValueError:
                                                st.session_state[widget_key] = value
                                        else:
                                            st.session_state[widget_key] = value
                                    else:
                                        st.session_state[widget_key] = value
                            except Exception:
                                st.error(f"Error resetting field {key}")
                
                # Update all widget keys with the original data using schema
                fields_schema = schema.get('fields', {})
                update_widget_keys(original_data, fields_schema)
                
                Notify.success("🔄 Form reset to original data")
                st.rerun()
            else:
                Notify.error("No original data available")
        
        except Exception as e:
            Notify.error("Operation failed")
            with st.expander("Details"):
                st.error(str(e))
    
    @staticmethod
    def render_edit_sidebar():
        """Render edit view sidebar information."""
        try:
            current_file = SessionManager.get_current_file()
            
            if not current_file:
                return
            
            st.sidebar.subheader("📝 Edit Session")
            
            # File info
            st.sidebar.write(f"**File:** {current_file}")
            st.sidebar.write(f"**User:** {SessionManager.get_current_user()}")
            
            # Session status
            if SessionManager.has_unsaved_changes():
                st.sidebar.warning("⚠️ Unsaved changes")
            else:
                st.sidebar.success("✅ No changes")
            
            # Validation status
            validation_errors = SessionManager.get_validation_errors()
            if validation_errors:
                st.sidebar.error(f"❌ {len(validation_errors)} validation errors")
                with st.sidebar.expander("View Errors"):
                    for error in validation_errors:
                        st.sidebar.error(f"• {error}")
            
            # Schema info
            schema = SessionManager.get_schema()
            if schema:
                st.sidebar.subheader("📋 Schema Info")
                st.sidebar.write(f"**Title:** {schema.get('title', 'Unknown')}")
                field_count = len(schema.get('fields', {}))
                st.sidebar.write(f"**Fields:** {field_count}")
            
            # Quick actions
            st.sidebar.subheader("⚡ Quick Actions")
            
            if st.sidebar.button("🔄 Refresh Data"):
                # Reload original data
                original_data = load_json_file(current_file)
                if original_data:
                    SessionManager.set_original_data(original_data)
                    st.sidebar.success("Data refreshed")
                    st.rerun()
            
            if st.sidebar.button("📋 Copy JSON"):
                import json
                form_data = SessionManager.get_form_data()
                json_str = json.dumps(form_data, indent=2)
                st.sidebar.code(json_str)
        
        except Exception as e:
            st.sidebar.error("Error loading edit info")
            logger.error(f"Error in edit sidebar: {e}", exc_info=True) 


# Convenience function
def render_edit_view():
    """Render the edit view."""
    EditView.render()