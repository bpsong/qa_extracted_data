"""
Session state management for Streamlit JSON QA webapp.
Handles session persistence, state transitions, and cleanup.
"""

import streamlit as st
from typing import Dict, Any, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

# Default values
DEFAULT_USER = "operator"
DEFAULT_LOCK_TIMEOUT = 60
DEFAULT_PAGE = "queue"


class SessionManager:
    """Manages Streamlit session state for the JSON QA webapp."""
    
    @staticmethod
    def initialize():
        """Initialize all session state variables with default values."""
        defaults = {
            'current_page': DEFAULT_PAGE,
            'current_file': None,
            'current_user': DEFAULT_USER,
            'lock_timeout': DEFAULT_LOCK_TIMEOUT,
            'form_data': {},
            'original_data': {},
            'schema': {},
            # New session keys related to active schema and schema metadata.
            # These are intentionally initialized here in an idempotent way so
            # calling initialize() multiple times is safe and existing keys
            # are not overwritten.
            'active_schema': None,
            'active_schema_mtime': None,
            'schema_fields': [],
            'schema_version': 0,
            'deprecated_fields_current_doc': [],
            'model_class': None,
            'last_activity': datetime.now(),
            'session_id': None,
            'edit_mode': False,
            'unsaved_changes': False,
            'validation_errors': [],
            'diff_cache': {},
            'ui_state': {
                'sidebar_expanded': True,
                'show_advanced': False,
                'auto_save': False,
                'theme': 'light'
            }
        }
        
        for key, default_value in defaults.items():
            if key not in st.session_state:
                st.session_state[key] = default_value
        
        # Generate session ID if not exists
        if not st.session_state.session_id:
            st.session_state.session_id = f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        logger.info(f"Session initialized: {st.session_state.session_id}")
    
    @staticmethod
    def get_current_page() -> str:
        """Get the current page."""
        return st.session_state.get('current_page', DEFAULT_PAGE)
    
    @staticmethod
    def set_current_page(page: str):
        """Set the current page and handle page transitions."""
        old_page = st.session_state.get('current_page')
        
        if old_page != page:
            logger.info(f"Page transition: {old_page} -> {page}")
            
            # Handle page-specific cleanup
            if old_page == 'edit' and page != 'edit':
                SessionManager._cleanup_edit_state()
            
            st.session_state.current_page = page
            SessionManager.update_activity()
    
    @staticmethod
    def get_current_file() -> Optional[str]:
        """Get the currently claimed file."""
        return st.session_state.get('current_file')
    
    @staticmethod
    def set_current_file(filename: Optional[str]):
        """Set the current file and initialize related state."""
        old_file = st.session_state.get('current_file')
        
        if old_file != filename:
            logger.info(f"File changed: {old_file} -> {filename}")
            
            # Clear file-specific state when changing files
            if old_file and old_file != filename:
                SessionManager._clear_file_state()
            
            st.session_state.current_file = filename
            
            if filename:
                st.session_state.edit_mode = True
            else:
                st.session_state.edit_mode = False
            
            SessionManager.update_activity()
    
    @staticmethod
    def get_current_user() -> str:
        """Get the current user."""
        return st.session_state.get('current_user', DEFAULT_USER)
    
    @staticmethod
    def set_current_user(user: str):
        """Set the current user."""
        if user != st.session_state.get('current_user'):
            logger.info(f"User changed: {st.session_state.get('current_user')} -> {user}")
            st.session_state.current_user = user
            SessionManager.update_activity()
    
    @staticmethod
    def get_lock_timeout() -> int:
        """Get the lock timeout in minutes."""
        return st.session_state.get('lock_timeout', DEFAULT_LOCK_TIMEOUT)
    
    @staticmethod
    def set_lock_timeout(timeout: int):
        """Set the lock timeout."""
        st.session_state.lock_timeout = max(5, min(240, timeout))  # Clamp between 5-240 minutes
    
    @staticmethod
    def get_form_data() -> Dict[str, Any]:
        """Get the current form data."""
        return st.session_state.get('form_data', {})
    
    @staticmethod
    def set_form_data(data: Dict[str, Any]):
        """Set the form data and mark as having unsaved changes."""
        original_data = st.session_state.get('original_data', {})
        
        # Check if data has changed from original
        has_changes = data != original_data
        st.session_state.unsaved_changes = has_changes
        
        st.session_state.form_data = data
        SessionManager.update_activity()
        
        # Clear diff cache when data changes
        st.session_state.diff_cache = {}
    
    @staticmethod
    def get_original_data() -> Dict[str, Any]:
        """Get the original data."""
        return st.session_state.get('original_data', {})
    
    @staticmethod
    def set_original_data(data: Dict[str, Any]):
        """Set the original data."""
        st.session_state.original_data = data
        
        # Initialize form data with original data if not set
        if not st.session_state.get('form_data'):
            st.session_state.form_data = data.copy()
    
    @staticmethod
    def get_schema() -> Dict[str, Any]:
        """Get the current schema."""
        return st.session_state.get('schema', {})
    
    @staticmethod
    def set_schema(schema: Dict[str, Any]):
        """Set the schema."""
        st.session_state.schema = schema
    
    @staticmethod
    def get_model_class():
        """Get the current Pydantic model class."""
        return st.session_state.get('model_class')
    
    @staticmethod
    def set_model_class(model_class):
        """Set the Pydantic model class."""
        st.session_state.model_class = model_class
    
    @staticmethod
    def has_unsaved_changes() -> bool:
        """Check if there are unsaved changes."""
        return st.session_state.get('unsaved_changes', False)
    
    @staticmethod
    def mark_saved():
        """Mark current changes as saved."""
        st.session_state.unsaved_changes = False
        SessionManager.update_activity()
    
    @staticmethod
    def get_validation_errors() -> list:
        """Get current validation errors."""
        return st.session_state.get('validation_errors', [])
    
    @staticmethod
    def set_validation_errors(errors: list):
        """Set validation errors."""
        st.session_state.validation_errors = errors
    
    @staticmethod
    def clear_validation_errors():
        """Clear validation errors."""
        st.session_state.validation_errors = []
    
    @staticmethod
    def get_ui_state() -> Dict[str, Any]:
        """Get UI state preferences."""
        return st.session_state.get('ui_state', {})
    
    @staticmethod
    def set_ui_state(key: str, value: Any):
        """Set a UI state preference."""
        if 'ui_state' not in st.session_state:
            st.session_state.ui_state = {}
        
        st.session_state.ui_state[key] = value
    
    @staticmethod
    def update_activity():
        """Update last activity timestamp."""
        st.session_state.last_activity = datetime.now()
    
    @staticmethod
    def get_last_activity() -> datetime:
        """Get last activity timestamp."""
        return st.session_state.get('last_activity', datetime.now())
    
    @staticmethod
    def get_session_id() -> str:
        """Get the session ID."""
        return st.session_state.get('session_id', 'unknown')
    
    @staticmethod
    def is_edit_mode() -> bool:
        """Check if currently in edit mode."""
        return st.session_state.get('edit_mode', False)
    
    @staticmethod
    def reset_session():
        """Reset the entire session state."""
        logger.info(f"Resetting session: {SessionManager.get_session_id()}")
        
        # Keep user preferences
        user = SessionManager.get_current_user()
        timeout = SessionManager.get_lock_timeout()
        ui_state = SessionManager.get_ui_state()
        
        # Clear all session state
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        
        # Reinitialize with preserved preferences
        SessionManager.initialize()
        SessionManager.set_current_user(user)
        SessionManager.set_lock_timeout(timeout)
        st.session_state.ui_state = ui_state
    
    @staticmethod
    def _clear_file_state():
        """Clear file-specific state."""
        st.session_state.form_data = {}
        st.session_state.original_data = {}
        st.session_state.schema = {}
        st.session_state.model_class = None
        st.session_state.unsaved_changes = False
        st.session_state.validation_errors = []
        st.session_state.diff_cache = {}
        st.session_state.edit_mode = False
    
    @staticmethod
    def _cleanup_edit_state():
        """Cleanup when leaving edit mode."""
        if SessionManager.has_unsaved_changes():
            logger.warning("Leaving edit mode with unsaved changes")
        
        # Could add auto-save logic here if needed
        pass
    
    @staticmethod
    def get_session_info() -> Dict[str, Any]:
        """Get comprehensive session information for debugging."""
        return {
            'session_id': SessionManager.get_session_id(),
            'current_page': SessionManager.get_current_page(),
            'current_file': SessionManager.get_current_file(),
            'current_user': SessionManager.get_current_user(),
            'edit_mode': SessionManager.is_edit_mode(),
            'unsaved_changes': SessionManager.has_unsaved_changes(),
            'last_activity': SessionManager.get_last_activity().isoformat(),
            'validation_errors_count': len(SessionManager.get_validation_errors()),
            'form_data_keys': list(SessionManager.get_form_data().keys()),
            'schema_loaded': bool(SessionManager.get_schema()),
            'model_loaded': SessionManager.get_model_class() is not None
        }
    
    @staticmethod
    def validate_session_state() -> list:
        """Validate current session state and return any issues."""
        issues = []
        
        # Check for required state when in edit mode
        if SessionManager.is_edit_mode():
            if not SessionManager.get_current_file():
                issues.append("Edit mode active but no current file set")
            
            if not SessionManager.get_schema():
                issues.append("Edit mode active but no schema loaded")
            
            if not SessionManager.get_model_class():
                issues.append("Edit mode active but no model class loaded")
        
        # Check for orphaned state
        if SessionManager.get_current_file() and not SessionManager.is_edit_mode():
            issues.append("Current file set but not in edit mode")
        
        if SessionManager.has_unsaved_changes() and not SessionManager.get_form_data():
            issues.append("Marked as having unsaved changes but no form data")
        
        return issues


# Convenience functions for common operations
def init_session():
    """Initialize session state."""
    SessionManager.initialize()


def get_current_page() -> str:
    """Get current page."""
    return SessionManager.get_current_page()


def set_current_page(page: str):
    """Set current page."""
    SessionManager.set_current_page(page)


def get_current_file() -> Optional[str]:
    """Get current file."""
    return SessionManager.get_current_file()


def set_current_file(filename: Optional[str]):
    """Set current file."""
    SessionManager.set_current_file(filename)


def get_current_user() -> str:
    """Get current user."""
    return SessionManager.get_current_user()


def has_unsaved_changes() -> bool:
    """Check for unsaved changes."""
    return SessionManager.has_unsaved_changes()


def reset_session():
    """Reset session."""
    SessionManager.reset_session()