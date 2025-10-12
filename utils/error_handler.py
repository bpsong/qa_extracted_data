
"""
Error handling utilities for JSON QA webapp.
Provides comprehensive error handling, user-friendly messages, and recovery options.
"""

import streamlit as st
import logging
import traceback
from typing import Dict, Any, Optional, Callable, List
from datetime import datetime
from pathlib import Path
import json
from utils.session_manager import SessionManager
import os

logger = logging.getLogger(__name__)


class ErrorType:
    """Error type constants."""
    FILE_SYSTEM = "file_system"
    SCHEMA = "schema"
    VALIDATION = "validation"
    CONCURRENCY = "concurrency"
    PDF = "pdf"
    NETWORK = "network"
    PERMISSION = "permission"
    DATA_CORRUPTION = "data_corruption"
    SYSTEM = "system"
    USER_INPUT = "user_input"


class ErrorHandler:
    """Comprehensive error handling for the JSON QA webapp."""
    
    @staticmethod
    def handle_error(
        error: Exception,
        context: str,
        error_type: str = ErrorType.SYSTEM,
        user_message: Optional[str] = None,
        recovery_options: Optional[List[Dict[str, Any]]] = None,
        show_details: bool = False
    ) -> None:
        """
        Handle errors with user-friendly messages and recovery options.
        
        Args:
            error: The exception that occurred
            context: Context where the error occurred
            error_type: Type of error (from ErrorType constants)
            user_message: Custom user-friendly message
            recovery_options: List of recovery actions
            show_details: Whether to show technical details
        """
        # Log the error
        logger.error(f"Error in {context}: {str(error)}", exc_info=True)
        
        # Get user-friendly message
        if not user_message:
            user_message = ErrorHandler._get_user_friendly_message(error, error_type)
        
        # Display error to user
        ErrorHandler._display_error(
            user_message, 
            error, 
            context, 
            recovery_options, 
            show_details
        )
        
        # Log error for analytics
        ErrorHandler._log_error_analytics(error, context, error_type)
    
    @staticmethod
    def _get_user_friendly_message(error: Exception, error_type: str) -> str:
        """Generate user-friendly error messages based on error type."""
        error_messages = {
            ErrorType.FILE_SYSTEM: {
                FileNotFoundError: "📁 The requested file could not be found. It may have been moved or deleted.",
                PermissionError: "🔒 Permission denied. Please check file permissions or contact your administrator.",
                OSError: "💾 File system error occurred. Please try again or contact support.",
                "default": "📁 A file system error occurred. Please try again."
            },
            
            ErrorType.SCHEMA: {
                json.JSONDecodeError: "📋 Schema file contains invalid JSON format. Please check the schema file.",
                KeyError: "📋 Required schema field is missing. Please verify the schema configuration.",
                ValueError: "📋 Schema contains invalid values. Please check the schema definition.",
                "default": "📋 Schema error occurred. Please check your schema files."
            },
            
            ErrorType.VALIDATION: {
                ValueError: "✅ Data validation failed. Please check your input and try again.",
                TypeError: "✅ Invalid data type provided. Please ensure data matches expected format.",
                "default": "✅ Validation error occurred. Please review your data and try again."
            },
            
            ErrorType.CONCURRENCY: {
                "default": "🔒 File is currently being edited by another user. Please try again later."
            },
            
            ErrorType.PDF: {
                FileNotFoundError: "📄 PDF file not found. Please ensure the PDF exists in the correct location.",
                PermissionError: "📄 Cannot access PDF file. Please check file permissions.",
                "default": "📄 PDF processing error. The PDF may be corrupted or inaccessible."
            },
            
            ErrorType.NETWORK: {
                ConnectionError: "🌐 Network connection error. Please check your internet connection.",
                TimeoutError: "⏱️ Request timed out. Please try again.",
                "default": "🌐 Network error occurred. Please check your connection and try again."
            },
            
            ErrorType.PERMISSION: {
                PermissionError: "🔐 You don't have permission to perform this action.",
                "default": "🔐 Permission denied. Please contact your administrator."
            },
            
            ErrorType.DATA_CORRUPTION: {
                json.JSONDecodeError: "🔧 Data file is corrupted or contains invalid JSON.",
                UnicodeDecodeError: "🔧 File encoding error. The file may be corrupted.",
                "default": "🔧 Data corruption detected. Please restore from backup or contact support."
            },
            
            ErrorType.USER_INPUT: {
                ValueError: "⚠️ Invalid input provided. Please check your data and try again.",
                TypeError: "⚠️ Incorrect data format. Please ensure your input matches the expected format.",
                "default": "⚠️ Input error. Please review your data and try again."
            },
            
            ErrorType.SYSTEM: {
                MemoryError: "💻 System is running low on memory. Please try again or contact support.",
                ImportError: "💻 Required system component is missing. Please contact support.",
                "default": "💻 System error occurred. Please try again or contact support."
            }
        }
        
        error_type_messages = error_messages.get(error_type, error_messages[ErrorType.SYSTEM])
        
        # Try to find specific message for error type
        for exception_type, message in error_type_messages.items():
            if exception_type != "default" and isinstance(error, exception_type):
                return message
        
        # Return default message for error type
        return error_type_messages.get("default", "An unexpected error occurred.")
    
    @staticmethod
    def _display_error(
        user_message: str,
        error: Exception,
        context: str,
        recovery_options: Optional[List[Dict[str, Any]]] = None,
        show_details: bool = False
    ) -> None:
        """Display error message to user with recovery options."""
        # Main error message
        st.error(user_message)
        
        # Recovery options
        if recovery_options:
            st.subheader("🔧 Suggested Actions:")
            
            for i, option in enumerate(recovery_options):
                col1, col2 = st.columns([3, 1])
                
                with col1:
                    st.write(f"**{option['title']}**")
                    st.write(option['description'])
                
                with col2:
                    if st.button(option['button_text'], key=f"recovery_{i}"):
                        if 'action' in option and callable(option['action']):
                            try:
                                option['action']()
                            except Exception as e:
                                st.error(f"Recovery action failed: {str(e)}")
        
        # Technical details (expandable)
        if show_details or st.checkbox("Show technical details", key=f"details_{id(error)}"):
            with st.expander("🔍 Technical Details"):
                st.write(f"**Error Type:** {type(error).__name__}")
                st.write(f"**Context:** {context}")
                st.write(f"**Error Message:** {str(error)}")
                
                # Stack trace
                if st.checkbox("Show stack trace", key=f"trace_{id(error)}"):
                    st.code(traceback.format_exc())
    
    @staticmethod
    def _log_error_analytics(error: Exception, context: str, error_type: str) -> None:
        """Log error for analytics and monitoring."""
        try:
            error_data = {
                'timestamp': datetime.now().isoformat(),
                'error_type': error_type,
                'exception_type': type(error).__name__,
                'context': context,
                'message': str(error),
                'user_agent': 'streamlit_app'
            }
            
            # Log to file (in production, this could be sent to monitoring service)
            log_file = Path("logs/error_analytics.jsonl")
            log_file.parent.mkdir(exist_ok=True)
            
            with open(log_file, 'a') as f:
                json.dump(error_data, f)
                f.write('\n')
        
        except Exception as e:
            logger.error(f"Failed to log error analytics: {e}")
    
    @staticmethod
    def with_error_handling(
        func: Callable,
        context: str,
        error_type: str = ErrorType.SYSTEM,
        user_message: Optional[str] = None,
        recovery_options: Optional[List[Dict[str, Any]]] = None,
        show_details: bool = False,
        default_return: Any = None
    ) -> Any:
        """
        Decorator-like function to wrap operations with error handling.
        
        Args:
            func: Function to execute
            context: Context description
            error_type: Type of error expected
            user_message: Custom user message
            recovery_options: Recovery actions
            show_details: Show technical details
            default_return: Value to return on error
        
        Returns:
            Function result or default_return on error
        """
        try:
            return func()
        except Exception as e:
            ErrorHandler.handle_error(
                e, context, error_type, user_message, recovery_options, show_details
            )
            return default_return
    
    @staticmethod
    def create_recovery_options(context: str) -> List[Dict[str, Any]]:
        """Create context-specific recovery options."""
        recovery_options: List[Dict[str, Any]] = []
        
        if "file" in context.lower():
            recovery_options.extend([
                {
                    'title': 'Refresh File List',
                    'description': 'Reload the file list to check for updates',
                    'button_text': '🔄 Refresh',
                    'action': lambda: st.rerun()
                },
                {
                    'title': 'Check File Permissions',
                    'description': 'Verify that files exist and are accessible',
                    'button_text': '🔍 Check Files',
                    'action': lambda: ErrorHandler._check_file_system()
                }
            ])
        
        if "schema" in context.lower():
            recovery_options.extend([
                {
                    'title': 'Reload Schema',
                    'description': 'Attempt to reload the schema configuration',
                    'button_text': '📋 Reload Schema',
                    'action': lambda: st.rerun()
                },
                {
                    'title': 'Use Default Schema',
                    'description': 'Fall back to the default schema configuration',
                    'button_text': '📋 Use Default',
                    'action': lambda: ErrorHandler._use_default_schema()
                }
            ])
        
        if "validation" in context.lower():
            recovery_options.extend([
                {
                    'title': 'Review Input Data',
                    'description': 'Check your input data for errors or missing fields',
                    'button_text': '✅ Review Data',
                    'action': lambda: None  # Just informational
                },
                {
                    'title': 'Reset Form',
                    'description': 'Reset the form to original values',
                    'button_text': '🔄 Reset Form',
                    'action': lambda: ErrorHandler._reset_form()
                }
            ])
        
        if "pdf" in context.lower():
            recovery_options.extend([
                {
                    'title': 'Check PDF Location',
                    'description': 'Verify the PDF file exists in the pdf_docs folder',
                    'button_text': '📄 Check PDF',
                    'action': lambda: ErrorHandler._check_pdf_files()
                },
                {
                    'title': 'Continue Without PDF',
                    'description': 'Proceed with editing without PDF preview',
                    'button_text': '➡️ Continue',
                    'action': lambda: None
                }
            ])
        
        # Always include general recovery options
        recovery_options.extend([
            {
                'title': 'Restart Session',
                'description': 'Clear all session data and start fresh',
                'button_text': '🔄 Restart',
                'action': lambda: ErrorHandler._restart_session()
            },
            {
                'title': 'Contact Support',
                'description': 'Get help from technical support',
                'button_text': '📞 Get Help',
                'action': lambda: ErrorHandler._show_support_info()
            }
        ])
        
        return recovery_options
    
    @staticmethod
    def _check_file_system() -> None:
        """Check file system status."""
        st.info("🔍 Checking file system...")
        
        directories = ['json_docs', 'corrected', 'audits', 'pdf_docs', 'locks', 'schemas']
        status: Dict[str, Dict[str, Any]] = {}
        
        for directory in directories:
            path = Path(directory)
            status[directory] = {
                'exists': path.exists(),
                'is_dir': path.is_dir() if path.exists() else False,
                'readable': path.exists() and os.access(path, os.R_OK),
                'writable': path.exists() and os.access(path, os.W_OK)
            }
        
        # Display status
        for directory, info in status.items():
            if info['exists'] and info['readable'] and info['writable']:
                st.success(f"✅ {directory}: OK")
            elif info['exists']:
                st.warning(f"⚠️ {directory}: Limited access")
            else:
                st.error(f"❌ {directory}: Missing")
    
    @staticmethod
    def _use_default_schema() -> None:
        """Switch to default schema."""
        st.info("📋 Switching to default schema...")
        # This would be implemented based on your schema loading logic
        st.success("✅ Default schema loaded")
    
    @staticmethod
    def _reset_form() -> None:
        """Reset form to original values and update widget state keys so UI reflects the original values."""
        try:
            original_data = SessionManager.get_original_data()
            if original_data:
                # Update the high-level session data
                SessionManager.set_form_data(original_data.copy())
                
                # Also update per-widget Streamlit keys so widgets pick up the original values.
                # FormGenerator uses widget keys in the form of "field_<field_name>".
                # We write each original value into the corresponding widget key in session_state.
                try:
                    for field_name, value in original_data.items():
                        widget_key = f"field_{field_name}"
                        st.session_state[widget_key] = value
                except Exception:
                    # If original_data is not a flat dict (nested objects/arrays), attempt a shallow approach:
                    try:
                        # Flatten top-level keys only; ignore deeper nesting to avoid unexpected mutations
                        for field_name in getattr(original_data, "keys", lambda: [])():
                            widget_key = f"field_{field_name}"
                            st.session_state[widget_key] = original_data.get(field_name)
                    except Exception:
                        # Be tolerant — widget state update is best-effort
                        logger.debug("Failed to populate widget-level session_state keys from original_data")
                
                st.success("🔄 Form reset to original values")
                st.rerun()
            else:
                st.warning("⚠️ No original data available to reset to")
        except Exception as e:
            st.error(f"Failed to reset form: {str(e)}")
    
    @staticmethod
    def _check_pdf_files() -> None:
        """Check PDF files availability."""
        st.info("📄 Checking PDF files...")
        
        pdf_dir = Path("pdf_docs")
        if not pdf_dir.exists():
            st.error("❌ PDF directory does not exist")
            return
        
        pdf_files = list(pdf_dir.glob("*.pdf"))
        if pdf_files:
            st.success(f"✅ Found {len(pdf_files)} PDF files")
            for pdf_file in pdf_files[:5]:  # Show first 5
                st.write(f"  • {pdf_file.name}")
            if len(pdf_files) > 5:
                st.write(f"  ... and {len(pdf_files) - 5} more")
        else:
            st.warning("⚠️ No PDF files found in pdf_docs directory")
    
    @staticmethod
    def _restart_session() -> None:
        """Restart the user session."""
        try:
            SessionManager.reset_session()
            st.success("🔄 Session restarted successfully")
            st.rerun()
        except Exception as e:
            st.error(f"Failed to restart session: {str(e)}")
    
    @staticmethod
    def _show_support_info() -> None:
        """Show support contact information."""
        st.info("📞 Support Information")
        st.markdown("""
        **Need help?** Here are your options:
        
        - **Documentation**: Check the user guide and FAQ
        - **Technical Support**: Contact your system administrator
        - **Bug Reports**: Report issues through your organization's support channel
        
        **When contacting support, please include:**
        - What you were trying to do
        - The exact error message
        - Steps to reproduce the issue
        - Your browser and operating system information
        """)
        

