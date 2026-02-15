"""
Schema Editor View for the JSON QA webapp.
Provides a visual interface for creating, editing, and managing YAML schema files.
"""

import streamlit as st
import logging
import yaml
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
import shutil
import re
import collections
from utils.ui_feedback import Notify
from utils.array_field_manager import ArrayFieldManager

# Helper functions for managing the editor dirty state and caches.
# These centralize dirty/clean semantics and keep backward compatibility
# with the older 'schema_editor_unsaved' session key.
def _mark_dirty() -> None:
    """
    Mark the schema editor as having unsaved changes.
    Sets both the canonical DIRTY_KEY and the legacy schema_editor_unsaved flag
    for compatibility with older code paths/UI.
    """
    try:
        st.session_state[DIRTY_KEY] = True
        # keep legacy key in sync
        st.session_state.schema_editor_unsaved = True
        Notify.once("Marked schema as unsaved", notification_type="info", key="schema_marked_dirty")
        # Log dirty transition with context if available
        try:
            field_count = len(st.session_state.get('schema_editor_fields', []))
            active_file = st.session_state.get('schema_editor_active_file')
            logger.debug(f"_mark_dirty called: {DIRTY_KEY}=True active_file={active_file} field_count={field_count}")
        except Exception as _e:
            logger.debug(f"_mark_dirty called: {DIRTY_KEY}=True (failed to read extra context: {_e})")
    except Exception:
        # Fail silently to avoid breaking UI on unexpected session state issues
        st.session_state[DIRTY_KEY] = True
        st.session_state.schema_editor_unsaved = True
        try:
            logger.debug(f"_mark_dirty fallback: set {DIRTY_KEY} and legacy flag to True")
        except Exception:
            pass

