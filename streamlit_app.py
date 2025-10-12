"""
Main Streamlit application for JSON QA webapp.
Schema-driven QA tool for validating and correcting JSON extracted from PDF documents.
"""

import streamlit as st
import os
from pathlib import Path
import logging
from datetime import datetime

# Import utility modules
from utils.file_utils import (
    initialize_directories,
    ensure_directories_exist, 
    cleanup_stale_locks,
    list_unverified_files,
    claim_file,
    release_file,
    load_json_file,
    save_corrected_json,
    append_audit_log,
    get_pdf_path,
    read_audit_logs
)
from utils.schema_loader import get_schema_for_file, load_schema, load_config, get_config_value
from utils.model_builder import create_model_from_schema, validate_model_data
from utils.diff_utils import calculate_diff, format_diff_for_display, has_changes, create_audit_diff_entry

def get_logging_level(level_str):
    """Map string logging level to logging constant."""
    level_map = {
        'DEBUG': logging.DEBUG,
        'INFO': logging.INFO,
        'WARNING': logging.WARNING,
        'ERROR': logging.ERROR,
        'CRITICAL': logging.CRITICAL
    }
    return level_map.get(level_str.upper(), logging.INFO)

# Configure logging dynamically from config
try:
    log_level_str = get_config_value('logging', 'level', 'INFO')
    log_level = get_logging_level(log_level_str)
    logging.basicConfig(level=log_level)
    logger = logging.getLogger(__name__)
    logger.info(f"Logging configured to level: {log_level_str}")
except Exception as e:
    # Fallback to INFO if config reading fails
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    logger.error(f"Failed to configure logging from config: {e}, using INFO level")

# Load configuration early
try:
    config = load_config()
    page_title = get_config_value('ui', 'page_title', 'JSON QA Webapp')
    lock_timeout = get_config_value('processing', 'lock_timeout', 60)
    app_version = get_config_value('app', 'version', 'Unknown')
    logger.info(f"Starting app version: {app_version}")
except Exception as e:
    logger.error(f"Failed to load configuration: {e}")
    page_title = "JSON QA Webapp"
    lock_timeout = 60

