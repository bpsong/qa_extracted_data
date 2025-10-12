"""
Custom exception classes for directory configuration errors.

This module provides specialized exception classes for different types
of directory configuration failures with centralized error handling.
"""

import logging
from typing import Optional, Dict, Any, List
from pathlib import Path

logger = logging.getLogger(__name__)


class DirectoryConfigError(Exception):
    """
    Base exception for directory configuration errors.
    
    Attributes:
        message: Error message
        context: Additional context information
        recovery_suggestions: List of suggested recovery actions
    """
    
    def __init__(self, message: str, context: Optional[Dict[str, Any]] = None, 
                 recovery_suggestions: Optional[List[str]] = None):
        self.message = message
        self.context = context or {}
        self.recovery_suggestions = recovery_suggestions or []
        super().__init__(self.message)
    
    def __str__(self) -> str:
        return self.message
    
    def get_full_details(self) -> Dict[str, Any]:
        """Get complete error details including context and suggestions."""
        return {
            'error_type': self.__class__.__name__,
            'message': self.message,
            'context': self.context,
            'recovery_suggestions': self.recovery_suggestions
        }


class ConfigurationLoadError(DirectoryConfigError):
    """
    Exception raised when configuration file loading fails.
    
    This includes YAML parsing errors, file not found, permission issues, etc.
    """
    
    def __init__(self, config_path: Path, original_error: Exception, 
                 message: Optional[str] = None):
        self.config_path = config_path
        self.original_error = original_error
        
        if message is None:
            message = f"Failed to load configuration from {config_path}: {str(original_error)}"
        
        context = {
            'config_path': str(config_path),
            'original_error_type': type(original_error).__name__,
            'original_error_message': str(original_error)
        }
        
        recovery_suggestions = [
            "Check if config.yaml exists and is readable",
            "Verify YAML syntax is correct",
            "Ensure file permissions allow reading",
            "Check for file corruption or encoding issues",
            "Application will use default configuration as fallback"
        ]
        
        super().__init__(message, context, recovery_suggestions)


class DirectoryValidationError(DirectoryConfigError):
    """
    Exception raised when directory path validation fails.
    
    This includes invalid paths, permission issues, or inaccessible locations.
    """
    
    def __init__(self, directory_name: str, directory_path: Path, 
                 validation_issue: str, message: Optional[str] = None):
        self.directory_name = directory_name
        self.directory_path = directory_path
        self.validation_issue = validation_issue
        
        if message is None:
            message = f"Directory validation failed for {directory_name} ({directory_path}): {validation_issue}"
        
        context = {
            'directory_name': directory_name,
            'directory_path': str(directory_path),
            'validation_issue': validation_issue,
            'path_exists': directory_path.exists(),
            'path_is_dir': directory_path.is_dir() if directory_path.exists() else False
        }
        
        recovery_suggestions = [
            f"Check if directory path is valid: {directory_path}",
            "Verify parent directories exist and are accessible",
            "Ensure proper read/write permissions are set",
            "Check for typos in directory configuration",
            "Consider using absolute paths instead of relative paths"
        ]
        
        super().__init__(message, context, recovery_suggestions)


class DirectoryCreationError(DirectoryConfigError):
    """
    Exception raised when directory creation fails.
    
    This includes permission denied, disk space issues, or filesystem errors.
    """
    
    def __init__(self, directory_name: str, directory_path: Path, 
                 creation_error: Exception, message: Optional[str] = None):
        self.directory_name = directory_name
        self.directory_path = directory_path
        self.creation_error = creation_error
        
        if message is None:
            message = f"Failed to create directory {directory_name} ({directory_path}): {str(creation_error)}"
        
        context = {
            'directory_name': directory_name,
            'directory_path': str(directory_path),
            'creation_error_type': type(creation_error).__name__,
            'creation_error_message': str(creation_error),
            'parent_exists': directory_path.parent.exists(),
            'parent_writable': directory_path.parent.exists() and 
                             directory_path.parent.is_dir() and 
                             (directory_path.parent.stat().st_mode & 0o200) != 0
        }
        
        recovery_suggestions = [
            "Check if parent directory exists and is writable",
            "Verify sufficient disk space is available",
            "Ensure proper permissions for directory creation",
            "Check if path conflicts with existing files",
            "Try creating directories manually and restart application"
        ]
        
        super().__init__(message, context, recovery_suggestions)


class DirectoryPermissionError(DirectoryConfigError):
    """
    Exception raised when directory permission issues are detected.
    
    This includes read-only directories, insufficient permissions, etc.
    """
    
    def __init__(self, directory_name: str, directory_path: Path, 
                 permission_issue: str, message: Optional[str] = None):
        self.directory_name = directory_name
        self.directory_path = directory_path
        self.permission_issue = permission_issue
        
        if message is None:
            message = f"Permission error for directory {directory_name} ({directory_path}): {permission_issue}"
        
        context = {
            'directory_name': directory_name,
            'directory_path': str(directory_path),
            'permission_issue': permission_issue,
            'path_exists': directory_path.exists(),
            'is_readable': directory_path.exists() and (directory_path.stat().st_mode & 0o400) != 0,
            'is_writable': directory_path.exists() and (directory_path.stat().st_mode & 0o200) != 0
        }
        
        recovery_suggestions = [
            f"Check permissions on directory: {directory_path}",
            "Ensure the application user has read/write access",
            "Consider changing directory ownership or permissions",
            "Verify the directory is not mounted read-only",
            "Check for filesystem-level restrictions"
        ]
        
        super().__init__(message, context, recovery_suggestions)