def _mark_clean() -> None:
    """
    Mark the schema editor as clean (no unsaved changes).
    Clears both canonical and legacy flags and records last save timestamp.
    """
    try:
        import inspect
        try:
            current_frame = inspect.currentframe()
            if current_frame:
                caller_frame = current_frame.f_back
                if caller_frame and caller_frame.f_code:
                    caller_name = caller_frame.f_code.co_name
                    caller_file = caller_frame.f_code.co_filename
                else:
                    caller_name = "unknown"
                    caller_file = "unknown"
            else:
                caller_name = "unknown"
                caller_file = "unknown"
        except Exception as inspect_e:
            logger.debug(f"_mark_clean: inspect failed ({inspect_e}), using unknown caller")
            caller_name = "unknown"
            caller_file = "unknown"
        logger.debug(f"_mark_clean called from {caller_name} in {caller_file}; setting dirty=False and last_save={datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        st.session_state[DIRTY_KEY] = False
        st.session_state.schema_editor_unsaved = False
        st.session_state[LAST_SAVE_TS_KEY] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        Notify.success("All changes saved")
        # Log clean transition with context
        try:
            active_file = st.session_state.get('schema_editor_active_file')
            field_count = len(st.session_state.get('schema_editor_fields', []))
            logger.debug(f"_mark_clean completed: {DIRTY_KEY}=False, active_file={active_file}, fields={field_count}, last_save={st.session_state.get(LAST_SAVE_TS_KEY)}")
        except Exception as _e:
            logger.debug(f"_mark_clean completed: {DIRTY_KEY}=False (failed to read extra context: {_e})")
    except Exception:
        st.session_state[DIRTY_KEY] = False
        st.session_state.schema_editor_unsaved = False
        try:
            logger.debug(f"_mark_clean fallback: set {DIRTY_KEY} and legacy flag to False")
        except Exception:
            pass

def _clear_schema_caches() -> None:
    """
    Clear relevant caches so that saved/updated schemas are picked up immediately.
    This wraps Streamlit's cache clearing and provides user feedback.
    """
    logger.debug("_clear_schema_caches: attempting to clear streamlit caches")
    try:
        # Clear streamlit cache for data functions
        if hasattr(st, "cache_data"):
            st.cache_data.clear()
            logger.debug("_clear_schema_caches: cache_data cleared")
        if hasattr(st, "cache_resource"):
            try:
                st.cache_resource.clear()
                logger.debug("_clear_schema_caches: cache_resource cleared")
            except Exception as e:
                # Some streamlit versions may not expose cache_resource.clear()
                logger.debug(f"_clear_schema_caches: cache_resource.clear() not available or failed: {e}")
                pass
        Notify.info("Schema caches cleared")
        logger.info("_clear_schema_caches: schema caches cleared successfully")
    except Exception as e:
        logger.warning(f"Failed to clear schema caches: {e}")
        # Not fatal for editor functionality

# Canonical dirty flag keys (incremental change)
DIRTY_KEY = "schema_dirty"
LAST_SAVE_TS_KEY = "schema_last_saved_at"


logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


class SchemaEditor:
    """Main controller class for the Schema Editor feature."""
    
    
    @staticmethod
    def render() -> None:
        """Main entry point for rendering the Schema Editor with comprehensive error handling."""
        try:
            # Initialize session state for schema editor
            # Show initialization toast on first render
            if not st.session_state.get('schema_editor_initialized', False):
                Notify.once("Schema Editor ready", notification_type="info", key="schema_editor_loaded")
            SchemaEditor._initialize_session_state()
            
            # Render appropriate view based on current mode
            mode = st.session_state.get('schema_editor_mode', 'list')
            
            if mode == 'list':
                SchemaEditor._render_list_view()
            elif mode == 'edit':
                SchemaEditor._render_editor_view()
            else:
                st.error(f"Unknown schema editor mode: {mode}")
                st.session_state.schema_editor_mode = 'list'
                st.rerun()
                
        except PermissionError as e:
            logger.error(f"Permission error in Schema Editor: {e}", exc_info=True)
            Notify.error("Permission Error in Schema Editor")
            st.error("❌ **Permission Error**")
            st.error("The Schema Editor cannot access the required files or directories.")
            st.info("**Recovery Options:**")
            st.info("• Check that you have read/write permissions to the schemas/ directory")
            st.info("• Ensure the application has proper file system access")
            st.info("• Try running the application with appropriate permissions")
            st.info("• Contact your system administrator if the problem persists")
            SchemaEditor._reset_to_safe_state()
            
        except FileNotFoundError as e:
            logger.error(f"File not found error in Schema Editor: {e}", exc_info=True)
            Notify.error("File System Error in Schema Editor")
            st.error("❌ **File System Error**")
            st.error("Required files or directories are missing.")
            st.info("**Recovery Options:**")
            st.info("• The schemas/ directory will be created automatically")
            st.info("• Check that the application is running in the correct directory")
            st.info("• Refresh the page to retry initialization")
            SchemaEditor._reset_to_safe_state()
            
        except yaml.YAMLError as e:
            logger.error(f"YAML error in Schema Editor: {e}", exc_info=True)
            Notify.error("YAML Processing Error in Schema Editor")
            st.error("❌ **YAML Processing Error**")
            st.error("There was an error processing YAML data.")
            st.info("**Recovery Options:**")
            st.info("• Check that all schema files have valid YAML syntax")
            st.info("• Use a YAML validator to check your files")
            st.info("• Remove or fix any corrupted schema files")
            st.info("• Refresh the page to retry")
            SchemaEditor._reset_to_safe_state()
            
        except Exception as e:
            logger.error(f"Unexpected error in Schema Editor: {e}", exc_info=True)
            Notify.error("Unexpected Error in Schema Editor")
            st.error("❌ **Unexpected Error**")
            st.error("An unexpected error occurred in the Schema Editor.")
            st.error(f"**Technical Details:** {str(e)}")
            st.info("**Recovery Options:**")
            st.info("• Refresh the page to restart the Schema Editor")
            st.info("• Check the application logs for more details")
            st.info("• Try using a different browser if the problem persists")
            st.info("• Report this issue if it continues to occur")
            SchemaEditor._reset_to_safe_state()
    
    @staticmethod
    def _reset_to_safe_state() -> None:
        """Reset Schema Editor to a safe state after errors."""
        try:
            # Clear potentially corrupted session state
            keys_to_clear = [
                'schema_editor_fields',
                'schema_editor_validation_results',
                'schema_editor_imported_schema',
                'schema_editor_pending_delete',
                'schema_editor_pending_duplicate',
                'schema_editor_pending_field_delete',
                'schema_editor_pending_navigation',
                'schema_editor_show_save_as'
            ]
            
            for key in keys_to_clear:
                if key in st.session_state:
                    del st.session_state[key]
            
            # Reset to list mode
            st.session_state.schema_editor_mode = 'list'
            st.session_state.schema_editor_active_file = None
            st.session_state.schema_editor_unsaved = False
            st.session_state.schema_editor_initialized = False
            
            logger.info("Schema Editor reset to safe state")
            
        except Exception as e:
            logger.error(f"Error resetting Schema Editor to safe state: {e}", exc_info=True)
            # If we can't even reset safely, just log it
    
    @staticmethod
    def _handle_graceful_degradation(operation: str, error: Exception) -> None:
        """
        Handle graceful degradation for failed operations.
        
        Args:
            operation: Name of the operation that failed
            error: The exception that occurred
        """
        # UserFeedback import removed - using Notify instead
        
        logger.error(f"Graceful degradation for {operation}: {error}", exc_info=True)
        
        # Provide operation-specific recovery guidance
        if "permission" in str(error).lower():
            Notify.error(f"{operation} failed due to permission issues")
            st.info("**Permission Recovery Options:**")
            st.info("• Check file and directory permissions")
            st.info("• Ensure the application has necessary access rights")
            st.info("• Try running with elevated permissions if appropriate")
            
        elif "space" in str(error).lower() or "disk" in str(error).lower():
            Notify.error(f"{operation} failed due to disk space issues")
            st.info("**Disk Space Recovery Options:**")
            st.info("• Free up disk space")
            st.info("• Clean up temporary files")
            st.info("• Move files to a different location with more space")
            
        elif "network" in str(error).lower() or "connection" in str(error).lower():
            Notify.error(f"{operation} failed due to network issues")
            st.info("**Network Recovery Options:**")
            st.info("• Check your network connection")
            st.info("• Retry the operation")
            st.info("• Work offline if possible")
            
        else:
            Notify.error(f"{operation} failed unexpectedly")
            st.info("**General Recovery Options:**")
            st.info("• Refresh the page and try again")
            st.info("• Check the application logs for details")
            st.info("• Try a different approach to accomplish your goal")
            st.info("• Contact support if the problem persists")
        
        # Offer to reset to safe state
        if st.button("🔄 Reset Schema Editor", key=f"reset_after_{operation.lower().replace(' ', '_')}"):
            SchemaEditor._reset_to_safe_state()
            st.rerun()
    
    @staticmethod
    def _render_list_view() -> None:
        """Render the schema list/browse view with enhanced UI polish."""
        # Keyboard shortcuts have been disabled
        st.header("📋 Schema Editor - File Manager")
        st.markdown("Manage your YAML schema files for data validation.")
        
        # Keyboard shortcuts info (disabled)
        
        # Top-level action buttons with enhanced styling
        col1, col2, col3, col4 = st.columns([2, 2, 1, 1])
        
        with col1:
            if st.button("➕ Create New Schema", type="primary",
                        help="Create a new schema from scratch",
                        key="create_new_schema_btn",
                        width='stretch'):
                # Clear any existing editor state and switch to edit mode
                st.session_state.schema_editor_active_file = None
                st.session_state.schema_editor_fields = []
                _mark_clean()
                st.session_state.schema_editor_initialized = False
                st.session_state.schema_editor_mode = 'edit'
                st.rerun()
        
        with col2:
            # Import YAML file uploader with enhanced validation
            uploaded_file = st.file_uploader(
                "📤 Import YAML Schema",
                type=['yaml', 'yml'],
                help="Upload a YAML schema file to import. Supports .yaml and .yml files up to 5MB.",
                key="schema_import_uploader"
            )
            
            if uploaded_file is not None:
                SchemaEditor._handle_schema_import(uploaded_file)
        
        with col3:
            if st.button("🔄 Refresh",
                        help="Reload schema file list from disk",
                        key="refresh_schema_list_btn",
                        width='stretch'):
                # Clear any cached data and rerun to refresh the list
                st.rerun()
        
        with col4:
            # Show total count with enhanced styling
            schema_files = list_schema_files()
            st.metric("Total Schemas", len(schema_files), 
                     help="Total number of schema files found")
        
        st.divider()
        
        # Handle pending file operations with confirmations
        SchemaEditor._handle_pending_operations()
        
        try:
            # Check if we got any schema files
            if not schema_files:
                Notify.info("📁 No schema files found in the schemas/ directory.")
                st.markdown("Create your first schema to get started!")
                
                # Check if schemas directory exists and is accessible
                schemas_dir = Path("schemas")
                if not schemas_dir.exists():
                    Notify.info("💡 The schemas/ directory will be created automatically when you save your first schema.")
                elif not os.access(schemas_dir, os.R_OK):
                    Notify.warn("⚠️ Cannot read the schemas/ directory. Check permissions.")
                elif not os.access(schemas_dir, os.W_OK):
                    Notify.warn("⚠️ Cannot write to the schemas/ directory. You may not be able to save schemas.")
            else:
                # Display file table with enhanced styling
                st.subheader(f"📄 Schema Files ({len(schema_files)} found)")
                
                # Add search/filter functionality for large lists
                if len(schema_files) > 5:
                    search_term = st.text_input("🔍 Search schemas", 
                                              placeholder="Type to filter schemas...",
                                              help="Filter schemas by filename")
                    if search_term:
                        schema_files = [f for f in schema_files 
                                      if search_term.lower() in f['filename'].lower()]
                
                # Create responsive table data for display
                for i, file_info in enumerate(schema_files):
                    with st.container():
                        # Use responsive columns that adapt to screen size
                        if st.session_state.get('mobile_view', False):
                            # Mobile-friendly stacked layout
                            st.markdown(f"**{file_info['filename']}**")
                            col1, col2 = st.columns(2)
                            with col1:
                                status_icon = "✅ Valid" if file_info['is_valid'] else "❌ Invalid"
                                st.caption(f"{status_icon} • {file_info['field_count']} fields")
                            with col2:
                                modified_str = file_info['modified'].strftime("%m/%d %H:%M")
                                size_kb = file_info['size'] / 1024
                                size_str = f"{size_kb:.1f}KB" if size_kb >= 1 else f"{file_info['size']}B"
                                st.caption(f"📅 {modified_str} • 📊 {size_str}")
                        else:
                            # Desktop layout with full columns
                            col1, col2, col3, col4, col5 = st.columns([3, 2, 1, 1, 2])
                            
                            with col1:
                                # File name with enhanced status indicator
                                status_icon = "✅" if file_info['is_valid'] else "❌"
                                status_tooltip = "Schema is valid" if file_info['is_valid'] else "Schema has validation errors"
                                st.write(f"{status_icon} **{file_info['filename']}**")
                                if not file_info['is_valid']:
                                    st.caption("⚠️ Contains validation errors")
                                
                            with col2:
                                # Last modified date with relative time
                                modified_str = file_info['modified'].strftime("%Y-%m-%d %H:%M")
                                st.write(f"📅 {modified_str}")
                                
                            with col3:
                                # File size with better formatting
                                size_kb = file_info['size'] / 1024
                                if size_kb < 1:
                                    size_str = f"{file_info['size']}B"
                                elif size_kb < 1024:
                                    size_str = f"{size_kb:.1f}KB"
                                else:
                                    size_str = f"{size_kb/1024:.1f}MB"
                                st.write(f"📊 {size_str}")
                                
                            with col4:
                                # Field count with color coding
                                field_count = file_info['field_count']
                                if field_count == 0:
                                    st.write("🏷️ No fields")
                                elif field_count == 1:
                                    st.write("🏷️ 1 field")
                                else:
                                    st.write(f"🏷️ {field_count} fields")
                                
                            with col5:
                                # Enhanced action buttons with better tooltips
                                button_col1, button_col2, button_col3 = st.columns(3)
                                
                                with button_col1:
                                    if st.button("✏️", key=f"edit_{i}",
                                                help="Edit this schema",
                                                width='stretch'):
                                        st.session_state.schema_editor_active_file = file_info['path']
                                        st.session_state.schema_editor_initialized = False
                                        st.session_state.schema_editor_mode = 'edit'
                                        st.rerun()
                                
                                with button_col2:
                                    if st.button("📋", key=f"duplicate_{i}", 
                                                help="Create a copy of this schema",
                                                width='stretch'):
                                        st.session_state.schema_editor_pending_duplicate = file_info['path']
                                        st.rerun()
                                
                                with button_col3:
                                    if st.button("🗑️", key=f"delete_{i}",
                                                help="Delete this schema",
                                                width='stretch'):
                                        st.session_state.schema_editor_pending_delete = file_info['path']
                                        st.rerun()
                        
                        # Add separator line with better styling
                        if i < len(schema_files) - 1:
                            st.divider()
                            
        except Exception as e:
            logger.error(f"Error rendering schema list: {e}", exc_info=True)
            Notify.error(f"Error loading schema files: {str(e)}")
            Notify.info("Please check that the schemas/ directory exists and is accessible.")
    
    @staticmethod
    def _render_editor_view() -> None:
        """Render the schema editing interface with error handling."""
        SchemaEditor._handle_pending_operations()
        try:
            # Handle pending operations in editor view
            
            # Keyboard shortcuts disabled for editor view
            
            # Check if Save As dialog should be shown
            if st.session_state.get('schema_editor_show_save_as', False):
                SchemaEditor._handle_save_as_dialog()
                return
            
            # Load schema data if editing existing file
            schema_data = SchemaEditor._load_editor_schema()
            
            if schema_data is None:
                Notify.error("Error Loading Schema")
                st.error("❌ **Error Loading Schema**")
                st.error("Could not load the schema data for editing.")
                st.info("**Recovery Options:**")
                st.info("• Return to the file list and try again")
                st.info("• Check that the schema file exists and is readable")
                st.info("• Create a new schema instead")
                
                if st.button("← Back to List", key="error_back_to_list"):
                    st.session_state.schema_editor_mode = 'list'
                    st.rerun()
                return
            
            # Header with filename and unsaved indicator
            SchemaEditor._render_editor_header(schema_data)
            
            # Schema metadata inputs (title, description)
            SchemaEditor._render_schema_metadata(schema_data)
            
            st.divider()
            
            # Main content area for field list and editors
            SchemaEditor._render_field_management_area(schema_data)
            
            # Check for pending field delete after rendering
            if st.session_state.get('schema_editor_pending_field_delete') is not None:
                logger.debug(f"Pending field delete detected in editor view but not handled: {st.session_state.schema_editor_pending_field_delete}")
            
        except Exception as e:
            logger.error(f"Error rendering editor view: {e}", exc_info=True)
            Notify.error("Editor Error in Schema Editor")
            st.error("❌ **Editor Error**")
            st.error("An error occurred while rendering the schema editor.")
            st.error(f"**Technical Details:** {str(e)}")
            st.info("**Recovery Options:**")
            st.info("• Return to the file list")
            st.info("• Refresh the page")
            st.info("• Try editing a different schema")
            
            if st.button("← Back to List", key="editor_error_back_to_list"):
                SchemaEditor._reset_to_safe_state()
                st.rerun()
    
    @staticmethod
    def _handle_schema_import(uploaded_file) -> None:
        """
        Handle schema import with comprehensive validation and error handling.
        
        Args:
            uploaded_file: Streamlit uploaded file object
        """
        # UserFeedback import removed - using Notify instead
        
        try:
            # Validate file size (max 5MB for schema files)
            file_size_mb = len(uploaded_file.getvalue()) / (1024 * 1024)
            if file_size_mb > 5:
                Notify.error(f"File too large: {file_size_mb:.1f}MB (max: 5MB)")
                st.info("Schema files should typically be much smaller. Please check your file.")
                return
            
            # Read and decode file content with error handling
            try:
                file_content = uploaded_file.getvalue().decode('utf-8')
            except UnicodeDecodeError as e:
                Notify.error("File encoding error: Unable to read file as UTF-8")
                st.info("Please ensure your YAML file is saved with UTF-8 encoding.")
                return
            
            # Parse YAML with detailed error reporting
            try:
                imported_schema = yaml.safe_load(file_content)
            except yaml.YAMLError as e:
                Notify.error("YAML Parsing Error")
                st.error(f"**Details:** {str(e)}")
                st.info("**Common YAML issues:**")
                st.info("• Check indentation (use spaces, not tabs)")
                st.info("• Ensure proper quoting of special characters")
                st.info("• Verify all brackets and braces are balanced")
                st.info("• Check for trailing spaces or invisible characters")
                return
            except Exception as e:
                logger.error(f"Unexpected YAML parsing error: {e}", exc_info=True)
                Notify.error(f"Unexpected parsing error: {str(e)}")
                return
            
            # Validate that we got a dictionary
            if not isinstance(imported_schema, dict):
                Notify.error("Invalid schema format: Root element must be a dictionary/object")
                st.info("Expected format: A YAML object with 'title', 'description', and 'fields' properties.")
                return
            
            # Comprehensive schema validation with detailed feedback
            is_valid, validation_errors, warnings = SchemaEditor._validate_imported_schema(imported_schema)
            
            # Show warnings for nested fields or unsupported features
            if warnings:
                Notify.warn("Import Warnings")
                st.warning("⚠️ **Import Warnings:**")
                for warning in warnings:
                    st.warning(f"  • {warning}")
                st.info("The schema will be imported but some features may not be editable in this version.")
            
            if is_valid:
                # Filter out unsupported fields before importing
                filtered_schema = SchemaEditor._filter_unsupported_fields(imported_schema)
                
                # Store filtered schema in session state for editing
                st.session_state.schema_editor_imported_schema = filtered_schema
                st.session_state.schema_editor_active_file = None  # New file
                st.session_state.schema_editor_initialized = False
                st.session_state.schema_editor_mode = 'edit'
                
                # Show success message with import summary
                field_count = len(filtered_schema.get('fields', {}))
                Notify.success(f"Successfully imported schema: {uploaded_file.name}")
                st.info(f"**Import Summary:**")
                st.info(f"  • Fields imported: {field_count}")
                st.info(f"  • File size: {file_size_mb:.1f}MB")
                if warnings:
                    st.info(f"  • Warnings: {len(warnings)} (see above)")
                
                st.rerun()
            else:
                Notify.error("Import Failed - Schema Validation Errors")
                st.error("❌ **Import Failed - Schema Validation Errors:**")
                for error in validation_errors:
                    st.error(f"  • {error}")
                st.info("**Recovery Options:**")
                st.info("• Fix the validation errors in your YAML file")
                st.info("• Use a schema validation tool to check your YAML")
                st.info("• Start with a simple schema and add complexity gradually")
                st.info("• Check the Schema Guide for supported field types and properties")
                
        except Exception as e:
            logger.error(f"Unexpected error during schema import: {e}", exc_info=True)
            Notify.error("Unexpected import error occurred")
            st.error(f"**Technical Details:** {str(e)}")
            st.info("**Recovery Options:**")
            st.info("• Try refreshing the page and importing again")
            st.info("• Check that your file is a valid YAML schema")
            st.info("• Contact support if the problem persists")
    
    @staticmethod
    def _validate_imported_schema(schema: Dict[str, Any]) -> Tuple[bool, List[str], List[str]]:
        """
        Validate imported schema and return detailed results.
        
        Args:
            schema: Imported schema dictionary
            
        Returns:
            Tuple of (is_valid, errors, warnings)
        """
        errors = []
        warnings = []
        
        try:
            # Basic structure validation
            is_valid, validation_errors = validate_schema_structure(schema)
            errors.extend(validation_errors)
            
            # Check for nested fields (arrays/objects) and warn about them
            fields = schema.get('fields', {})
            for field_name, field_config in fields.items():
                field_type = field_config.get('type', 'string')
                
                # Warn about unsupported field types
                if field_type == 'object':
                    warnings.append(f"Field '{field_name}' has type '{field_type}' which is not yet supported in the editor")
                elif field_type == 'array':
                    # Validate array field configuration
                    array_errors = SchemaEditor._validate_imported_array_field(field_name, field_config)
                    errors.extend(array_errors)
                elif field_type not in ['string', 'integer', 'number', 'float', 'boolean', 'enum', 'date', 'datetime']:
                    warnings.append(f"Field '{field_name}' has unknown type '{field_type}' - will be converted to 'string'")
                
                # Check for nested properties that indicate complex structures (but not for arrays)
                if isinstance(field_config, dict) and field_type != 'array':
                    if 'properties' in field_config:
                        warnings.append(f"Field '{field_name}' has nested properties which will be ignored")
                    if 'items' in field_config:
                        warnings.append(f"Field '{field_name}' has array items definition which will be ignored")
            
            # Check for unsupported top-level properties
            unsupported_props = set(schema.keys()) - {'title', 'description', 'fields'}
            if unsupported_props:
                for prop in unsupported_props:
                    warnings.append(f"Top-level property '{prop}' is not supported and will be ignored")
            
            return is_valid, errors, warnings
            
        except Exception as e:
            logger.error(f"Error validating imported schema: {e}", exc_info=True)
            errors.append(f"Validation error: {str(e)}")
            return False, errors, warnings
    
    @staticmethod
    def _validate_imported_array_field(field_name: str, field_config: Dict[str, Any]) -> List[str]:
        """
        Validate imported array field configuration.
        
        Args:
            field_name: Name of the array field
            field_config: Field configuration dictionary
            
        Returns:
            List of validation error messages
        """
        errors = []
        
        try:
            # Use ArrayFieldManager validation
            validation_errors = ArrayFieldManager.validate_array_config(field_config)
            
            # Prefix errors with field name for context
            for error in validation_errors:
                errors.append(f"Array field '{field_name}': {error}")
            
        except Exception as e:
            logger.error(f"Error validating imported array field {field_name}: {e}", exc_info=True)
            errors.append(f"Array field '{field_name}': Validation error - {str(e)}")
        
        return errors
    
    @staticmethod
    def _filter_unsupported_fields(schema: Dict[str, Any]) -> Dict[str, Any]:
        """
        Filter out unsupported fields and properties from imported schema.
        
        Args:
            schema: Original schema dictionary
            
        Returns:
            Filtered schema dictionary with only supported features
        """
        try:
            # Create filtered schema with only supported top-level properties
            filtered_schema = {
                'title': schema.get('title', ''),
                'description': schema.get('description', ''),
                'fields': {}
            }
            
            # Process fields
            original_fields = schema.get('fields', {})
            supported_types = ['string', 'integer', 'number', 'float', 'boolean', 'enum', 'date', 'datetime', 'array']
            
            for field_name, field_config in original_fields.items():
                if not isinstance(field_config, dict):
                    continue
                
                field_type = field_config.get('type', 'string')
                
                # Convert unsupported types to string
                if field_type not in supported_types:
                    field_type = 'string'
                
                # Create filtered field config with only supported properties
                filtered_field = {
                    'type': field_type,
                    'label': field_config.get('label', field_name.replace('_', ' ').title()),
                    'required': field_config.get('required', False),
                    'help': field_config.get('help', ''),
                }
                
                # Add type-specific properties
                if field_type == 'string':
                    if 'min_length' in field_config:
                        filtered_field['min_length'] = field_config['min_length']
                    if 'max_length' in field_config:
                        filtered_field['max_length'] = field_config['max_length']
                    if 'pattern' in field_config:
                        filtered_field['pattern'] = field_config['pattern']
                    if 'default' in field_config:
                        filtered_field['default'] = field_config['default']
                
                elif field_type in ['integer', 'number', 'float']:
                    if 'min_value' in field_config:
                        filtered_field['min_value'] = field_config['min_value']
                    if 'max_value' in field_config:
                        filtered_field['max_value'] = field_config['max_value']
                    if 'step' in field_config:
                        filtered_field['step'] = field_config['step']
                    if 'default' in field_config:
                        filtered_field['default'] = field_config['default']
                
                elif field_type == 'enum':
                    if 'choices' in field_config:
                        filtered_field['choices'] = field_config['choices']
                    if 'default' in field_config:
                        filtered_field['default'] = field_config['default']
                
                elif field_type == 'boolean':
                    if 'default' in field_config:
                        filtered_field['default'] = field_config['default']
                
                elif field_type == 'array':
                    # Handle array field import
                    if 'items' in field_config:
                        filtered_field['items'] = SchemaEditor._filter_array_items_config(field_config['items'])
                
                # Add readonly property if present
                if 'readonly' in field_config:
                    filtered_field['readonly'] = field_config['readonly']
                
                # Clean None values
                filtered_field = {k: v for k, v in filtered_field.items() if v is not None and v != ''}
                
                filtered_schema['fields'][field_name] = filtered_field
            
            return filtered_schema
            
        except Exception as e:
            logger.error(f"Error filtering schema: {e}", exc_info=True)
            # Return original schema if filtering fails
            return schema
    
    @staticmethod
    def _filter_array_items_config(items_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Filter array items configuration to include only supported properties.
        
        Args:
            items_config: Original items configuration
            
        Returns:
            Filtered items configuration
        """
        try:
            item_type = items_config.get('type', 'string')
            filtered_items = {'type': item_type}
            
            if item_type == 'object':
                # Handle object array items
                if 'properties' in items_config:
                    filtered_items['properties'] = {}
                    properties = items_config['properties']
                    
                    for prop_name, prop_config in properties.items():
                        if isinstance(prop_config, dict):
                            prop_type = prop_config.get('type', 'string')
                            
                            filtered_prop = {
                                'type': prop_type,
                                'label': prop_config.get('label', prop_name.replace('_', ' ').title()),
                                'required': prop_config.get('required', False)
                            }
                            
                            # Add type-specific properties for object properties
                            if prop_type == 'string':
                                for key in ['min_length', 'max_length', 'pattern']:
                                    if key in prop_config:
                                        filtered_prop[key] = prop_config[key]
                            elif prop_type in ['integer', 'number']:
                                for key in ['min_value', 'max_value', 'step']:
                                    if key in prop_config:
                                        filtered_prop[key] = prop_config[key]
                            elif prop_type == 'enum':
                                if 'choices' in prop_config:
                                    filtered_prop['choices'] = prop_config['choices']
                                if 'default' in prop_config:
                                    filtered_prop['default'] = prop_config['default']
                            elif prop_type == 'boolean':
                                if 'default' in prop_config:
                                    filtered_prop['default'] = prop_config['default']
                            
                            # Clean None values
                            filtered_prop = {k: v for k, v in filtered_prop.items() if v is not None and v != ''}
                            filtered_items['properties'][prop_name] = filtered_prop
            
            else:
                # Handle scalar array items
                if item_type == 'string':
                    for key in ['min_length', 'max_length', 'pattern']:
                        if key in items_config:
                            filtered_items[key] = items_config[key]
                elif item_type in ['integer', 'number']:
                    for key in ['min_value', 'max_value', 'step']:
                        if key in items_config:
                            filtered_items[key] = items_config[key]
                elif item_type == 'enum':
                    if 'choices' in items_config:
                        filtered_items['choices'] = items_config['choices']
                    if 'default' in items_config:
                        filtered_items['default'] = items_config['default']
                elif item_type == 'boolean':
                    if 'default' in items_config:
                        filtered_items['default'] = items_config['default']
            
            return filtered_items
            
        except Exception as e:
            logger.error(f"Error filtering array items config: {e}", exc_info=True)
            # Return basic config if filtering fails
            return {'type': items_config.get('type', 'string')}
    
    @staticmethod
    def _initialize_session_state() -> None:
        """Initialize session state variables for schema editor."""
        # Diagnostic toggle (default off)
        if 'schema_editor_diagnostic_mode' not in st.session_state:
            st.session_state.schema_editor_diagnostic_mode = False
        diag_mode = st.session_state.schema_editor_diagnostic_mode
        if diag_mode:
            logger.info("SchemaEditor: diagnostic mode enabled")
        # Navigation state
        if 'schema_editor_mode' not in st.session_state:
            st.session_state.schema_editor_mode = 'list'
            if diag_mode:
                logger.debug("_initialize_session_state: initialized schema_editor_mode='list'")
        
        if 'schema_editor_active_file' not in st.session_state:
            st.session_state.schema_editor_active_file = None
        
        # Editor state
        if 'schema_editor_fields' not in st.session_state:
            st.session_state.schema_editor_fields = []
        
        if 'schema_editor_errors' not in st.session_state:
            st.session_state.schema_editor_errors = []
        
        if 'schema_editor_unsaved' not in st.session_state:
            st.session_state.schema_editor_unsaved = False
        
        # Schema metadata
        if 'schema_editor_title' not in st.session_state:
            st.session_state.schema_editor_title = ''
        
        if 'schema_editor_description' not in st.session_state:
            st.session_state.schema_editor_description = ''
        
        # Field management
        if 'schema_editor_field_counter' not in st.session_state:
            st.session_state.schema_editor_field_counter = 0
        
        if 'schema_editor_validation_results' not in st.session_state:
            st.session_state.schema_editor_validation_results = {}
        
        # Pending operations
        if 'schema_editor_pending_delete' not in st.session_state:
            st.session_state.schema_editor_pending_delete = None
        
        if 'schema_editor_pending_duplicate' not in st.session_state:
            st.session_state.schema_editor_pending_duplicate = None
        
        if 'schema_editor_pending_field_delete' not in st.session_state:
            st.session_state.schema_editor_pending_field_delete = None
        
        if 'schema_editor_pending_navigation' not in st.session_state:
            st.session_state.schema_editor_pending_navigation = None
        
        # Save As dialog
        if 'schema_editor_show_save_as' not in st.session_state:
            st.session_state.schema_editor_show_save_as = False
        
        # Schema initialization flag
        if 'schema_editor_initialized' not in st.session_state:
            st.session_state.schema_editor_initialized = False
            if diag_mode:
                logger.debug("_initialize_session_state: initialized schema_editor_initialized=False")
        # Dirty state initialization with logging
        if DIRTY_KEY not in st.session_state:
            st.session_state[DIRTY_KEY] = False
            if diag_mode:
                logger.debug(f"_initialize_session_state: initialized {DIRTY_KEY}=False")
        if LAST_SAVE_TS_KEY not in st.session_state:
            st.session_state[LAST_SAVE_TS_KEY] = None
            if diag_mode:
                logger.debug(f"_initialize_session_state: initialized {LAST_SAVE_TS_KEY}=None")
    
    @staticmethod
    def _load_editor_schema() -> Dict[str, Any]:
        """Load schema data for editing."""
        # Check if we have an imported schema in session state
        if 'schema_editor_imported_schema' in st.session_state:
            schema_data = st.session_state.schema_editor_imported_schema
            # Clear the imported schema from session state
            del st.session_state.schema_editor_imported_schema
            
            # Initialize editor state with imported data
            SchemaEditor._initialize_editor_from_schema(schema_data)
            return schema_data
        
        # Check if we're editing an existing file AND haven't initialized yet
        active_file = st.session_state.get('schema_editor_active_file')
        if active_file and not st.session_state.get('schema_editor_initialized', False):
            schema_data = load_schema(active_file)
            if schema_data:
                logger.debug(f"_load_editor_schema: loading existing file '{active_file}', calling _initialize_editor_from_schema")
                # Initialize editor state with loaded data
                SchemaEditor._initialize_editor_from_schema(schema_data)
                # Mark as initialized to prevent reloading on every rerun
                st.session_state.schema_editor_initialized = True
                logger.debug(f"_load_editor_schema: initialization complete for '{active_file}'; dirty={st.session_state.get(DIRTY_KEY, False)}")
                return schema_data
        
        # Build schema from current session state (for existing sessions)
        if st.session_state.get('schema_editor_initialized', False):
            return SchemaEditor._build_schema_from_session()
        
        # Return empty schema for new files
        return {
            'title': '',
            'description': '',
            'fields': {}
        }
    
    @staticmethod
    def _initialize_editor_from_schema(schema_data: Dict[str, Any]) -> None:
        """Initialize editor session state from schema data."""
        import uuid

        # Convert schema fields to editor format with UUIDs
        editor_fields = []
        fields = schema_data.get('fields', {})

        for field_name, field_config in fields.items():
            editor_field = {
                'id': str(uuid.uuid4()),  # Unique ID for UI stability
                'name': field_name,
                **field_config  # Include all field configuration
            }
            editor_fields.append(editor_field)

        # Store in session state
        st.session_state.schema_editor_fields = editor_fields
        st.session_state.schema_editor_title = schema_data.get('title', '')
        st.session_state.schema_editor_description = schema_data.get('description', '')

        # Initialize clean state WITHOUT calling _mark_clean() to avoid "All changes saved" banner
        # This prevents the misleading UX where opening a schema shows it as "already saved"
        st.session_state[DIRTY_KEY] = False
        st.session_state[LAST_SAVE_TS_KEY] = None  # Don't set timestamp on load - only on actual saves
        st.session_state.schema_editor_unsaved = False

        logger.debug(f"_initialize_editor_from_schema: initialized schema with {len(editor_fields)} fields, title='{schema_data.get('title', 'Untitled')}' (without calling _mark_clean)")
        logger.debug(f"_initialize_editor_from_schema: set dirty=False, last_save=None to avoid immediate 'saved' banner")
    
    @staticmethod
    def _render_editor_header(schema_data: Dict[str, Any]) -> None:
        """Render editor header with enhanced UI polish."""
        # Keyboard shortcuts info (disabled)
        
        # Create responsive header columns
        col1, col2, col3 = st.columns([3, 1, 1])
        
        with col1:
            # Show filename or "New Schema" with enhanced styling
            active_file = st.session_state.get('schema_editor_active_file')
            if active_file:
                filename = Path(active_file).name
                st.header(f"✏️ Editing: {filename}")
                st.caption(f"📁 Path: {active_file}")
            else:
                st.header("✏️ New Schema")
                st.caption("💡 Remember to save your schema when finished")
        
        with col2:
            # Diagnostic mode toggle (hidden by default, can be enabled via session state or UI)
            diag_mode = st.session_state.get('schema_editor_diagnostic_mode', False)
            new_diag_mode = st.checkbox("🔧 Diagnostic Mode (Advanced)", value=diag_mode, key="diag_toggle",
                                        help="Enable detailed logging for troubleshooting. Check console/logs for output.")
            if new_diag_mode != diag_mode:
                st.session_state.schema_editor_diagnostic_mode = new_diag_mode
                if new_diag_mode:
                    logger.info("Diagnostic mode enabled via UI toggle")
                else:
                    logger.info("Diagnostic mode disabled via UI toggle")
                st.rerun()

            # Enhanced unsaved changes indicator with tooltip.
            # Prefer a single canonical dirty flag (DIRTY_KEY) but fall back to
            # the existing schema_editor_unsaved key for backwards compatibility.
            dirty = st.session_state.get(DIRTY_KEY, st.session_state.get('schema_editor_unsaved', False))
            ts = st.session_state.get(LAST_SAVE_TS_KEY, None)
            # Log the dirty value read and banner decision for diagnostics
            try:
                active_file = st.session_state.get('schema_editor_active_file')
                logger.debug(f"_render_editor_header: dirty={dirty}, last_save_ts={ts}, active_file={active_file}; deciding banner")
            except Exception as _e:
                logger.debug(f"_render_editor_header: dirty={dirty}, last_save_ts={ts} (failed to read active_file: {_e}); deciding banner")
            if dirty:
                logger.debug("_render_editor_header: showing Unsaved banner because dirty==True")
                st.warning("⚠️ Unsaved")
                st.caption("Changes not saved")
            else:
                logger.debug("_render_editor_header: showing banner (dirty==False); ts={ts}")
                if ts:
                    # Show saved banner with timestamp when actually saved
                    st.info(f"✅ Saved • Last saved: {ts}")
                else:
                    # Show no banner when schema is loaded but never saved
                    # This prevents the misleading "All changes saved" on initial load
                    pass  # No banner shown for loaded schemas
        
        with col3:
            # Back to list button with enhanced tooltip
            if st.button("← Back to List", key="back_to_list",
                        help="Return to schema list. Will prompt if unsaved changes exist.",
                        width='stretch'):
                SchemaEditor._handle_back_to_list()
        
        # Enhanced save and export buttons with better layout
        st.divider()
        col1, col2, col3, col4, col5 = st.columns([1, 1, 1, 1, 1])
        
        with col1:
            can_save = SchemaEditor._can_save_schema()
            save_tooltip = "Save current schema" if can_save else "Fix validation errors before saving"
            if st.button("💾 Save", type="primary", key="save_schema",
                        disabled=not can_save,
                        help=save_tooltip,
                        width='stretch'):
                SchemaEditor._save_current_schema()
        
        with col2:
            if st.button("💾 Save As...", key="save_as_schema",
                        help="Save schema with a new name",
                        width='stretch'):
                SchemaEditor._show_save_as_dialog()
        
        with col3:
            if st.button("📤 Export", key="export_schema",
                        help="Download schema as YAML file",
                        width='stretch'):
                SchemaEditor._export_current_schema()
        
        with col4:
            # Enhanced validation status with detailed tooltip
            validation_results = st.session_state.get('schema_editor_validation_results', {})
            if validation_results.get('errors'):
                error_count = len(validation_results['errors'])
                st.error(f"❌ {error_count} error{'s' if error_count != 1 else ''}")
                st.caption("Click Validate for details")
            else:
                st.success("✅ Valid")
                st.caption("Schema is valid")
        
    
    @staticmethod
    def _render_schema_metadata(schema_data: Dict[str, Any]) -> None:
        """Render schema metadata inputs with enhanced UI polish."""
        st.subheader("📝 Schema Information")
        
        # Initialize session state values if not present
        if 'schema_editor_title' not in st.session_state:
            st.session_state.schema_editor_title = schema_data.get('title', '')
        if 'schema_editor_description' not in st.session_state:
            st.session_state.schema_editor_description = schema_data.get('description', '')
        
        # Enhanced responsive layout for metadata
        col1, col2 = st.columns([2, 1])
        
        with col1:
            # Title input with enhanced help
            new_title = st.text_input(
                "Schema Title",
                value=st.session_state.schema_editor_title,
                help="A descriptive title for this schema. This will be displayed in forms and documentation.",
                placeholder="e.g., Customer Information Schema",
                key="schema_title_input"
            )
            
            # Description input with enhanced help
            new_description = st.text_area(
                "Schema Description",
                value=st.session_state.schema_editor_description,
                help="Brief description of what this schema validates. Explain the purpose and context.",
                placeholder="e.g., Validates customer contact information including name, email, and address fields.",
                height=100,
                key="schema_description_input"
            )
        
        with col2:
            # Metadata statistics and tips
            st.markdown("**📊 Schema Stats**")
            field_count = len(st.session_state.get('schema_editor_fields', []))
            required_count = sum(1 for f in st.session_state.get('schema_editor_fields', []) 
                               if f.get('required', False))
            
            st.metric("Total Fields", field_count)
            st.metric("Required Fields", required_count)
            
            # Quick tips
            with st.expander("💡 Tips", expanded=False):
                st.markdown("""
                **Good Schema Titles:**
                - Be descriptive and specific
                - Use title case
                - Keep under 50 characters
                
                **Good Descriptions:**
                - Explain the purpose
                - Mention key field types
                - Note any special requirements
                """)
        
        # Update session state and mark as unsaved if changed
        if new_title != st.session_state.schema_editor_title:
            st.session_state.schema_editor_title = new_title
            _mark_dirty()
        
        if new_description != st.session_state.schema_editor_description:
            st.session_state.schema_editor_description = new_description
            _mark_dirty()
    
    @staticmethod
    def _render_field_management_area(schema_data: Dict[str, Any]) -> None:
        """Render main content area for field list and editors with enhanced UI."""
        st.subheader("🏷️ Schema Fields")
        
        # Initialize fields in session state if not present
        if 'schema_editor_fields' not in st.session_state:
            st.session_state.schema_editor_fields = []
        
        # Show validation summary at the top
        SchemaEditor._show_validation_summary()
        
        # Enhanced field management buttons with better layout
        col1, col2, col3, col4 = st.columns([2, 1, 1, 1])
        
        with col1:
            if st.button("➕ Add Field", type="primary", key="add_field_btn",
                        help="Add a new field to the schema",
                        width='stretch'):
                SchemaEditor._add_new_field()
        
        with col2:
            field_count = len(st.session_state.schema_editor_fields)
            st.metric("Total Fields", field_count, 
                     help="Number of fields in this schema")
        
        with col3:
            if st.button("🔍 Validate", key="validate_schema_btn",
                        help="Run comprehensive validation",
                        width='stretch'):
                SchemaEditor._validate_current_schema()
                SchemaEditor._show_detailed_validation_feedback()
        
        with col4:
            # Field management options
            with st.popover("⚙️ Field Options", help="Field management tools"):
                if st.button("📋 Add Multiple Fields", key="add_multiple",
                           width='stretch'):
                    st.session_state.schema_editor_show_bulk_add = True
                    st.rerun()
                
                if st.button("🔄 Reorder Fields", key="reorder_fields",
                           width='stretch'):
                    st.session_state.schema_editor_show_reorder = True
                    st.rerun()
                
                if st.button("📊 Field Statistics", key="field_stats",
                           width='stretch'):
                    SchemaEditor._show_field_statistics()
        
        # Display fields with enhanced organization
        fields = st.session_state.schema_editor_fields
        
        if not fields:
            # Enhanced empty state with helpful guidance
            Notify.info("No fields defined yet. Click 'Add Field' to get started.")
            
            with st.expander("🚀 Quick Start Guide", expanded=True):
                st.markdown("""
                **Getting Started with Schema Fields:**
                
                1. **Click 'Add Field'** to create your first field
                2. **Choose a field type** (string, number, boolean, etc.)
                3. **Set field properties** like label, help text, and validation rules
                4. **Add more fields** as needed for your data structure
                5. **Validate and save** your schema when complete
                
                **Common Field Types:**
                - **String**: Text input (names, descriptions, IDs)
                - **Integer/Number**: Numeric values (ages, quantities, prices)
                - **Boolean**: Yes/No or True/False values
                - **Enum**: Dropdown with predefined choices
                - **Date/DateTime**: Date and time values
                """)
        else:
            # Field organization options
            if len(fields) > 3:
                col1, col2 = st.columns([1, 1])
                with col1:
                    show_collapsed = st.checkbox("🔽 Collapse All Fields", 
                                               help="Collapse all field editors for better overview")
                with col2:
                    field_filter = st.selectbox("🔍 Filter by Type", 
                                              options=["All Types"] + list(set(f.get('type', 'string') for f in fields)),
                                              help="Show only fields of selected type")
            
            # Render each field with enhanced styling
            for i, field in enumerate(fields):
                # Apply field filter if set
                if len(fields) > 3 and 'field_filter' in locals():
                    if field_filter != "All Types" and field.get('type', 'string') != field_filter:
                        continue
                
                # Pass collapse state to field renderer
                collapse_state = locals().get('show_collapsed', False) if len(fields) > 3 else False
                SchemaEditor._render_field_editor(i, field, collapsed=collapse_state)
    
    @staticmethod
    def _add_new_field() -> None:
        """Add a new field to the schema."""
        import uuid
        # UserFeedback import removed - using Notify instead
        
        try:
            # Ensure fields list exists
            if 'schema_editor_fields' not in st.session_state:
                st.session_state.schema_editor_fields = []
            
            # Generate unique field name
            field_counter = st.session_state.get('schema_editor_field_counter', 0) + 1
            st.session_state.schema_editor_field_counter = field_counter
            
            new_field = {
                'id': str(uuid.uuid4()),
                'name': f'field_{field_counter}',
                'type': 'string',
                'label': f'Field {field_counter}',
                'required': False,
                'help': ''
            }
            
            # Add the new field
            st.session_state.schema_editor_fields.append(new_field)
            _mark_dirty()
            
            # Show feedback
            Notify.success(f"Added field: {new_field['name']}")
            
            # Force rerun to refresh the interface
            st.rerun()
            
        except Exception as e:
            logger.error(f"Error adding new field: {e}", exc_info=True)
            Notify.error(f"Failed to add new field: {str(e)}")
    
    @staticmethod
    def _render_field_editor(index: int, field: Dict[str, Any], collapsed: bool = False) -> None:
        """Render editor for a single field with enhanced UI polish."""
        field_id = field['id']
        # Diagnostic logging to detect duplicate IDs and rendering paths\nlogger.debug(f\"editor_render_start: field_index={index} field_id={field_id} field_name={field.get('name')}\")\nids = [f.get('id') for f in st.session_state.get('schema_editor_fields', [])]\nlogger.debug(f\"editor_field_ids: {ids}\")\nlogger.debug(f\"editor_field_id_counts: {dict(collections.Counter(ids))}\")\n
        
        # Validate field in real-time
        field_errors = SchemaEditor._validate_field_real_time(index, field)
        
        # Create expandable container for field with enhanced indicators
        field_name = field.get('name', 'Unnamed Field')
        field_type = field.get('type', 'string')
        required_indicator = " 🔴" if field.get('required', False) else ""
        error_indicator = " ❌" if field_errors else " ✅"
        
        # Enhanced field header with more information
        field_header = f"🏷️ {field_name} ({field_type}){required_indicator}{error_indicator}"
        
        with st.expander(field_header, expanded=not collapsed):
            # Show inline field errors at the top with better formatting
            if field_errors:
                st.error("**⚠️ Field Validation Errors:**")
                for error in field_errors:
                    st.error(f"  • {error}")
                st.divider()
            
            # Enhanced field management buttons with better tooltips
            col1, col2, col3, col4, col5 = st.columns([1, 1, 1, 1, 2])
            
            with col1:
                if st.button("🔼", key=f"move_up_{field_id}",
                           help="Move field up in order",
                           disabled=(index == 0),
                           width='stretch'):
                    SchemaEditor._move_field_up(index)
            
            with col2:
                if st.button("🔽", key=f"move_down_{field_id}",
                           help="Move field down in order",
                           disabled=(index == len(st.session_state.schema_editor_fields) - 1),
                           width='stretch'):
                    SchemaEditor._move_field_down(index)
            
            with col3:
                if st.button("📋", key=f"duplicate_{field_id}", 
                           help="Duplicate this field",
                           width='stretch'):
                    SchemaEditor._duplicate_field(index)
            
            with col4:
                if st.button("🗑️", key=f"delete_{field_id}",
                           help="Delete this field",
                           width='stretch'):
                    SchemaEditor._delete_field(index)
            
            with col5:
                # Field position indicator
                total_fields = len(st.session_state.schema_editor_fields)
                st.caption(f"Position: {index + 1} of {total_fields}")
            
            # Enhanced basic field properties with responsive layout
            col1, col2 = st.columns([1, 1])
            
            with col1:
                new_name = st.text_input(
                    "Field Name",
                    value=field.get('name', ''),
                    key=f"name_{field_id}",
                    help="Internal field name (use snake_case). Must be unique within the schema.",
                    placeholder="e.g., customer_email"
                )
                
                # Enhanced field type selector with descriptions
                current_type = field.get('type', 'string')
                supported_types = ['string', 'integer', 'number', 'boolean', 'enum', 'date', 'datetime', 'array']
                type_descriptions = {
                    'string': 'Text input with optional validation',
                    'integer': 'Whole numbers only',
                    'number': 'Decimal numbers',
                    'boolean': 'True/False checkbox',
                    'enum': 'Dropdown with predefined choices',
                    'date': 'Date picker',
                    'datetime': 'Date and time picker',
                    'array': 'List of values (scalar or objects)'
                }
                
                # Handle unsupported types gracefully
                if current_type not in supported_types:
                    st.warning(f"⚠️ Field type '{current_type}' is not yet supported in this editor. Converting to 'string' for editing.")
                    current_type = 'string'
                
                new_type = st.selectbox(
                    "Field Type",
                    options=supported_types,
                    index=supported_types.index(current_type),
                    key=f"type_{field_id}",
                    help="Choose the data type for this field",
                    format_func=lambda x: f"{x} - {type_descriptions.get(x, '')}"
                )
            
            with col2:
                new_label = st.text_input(
                    "Display Label",
                    value=field.get('label', ''),
                    key=f"label_{field_id}",
                    help="User-friendly label shown in forms and documentation",
                    placeholder="e.g., Customer Email Address"
                )
                
                # Enhanced required checkbox with better explanation
                new_required = st.checkbox(
                    "Required Field",
                    value=field.get('required', False),
                    key=f"required_{field_id}",
                    help="If checked, users must provide a value for this field"
                )
                
                # Add readonly option
                new_readonly = st.checkbox(
                    "Read-only Field",
                    value=field.get('readonly', False),
                    key=f"readonly_{field_id}",
                    help="If checked, users cannot edit this field (display only)"
                )
            
            # Enhanced help text with character counter
            help_text = field.get('help', '')
            new_help = st.text_area(
                "Help Text",
                value=help_text,
                key=f"help_{field_id}",
                help="Optional help text shown to users. Keep it concise and helpful.",
                height=60,
                placeholder="e.g., Enter a valid email address for customer communications"
            )
            
            # Show character count for help text
            if new_help:
                help_length = len(new_help)
                if help_length > 200:
                    st.warning(f"Help text is {help_length} characters. Consider keeping it under 200 for better readability.")
                else:
                    st.caption(f"Help text: {help_length} characters")
            
            # Update field data if changed
            updated_field = {
                **field,
                'name': new_name,
                'type': new_type,
                'label': new_label,
                'required': new_required,
                'readonly': new_readonly,
                'help': new_help
            }
            
            # Check if field was modified and update validation
            if updated_field != field:
                st.session_state.schema_editor_fields[index] = updated_field
                _mark_dirty()
                # Update validation on change
                SchemaEditor._update_validation_on_change()
            
            # Type-specific field editors with enhanced UI
            SchemaEditor._render_type_specific_editor(field_id, updated_field)
    
    @staticmethod
    def _move_field_up(index: int) -> None:
        """Move field up in the list."""
        if index > 0:
            fields = st.session_state.schema_editor_fields
            fields[index], fields[index - 1] = fields[index - 1], fields[index]
            Notify.info("Moved field up")
            _mark_dirty()
            st.rerun()
            fields[index], fields[index - 1] = fields[index - 1], fields[index]
            Notify.info("Moved field up")
            _mark_dirty()
            st.rerun()
    
    @staticmethod
    def _move_field_down(index: int) -> None:
        """Move field down in the list."""
        fields = st.session_state.schema_editor_fields
        if index < len(fields) - 1:
            fields[index], fields[index + 1] = fields[index + 1], fields[index]
            _mark_dirty()
            st.rerun()
    
    @staticmethod
    def _delete_field(index: int) -> None:
        """Delete field with confirmation."""
        # Store the field index to delete in session state for confirmation
        st.session_state.schema_editor_pending_field_delete = index
        st.rerun()
    
    @staticmethod
    def _duplicate_field(index: int) -> None:
        """Duplicate an existing field."""
        import uuid
        # UserFeedback import removed - using Notify instead
        
        try:
            fields = st.session_state.schema_editor_fields
            if 0 <= index < len(fields):
                original_field = fields[index]
                
                # Create a copy with new ID and modified name
                field_counter = st.session_state.get('schema_editor_field_counter', 0) + 1
                st.session_state.schema_editor_field_counter = field_counter
                
                duplicated_field = {
                    **original_field,
                    'id': str(uuid.uuid4()),
                    'name': f"{original_field['name']}_copy_{field_counter}",
                    'label': f"{original_field.get('label', '')} (Copy)"
                }
                
                # Insert the duplicated field right after the original
                fields.insert(index + 1, duplicated_field)
                _mark_dirty()
                
                Notify.success(f"Duplicated field: {original_field['name']}")
                st.rerun()
                
        except Exception as e:
            logger.error(f"Error duplicating field: {e}", exc_info=True)
            Notify.error(f"Failed to duplicate field: {str(e)}")
    
    @staticmethod
    def _show_field_statistics() -> None:
        """Show detailed field statistics in a modal."""
        fields = st.session_state.get('schema_editor_fields', [])
        
        if not fields:
            st.info("No fields to analyze.")
            return
        
        # Calculate statistics
        total_fields = len(fields)
        required_fields = sum(1 for f in fields if f.get('required', False))
        readonly_fields = sum(1 for f in fields if f.get('readonly', False))
        
        # Field type distribution
        type_counts = {}
        for field in fields:
            field_type = field.get('type', 'string')
            type_counts[field_type] = type_counts.get(field_type, 0) + 1
        
        # Fields with validation rules
        fields_with_patterns = sum(1 for f in fields if f.get('pattern'))
        fields_with_length_limits = sum(1 for f in fields if f.get('min_length') or f.get('max_length'))
        fields_with_numeric_limits = sum(1 for f in fields if f.get('min_value') is not None or f.get('max_value') is not None)
        fields_with_defaults = sum(1 for f in fields if 'default' in f)
        
        # Display statistics
        st.markdown("### 📊 Field Statistics")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Fields", total_fields)
            st.metric("Required Fields", required_fields, f"{required_fields/total_fields*100:.1f}%")
        
        with col2:
            st.metric("Read-only Fields", readonly_fields, f"{readonly_fields/total_fields*100:.1f}%")
            st.metric("Fields with Defaults", fields_with_defaults)
        
        with col3:
            st.metric("With Validation", fields_with_patterns + fields_with_length_limits + fields_with_numeric_limits)
        
        # Field type distribution
        st.markdown("### 🏷️ Field Type Distribution")
        for field_type, count in sorted(type_counts.items()):
            percentage = count / total_fields * 100
            st.write(f"**{field_type}**: {count} fields ({percentage:.1f}%)")
        
        # Validation statistics
        if any([fields_with_patterns, fields_with_length_limits, fields_with_numeric_limits]):
            st.markdown("### ✅ Validation Rules")
            if fields_with_patterns:
                st.write(f"**Pattern validation**: {fields_with_patterns} fields")
            if fields_with_length_limits:
                st.write(f"**Length limits**: {fields_with_length_limits} fields")
            if fields_with_numeric_limits:
                st.write(f"**Numeric limits**: {fields_with_numeric_limits} fields")
    
    @staticmethod
    def _validate_current_schema() -> None:
        """Validate the current schema and show results."""
        diag_mode = st.session_state.get('schema_editor_diagnostic_mode', False)
        # Build schema from current session state
        schema_dict = SchemaEditor._build_schema_from_session()
        if diag_mode:
            logger.debug(f"_validate_current_schema: built schema with {len(schema_dict.get('fields', {}))} fields, title='{schema_dict.get('title', 'Untitled')}'")
        
        # Validate schema
        if diag_mode:
            logger.debug(f"_validate_current_schema: starting validation on schema with {len(schema_dict.get('fields', {}))} fields")
        is_valid, errors = validate_schema_structure(schema_dict)
        if diag_mode:
            logger.debug(f"_validate_current_schema: validation complete; is_valid={is_valid}, errors={len(errors)}")
        
        # Store validation results in session state
        st.session_state.schema_editor_validation_results = {
            'is_valid': is_valid,
            'errors': errors,
            'last_validated': datetime.now()
        }
        
        # Display validation summary using Notify
        if not is_valid:
            Notify.error("Schema validation failed")
            for error in errors:
                st.error(f"  • {error}")
    
    @staticmethod
    def _validate_field_real_time(field_index: int, field: Dict[str, Any]) -> List[str]:
        """
        Validate a single field in real-time and return errors.
        
        Args:
            field_index: Index of the field in the fields list
            field: Field configuration dictionary
            
        Returns:
            List of validation errors for this field
        """
        field_name = field.get('name', f'field_{field_index}')
        
        # Validate field configuration
        field_errors = validate_field(field_name, field)
        
        # Check for duplicate field names
        if field_name:
            fields = st.session_state.get('schema_editor_fields', [])
            duplicate_count = sum(1 for f in fields if f.get('name') == field_name)
            if duplicate_count > 1:
                field_errors.append(f"Field name '{field_name}' is used multiple times")
        
        return field_errors
    
    @staticmethod
    def _show_validation_summary() -> None:
        """Show validation summary at the top of the editor."""
        # Get current validation results
        validation_results = st.session_state.get('schema_editor_validation_results', {})
        
        if not validation_results:
            return
        
        errors = validation_results.get('errors', [])
        is_valid = validation_results.get('is_valid', True)
        
        if errors:
            # Show validation summary with expandable details
            with st.expander("❌ Validation Issues Found", expanded=True):
                st.error(f"Found {len(errors)} validation error(s):")
                for error in errors:
                    st.error(f"  • {error}")
                st.info("💡 Fix these issues before saving the schema.")
        elif is_valid:
            st.success("✅ Schema validation passed - ready to save!")
    
    @staticmethod
    def _update_validation_on_change() -> None:
        """Update validation results when fields change."""
        # Build current schema
        schema_dict = SchemaEditor._build_schema_from_session()
        
        # Run validation
        is_valid, errors = validate_schema_structure(schema_dict)
        
        # Update session state
        st.session_state.schema_editor_validation_results = {
            'is_valid': is_valid,
            'errors': errors,
            'last_validated': datetime.now()
        }
    
    @staticmethod
    def _can_save_schema() -> bool:
        """Check if schema can be saved (no validation errors)."""
        # Run validation if not already done
        if 'schema_editor_validation_results' not in st.session_state:
            SchemaEditor._validate_current_schema()
        
        validation_results = st.session_state.get('schema_editor_validation_results', {})
        errors = validation_results.get('errors', [])
        
        # Schema can be saved if there are no validation errors
        return len(errors) == 0
    
    @staticmethod
    def _build_schema_from_session() -> Dict[str, Any]:
        """Build schema dictionary from current session state."""
        schema_dict = {
            'title': st.session_state.get('schema_editor_title', ''),
            'description': st.session_state.get('schema_editor_description', ''),
            'fields': {}
        }
        
        # Add fields
        for field in st.session_state.get('schema_editor_fields', []):
            field_name = field.get('name', '')
            if field_name:
                # Create field config without the internal 'id'
                field_config = {k: v for k, v in field.items() if k not in ['id', 'name']}
                # Clean up empty/None values
                field_config = {k: v for k, v in field_config.items() if v is not None and v != ''}
                schema_dict['fields'][field_name] = field_config
        
        return schema_dict
    
    @staticmethod
    def _save_current_schema() -> bool:
        """Save the current schema to file."""
        # UserFeedback import removed - using Notify instead
        
        try:
            # Run comprehensive validation before saving
            schema_dict = SchemaEditor._build_schema_from_session()
            is_valid, errors = validate_schema_structure(schema_dict)
            
            if not is_valid:
                Notify.error("Cannot save schema with validation errors")
                for error in errors:
                    st.error(f"  • {error}")
                return False
            
            # Determine save path
            active_file = st.session_state.get('schema_editor_active_file')
            if active_file:
                # Saving existing file
                save_path = active_file
            else:
                # New file - need filename
                title = schema_dict.get('title', '').strip()
                if title:
                    # Generate filename from title
                    filename = SchemaEditor._generate_filename_from_title(title)
                else:
                    # Use default filename
                    filename = "new_schema.yaml"
                
                save_path = f"schemas/{filename}"
                
                # Check if file already exists
                if Path(save_path).exists():
                    Notify.warn(f"File {filename} already exists. Use 'Save As' to specify a different name.")
                    return False
            
            # Log pre-save context: dirty flag, path, field count
            diag_mode = st.session_state.get('schema_editor_diagnostic_mode', False)
            if diag_mode:
                dirty_pre = st.session_state.get(DIRTY_KEY, st.session_state.get('schema_editor_unsaved', False))
                field_count_pre = len(schema_dict.get('fields', {}))
                logger.debug(f"_save_current_schema DIAG: pre-save dirty={dirty_pre}, path={save_path}, fields={field_count_pre}")
            try:
                dirty_pre = st.session_state.get(DIRTY_KEY, st.session_state.get('schema_editor_unsaved', False))
                field_count_pre = len(schema_dict.get('fields', {}))
                logger.debug(f"_save_current_schema: starting save pre-state dirty={dirty_pre} save_path={save_path} field_count={field_count_pre}")
            except Exception as _e:
                logger.debug(f"_save_current_schema: starting save (failed to read full context: {_e})")
            
            # Save the schema with comprehensive error handling
            # Add schema versioning
            if 'schema_version' not in schema_dict:
                schema_dict['schema_version'] = 1
            else:
                schema_dict['schema_version'] += 1
            success, error_message = save_schema(save_path, schema_dict)
            if success:
                logger.info(f"_save_current_schema: save succeeded for {save_path}")
                # Clear higher-level schema caches so new schema is picked up
                try:
                    _clear_schema_caches()
                except Exception:
                    # Non-fatal; proceed
                    logger.debug(f"_save_current_schema: _clear_schema_caches raised an exception but continuing")
                    pass
                
                # Clear related session keys if they exist (keep minimal)
                for key in ["active_schema", "active_schema_mtime", "schema_fields", "schema_version"]:
                    if key in st.session_state:
                        del st.session_state[key]
                
                # Provide user feedback while preserving existing Notify usage
                st.success("Schema saved.")
                st.toast("Schema cache cleared. New edits will use the latest schema.", icon="✅")
                # Debounced success notification to avoid duplicate toasts
                Notify.once("schema_saved_ok", notification_type="success", key="schema_saved_once_ok")
                
                # Update session state
                st.session_state.schema_editor_active_file = save_path
                # Mark editor as clean using canonical helper (keeps legacy flag in sync)
                _mark_clean()
                
                # Explicit rerun to update UI banner after state change
                st.rerun()

                # The following will run on the next execution after rerun
                # Log post-save dirty state
                try:
                    dirty_post = st.session_state.get(DIRTY_KEY, st.session_state.get('schema_editor_unsaved', False))
                    logger.debug(f"_save_current_schema: post-save dirty={dirty_post} active_file={st.session_state.get('schema_editor_active_file')}")
                except Exception:
                    logger.debug("_save_current_schema: post-save dirty read failed")
                
                # Reload the saved schema to refresh metadata like field counts.
                try:
                    latest = load_schema(save_path)
                    if latest:
                        # Update any relevant session metadata if present
                        st.session_state['active_schema'] = latest
                        st.session_state['active_schema_mtime'] = Path(save_path).stat().st_mtime
                        st.session_state['schema_fields'] = latest.get('fields', {})
                        st.session_state['schema_version'] = latest.get('schema_version', schema_dict.get('schema_version'))
                        logger.debug(f"_save_current_schema: reload after save succeeded for {save_path} fields={len(latest.get('fields', {}))}")
                    else:
                        logger.debug(f"_save_current_schema: reload after save returned no data for {save_path}")
                except Exception as e:
                    # Don't let reload failures block the save operation
                    logger.warning(f"Saved schema reload failed for {save_path}: {e}")
                
                # Show more detailed save feedback via Notify (non-debounced informational)
                filename = Path(save_path).name
                field_count = len(schema_dict.get('fields', {}))
                Notify.info("Save Details")
                with st.expander("💾 Save Details:", expanded=False):
                    st.write(f"• **File:** {filename}")
                    st.write(f"• **Fields:** {field_count}")
                    st.write(f"• **Title:** {schema_dict.get('title', 'No title')}")
                
                return True
            else:
                logger.error(f"_save_current_schema: save failed for {save_path}: {error_message}")
                # Log post-failure dirty state to help diagnose if dirty flag was changed
                try:
                    dirty_after_fail = st.session_state.get(DIRTY_KEY, st.session_state.get('schema_editor_unsaved', False))
                    logger.debug(f"_save_current_schema: after failed save dirty={dirty_after_fail}")
                except Exception:
                    logger.debug("_save_current_schema: could not read dirty flag after failed save")
                Notify.error(f"Failed to save schema: {error_message}")
                st.info("**Recovery Options:**")
                st.info("• Check file permissions in the schemas/ directory")
                st.info("• Ensure sufficient disk space is available")
                st.info("• Try saving with a different filename")
                st.info("• Export the schema and save manually")
                return False
                
        except Exception as e:
            logger.error(f"Error saving schema: {e}", exc_info=True)
            
            # Provide specific error messages based on exception type
            if "Permission denied" in str(e):
                Notify.error("Save failed: Permission denied. Check file permissions.")
            elif "No space left" in str(e):
                Notify.error("Save failed: No disk space available.")
            elif "File not found" in str(e):
                Notify.error("Save failed: Directory not found. Check that schemas/ directory exists.")
            else:
                Notify.error(f"Save failed: {str(e)}")
            
            # Log dirty flag when an unexpected exception prevented save
            try:
                dirty_on_exception = st.session_state.get(DIRTY_KEY, st.session_state.get('schema_editor_unsaved', False))
                logger.debug(f"_save_current_schema: exception path dirty={dirty_on_exception}")
            except Exception:
                logger.debug("_save_current_schema: could not read dirty flag during exception handling")
            
            return False
    
    @staticmethod
    def _show_save_as_dialog() -> None:
        """Show Save As dialog for specifying filename."""
        # Store that we want to show save as dialog
        st.session_state.schema_editor_show_save_as = True
        st.rerun()
    
    @staticmethod
    def _handle_save_as_dialog() -> None:
        """Handle the Save As dialog."""
        # UserFeedback import removed - using Notify instead
        
        st.subheader("💾 Save Schema As...")
        
        # Get current title for default filename
        current_title = st.session_state.get('schema_editor_title', '').strip()
        default_filename = SchemaEditor._generate_filename_from_title(current_title) if current_title else "new_schema.yaml"
        
        # Filename input
        filename = st.text_input(
            "Filename",
            value=default_filename,
            help="Enter filename with .yaml extension",
            key="save_as_filename"
        )
        
        # Validate filename
        filename_errors = []
        if not filename:
            filename_errors.append("Filename cannot be empty")
        elif not filename.endswith('.yaml'):
            filename_errors.append("Filename must end with .yaml")
        elif not re.match(r'^[a-zA-Z0-9_\-\.]+$', filename):
            filename_errors.append("Filename can only contain letters, numbers, underscores, hyphens, and dots")
        
        # Check if file exists
        save_path = f"schemas/{filename}"
        file_exists = Path(save_path).exists() if filename and not filename_errors else False
        
        if file_exists:
            st.warning(f"⚠️ File '{filename}' already exists and will be overwritten.")
        
        # Show validation errors
        if filename_errors:
            for error in filename_errors:
                st.error(f"❌ {error}")
        
        # Action buttons
        col1, col2, col3 = st.columns(3)
        
        with col1:
            save_disabled = bool(filename_errors) or not SchemaEditor._can_save_schema()
            if st.button("💾 Save", type="primary", key="confirm_save_as", disabled=save_disabled):
                try:
                    # Build and validate schema
                    schema_dict = SchemaEditor._build_schema_from_session()
                    is_valid, errors = validate_schema_structure(schema_dict)
                    
                    if not is_valid:
                        Notify.error("Cannot save schema with validation errors")
                        for error in errors:
                            st.error(f"  • {error}")
                        return
                    
                    # Save the schema with error handling
                    success, error_message = save_schema(save_path, schema_dict)
                    if success:
                        # Update session state
                        st.session_state.schema_editor_active_file = save_path
                        _mark_clean()
                        st.session_state.schema_editor_show_save_as = False
                        
                        Notify.success(f"Saved as: {filename}")
                        # Explicit rerun to update UI banner after state change
                        st.rerun()
                    else:
                        Notify.error("Save schema file failed")
                        
                except Exception as e:
                    logger.error(f"Error in Save As: {e}", exc_info=True)
                    Notify.error(f"Error saving schema: {str(e)}")
        
        with col2:
            if file_exists and st.button("🔄 Overwrite", key="overwrite_save_as"):
                try:
                    # Build and validate schema
                    schema_dict = SchemaEditor._build_schema_from_session()
                    is_valid, errors = validate_schema_structure(schema_dict)
                    
                    if not is_valid:
                        Notify.error("Cannot save schema with validation errors")
                        for error in errors:
                            st.error(f"  • {error}")
                        return
                    
                    # Save the schema (overwrite) with error handling
                    success, error_message = save_schema(save_path, schema_dict)
                    if success:
                        # Update session state
                        st.session_state.schema_editor_active_file = save_path
                        _mark_clean()
                        st.session_state.schema_editor_show_save_as = False
                        
                        Notify.info(f"Overwrote: {filename}")
                        # Explicit rerun to update UI banner after state change
                        st.rerun()
                    else:
                        Notify.error("Save As failed")
                        
                except Exception as e:
                    logger.error(f"Error in overwrite: {e}", exc_info=True)
                    Notify.error(f"Error saving schema: {str(e)}")
        
        with col3:
            if st.button("❌ Cancel", key="cancel_save_as"):
                st.session_state.schema_editor_show_save_as = False
                st.rerun()
    
    @staticmethod
    def _generate_filename_from_title(title: str) -> str:
        """Generate a valid filename from schema title."""
        # Convert to lowercase and replace spaces/special chars with underscores
        filename = re.sub(r'[^a-zA-Z0-9_\-]', '_', title.lower())
        # Remove multiple consecutive underscores
        filename = re.sub(r'_+', '_', filename)
        # Remove leading/trailing underscores
        filename = filename.strip('_')
        # Ensure it's not empty
        if not filename:
            filename = "schema"
        # Add extension
        return f"{filename}.yaml"
    
    @staticmethod
    def _show_detailed_validation_feedback() -> None:
        """Show detailed validation feedback after validation."""
        # UserFeedback import removed - using Notify instead
        
        validation_results = st.session_state.get('schema_editor_validation_results', {})
        errors = validation_results.get('errors', [])
        is_valid = validation_results.get('is_valid', False)
        
        if is_valid and not errors:
            Notify.success("Schema validation passed - ready to save!")
            st.info("💡 **Validation Summary:**")
            st.info("  • All fields have valid configurations")
            st.info("  • No duplicate field names found")
            st.info("  • Schema structure is correct")
        else:
            Notify.error(f"Schema validation failed with {len(errors)} error(s)")
            
            # Categorize errors for better display
            field_errors = []
            schema_errors = []
            
            for error in errors:
                if "Field '" in error:
                    field_errors.append(error)
                else:
                    schema_errors.append(error)
            
            if schema_errors:
                st.error("**Schema Structure Errors:**")
                for error in schema_errors:
                    st.error(f"  • {error}")
            
            if field_errors:
                st.error("**Field Configuration Errors:**")
                for error in field_errors:
                    st.error(f"  • {error}")
            
            st.info("💡 **Fix these issues before saving the schema.**")
    
    @staticmethod
    def _export_current_schema() -> None:
        """Export current schema as downloadable YAML."""
        # UserFeedback import removed - using Notify instead
        
        try:
            # Build schema from current session state
            schema_dict = SchemaEditor._build_schema_from_session()
            
            # Validate schema before export
            is_valid, validation_errors = validate_schema_structure(schema_dict)
            if not is_valid:
                Notify.error("Cannot export schema with validation errors")
                for error in validation_errors:
                    st.error(f"  • {error}")
                return
            
            # Test compatibility with form generator
            compatibility_errors = SchemaEditor._test_form_generator_compatibility(schema_dict)
            if compatibility_errors:
                Notify.warn("Schema may have compatibility issues with form generator")
                for error in compatibility_errors:
                    st.warning(f"  • {error}")
                st.info("The schema will still be exported, but you may need to review these issues.")
            
            # Clean the schema dictionary to match expected format
            cleaned_schema = _clean_schema_dict(schema_dict)
            
            # Ensure proper structure for form generator compatibility
            logger.debug(f"_export_current_schema: before normalization, fields={len(cleaned_schema.get('fields', {}))}")
            cleaned_schema = SchemaEditor._ensure_form_generator_compatibility(cleaned_schema)
            logger.debug(f"_export_current_schema: after normalization, fields={len(cleaned_schema.get('fields', {}))}, changes_detected={len(cleaned_schema.get('fields', {})) > 0}")
            
            # Convert to YAML string with exact formatting expected by existing modules
            yaml_content = yaml.dump(
                cleaned_schema,
                default_flow_style=False,
                indent=2,
                sort_keys=False,
                allow_unicode=True,
                width=float('inf')  # Prevent line wrapping
            )
            
            # Generate filename for download
            title = schema_dict.get('title', '').strip()
            if title:
                download_filename = SchemaEditor._generate_filename_from_title(title)
            else:
                download_filename = "exported_schema.yaml"
            
            # Show export preview
            with st.expander("📋 Export Preview", expanded=False):
                st.code(yaml_content, language='yaml')
                
                # Show compatibility summary
                field_count = len(cleaned_schema.get('fields', {}))
                supported_types = set()
                for field_config in cleaned_schema.get('fields', {}).values():
                    supported_types.add(field_config.get('type', 'string'))
                
                st.info("**Export Summary:**")
                st.info(f"  • Fields: {field_count}")
                st.info(f"  • Types used: {', '.join(sorted(supported_types))}")
                st.info(f"  • Form generator compatible: {'✅ Yes' if not compatibility_errors else '⚠️ With warnings'}")
            
            # Provide download button
            st.download_button(
                label="📥 Download YAML",
                data=yaml_content,
                file_name=download_filename,
                mime="application/x-yaml",
                key="download_schema_yaml",
                help=f"Download schema as {download_filename}"
            )
            
            Notify.success(f"Schema ready for download as: {download_filename}")
            st.info("💡 **Next Steps:** Upload this schema to your schemas/ directory to use it with the form generator.")
            
        except Exception as e:
            logger.error(f"Error exporting schema: {e}", exc_info=True)
            Notify.error(f"Error exporting schema: {str(e)}")
    
    @staticmethod
    def _test_form_generator_compatibility(schema_dict: Dict[str, Any]) -> List[str]:
        """Test schema compatibility with the form generator."""
        warnings = []
        
        try:
            fields = schema_dict.get('fields', {})
            
            for field_name, field_config in fields.items():
                field_type = field_config.get('type', 'string')
                
                # Check for unsupported field types
                supported_types = ['string', 'integer', 'number', 'float', 'boolean', 'enum', 'date', 'datetime', 'array']
                if field_type not in supported_types:
                    warnings.append(f"Field '{field_name}' has unsupported type '{field_type}'")
                
                # Check enum fields have choices
                if field_type == 'enum' and not field_config.get('choices'):
                    warnings.append(f"Enum field '{field_name}' missing required 'choices' property")
                
                # Check for missing required properties
                if not field_config.get('label'):
                    warnings.append(f"Field '{field_name}' missing recommended 'label' property")
                
                # Check numeric constraints
                if field_type in ['integer', 'number', 'float']:
                    min_val = field_config.get('min_value')
                    max_val = field_config.get('max_value')
                    if min_val is not None and max_val is not None and min_val > max_val:
                        warnings.append(f"Field '{field_name}' has min_value > max_value")
                
                # Check string constraints
                if field_type == 'string':
                    min_len = field_config.get('min_length')
                    max_len = field_config.get('max_length')
                    if min_len is not None and max_len is not None and min_len > max_len:
                        warnings.append(f"Field '{field_name}' has min_length > max_length")
                    
                    # Check regex pattern
                    pattern = field_config.get('pattern')
                    if pattern:
                        try:
                            import re
                            re.compile(pattern)
                        except re.error:
                            warnings.append(f"Field '{field_name}' has invalid regex pattern")
            
        except Exception as e:
            warnings.append(f"Error testing compatibility: {str(e)}")
        
        return warnings
    
    @staticmethod
    def _ensure_form_generator_compatibility(schema_dict: Dict[str, Any]) -> Dict[str, Any]:
        """Ensure schema structure is compatible with form generator."""
        diag_mode = st.session_state.get('schema_editor_diagnostic_mode', False)
        if diag_mode:
            logger.debug(f"_ensure_form_generator_compatibility: input schema has {len(schema_dict.get('fields', {}))} fields")
        # Make a copy to avoid modifying the original
        compatible_schema = dict(schema_dict)
        
        # Ensure required top-level properties
        if 'title' not in compatible_schema:
            compatible_schema['title'] = 'Untitled Schema'
        
        if 'description' not in compatible_schema:
            compatible_schema['description'] = 'Schema created with Schema Editor'
        
        if 'fields' not in compatible_schema:
            compatible_schema['fields'] = {}
        
        # Process fields for compatibility
        fields = compatible_schema['fields']
        for field_name, field_config in fields.items():
            # Ensure each field has required properties
            if 'type' not in field_config:
                field_config['type'] = 'string'
            
            if 'label' not in field_config:
                field_config['label'] = field_name.replace('_', ' ').title()
            
            
            # Ensure enum fields have choices
            if field_config.get('type') == 'enum' and 'choices' not in field_config:
                field_config['choices'] = ['Option 1', 'Option 2']
            
            # Set default step values for numeric types
            if field_config.get('type') == 'integer' and 'step' not in field_config:
                field_config['step'] = 1
            elif field_config.get('type') in ['number', 'float'] and 'step' not in field_config:
                field_config['step'] = 0.01
        
        if diag_mode:
            output_fields = len(compatible_schema.get('fields', {}))
            logger.debug(f"_ensure_form_generator_compatibility: output schema has {output_fields} fields; changes_made={output_fields != len(schema_dict.get('fields', {}))}")
        return compatible_schema
    
    @staticmethod
    def _render_type_specific_editor(field_id: str, field: Dict[str, Any]) -> None:
        """Render type-specific field editor based on field type."""
        field_type = field.get('type', 'string')
        
        if field_type == 'string':
            SchemaEditor._render_string_field_editor(field_id, field)
        elif field_type in ['integer', 'number', 'float']:
            SchemaEditor._render_numeric_field_editor(field_id, field)
        elif field_type == 'boolean':
            SchemaEditor._render_boolean_field_editor(field_id, field)
        elif field_type == 'enum':
            SchemaEditor._render_enum_field_editor(field_id, field)
        elif field_type in ['date', 'datetime']:
            SchemaEditor._render_date_field_editor(field_id, field)
        elif field_type == 'array':
            SchemaEditor._render_array_field_editor(field_id, field)
        else:
            # Handle unsupported types gracefully
            st.info(f"ℹ️ Field type '{field_type}' editing will be available in a future phase.")
            st.write("Complex nested types are planned for future development phases.")
            
            # Update field in session state with minimal changes (no readonly update needed here)
            field_index = None
            for i, f in enumerate(st.session_state.schema_editor_fields):
                if f['id'] == field_id:
                    field_index = i
                    break
            
            if field_index is not None:
                updated_field = field  # No changes for unsupported types
                st.session_state.schema_editor_fields[field_index] = updated_field
    
    @staticmethod
    def _render_string_field_editor(field_id: str, field: Dict[str, Any]) -> None:
        """Render string field editor with validation."""
        st.subheader("🔤 String Field Configuration")
        
        # Get current field index for updating
        field_index = None
        for i, f in enumerate(st.session_state.schema_editor_fields):
            if f['id'] == field_id:
                field_index = i
                break
        
        if field_index is None:
            st.error("Field not found in session state")
            return
        
        # Create columns for layout
        col1, col2 = st.columns(2)
        
        with col1:
            # Default value
            default_value = st.text_input(
                "Default Value",
                value=field.get('default', ''),
                key=f"default_{field_id}",
                help="Optional default value for this field"
            )
            
            # Min length
            min_length = st.number_input(
                "Minimum Length",
                min_value=0,
                max_value=10000,
                value=field.get('min_length', 0),
                key=f"min_length_{field_id}",
                help="Minimum number of characters required"
            )
        
        with col2:
            # Max length
            max_length = st.number_input(
                "Maximum Length",
                min_value=1,
                max_value=10000,
                value=field.get('max_length', 255),
                key=f"max_length_{field_id}",
                help="Maximum number of characters allowed"
            )
            
        # Pattern input (full width)
        pattern = st.text_input(
            "Validation Pattern (Regex)",
            value=field.get('pattern', ''),
            key=f"pattern_{field_id}",
            help="Regular expression pattern for validation (optional)"
        )
        
        # Validate regex pattern in real-time
        pattern_error = None
        if pattern:
            pattern_error = SchemaEditor._validate_regex_pattern(pattern)
            if pattern_error:
                st.error(f"❌ **Pattern Error:** {pattern_error}")
            else:
                st.success("✅ Pattern is valid")
        
        # Validate min_length <= max_length
        length_error = None
        if min_length is not None and max_length is not None and min_length > max_length:
            length_error = "Minimum length cannot be greater than maximum length"
            st.error(f"❌ **Length Error:** {length_error}")
        
        # Update field in session state
        updated_field = {
            **field,
            'default': default_value if default_value else None,
            'min_length': int(min_length) if min_length is not None and min_length > 0 else None,
            'max_length': int(max_length) if max_length is not None and max_length != 255 else None,
            'pattern': pattern if pattern else None
        }
        
        # Check if field was modified
        if updated_field != field:
            st.session_state.schema_editor_fields[field_index] = updated_field
            _mark_dirty()
            # Update validation on change
            SchemaEditor._update_validation_on_change()
        
        # Store validation errors for this field
        errors = []
        if pattern_error:
            errors.append(pattern_error)
        if length_error:
            errors.append(length_error)
        
        if 'schema_editor_validation_results' not in st.session_state:
            st.session_state.schema_editor_validation_results = {}
        st.session_state.schema_editor_validation_results[field_id] = errors
    
    @staticmethod
    def _validate_regex_pattern(pattern: str) -> Optional[str]:
        """Validate regex pattern compilation."""
        return validate_regex_pattern(pattern)
    
    @staticmethod
    def _render_numeric_field_editor(field_id: str, field: Dict[str, Any]) -> None:
        """Render numeric field editor (integer, number, float) with validation."""
        field_type = field.get('type', 'number')
        type_display = field_type.title()
        
        if field_type == 'integer':
            st.subheader("🔢 Integer Field Configuration")
            icon = "🔢"
        elif field_type == 'float':
            st.subheader("🔢 Float Field Configuration")
            icon = "🔢"
        else:  # number
            st.subheader("🔢 Number Field Configuration")
            icon = "🔢"
        
        # Get current field index for updating
        field_index = None
        for i, f in enumerate(st.session_state.schema_editor_fields):
            if f['id'] == field_id:
                field_index = i
                break
        
        if field_index is None:
            st.error("Field not found in session state")
            return
        
        # Create columns for layout
        col1, col2 = st.columns(2)
        
        # Determine default step based on type
        default_step = 1 if field_type == 'integer' else 0.01
        
        with col1:
            # Min value - ensure type consistency
            if field_type == 'integer':
                current_min = field.get('min_value')
                min_value = st.number_input(
                    "Minimum Value",
                    value=int(current_min) if current_min is not None else 0,
                    key=f"min_value_{field_id}",
                    help=f"Minimum allowed value for this {field_type} field",
                    step=1
                )
            else:
                current_min = field.get('min_value')
                min_value = st.number_input(
                    "Minimum Value",
                    value=float(current_min) if current_min is not None else 0.0,
                    key=f"min_value_{field_id}",
                    help=f"Minimum allowed value for this {field_type} field",
                    step=0.01
                )
            
            # Step value - ensure type consistency
            if field_type == 'integer':
                current_step = field.get('step')
                step_value = st.number_input(
                    "Step Size",
                    min_value=1,
                    value=int(current_step) if current_step is not None else 1,
                    key=f"step_{field_id}",
                    help="Step size for input controls",
                    step=1
                )
            else:
                current_step = field.get('step')
                step_value = st.number_input(
                    "Step Size",
                    min_value=0.001,
                    value=float(current_step) if current_step is not None else 0.01,
                    key=f"step_{field_id}",
                    help="Step size for input controls",
                    step=0.001
                )
        
        with col2:
            # Max value - ensure type consistency
            if field_type == 'integer':
                current_max = field.get('max_value')
                max_value = st.number_input(
                    "Maximum Value",
                    value=int(current_max) if current_max is not None else 1000000,
                    key=f"max_value_{field_id}",
                    help=f"Maximum allowed value for this {field_type} field",
                    step=1
                )
            else:
                current_max = field.get('max_value')
                max_value = st.number_input(
                    "Maximum Value",
                    value=float(current_max) if current_max is not None else 1000000.0,
                    key=f"max_value_{field_id}",
                    help=f"Maximum allowed value for this {field_type} field",
                    step=0.01
                )
            
        # Default value (full width) - ensure type consistency
        if field_type == 'integer':
            default_value = st.number_input(
                "Default Value",
                value=int(field.get('default', 0)) if field.get('default') is not None else 0,
                key=f"default_{field_id}",
                help="Optional default value for this field",
                step=1
            )
        else:
            default_value = st.number_input(
                "Default Value",
                value=float(field.get('default', 0.0)) if field.get('default') is not None else 0.0,
                key=f"default_{field_id}",
                help="Optional default value for this field",
                step=0.01
            )
        
        # Validation
        errors = []
        
        # Validate step > 0
        if step_value <= 0:
            errors.append("Step size must be greater than 0")
            st.error("❌ **Step Error:** Step size must be greater than 0")
        
        # Validate min_value <= max_value
        if min_value is not None and max_value is not None and min_value > max_value:
            errors.append("Minimum value cannot be greater than maximum value")
            st.error("❌ **Range Error:** Minimum value cannot be greater than maximum value")
            logger.debug(f"numeric_editor_before_convert: field_id={field_id} raw_default={field.get('default')} raw_min={field.get('min_value')} raw_max={field.get('max_value')} raw_step={field.get('step')}")
        
        # Validate default value is within range
        if (default_value is not None and 
            ((min_value is not None and default_value < min_value) or 
             (max_value is not None and default_value > max_value))):
            errors.append("Default value must be between minimum and maximum values")
            st.error("❌ **Default Error:** Default value must be between minimum and maximum values")
        
        # Ensure proper type conversion for storage (guard None)
        if field_type == 'integer':
            # Convert to integers for storage if present
            if default_value is not None:
                default_value = int(default_value)
            if min_value is not None:
                min_value = int(min_value)
            if max_value is not None:
                max_value = int(max_value)
            if step_value is not None:
                step_value = int(step_value)
        else:
            # Ensure floats for non-integer types if present
            if default_value is not None:
                default_value = float(default_value)
            if min_value is not None:
                min_value = float(min_value)
            if max_value is not None:
                max_value = float(max_value)
            if step_value is not None:
                step_value = float(step_value)
        
        if not errors:
            st.success("✅ All numeric constraints are valid")
        
        # Update field in session state
        updated_field = {
            **field,
            'min_value': min_value if min_value != 0 else None,
            'max_value': max_value if max_value != 1000000 else None,
            'step': step_value if step_value != default_step else None,
            'default': default_value if default_value != (0 if field_type == 'integer' else 0.0) else None
        }
        
        # Check if field was modified
        if updated_field != field:
            st.session_state.schema_editor_fields[field_index] = updated_field
            _mark_dirty()
            # Update validation on change
            SchemaEditor._update_validation_on_change()
        
        # Store validation errors for this field
        if 'schema_editor_validation_results' not in st.session_state:
            st.session_state.schema_editor_validation_results = {}
        st.session_state.schema_editor_validation_results[field_id] = errors
    
    @staticmethod
    def _render_boolean_field_editor(field_id: str, field: Dict[str, Any]) -> None:
        """Render boolean field editor with validation."""
        st.subheader("☑️ Boolean Field Configuration")
        
        # Get current field index for updating
        field_index = None
        for i, f in enumerate(st.session_state.schema_editor_fields):
            if f['id'] == field_id:
                field_index = i
                break
        
        if field_index is None:
            st.error("Field not found in session state")
            return
        
        # Create columns for layout
        col1, col2 = st.columns(2)
        
        with col1:
            # Default value option
            default_option = st.selectbox(
                "Default Value",
                options=["None (unset)", "True", "False"],
                index=0 if field.get('default') is None else (1 if field.get('default') is True else 2),
                key=f"default_option_{field_id}",
                help="Optional default value for this boolean field"
            )
        
        with col2:
            pass  # Readonly is handled in the general field editor - no duplicate needed here
        
        # Convert default option to actual value
        if default_option == "None (unset)":
            default_value = None
        elif default_option == "True":
            default_value = True
        else:  # "False"
            default_value = False
        
        # Boolean fields have no specific validation constraints
        st.success("✅ Boolean field configuration is valid")
        
        # Update field in session state
        updated_field = {
            **field,
            'default': default_value
        }
        
        # Check if field was modified
        if updated_field != field:
            st.session_state.schema_editor_fields[field_index] = updated_field
            _mark_dirty()
        
        # Store validation errors for this field (none for boolean)
        if 'schema_editor_validation_results' not in st.session_state:
            st.session_state.schema_editor_validation_results = {}
        st.session_state.schema_editor_validation_results[field_id] = []
    
    @staticmethod
    def _render_enum_field_editor(field_id: str, field: Dict[str, Any]) -> None:
        """Render enum field editor with choices management and validation."""
        st.subheader("📋 Enum Field Configuration")
        
        # Get current field index for updating
        field_index = None
        for i, f in enumerate(st.session_state.schema_editor_fields):
            if f['id'] == field_id:
                field_index = i
                break
        
        if field_index is None:
            st.error("Field not found in session state")
            return
        
        # Get current choices
        current_choices = field.get('choices', [])
        
        # Choices editor using text area approach
        st.write("**Choices List**")
        st.write("Enter one choice per line:")
        
        choices_text = st.text_area(
            "Choices",
            value='\n'.join(current_choices) if current_choices else '',
            key=f"choices_{field_id}",
            help="Enter each choice on a separate line",
            height=120,
            label_visibility="collapsed"
        )
        
        # Parse choices from text area
        choices = [choice.strip() for choice in choices_text.split('\n') if choice.strip()]
        
        # Create columns for other settings
        col1, col2 = st.columns(2)
        
        with col1:
            # Default value selector
            default_options = ["None (no default)"] + choices
            current_default = field.get('default')
            
            if current_default and current_default in choices:
                default_index = choices.index(current_default) + 1
            else:
                default_index = 0
            
            selected_default = st.selectbox(
                "Default Value",
                options=default_options,
                index=default_index,
                key=f"default_{field_id}",
                help="Optional default selection (must be from choices list)"
            )
        
        with col2:
            pass  # Readonly is handled in the general field editor - no duplicate needed here
        
        # Validation
        errors = []
        
        # Validate choices list is not empty
        if not choices:
            errors.append("Enum fields must have at least one choice")
            st.error("❌ **Choices Error:** Enum fields must have at least one choice")
        
        # Validate default value is in choices (if provided)
        default_value = None
        if selected_default != "None (no default)":
            if selected_default in choices:
                default_value = selected_default
            else:
                errors.append("Default value must be in the choices list")
                st.error("❌ **Default Error:** Default value must be in the choices list")
        
        # Check for duplicate choices
        if len(choices) != len(set(choices)):
            errors.append("Duplicate choices are not allowed")
            st.error("❌ **Duplicate Error:** Duplicate choices are not allowed")
        
        if not errors:
            st.success(f"✅ Enum configuration is valid ({len(choices)} choices)")
        
        # Show choices preview
        if choices:
            st.write("**Choices Preview:**")
            for i, choice in enumerate(choices, 1):
                icon = "🔸" if choice != default_value else "🔹"
                st.write(f"{icon} {i}. {choice}")
        
        # Update field in session state
        updated_field = {
            **field,
            'choices': choices if choices else None,
            'default': default_value
        }
        
        # Check if field was modified
        if updated_field != field:
            st.session_state.schema_editor_fields[field_index] = updated_field
            _mark_dirty()
            # Update validation on change
            SchemaEditor._update_validation_on_change()
        
        # Store validation errors for this field
        if 'schema_editor_validation_results' not in st.session_state:
            st.session_state.schema_editor_validation_results = {}
        st.session_state.schema_editor_validation_results[field_id] = errors
    
    @staticmethod
    def _render_date_field_editor(field_id: str, field: Dict[str, Any]) -> None:
        """Render date/datetime field editor."""
        field_type = field.get('type', 'date')
        
        if field_type == 'datetime':
            st.subheader("📅 DateTime Field Configuration")
            help_text = "Date and time values stored as ISO datetime strings"
        else:
            st.subheader("📅 Date Field Configuration")
            help_text = "Date values stored as ISO date strings (YYYY-MM-DD)"
        
        # Get current field index for updating
        field_index = None
        for i, f in enumerate(st.session_state.schema_editor_fields):
            if f['id'] == field_id:
                field_index = i
                break
        
        if field_index is None:
            st.error("Field not found in session state")
            return
        
        # Date/datetime fields only have basic properties - no additional constraints
        st.info(f"ℹ️ {help_text}")
        
        # Date/datetime fields have no specific validation constraints
        st.success(f"✅ {field_type.title()} field configuration is valid")
        
        # Update field in session state
        updated_field = field  # No changes needed for date/datetime specific
        
        # Check if field was modified
        if updated_field != field:
            st.session_state.schema_editor_fields[field_index] = updated_field
            _mark_dirty()
        
        # Store validation errors for this field (none for date/datetime)
        if 'schema_editor_validation_results' not in st.session_state:
            st.session_state.schema_editor_validation_results = {}
        st.session_state.schema_editor_validation_results[field_id] = []
    
    @staticmethod
    def _render_array_field_editor(field_id: str, field: Dict[str, Any]) -> None:
        """Render array field editor using ArrayFieldManager."""
        # Get current field index for updating
        field_index = None
        for i, f in enumerate(st.session_state.schema_editor_fields):
            if f['id'] == field_id:
                field_index = i
                break
        
        if field_index is None:
            st.error("Field not found in session state")
            return
        
        # Store original field for comparison (deep copy to catch nested changes)
        import copy
        original_field = copy.deepcopy(field)
        
        # Use ArrayFieldManager to render the configuration interface
        ArrayFieldManager.render_array_field_config(field_id, field)
        
        # Validate array configuration
        validation_errors = ArrayFieldManager.validate_array_config(field)
        
        # Display validation results
        if validation_errors:
            st.error("❌ Array Configuration Errors:")
            for error in validation_errors:
                st.error(f"  • {error}")
        else:
            st.success("✅ Array field configuration is valid")
        
        # Check if field was modified and update session state
        if field != original_field:
            st.session_state.schema_editor_fields[field_index] = field
            _mark_dirty()
        
        # Store validation errors for this field
        if 'schema_editor_validation_results' not in st.session_state:
            st.session_state.schema_editor_validation_results = {}
        st.session_state.schema_editor_validation_results[field_id] = validation_errors
    
    @staticmethod
    def _handle_back_to_list() -> None:
        """Handle back to list with unsaved changes confirmation."""
        if st.session_state.get('schema_editor_unsaved', False):
            # Store the navigation request for confirmation
            st.session_state.schema_editor_pending_navigation = 'list'
            st.rerun()
        else:
            # No unsaved changes, navigate directly
            st.session_state.schema_editor_mode = 'list'
            st.rerun()
    
    @staticmethod
    def _handle_pending_operations() -> None:
        """Handle pending file operations with confirmation dialogs."""
        # UserFeedback import removed - using Notify instead
        
        # Handle pending navigation with unsaved changes
        if st.session_state.get('schema_editor_pending_navigation'):
            st.warning("⚠️ **Unsaved Changes**")
            st.write("You have unsaved changes. What would you like to do?")
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                if st.button("💾 Save & Continue", type="primary", key="save_and_continue"):
                    # Check if schema can be saved (no validation errors)
                    if SchemaEditor._can_save_schema():
                        # Attempt to save the schema
                        if SchemaEditor._save_current_schema():
                            target_mode = st.session_state.schema_editor_pending_navigation
                            st.session_state.schema_editor_mode = target_mode
                            st.session_state.schema_editor_pending_navigation = None
                            _mark_clean()
                            # Explicit rerun to update UI after navigation
                            st.rerun()
                        # If save failed, error message is already shown by _save_current_schema
                    else:
                        st.error("❌ Cannot save: Schema has validation errors. Please fix them first.")
                        # Run validation to show current errors
                        SchemaEditor._validate_current_schema()
            
            with col2:
                if st.button("🚫 Discard Changes", key="discard_changes"):
                    target_mode = st.session_state.schema_editor_pending_navigation
                    st.session_state.schema_editor_mode = target_mode
                    st.session_state.schema_editor_pending_navigation = None
                    _mark_clean()
                    # Clear editor state
                    st.session_state.schema_editor_fields = []
                    st.session_state.schema_editor_title = ''
                    st.session_state.schema_editor_description = ''
                    st.rerun()
            
            with col3:
                if st.button("❌ Cancel", key="cancel_navigation"):
                    st.session_state.schema_editor_pending_navigation = None
                    st.rerun()
            st.stop()
            return
        
        # Handle pending field delete operation
        if st.session_state.get('schema_editor_pending_field_delete') is not None:
            field_index = st.session_state.schema_editor_pending_field_delete
            fields = st.session_state.get('schema_editor_fields', [])
            
            if field_index < len(fields):
                field_name = fields[field_index].get('name', 'Unnamed Field')
                
                st.warning(f"⚠️ **Confirm Field Deletion**")
                st.write(f"Are you sure you want to delete field **{field_name}**?")
                st.write("This action cannot be undone.")
                
                col1, col2 = st.columns(2)
                
                with col1:
                    if st.button("🗑️ Delete Field", type="primary", key="confirm_field_delete"):
                        # Remove the field
                        st.session_state.schema_editor_fields.pop(field_index)
                        Notify.warn(f"Deleted field: {field_name}")
                        _mark_dirty()
                        st.session_state.schema_editor_pending_field_delete = None
                        st.rerun()
                
                with col2:
                    if st.button("❌ Cancel", key="cancel_field_delete"):
                        st.session_state.schema_editor_pending_field_delete = None
                        st.rerun()
                st.stop()
            else:
                # Invalid index, clear the pending operation
                st.session_state.schema_editor_pending_field_delete = None
                st.rerun()
                return
        
        # Handle pending delete operation
        if st.session_state.get('schema_editor_pending_delete'):
            file_path = st.session_state.schema_editor_pending_delete
            filename = Path(file_path).name
            
            st.warning(f"⚠️ **Confirm Deletion**")
            st.write(f"Are you sure you want to delete **{filename}**?")
            st.write("This action cannot be undone.")
            
            col1, col2 = st.columns(2)
            
            with col1:
                if st.button("🗑️ Delete", type="primary", key="confirm_delete"):
                    try:
                        success, error_message = delete_schema(file_path)
                        if success:
                            Notify.success(f"Successfully deleted {filename}")
                        else:
                            Notify.error(f"Failed to delete {filename}: {error_message}")
                            st.info("**Recovery Options:**")
                            st.info("• Check file permissions")
                            st.info("• Ensure the file is not open in another application")
                            st.info("• Try refreshing the page and attempting again")
                    except Exception as e:
                        logger.error(f"Unexpected error deleting schema: {e}", exc_info=True)
                        Notify.error(f"Unexpected error deleting schema: {str(e)}")
                    finally:
                        st.session_state.schema_editor_pending_delete = None
                        st.rerun()
            
            with col2:
                if st.button("❌ Cancel", key="cancel_delete"):
                    st.session_state.schema_editor_pending_delete = None
                    st.rerun()
            st.stop()
        
        # Handle pending duplicate operation
        if st.session_state.get('schema_editor_pending_duplicate'):
            file_path = st.session_state.schema_editor_pending_duplicate
            filename = Path(file_path).name
            
            st.info(f"📋 **Confirm Duplication**")
            st.write(f"Create a copy of **{filename}**?")
            st.write("The copy will be named with a '_copy' suffix.")
            
            col1, col2 = st.columns(2)
            
            with col1:
                if st.button("📋 Duplicate", type="primary", key="confirm_duplicate"):
                    try:
                        new_path, error_message = duplicate_schema(file_path)
                        if new_path:
                            new_filename = Path(new_path).name
                            Notify.success(f"Successfully created copy: {new_filename}")
                        else:
                            Notify.error(f"Failed to duplicate {filename}: {error_message}")
                            st.info("**Recovery Options:**")
                            st.info("• Check available disk space")
                            st.info("• Verify file permissions in schemas/ directory")
                            st.info("• Try with a different filename")
                            st.info("• Manually copy the file if needed")
                    except Exception as e:
                        logger.error(f"Unexpected error duplicating schema: {e}", exc_info=True)
                        Notify.error(f"Unexpected error duplicating schema: {str(e)}")
                    finally:
                        st.session_state.schema_editor_pending_duplicate = None
                        st.rerun()
            
            with col2:
                if st.button("❌ Cancel", key="cancel_duplicate"):
                    st.session_state.schema_editor_pending_duplicate = None
                    st.rerun()
            st.stop()


# File I/O Helper Functions

def list_schema_files() -> List[Dict[str, Any]]:
    """
    Scan schemas/ directory for .yaml files and return list with metadata.
    Enhanced with comprehensive error handling and graceful degradation.
    
    Returns:
        List of dictionaries containing file information including:
        - filename: str
        - path: str (full path)
        - size: int (file size in bytes)
        - modified: datetime (last modified timestamp)
        - is_valid: bool (whether schema is valid)
        - field_count: int (number of fields in schema)
        - error_message: str (if there were issues loading the file)
    """
    schemas_dir = Path("schemas")
    schema_files = []
    
    try:
        # Ensure schemas directory exists with proper error handling
        try:
            schemas_dir.mkdir(exist_ok=True)
        except PermissionError:
            logger.error("Permission denied: Cannot create schemas directory")
            # Return empty list but log the issue
            return []
        except OSError as e:
            logger.error(f"OS error creating schemas directory: {e}")
            return []
        
        # Check if directory is readable
        if not os.access(schemas_dir, os.R_OK):
            logger.error("Permission denied: Cannot read schemas directory")
            return []
        
        # Scan for .yaml files with comprehensive error handling
        try:
            yaml_files = list(schemas_dir.glob("*.yaml"))
        except OSError as e:
            logger.error(f"Error scanning schemas directory: {e}")
            return []
        
        for yaml_file in yaml_files:
            file_info = {
                'filename': yaml_file.name,
                'path': str(yaml_file),
                'size': 0,
                'modified': datetime.now(),
                'is_valid': False,
                'field_count': 0,
                'error_message': None
            }
            
            try:
                # Get file metadata with error handling
                try:
                    stat = yaml_file.stat()
                    file_info['size'] = stat.st_size
                    file_info['modified'] = datetime.fromtimestamp(stat.st_mtime)
                except (OSError, PermissionError) as e:
                    logger.warning(f"Cannot access file metadata for {yaml_file.name}: {e}")
                    file_info['error_message'] = f"File access error: {str(e)}"
                
                # Load and validate schema with comprehensive error handling
                try:
                    schema_data = load_schema(str(yaml_file))
                    if schema_data and isinstance(schema_data, dict):
                        # Use comprehensive validation
                        is_valid, validation_errors = validate_schema_structure(schema_data)
                        file_info['is_valid'] = is_valid
                        
                        # Count fields regardless of validation status
                        fields = schema_data.get('fields', {})
                        if isinstance(fields, dict):
                            file_info['field_count'] = len(fields)
                        
                        if not is_valid:
                            logger.debug(f"Schema validation issues for {yaml_file.name}: {validation_errors}")
                            file_info['error_message'] = f"Validation errors: {len(validation_errors)} issues"
                    else:
                        file_info['error_message'] = "Invalid schema format"
                        
                except yaml.YAMLError as e:
                    logger.warning(f"YAML parsing error for {yaml_file.name}: {e}")
                    file_info['error_message'] = f"YAML error: {str(e)}"
                except UnicodeDecodeError as e:
                    logger.warning(f"Encoding error for {yaml_file.name}: {e}")
                    file_info['error_message'] = "File encoding error"
                except Exception as e:
                    logger.warning(f"Schema loading failed for {yaml_file.name}: {e}")
                    file_info['error_message'] = f"Loading error: {str(e)}"
                
                schema_files.append(file_info)
                
            except Exception as e:
                logger.error(f"Unexpected error processing schema file {yaml_file.name}: {e}")
                file_info['error_message'] = f"Unexpected error: {str(e)}"
                schema_files.append(file_info)
        
        # Sort by filename for consistent ordering
        schema_files.sort(key=lambda x: x['filename'].lower())
        
    except Exception as e:
        logger.error(f"Critical error scanning schemas directory: {e}")
        # Return empty list on critical errors
        return []
    
    return schema_files


def load_schema(path: str) -> Optional[Dict[str, Any]]:
    """
    Load and parse a YAML schema file with comprehensive error handling.
    
    Args:
        path: Path to the schema file
        
    Returns:
        Dictionary containing schema data, or None if loading failed
    """
    try:
        schema_path = Path(path)
        
        # Check if file exists
        if not schema_path.exists():
            logger.error(f"Schema file not found: {path}")
            return None
        
        # Check if file is readable
        if not os.access(schema_path, os.R_OK):
            logger.error(f"Permission denied reading schema file: {path}")
            return None
        
        # Check file size (prevent loading extremely large files)
        try:
            file_size = schema_path.stat().st_size
            if file_size > 10 * 1024 * 1024:  # 10MB limit
                logger.error(f"Schema file too large: {path} ({file_size} bytes)")
                return None
            if file_size == 0:
                logger.warning(f"Schema file is empty: {path}")
                return {'title': '', 'description': '', 'fields': {}}
        except OSError as e:
            logger.error(f"Cannot access file stats for {path}: {e}")
            return None
        
        # Read and parse file with comprehensive error handling
        try:
            with open(schema_path, 'r', encoding='utf-8') as f:
                file_content = f.read()
                
                # Check for empty content
                if not file_content.strip():
                    logger.warning(f"Schema file is empty: {path}")
                    return {'title': '', 'description': '', 'fields': {}}
                
                schema_data = yaml.safe_load(file_content)
                
        except UnicodeDecodeError as e:
            logger.error(f"Encoding error reading {path}: {e}")
            # Try with different encodings as fallback
            try:
                with open(schema_path, 'r', encoding='latin-1') as f:
                    file_content = f.read()
                    schema_data = yaml.safe_load(file_content)
                logger.warning(f"Successfully loaded {path} with latin-1 encoding")
            except Exception as fallback_e:
                logger.error(f"Failed to load {path} with fallback encoding: {fallback_e}")
                return None
                
        except yaml.YAMLError as e:
            logger.error(f"YAML parsing error in {path}: {e}")
            return None
        except PermissionError as e:
            logger.error(f"Permission denied reading {path}: {e}")
            return None
        except OSError as e:
            logger.error(f"OS error reading {path}: {e}")
            return None
        
        # Validate loaded data
        if schema_data is None:
            logger.warning(f"Schema file contains only null/empty content: {path}")
            return {'title': '', 'description': '', 'fields': {}}
        
        if not isinstance(schema_data, dict):
            logger.error(f"Invalid schema format in {path}: root element is not a dictionary")
            return None
        
        # Ensure required structure exists with graceful defaults
        if 'fields' not in schema_data:
            logger.warning(f"Schema {path} missing 'fields' section, adding empty fields")
            schema_data['fields'] = {}
        elif not isinstance(schema_data['fields'], dict):
            logger.warning(f"Schema {path} has invalid 'fields' section, resetting to empty")
            schema_data['fields'] = {}
        
        # Ensure title and description exist
        if 'title' not in schema_data:
            schema_data['title'] = ''
        if 'description' not in schema_data:
            schema_data['description'] = ''
        
        logger.info(f"Successfully loaded schema: {path}")
        return schema_data
        
    except Exception as e:
        logger.error(f"Unexpected error loading schema {path}: {e}", exc_info=True)
        return None


def save_schema(path: str, schema_dict: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
    """
    Save schema dictionary to YAML file with comprehensive error handling.
    
    Args:
        path: Path where to save the schema file
        schema_dict: Dictionary containing schema data
        
    Returns:
        Tuple of (success: bool, error_message: Optional[str])
    """
    try:
        schema_path = Path(path)
        
        # Validate input data
        if not isinstance(schema_dict, dict):
            error_msg = "Schema data must be a dictionary"
            logger.error(f"Save failed for {path}: {error_msg}")
            return False, error_msg
        
        # Check if parent directory exists and is writable
        parent_dir = schema_path.parent
        try:
            parent_dir.mkdir(parents=True, exist_ok=True)
        except PermissionError:
            error_msg = f"Permission denied: Cannot create directory {parent_dir}"
            logger.error(f"Save failed for {path}: {error_msg}")
            return False, error_msg
        except OSError as e:
            error_msg = f"Cannot create directory {parent_dir}: {str(e)}"
            logger.error(f"Save failed for {path}: {error_msg}")
            return False, error_msg
        
        # Check if we can write to the target location
        if schema_path.exists() and not os.access(schema_path, os.W_OK):
            error_msg = f"Permission denied: Cannot write to {path}"
            logger.error(f"Save failed: {error_msg}")
            return False, error_msg
        
        if not os.access(parent_dir, os.W_OK):
            error_msg = f"Permission denied: Cannot write to directory {parent_dir}"
            logger.error(f"Save failed: {error_msg}")
            return False, error_msg
        
        # Check available disk space (basic check)
        try:
            import shutil
            free_space = shutil.disk_usage(parent_dir).free
            if free_space < 1024 * 1024:  # Less than 1MB free
                error_msg = "Insufficient disk space"
                logger.error(f"Save failed for {path}: {error_msg}")
                return False, error_msg
        except Exception as e:
            logger.warning(f"Could not check disk space: {e}")
        
        # Clean the schema dictionary - remove None values and empty strings
        try:
            cleaned_schema = _clean_schema_dict(schema_dict)
        except Exception as e:
            error_msg = f"Error cleaning schema data: {str(e)}"
            logger.error(f"Save failed for {path}: {error_msg}")
            return False, error_msg
        
        # Create backup if file exists
        backup_path = None
        if schema_path.exists():
            try:
                backup_path = schema_path.with_suffix(f"{schema_path.suffix}.backup")
                shutil.copy2(schema_path, backup_path)
                logger.debug(f"Created backup: {backup_path}")
            except Exception as e:
                logger.warning(f"Could not create backup for {path}: {e}")
        
        # Save with proper YAML formatting
        try:
            # Write to temporary file first for atomic operation
            temp_path = schema_path.with_suffix(f"{schema_path.suffix}.tmp")
            
            with open(temp_path, 'w', encoding='utf-8') as f:
                yaml.dump(
                    cleaned_schema,
                    f,
                    default_flow_style=False,
                    indent=2,
                    sort_keys=False,
                    allow_unicode=True,
                    width=float('inf')  # Prevent line wrapping
                )
            
            # Atomic move from temp to final location
            if os.name == 'nt':  # Windows
                if schema_path.exists():
                    schema_path.unlink()
                temp_path.rename(schema_path)
            else:  # Unix-like systems
                temp_path.rename(schema_path)
            
            # Clean up backup if save was successful
            if backup_path and backup_path.exists():
                try:
                    backup_path.unlink()
                except Exception as e:
                    logger.warning(f"Could not remove backup {backup_path}: {e}")
            
            logger.info(f"Successfully saved schema: {path}")
            return True, None
            
        except PermissionError as e:
            error_msg = f"Permission denied writing to {path}: {str(e)}"
            logger.error(f"Save failed: {error_msg}")
            return False, error_msg
        except OSError as e:
            error_msg = f"OS error writing to {path}: {str(e)}"
            logger.error(f"Save failed: {error_msg}")
            return False, error_msg
        except yaml.YAMLError as e:
            error_msg = f"YAML serialization error: {str(e)}"
            logger.error(f"Save failed for {path}: {error_msg}")
            return False, error_msg
        finally:
            # Clean up temp file if it exists
            temp_path = schema_path.with_suffix(f"{schema_path.suffix}.tmp")
            if temp_path.exists():
                try:
                    temp_path.unlink()
                except Exception as e:
                    logger.warning(f"Could not remove temp file {temp_path}: {e}")
        
    except Exception as e:
        error_msg = f"Unexpected error: {str(e)}"
        logger.error(f"Save failed for {path}: {error_msg}", exc_info=True)
        return False, error_msg


def delete_schema(path: str) -> Tuple[bool, Optional[str]]:
    """
    Delete a schema file with comprehensive error handling.
    
    Args:
        path: Path to the schema file to delete
        
    Returns:
        Tuple of (success: bool, error_message: Optional[str])
    """
    try:
        schema_path = Path(path)
        
        # Check if file exists
        if not schema_path.exists():
            error_msg = f"Schema file not found: {path}"
            logger.warning(error_msg)
            return False, error_msg
        
        # Check if file is actually a file (not a directory)
        if not schema_path.is_file():
            error_msg = f"Path is not a file: {path}"
            logger.error(error_msg)
            return False, error_msg
        
        # Check permissions
        if not os.access(schema_path, os.W_OK):
            error_msg = f"Permission denied: Cannot delete {path}"
            logger.error(error_msg)
            return False, error_msg
        
        # Check if parent directory is writable
        parent_dir = schema_path.parent
        if not os.access(parent_dir, os.W_OK):
            error_msg = f"Permission denied: Cannot modify directory {parent_dir}"
            logger.error(error_msg)
            return False, error_msg
        
        # Create backup before deletion (optional safety measure)
        backup_created = False
        backup_path = None
        try:
            backup_path = schema_path.with_suffix(f"{schema_path.suffix}.deleted")
            shutil.copy2(schema_path, backup_path)
            backup_created = True
            logger.debug(f"Created deletion backup: {backup_path}")
        except Exception as e:
            logger.warning(f"Could not create deletion backup for {path}: {e}")
        
        # Perform deletion
        try:
            schema_path.unlink()
            logger.info(f"Successfully deleted schema: {path}")
            
            # Remove backup after successful deletion
            if backup_created and backup_path and backup_path.exists():
                try:
                    backup_path.unlink()
                except Exception as e:
                    logger.warning(f"Could not remove deletion backup {backup_path}: {e}")
            
            return True, None
            
        except PermissionError as e:
            error_msg = f"Permission denied deleting {path}: {str(e)}"
            logger.error(error_msg)
            return False, error_msg
        except OSError as e:
            error_msg = f"OS error deleting {path}: {str(e)}"
            logger.error(error_msg)
            return False, error_msg
        
    except Exception as e:
        error_msg = f"Unexpected error deleting {path}: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return False, error_msg


def duplicate_schema(path: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Duplicate a schema file with comprehensive error handling and "_copy" suffix handling.
    
    Args:
        path: Path to the schema file to duplicate
        
    Returns:
        Tuple of (new_path: Optional[str], error_message: Optional[str])
    """
    try:
        source_path = Path(path)
        
        # Check if source file exists
        if not source_path.exists():
            error_msg = f"Source schema file not found: {path}"
            logger.error(error_msg)
            return None, error_msg
        
        # Check if source is actually a file
        if not source_path.is_file():
            error_msg = f"Source path is not a file: {path}"
            logger.error(error_msg)
            return None, error_msg
        
        # Check if source file is readable
        if not os.access(source_path, os.R_OK):
            error_msg = f"Permission denied: Cannot read source file {path}"
            logger.error(error_msg)
            return None, error_msg
        
        # Check if destination directory is writable
        parent_dir = source_path.parent
        if not os.access(parent_dir, os.W_OK):
            error_msg = f"Permission denied: Cannot write to directory {parent_dir}"
            logger.error(error_msg)
            return None, error_msg
        
        # Check available disk space
        try:
            source_size = source_path.stat().st_size
            free_space = shutil.disk_usage(parent_dir).free
            if free_space < source_size * 2:  # Need at least 2x file size
                error_msg = "Insufficient disk space for duplication"
                logger.error(f"Duplication failed for {path}: {error_msg}")
                return None, error_msg
        except Exception as e:
            logger.warning(f"Could not check disk space for duplication: {e}")
        
        # Generate new filename with _copy suffix
        base_name = source_path.stem
        extension = source_path.suffix
        
        # Handle multiple copies by adding numbers
        copy_counter = 1
        new_path = None
        
        while copy_counter <= 100:  # Prevent infinite loop
            if copy_counter == 1:
                new_name = f"{base_name}_copy{extension}"
            else:
                new_name = f"{base_name}_copy{copy_counter}{extension}"
            
            new_path = parent_dir / new_name
            
            if not new_path.exists():
                break
            
            copy_counter += 1
        
        if copy_counter > 100:
            error_msg = f"Too many copies exist for {path} (limit: 100)"
            logger.error(error_msg)
            return None, error_msg
        
        # Perform the copy operation with error handling
        try:
            # Defensive check for analyzer: ensure new_path is set and not None
            if new_path is None:
                error_msg = "Internal error: destination path was not determined"
                logger.error(f"Duplication failed for {path}: {error_msg}")
                return None, error_msg

            # Ensure we pass str paths to shutil.copy2 to satisfy type checkers
            shutil.copy2(str(source_path), str(new_path))
            
            # Verify the copy was successful
            if not new_path.exists():
                error_msg = "Copy operation completed but file was not created"
                logger.error(f"Duplication verification failed for {path}: {error_msg}")
                return None, error_msg
            
            # Verify file size matches
            try:
                source_size = source_path.stat().st_size
                copy_size = new_path.stat().st_size
                if source_size != copy_size:
                    error_msg = f"Copy size mismatch: source {source_size} bytes, copy {copy_size} bytes"
                    logger.error(f"Duplication verification failed for {path}: {error_msg}")
                    # Clean up incomplete copy
                    try:
                        new_path.unlink()
                    except Exception:
                        pass
                    return None, error_msg
            except Exception as e:
                logger.warning(f"Could not verify copy size for {path}: {e}")
            
            logger.info(f"Successfully duplicated schema: {path} -> {new_path}")
            return str(new_path), None
            
        except PermissionError as e:
            error_msg = f"Permission denied during copy: {str(e)}"
            logger.error(f"Duplication failed for {path}: {error_msg}")
            return None, error_msg
        except OSError as e:
            error_msg = f"OS error during copy: {str(e)}"
            logger.error(f"Duplication failed for {path}: {error_msg}")
            return None, error_msg
    except Exception as e:
        error_msg = f"Unexpected error during duplication: {str(e)}"
        logger.error(f"Duplication failed for {path}: {error_msg}", exc_info=True)
        return None, error_msg


# ============================================================================
# VALIDATION ENGINE - Field-level and Schema-level Validation
# ============================================================================

def validate_field(field_name: str, field_config: Dict[str, Any]) -> List[str]:
    """
    Validate individual field configuration checking.
    
    Args:
        field_name: Name of the field
        field_config: Field configuration dictionary
        
    Returns:
        List of validation errors
    """
    errors = []
    
    try:
        if not isinstance(field_config, dict):
            errors.append(f"Field '{field_name}' configuration must be a dictionary")
            return errors
        
        # Check required properties
        if 'type' not in field_config:
            errors.append(f"Field '{field_name}' missing required 'type' property")
        else:
            field_type = field_config['type']
            valid_types = ['string', 'integer', 'number', 'float', 'boolean', 'enum', 'date', 'datetime', 'array']
            if field_type not in valid_types:
                errors.append(f"Field '{field_name}' has invalid type '{field_type}'. Valid types: {valid_types}")
        
        if 'label' not in field_config:
            errors.append(f"Field '{field_name}' missing required 'label' property")
        
        # Validate field name format
        if not field_name or not isinstance(field_name, str):
            errors.append(f"Field name must be a non-empty string")
        elif len(field_name.strip()) == 0:
            errors.append(f"Field name cannot be empty or only whitespace")
        elif len(field_name) > 100:
            errors.append(f"Field name '{field_name}' is too long (max 100 characters)")
        
        # Validate type-specific constraints
        field_type = field_config.get('type')
        if field_type == 'string':
            errors.extend(validate_string_constraints(field_name, field_config))
        elif field_type in ['integer', 'number', 'float']:
            errors.extend(validate_numeric_constraints(field_name, field_config))
        elif field_type == 'enum':
            errors.extend(validate_enum_choices(field_name, field_config))
        elif field_type == 'boolean':
            errors.extend(validate_boolean_constraints(field_name, field_config))
        elif field_type in ['date', 'datetime']:
            errors.extend(validate_date_constraints(field_name, field_config))
        elif field_type == 'array':
            array_errors = ArrayFieldManager.validate_array_config(field_config)
            for error in array_errors:
                errors.append(f"Field '{field_name}' array: {error}")
        
    except Exception as e:
        errors.append(f"Error validating field '{field_name}': {str(e)}")
    
    return errors


def validate_regex_pattern(pattern: str) -> Optional[str]:
    """
    Validate regex pattern with safe regex compilation testing.
    
    Args:
        pattern: Regular expression pattern to validate
        
    Returns:
        Error message if invalid, None if valid
    """
    if not pattern:
        return None
    
    try:
        re.compile(pattern)
        return None
    except re.error as e:
        return f"Invalid regex pattern: {str(e)}"
    except Exception as e:
        return f"Error compiling regex: {str(e)}"


def validate_numeric_constraints(field_name: str, config: Dict[str, Any]) -> List[str]:
    """
    Validate numeric field constraints for min/max/step validation.
    
    Args:
        field_name: Name of the field
        config: Field configuration dictionary
        
    Returns:
        List of validation errors
    """
    errors = []
    
    # Validate min_value and max_value
    min_value = config.get('min_value')
    max_value = config.get('max_value')
    
    if min_value is not None and not isinstance(min_value, (int, float)):
        errors.append(f"Field '{field_name}' min_value must be a number")
    
    if max_value is not None and not isinstance(max_value, (int, float)):
        errors.append(f"Field '{field_name}' max_value must be a number")
    
    if min_value is not None and max_value is not None and min_value > max_value:
        errors.append(f"Field '{field_name}' min_value cannot be greater than max_value")
    
    # Validate step
    step = config.get('step')
    if step is not None:
        if not isinstance(step, (int, float)) or step <= 0:
            errors.append(f"Field '{field_name}' step must be a positive number")
    
    # Validate default value type and range
    default = config.get('default')
    if default is not None:
        field_type = config.get('type')
        if field_type == 'integer' and not isinstance(default, int):
            errors.append(f"Field '{field_name}' default value must be an integer")
        elif field_type in ['number', 'float'] and not isinstance(default, (int, float)):
            errors.append(f"Field '{field_name}' default value must be a number")
        
        # Check if default is within range
        if isinstance(default, (int, float)):
            if min_value is not None and default < min_value:
                errors.append(f"Field '{field_name}' default value is below minimum value")
            if max_value is not None and default > max_value:
                errors.append(f"Field '{field_name}' default value is above maximum value")
    
    return errors


def validate_enum_choices(field_name: str, config: Dict[str, Any]) -> List[str]:
    """
    Validate enum field choices and default values.
    
    Args:
        field_name: Name of the field
        config: Field configuration dictionary
        
    Returns:
        List of validation errors
    """
    errors = []
    
    # Validate choices
    choices = config.get('choices')
    if choices is None:
        errors.append(f"Field '{field_name}' of type 'enum' must have 'choices' property")
    elif not isinstance(choices, list):
        errors.append(f"Field '{field_name}' choices must be a list")
    elif len(choices) == 0:
        errors.append(f"Field '{field_name}' choices must be a non-empty list")
    else:
        # Check for duplicate choices
        if len(choices) != len(set(choices)):
            errors.append(f"Field '{field_name}' choices contain duplicates")
        
        # Check that all choices are strings or numbers
        for i, choice in enumerate(choices):
            if not isinstance(choice, (str, int, float)):
                errors.append(f"Field '{field_name}' choice at index {i} must be a string or number")
    
    # Validate default value is in choices
    default = config.get('default')
    if default is not None and choices is not None and isinstance(choices, list):
        if default not in choices:
            errors.append(f"Field '{field_name}' default value '{default}' not in choices list")
    
    return errors


def validate_string_constraints(field_name: str, config: Dict[str, Any]) -> List[str]:
    """
    Validate string field specific constraints.
    
    Args:
        field_name: Name of the field
        config: Field configuration dictionary
        
    Returns:
        List of validation errors
    """
    errors = []
    
    # Validate min_length and max_length
    min_length = config.get('min_length')
    max_length = config.get('max_length')
    
    if min_length is not None:
        if not isinstance(min_length, int) or min_length < 0:
            errors.append(f"Field '{field_name}' min_length must be a non-negative integer")
    
    if max_length is not None:
        if not isinstance(max_length, int) or max_length < 0:
            errors.append(f"Field '{field_name}' max_length must be a non-negative integer")
    
    if min_length is not None and max_length is not None and min_length > max_length:
        errors.append(f"Field '{field_name}' min_length cannot be greater than max_length")
    
    # Validate regex pattern
    pattern = config.get('pattern')
    if pattern is not None:
        pattern_error = validate_regex_pattern(pattern)
        if pattern_error:
            errors.append(f"Field '{field_name}' has {pattern_error}")
    
    # Validate default value length
    default = config.get('default')
    if default is not None:
        if not isinstance(default, str):
            errors.append(f"Field '{field_name}' default value must be a string")
        else:
            if min_length is not None and len(default) < min_length:
                errors.append(f"Field '{field_name}' default value is shorter than minimum length")
            if max_length is not None and len(default) > max_length:
                errors.append(f"Field '{field_name}' default value is longer than maximum length")
            
            # Validate default against pattern
            if pattern is not None:
                try:
                    if not re.match(pattern, default):
                        errors.append(f"Field '{field_name}' default value does not match pattern")
                except re.error:
                    # Pattern error already caught above
                    pass
    
    return errors


def validate_boolean_constraints(field_name: str, config: Dict[str, Any]) -> List[str]:
    """
    Validate boolean field constraints.
    
    Args:
        field_name: Name of the field
        config: Field configuration dictionary
        
    Returns:
        List of validation errors
    """
    errors = []
    
    # Validate default value type
    default = config.get('default')
    if default is not None and not isinstance(default, bool):
        errors.append(f"Field '{field_name}' default value must be a boolean (true/false)")
    
    return errors


def validate_date_constraints(field_name: str, config: Dict[str, Any]) -> List[str]:
    """
    Validate date/datetime field constraints.
    
    Args:
        field_name: Name of the field
        config: Field configuration dictionary
        
    Returns:
        List of validation errors
    """
    errors = []
    
    # Validate default value format (if provided)
    default = config.get('default')
    if default is not None:
        if not isinstance(default, str):
            errors.append(f"Field '{field_name}' default value must be a string")
        else:
            field_type = config.get('type')
            if field_type == 'date':
                # Validate ISO date format (YYYY-MM-DD)
                try:
                    from datetime import datetime
                    datetime.strptime(default, '%Y-%m-%d')
                except ValueError:
                    errors.append(f"Field '{field_name}' default value must be in ISO date format (YYYY-MM-DD)")
            elif field_type == 'datetime':
                # Validate ISO datetime format
                try:
                    from datetime import datetime
                    # Try common ISO formats
                    formats = ['%Y-%m-%dT%H:%M:%S', '%Y-%m-%dT%H:%M:%SZ', '%Y-%m-%dT%H:%M:%S.%f']
                    parsed = False
                    for fmt in formats:
                        try:
                            datetime.strptime(default, fmt)
                            parsed = True
                            break
                        except ValueError:
                            continue
                    if not parsed:
                        errors.append(f"Field '{field_name}' default value must be in ISO datetime format")
                except Exception:
                    errors.append(f"Field '{field_name}' default value has invalid datetime format")
    
    return errors


def validate_schema_structure(schema: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """
    Validate overall schema structure and return validation results.
    
    Args:
        schema: Schema dictionary to validate
        
    Returns:
        Tuple of (is_valid, list_of_errors)
    """
    errors = []
    
    try:
        # Check if schema is a dictionary
        if not isinstance(schema, dict):
            errors.append("Schema must be a dictionary")
            return False, errors
        
        # Check for fields section
        if 'fields' not in schema:
            errors.append("Schema missing 'fields' section")
        else:
            fields = schema['fields']
            if not isinstance(fields, dict):
                errors.append("'fields' section must be a dictionary")
            else:
                # Validate field names for uniqueness and format
                field_name_errors = validate_field_names(fields)
                errors.extend(field_name_errors)
                
                # Validate each field
                for field_name, field_config in fields.items():
                    field_errors = validate_field(field_name, field_config)
                    errors.extend(field_errors)
        
        # Check optional title and description
        if 'title' in schema and not isinstance(schema['title'], str):
            errors.append("'title' must be a string")
        
        if 'description' in schema and not isinstance(schema['description'], str):
            errors.append("'description' must be a string")
        
        is_valid = len(errors) == 0
        return is_valid, errors
        
    except Exception as e:
        errors.append(f"Validation error: {str(e)}")
        return False, errors


def validate_field_names(fields: Dict[str, Any]) -> List[str]:
    """
    Validate field name uniqueness and format checking.
    
    Args:
        fields: Dictionary of field configurations
        
    Returns:
        List of validation errors
    """
    errors = []
    
    try:
        field_names = list(fields.keys())
        
        # Check for empty field names
        for field_name in field_names:
            errors.extend(_validate_single_field_name(field_name))
        
        # Check for duplicate field names (case-insensitive)
        lower_names = [name.lower() for name in field_names if isinstance(name, str)]
        if len(lower_names) != len(set(lower_names)):
            errors.append("Field names must be unique (case-insensitive)")
        
        # Check for reserved field names
        reserved_names = ['id', 'type', 'class', 'name', 'value']
        for field_name in field_names:
            if isinstance(field_name, str) and field_name.lower() in reserved_names:
                errors.append(f"Field name '{field_name}' is reserved and cannot be used")
        
    except Exception as e:
        errors.append(f"Error validating field names: {str(e)}")
    
    return errors


def _validate_single_field_name(field_name: Any) -> List[str]:
    """Validate a single field name and return its validation errors."""
    if not field_name or not isinstance(field_name, str):
        return ["Field names must be non-empty strings"]
    if len(field_name.strip()) == 0:
        return ["Field names cannot be empty or only whitespace"]
    if len(field_name) > 100:
        return [f"Field name '{field_name}' is too long (max 100 characters)"]
    return []





def _clean_schema_dict(schema_dict: Dict[str, Any]) -> Dict[str, Any]:
    """
    Clean schema dictionary by removing None values and empty strings.
    
    Args:
        schema_dict: Dictionary to clean
        
    Returns:
        Cleaned dictionary
    """
    def clean_value(value):
        if isinstance(value, dict):
            cleaned = {}
            for k, v in value.items():
                cleaned_v = clean_value(v)
                if cleaned_v is not None and cleaned_v != "":
                    cleaned[k] = cleaned_v
            return cleaned if cleaned else None
        elif isinstance(value, list):
            cleaned = [clean_value(item) for item in value]
            cleaned = [item for item in cleaned if item is not None and item != ""]
            return cleaned if cleaned else None
        elif value is None or value == "":
            return None
        else:
            return value
    
    result = clean_value(schema_dict)
    if isinstance(result, dict):
        return result
    # Ensure we always return a dictionary
    return {}
