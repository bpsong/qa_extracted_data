"""
Directory validation utilities for the JSON QA webapp.

This module provides validation functionality for directory paths,
checking existence, permissions, and accessibility.
"""

import os
import stat
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional
import logging

from .directory_config import DirectoryConfig

logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    """
    Result of directory path validation.
    
    Attributes:
        path: The directory path that was validated
        is_valid: Whether the path format is valid
        exists: Whether the directory exists
        is_writable: Whether the directory is writable
        is_readable: Whether the directory is readable
        error_message: Optional error message if validation failed
    """
    path: Path
    is_valid: bool
    exists: bool
    is_writable: bool
    is_readable: bool = True
    error_message: Optional[str] = None
    
    @property
    def is_ready(self) -> bool:
        """
        Check if directory is ready for use.
        
        Returns:
            True if directory is valid, exists, and has proper permissions
        """
        return self.is_valid and self.exists and self.is_writable and self.is_readable


class DirectoryValidator:
    """
    Validator for directory paths and permissions.
    """
    
    def validate_path(self, path: Path) -> ValidationResult:
        """
        Validate a single directory path.
        
        Args:
            path: Path object to validate
            
        Returns:
            ValidationResult with validation details
        """
        logger.debug(f"Validating directory path: {path}")
        
        # Initialize result with basic path info
        result = ValidationResult(
            path=path,
            is_valid=False,
            exists=False,
            is_writable=False,
            is_readable=False
        )
        
        try:
            # Check if path format is valid
            resolved_path = path.resolve()
            result.is_valid = True
            
            # Check if directory exists
            if path.exists():
                result.exists = True
                
                # Check if it's actually a directory
                if not path.is_dir():
                    result.error_message = f"Path exists but is not a directory: {path}"
                    logger.warning(result.error_message)
                    return result
                
                # Check permissions
                result.is_readable = self._check_readable(path)
                result.is_writable = self._check_writable(path)
                
                if not result.is_readable:
                    result.error_message = f"Directory is not readable: {path}"
                elif not result.is_writable:
                    result.error_message = f"Directory is not writable: {path}"
                    
            else:
                # Directory doesn't exist - check if parent is writable for creation
                parent_path = path.parent
                if parent_path.exists() and parent_path.is_dir():
                    if self._check_writable(parent_path):
                        result.error_message = f"Directory does not exist but can be created: {path}"
                        logger.info(result.error_message)
                    else:
                        result.error_message = f"Directory does not exist and parent is not writable: {path}"
                        logger.warning(result.error_message)
                else:
                    result.error_message = f"Directory does not exist and parent path is invalid: {path}"
                    logger.warning(result.error_message)
                    
        except (OSError, ValueError, PermissionError) as e:
            result.error_message = f"Path validation failed: {path} - {str(e)}"
            logger.error(result.error_message)
            
        return result
    
    def validate_all_paths(self, config: DirectoryConfig) -> List[ValidationResult]:
        """
        Validate all directory paths in the configuration.
        
        Args:
            config: DirectoryConfig instance to validate
            
        Returns:
            List of ValidationResult objects for each directory
        """
        logger.info("Validating all directory paths in configuration")
        
        results = []
        directory_dict = config.to_dict()
        
        for name, path in directory_dict.items():
            logger.debug(f"Validating {name} directory: {path}")
            result = self.validate_path(path)
            results.append(result)
            
            if result.is_ready:
                logger.info(f"Directory validation passed for {name}: {path}")
            elif result.exists and not (result.is_readable and result.is_writable):
                logger.warning(f"Directory exists but has permission issues for {name}: {path}")
            elif not result.exists:
                logger.info(f"Directory does not exist for {name}: {path}")
            else:
                logger.error(f"Directory validation failed for {name}: {path}")
        
        return results
    
    def check_permissions(self, path: Path) -> dict:
        """
        Check read/write permissions for a directory path.
        
        Args:
            path: Path to check permissions for
            
        Returns:
            Dictionary with permission details
        """
        permissions = {
            'readable': False,
            'writable': False,
            'executable': False,
            'exists': False,
            'is_directory': False
        }
        
        try:
            if path.exists():
                permissions['exists'] = True
                permissions['is_directory'] = path.is_dir()
                
                if permissions['is_directory']:
                    permissions['readable'] = self._check_readable(path)
                    permissions['writable'] = self._check_writable(path)
                    permissions['executable'] = self._check_executable(path)
                    
        except (OSError, PermissionError) as e:
            logger.error(f"Failed to check permissions for {path}: {e}")
            
        return permissions
    
    def _check_readable(self, path: Path) -> bool:
        """Check if directory is readable."""
        try:
            return os.access(path, os.R_OK)
        except (OSError, PermissionError):
            return False
    
    def _check_writable(self, path: Path) -> bool:
        """Check if directory is writable."""
        try:
            return os.access(path, os.W_OK)
        except (OSError, PermissionError):
            return False
    
    def _check_executable(self, path: Path) -> bool:
        """Check if directory is executable (can be entered)."""
        try:
            return os.access(path, os.X_OK)
        except (OSError, PermissionError):
            return False
    
    def get_validation_summary(self, results: List[ValidationResult]) -> dict:
        """
        Get a summary of validation results.
        
        Args:
            results: List of ValidationResult objects
            
        Returns:
            Dictionary with validation summary
        """
        summary = {
            'total_directories': len(results),
            'valid_paths': 0,
            'existing_directories': 0,
            'ready_directories': 0,
            'permission_issues': 0,
            'missing_directories': 0,
            'invalid_paths': 0,
            'errors': []
        }
        
        for result in results:
            if result.is_valid:
                summary['valid_paths'] += 1
            else:
                summary['invalid_paths'] += 1
                
            if result.exists:
                summary['existing_directories'] += 1
            else:
                summary['missing_directories'] += 1
                
            if result.is_ready:
                summary['ready_directories'] += 1
            elif result.exists and not (result.is_readable and result.is_writable):
                summary['permission_issues'] += 1
                
            if result.error_message:
                summary['errors'].append({
                    'path': str(result.path),
                    'message': result.error_message
                })
        
        return summary