def handle_directory_error(error: Exception, context: str) -> bool:
    """
    Handle directory-related errors with appropriate fallbacks.
    
    Args:
        error: The exception that occurred
        context: Context where the error occurred (e.g., "startup", "file_operation")
        
    Returns:
        True if error was handled and operation can continue, False if critical
    """
    logger.error(f"Directory error in {context}: {error}")
    
    if isinstance(error, ConfigurationLoadError):
        logger.warning(f"Configuration load error in {context}: {error.message}")
        logger.info("Falling back to default directory configuration")
        
        # Log recovery suggestions
        for suggestion in error.recovery_suggestions:
            logger.info(f"Recovery suggestion: {suggestion}")
        
        return True  # Can continue with defaults
        
    elif isinstance(error, DirectoryValidationError):
        logger.error(f"Directory validation failed in {context}: {error.message}")
        
        # Log context information
        
        # Log recovery suggestions
        for suggestion in error.recovery_suggestions:
            logger.error(f"Recovery action needed: {suggestion}")
        
        return False  # Cannot continue safely
        
    elif isinstance(error, DirectoryCreationError):
        logger.error(f"Directory creation failed in {context}: {error.message}")
        
        # Log context information
        
        # Log recovery suggestions
        for suggestion in error.recovery_suggestions:
            logger.error(f"Recovery action needed: {suggestion}")
        
        return False  # Cannot continue without directories
        
    elif isinstance(error, DirectoryPermissionError):
        logger.error(f"Directory permission error in {context}: {error.message}")
        
        # Log context information
        
        # Log recovery suggestions
        for suggestion in error.recovery_suggestions:
            logger.error(f"Recovery action needed: {suggestion}")
        
        return False  # Cannot continue with permission issues
        
    elif isinstance(error, DirectoryConfigError):
        logger.error(f"General directory config error in {context}: {error.message}")
        
        # Log recovery suggestions if available
        for suggestion in error.recovery_suggestions:
            logger.info(f"Recovery suggestion: {suggestion}")
        
        return True  # Try to continue with defaults
        
    else:
        logger.error(f"Unexpected error in {context}: {error}")
        return False  # Unknown error, cannot safely continue


def create_user_friendly_error_message(error: DirectoryConfigError) -> Dict[str, Any]:
    """
    Create user-friendly error message for display in UI.
    
    Args:
        error: DirectoryConfigError instance
        
    Returns:
        Dictionary with formatted error information for UI display
    """
    error_details = error.get_full_details()
    
    # Map error types to user-friendly titles and icons
    error_type_info = {
        'ConfigurationLoadError': {
            'title': 'Configuration File Error',
            'icon': '📄',
            'severity': 'warning'
        },
        'DirectoryValidationError': {
            'title': 'Directory Validation Error',
            'icon': '📁',
            'severity': 'error'
        },
        'DirectoryCreationError': {
            'title': 'Directory Creation Error',
            'icon': '🚫',
            'severity': 'error'
        },
        'DirectoryPermissionError': {
            'title': 'Directory Permission Error',
            'icon': '🔒',
            'severity': 'error'
        },
        'DirectoryConfigError': {
            'title': 'Directory Configuration Error',
            'icon': '⚙️',
            'severity': 'warning'
        }
    }
    
    error_type = error_details['error_type']
    type_info = error_type_info.get(error_type, {
        'title': 'Directory Error',
        'icon': '❌',
        'severity': 'error'
    })
    
    return {
        'title': f"{type_info['icon']} {type_info['title']}",
        'message': error_details['message'],
        'severity': type_info['severity'],
        'context': error_details['context'],
        'recovery_suggestions': error_details['recovery_suggestions'],
        'technical_details': {
            'error_type': error_type,
            'context_info': error_details['context']
        }
    }


def log_error_with_context(error: DirectoryConfigError, operation: str) -> None:
    """
    Log error with full context information.
    
    Args:
        error: DirectoryConfigError instance
        operation: Description of the operation that failed
    """
    logger.error(f"Directory error during {operation}")
    logger.error(f"Error type: {type(error).__name__}")
    logger.error(f"Error message: {error.message}")
    
    # Log context information
    if error.context:
        logger.error("Error context:")
        for key, value in error.context.items():
            logger.error(f"  {key}: {value}")
    
    # Log recovery suggestions
    if error.recovery_suggestions:
        logger.info("Recovery suggestions:")
        for i, suggestion in enumerate(error.recovery_suggestions, 1):
            logger.info(f"  {i}. {suggestion}")


def wrap_directory_operation(operation_name: str):
    """
    Decorator to wrap directory operations with error handling.
    
    Args:
        operation_name: Name of the operation for logging context
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except DirectoryConfigError as e:
                log_error_with_context(e, operation_name)
                if not handle_directory_error(e, operation_name):
                    raise
                return None
            except Exception as e:
                logger.error(f"Unexpected error in {operation_name}: {e}")
                raise DirectoryConfigError(
                    f"Unexpected error during {operation_name}: {str(e)}",
                    context={'operation': operation_name, 'original_error': str(e)},
                    recovery_suggestions=[
                        "Check application logs for detailed error information",
                        "Verify system resources and permissions",
                        "Try restarting the application"
                    ]
                )
        return wrapper
    return decorator