# Page configuration
st.set_page_config(
    page_title=page_title,
    page_icon="📋",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Constants
DEFAULT_USER = "operator"
LOCK_TIMEOUT_MINUTES = lock_timeout


def main():
    """Main application entry point."""
    from utils.error_handler import ErrorHandler, ErrorType
    from utils.ui_feedback import show_loading
    
    try:
        # Initialize application with loading indicator
        with show_loading("Initializing application..."):
            setup_directories()
            init_session_state()
            cleanup_stale_locks(LOCK_TIMEOUT_MINUTES)
        
        # Render application
        render_header()
        render_sidebar()
        render_main_content()
        
    except Exception as e:
        ErrorHandler.handle_error(
            e, 
            "application startup", 
            ErrorType.SYSTEM,
            recovery_options=ErrorHandler.create_recovery_options("system")
        )


def setup_directories():
    """Initialize directory configuration and ensure all required directories exist."""
    try:
        # Initialize directory configuration system
        if not initialize_directories():
            logger.error("Failed to initialize directory configuration")
            st.error("❌ **Directory Configuration Error**")
            st.error("Failed to initialize directory configuration. Please check your config.yaml file and directory permissions.")
            st.info("💡 **Troubleshooting:**")
            st.info("• Ensure config.yaml exists and has valid directory configuration")
            st.info("• Check that the application has write permissions to create directories")
            st.info("• Verify that configured directory paths are valid")
            st.stop()
        
        # Fallback to legacy method for additional safety
        ensure_directories_exist()
        logger.info("Directory setup completed successfully")
        
        # Validate configuration and schema
        validate_configuration()
        
    except Exception as e:
        logger.error(f"Failed to setup directories: {e}")
        st.error("❌ **Critical Error During Startup**")
        st.error(f"Directory setup failed: {str(e)}")
        st.info("💡 **Recovery Options:**")
        st.info("• Check application logs for detailed error information")
        st.info("• Verify file system permissions")
        st.info("• Ensure config.yaml is properly formatted")
        st.info("• Try restarting the application")
        st.stop()


def validate_configuration():
    """Validate configuration and provide user feedback."""
    try:
        from utils.config_loader import load_config, validate_config, get_config_summary
        from utils.directory_validator import DirectoryValidator
        from utils.file_utils import get_directories
        
        # Load and validate configuration
        config = load_config()
        is_valid = validate_config(config)
        
        if not is_valid:
            st.warning("⚠️ **Configuration Issues Detected**")
            st.warning("Some configuration settings are invalid, using defaults where necessary.")
        
        # Get configuration summary for user feedback
        config_summary = get_config_summary(config)
        
        # Validate directory accessibility
        dirs = get_directories()
        validator = DirectoryValidator()
        validation_results = validator.validate_all_paths(dirs)
        validation_summary = validator.get_validation_summary(validation_results)
        
        # Show configuration status in sidebar or as success message
        if validation_summary['ready_directories'] == validation_summary['total_directories']:
            logger.info("✅ All directories are ready and accessible")
            # Custom directory UI message removed to avoid taking up space.
            # If you want a compact indicator later, consider using a small st.caption or a status icon.
        else:
            st.warning("⚠️ **Directory Configuration Issues**")
            if validation_summary['permission_issues'] > 0:
                st.warning(f"• {validation_summary['permission_issues']} directories have permission issues")
            if validation_summary['missing_directories'] > 0:
                st.info(f"• {validation_summary['missing_directories']} directories were created automatically")
        
        # Validate schema
        primary_schema = get_config_value('schema', 'primary_schema', 'default_schema.yaml')
        
        try:
            from utils.schema_loader import get_configured_schema
            schema = get_configured_schema()
            
            if schema:
                logger.info(f"✅ Schema validated: {primary_schema}")
            else:
                st.warning("⚠️ **Schema Validation Warning**")
                st.warning(f"Primary schema '{primary_schema}' not found, using fallback mechanisms")
                
        except Exception as schema_error:
            logger.warning(f"Schema validation failed: {schema_error}")
            st.warning("⚠️ **Schema Loading Issues**")
            st.warning("Schema validation failed, but fallback mechanisms are in place")
            
    except Exception as e:
        logger.error(f"Configuration validation failed: {e}")
        st.error("❌ **Configuration Validation Failed**")
        st.error(f"Error: {str(e)}")
        st.info("💡 **Troubleshooting:**")
        st.info("• Check config.yaml file format and content")
        st.info("• Verify schema files are accessible")
        st.info("• Check application logs for detailed errors")
        # Don't raise - let the app continue with defaults


def init_session_state():
    """Initialize session state variables."""
    if 'current_page' not in st.session_state:
        st.session_state.current_page = 'queue'
    
    if 'current_file' not in st.session_state:
        st.session_state.current_file = None
    
    if 'current_user' not in st.session_state:
        st.session_state.current_user = DEFAULT_USER
    
    if 'lock_timeout' not in st.session_state:
        st.session_state.lock_timeout = LOCK_TIMEOUT_MINUTES
    
    if 'form_data' not in st.session_state:
        st.session_state.form_data = {}
    
    if 'original_data' not in st.session_state:
        st.session_state.original_data = {}
    
    if 'schema' not in st.session_state:
        st.session_state.schema = {}
    
    if 'model_class' not in st.session_state:
        st.session_state.model_class = None


def render_header():
    """Render application header."""
    # Custom CSS to reduce header sizes and spacing
    st.markdown("""
    <style>
    /* Eliminate ALL top spacing */
    .main .block-container {
        padding-top: 0rem !important;
        padding-bottom: 1rem !important;
        max-width: 100% !important;
        margin-top: 0rem !important;
    }
    
    /* Remove top margin from main content area */
    .main {
        padding-top: 0rem !important;
        margin-top: 0rem !important;
    }
    
    /* Remove top spacing from the entire app */
    .appview-container .main .block-container {
        padding-top: 0rem !important;
        margin-top: 0rem !important;
    }
    
    /* Target the root container */
    .stApp > div:first-child {
        margin-top: 0rem !important;
        padding-top: 0rem !important;
    }
    
    /* Remove Streamlit's default header spacing */
    .stApp > header {
        height: 0rem !important;
        display: none !important;
    }
    
    /* Remove toolbar spacing */
    .stToolbar {
        display: none !important;
    }
    
    /* Remove any top margins from the first elements */
    .main > div:first-child {
        margin-top: 0rem !important;
        padding-top: 0rem !important;
    }
    
    /* Force remove all top spacing */
    * {
        margin-top: 0rem !important;
    }
    
    /* Specifically target the title container */
    .main h1:first-child {
        margin-top: 0rem !important;
        padding-top: 0rem !important;
    }
    
    /* Make main title same size as h2 Navigation */
    .main h1,
    h1#json-qa-webapp,
    .main h1#json-qa-webapp {
        font-size: 1.2rem !important;
        margin-bottom: 0.2rem !important;
        margin-top: 0rem !important;
        line-height: 1.1 !important;
        padding-top: 0rem !important;
        font-weight: 600 !important;
    }
    
    /* Reduce header sizes throughout the app */
    .main h2 {
        font-size: 1.0rem !important;
        margin-bottom: 0.2rem !important;
        margin-top: 0.3rem !important;
    }
    
    /* Make subheaders (h3) same size as Navigation header */
    .main h3,
    h3#file-queue,
    .main h3#file-queue {
        font-size: 1.2rem !important;
        margin-bottom: 0.2rem !important;
        margin-top: 0.3rem !important;
        font-weight: 600 !important;
    }
    
    /* Target the specific Streamlit emotion cache classes for metrics */
    .st-emotion-cache-1q82h82,
    .st-emotion-cache-1rrh444,
    [data-testid="metric-container"] .st-emotion-cache-1q82h82,
    [data-testid="metric-container"] .st-emotion-cache-1rrh444 {
        font-size: 0.7rem !important;
        font-weight: 700 !important;
        line-height: 1.2 !important;
    }
    
    /* Override any large font sizes in metric containers */
    [data-testid="metric-container"] * {
        font-size: 0.7rem !important;
    }
    
    /* Target metric values specifically */
    [data-testid="metric-container"] [data-testid="metric-value"],
    [data-testid="metric-container"] div[data-testid="metric-value"] {
        font-size: 0.7rem !important;
        font-weight: 700 !important;
    }
    
    /* Target metric labels */
    [data-testid="metric-container"] [data-testid="metric-label"],
    [data-testid="metric-container"] div[data-testid="metric-label"] {
        font-size: 0.7rem !important;
        font-weight: 400 !important;
    }
    
    /* Nuclear option - override ALL large font sizes */
    div[style*="font-size: 2.25rem"],
    div[class*="st-emotion-cache"] {
        font-size: 0.7rem !important;
    }
    
    /* Target any element with large font size inside metric containers */
    [data-testid="metric-container"] div[style*="font-size"],
    [data-testid="metric-container"] div[class*="emotion-cache"] {
        font-size: 0.7rem !important;
    }
    
    /* Reduce spacing in metrics significantly */
    [data-testid="metric-container"] {
        margin-bottom: 0.1rem !important;
        padding: 0.2rem 0 !important;
    }
    
    /* Reduce divider spacing */
    hr {
        margin: 0.3rem 0 !important;
    }
    
    /* Reduce spacing after info boxes */
    .stAlert {
        margin-bottom: 0.2rem !important;
        padding: 0.4rem !important;
        font-size: 0.8rem !important;
    }
    
    /* Reduce spacing between elements */
    .element-container {
        margin-bottom: 0.2rem !important;
    }
    
    /* Compact markdown text */
    .main .markdown-text-container {
        margin-bottom: 0.1rem !important;
    }
    
    /* Remove extra spacing from first element */
    .main .block-container > div:first-child {
        margin-top: 0rem !important;
        padding-top: 0rem !important;
    }
    
    /* Make regular text smaller */
    .main p {
        font-size: 0.85rem !important;
        margin-bottom: 0.2rem !important;
    }
    
    /* Make selectboxes more compact */
    .stSelectbox > div > div {
        padding: 0.2rem 0.5rem !important;
        font-size: 0.8rem !important;
    }
    
    /* Make buttons more compact */
    .stButton > button {
        padding: 0.3rem 0.8rem !important;
        font-size: 0.8rem !important;
        height: auto !important;
    }
    
    /* Reduce spacing in columns */
    .row-widget {
        margin-bottom: 0.2rem !important;
    }
    
    /* Make file list items more compact */
    .element-container div[data-testid="column"] {
        padding: 0.1rem !important;
    }
    
    /* Reduce spacing around containers */
    .block-container .element-container {
        margin-bottom: 0.1rem !important;
    }
    </style>
    """, unsafe_allow_html=True)
    
    app_name = get_config_value('app', 'name', 'JSON QA Webapp')
    st.title(f"📋 {app_name}")
    
    # Combine description and schema info on one line
    primary_schema = get_config_value('schema', 'primary_schema', 'default_schema.yaml')
    st.markdown(f"**Schema-driven validation and correction of JSON data extracted from PDF documents** | 📄 Current Schema: **{primary_schema}**")
    
    # Compact status bar
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        unverified_count = len(list_unverified_files())
        st.metric("Unverified Files", unverified_count)
    
    with col2:
        current_file = st.session_state.get('current_file', 'None')
        st.metric("Current File", current_file if current_file else 'None')
    
    with col3:
        current_user = st.session_state.get('current_user', DEFAULT_USER)
        st.metric("Current User", current_user)
    
    with col4:
        current_page = st.session_state.get('current_page', 'queue').title()
        st.metric("Current View", current_page)


def render_sidebar():
    """Render application sidebar."""
    with st.sidebar:
        sidebar_title = get_config_value('ui', 'sidebar_title', 'Navigation')
        st.header(sidebar_title)
        
        # Page navigation
        page = st.radio(
            "Select View:",
            options=['queue', 'edit', 'audit', 'schema_editor'],
            format_func=lambda x: {
                'queue': '📋 Queue View',
                'edit': '✏️ Edit View', 
                'audit': '📊 Audit View',
                'schema_editor': '🔧 Schema Editor'
            }[x],
            index=['queue', 'edit', 'audit', 'schema_editor'].index(st.session_state.current_page)
        )
        
        if page != st.session_state.current_page:
            st.session_state.current_page = page
            st.rerun()
        
        st.divider()
        
        # User settings
        st.header("Settings")
        
        new_user = st.text_input(
            "Current User:",
            value=st.session_state.current_user,
            help="Your username for audit logging"
        )
        
        if new_user != st.session_state.current_user:
            st.session_state.current_user = new_user
        
        new_timeout = st.number_input(
            "Lock Timeout (minutes):",
            min_value=5,
            max_value=240,
            value=st.session_state.lock_timeout,
            help="How long to hold file locks"
        )
        
        if new_timeout != st.session_state.lock_timeout:
            st.session_state.lock_timeout = new_timeout
        
        st.divider()
        
        # Quick actions
        st.header("Quick Actions")
        
        if st.button("🔄 Refresh Data", help="Refresh file list and cleanup stale locks"):
            cleanup_stale_locks(st.session_state.lock_timeout)
            st.rerun()
        
        if st.button("🔓 Release Current File", help="Release lock on current file"):
            if st.session_state.current_file:
                if release_file(st.session_state.current_file):
                    st.success(f"Released {st.session_state.current_file}")
                    st.session_state.current_file = None
                    st.session_state.current_page = 'queue'
                    st.rerun()
                else:
                    st.error("Failed to release file")
            else:
                st.info("No file currently claimed")
        
        st.divider()
        
        # Page-specific sidebar content
        if st.session_state.current_page == 'queue':
            from utils.queue_view import QueueView
            QueueView.render_queue_stats()
        elif st.session_state.current_page == 'edit':
            from utils.edit_view import EditView
            EditView.render_edit_sidebar()
        elif st.session_state.current_page == 'audit':
            from utils.audit_view import AuditView
            AuditView.render_audit_sidebar()
        elif st.session_state.current_page == 'schema_editor':
            # Schema editor sidebar content will be added in future tasks
            st.markdown("**Schema Editor**")
            st.markdown("Manage validation schemas")


def render_main_content():
    """Render main content area based on current page."""
    page = st.session_state.current_page
    
    if page == 'queue':
        render_queue_view()
    elif page == 'edit':
        render_edit_view()
    elif page == 'audit':
        render_audit_view()
    elif page == 'schema_editor':
        render_schema_editor_view()
    else:
        st.error(f"Unknown page: {page}")


def render_queue_view():
    """Render the queue view showing unverified files."""
    from utils.queue_view import QueueView
    
    try:
        QueueView.render()
    except Exception as e:
        st.error(f"Error loading file queue: {str(e)}")
        logger.error(f"Error in queue view: {e}", exc_info=True)


def render_edit_view():
    """Render the edit view for validating and correcting JSON data."""
    from utils.edit_view import EditView
    
    try:
        EditView.render(cancel_callback=cancel_editing)
    except Exception as e:
        st.error(f"Error in edit view: {str(e)}")
        logger.error(f"Error in edit view: {e}", exc_info=True)


def render_pdf_preview():
    """Render PDF preview in the left column."""
    from utils.pdf_viewer import PDFViewer
    
    try:
        PDFViewer.render_pdf_preview(st.session_state.current_file)
    except Exception as e:
        st.error(f"Error loading PDF preview: {str(e)}")
        logger.error(f"Error in PDF preview: {e}", exc_info=True)


def render_dynamic_form():
    """Render dynamic form based on schema."""
    from utils.form_generator import FormGenerator
    from utils.session_manager import SessionManager
    
    try:
        if not st.session_state.schema:
            st.error("Schema not loaded")
            return
        
        # Render the dynamic form
        updated_data = FormGenerator.render_dynamic_form(
            st.session_state.schema,
            st.session_state.form_data
        )
        
        # Update session state if data changed
        if updated_data != st.session_state.form_data:
            SessionManager.set_form_data(updated_data)
            st.rerun()
    
    except Exception as e:
        st.error(f"Error rendering form: {str(e)}")
        logger.error(f"Error in dynamic form: {e}", exc_info=True)


def render_diff_section():
    """Render the diff section showing changes."""
    st.subheader("🔍 Changes Preview")
    
    if not st.session_state.original_data or not st.session_state.form_data:
        st.info("No data to compare")
        return
    
    try:
        diff = calculate_diff(st.session_state.original_data, st.session_state.form_data)
        
        if has_changes(diff):
            # Get original and modified data from session state if available
            original_data = st.session_state.get('original_data')
            modified_data = st.session_state.get('current_data')
            formatted_diff = format_diff_for_display(diff, original_data, modified_data)
            st.markdown(formatted_diff)
        else:
            st.success("✅ No changes detected")
    
    except Exception as e:
        st.error(f"Error calculating diff: {str(e)}")


def render_action_buttons():
    """Render action buttons for submit/cancel."""
    st.divider()
    
    col1, col2, col3 = st.columns([1, 1, 2])
    
    with col1:
        if st.button("💾 Submit Changes", type="primary", help="Save corrections and release file"):
            submit_changes()
    
    with col2:
        if st.button("❌ Cancel", help="Cancel editing and release file"):
            cancel_editing()
    
    with col3:
        if st.button("🔄 Reset to Original", help="Reset form to original data"):
            st.session_state.form_data = st.session_state.original_data.copy()
            st.rerun()


def submit_changes():
    """Submit the corrected data."""
    try:
        if not st.session_state.current_file or not st.session_state.form_data:
            st.error("No data to submit")
            return
        
        # Validate data
        if st.session_state.model_class:
            validation_errors = validate_model_data(st.session_state.form_data, st.session_state.model_class)
            if validation_errors:
                st.error("❌ Validation failed:")
                for error in validation_errors:
                    st.error(f"  • {error}")
                return
        
        # Save corrected data
        if save_corrected_json(st.session_state.current_file, st.session_state.form_data):
            # Create audit entry
            audit_entry = create_audit_diff_entry(
                st.session_state.original_data,
                st.session_state.form_data
            )
            audit_entry.update({
                'filename': st.session_state.current_file,
                'timestamp': datetime.now().isoformat(),
                'user': st.session_state.current_user,
                'action': 'corrected'
            })
            
            # Log audit entry
            append_audit_log(audit_entry)
            
            # Release file
            release_file(st.session_state.current_file)
            
            # Reset session
            reset_session()
            
            st.success("✅ Changes submitted successfully!")
            st.session_state.current_page = 'queue'
            st.rerun()
        else:
            st.error("❌ Failed to save corrected data")
    
    except Exception as e:
        st.error(f"Error submitting changes: {str(e)}")
        logger.error(f"Error submitting changes: {e}", exc_info=True)


def cancel_editing():
    """Cancel editing and release the file."""
    try:
        # Proceed with cancel (confirmation handled in EditView)
        if st.session_state.current_file:
            release_file(st.session_state.current_file)
        
        reset_session()
        st.session_state.current_page = 'queue'
        st.session_state.show_cancel_confirm = False
        st.info("✅ Editing cancelled, file released")
        st.rerun()
    
    except Exception as e:
        st.error(f"Error cancelling: {str(e)}")


def has_unsaved_changes():
    """Check if there are unsaved changes in the form."""
    original = st.session_state.get('original_data', {})
    current = st.session_state.get('form_data', {})
    return original != current


def reset_session():
    """Reset session state for editing."""
    st.session_state.current_file = None
    st.session_state.form_data = {}
    st.session_state.original_data = {}
    st.session_state.schema = {}
    st.session_state.model_class = None


def render_audit_view():
    """Render the audit view showing processed files and changes."""
    from utils.audit_view import AuditView
    
    try:
        AuditView.render()
    except Exception as e:
        st.error(f"Error loading audit view: {str(e)}")
        logger.error(f"Error in audit view: {e}", exc_info=True)


def render_schema_editor_view():
    """Render the schema editor view for managing YAML schemas."""
    from utils.schema_editor_view import SchemaEditor
    
    try:
        SchemaEditor.render()
    except Exception as e:
        st.error(f"Error loading schema editor: {str(e)}")
        logger.error(f"Error in schema editor: {e}", exc_info=True)


if __name__ == "__main__":
    main()