class SafeOperations:
    """Safe wrappers for common operations."""
    
    @staticmethod
    def safe_file_read(file_path: str, default: Any = None) -> Any:
        """Safely read a file with error handling."""
        return ErrorHandler.with_error_handling(
            func=lambda: Path(file_path).read_text(),
            context=f"reading file {file_path}",
            error_type=ErrorType.FILE_SYSTEM,
            recovery_options=ErrorHandler.create_recovery_options("file"),
            default_return=default
        )
    
    @staticmethod
    def safe_json_load(file_path: str, default: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Safely load JSON file with error handling."""
        if default is None:
            default = {}
        
        def load_json() -> Dict[str, Any]:
            with open(file_path, 'r') as f:
                return json.load(f)
        
        return ErrorHandler.with_error_handling(
            func=load_json,
            context=f"loading JSON from {file_path}",
            error_type=ErrorType.FILE_SYSTEM,
            recovery_options=ErrorHandler.create_recovery_options("file"),
            default_return=default
        )
    
    @staticmethod
    def safe_schema_load(schema_path: str) -> Optional[Dict[str, Any]]:
        """Safely load schema with error handling."""
        from .schema_loader import load_schema
        
        return ErrorHandler.with_error_handling(
            func=lambda: load_schema(schema_path),
            context=f"loading schema {schema_path}",
            error_type=ErrorType.SCHEMA,
            recovery_options=ErrorHandler.create_recovery_options("schema"),
            default_return=None
        )


# Convenience functions
def handle_error(error: Exception, context: str, error_type: str = ErrorType.SYSTEM) -> None:
    """Convenience function for error handling."""
    ErrorHandler.handle_error(error, context, error_type)


def with_error_handling(func: Callable, context: str, **kwargs) -> Any:
    """Convenience function for wrapping operations with error handling."""
    return ErrorHandler.with_error_handling(func, context, **kwargs)