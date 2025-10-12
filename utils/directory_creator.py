"""
Directory creation utilities for the JSON QA webapp.

This module provides functionality to create missing directories
with proper error handling and logging.
"""

import os
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional
import logging

from .directory_config import DirectoryConfig

logger = logging.getLogger(__name__)


@dataclass
class CreationResult:
    """
    Result of directory creation operation.
    
    Attributes:
        path: The directory path that was processed
        created: Whether the directory was successfully created
        already_existed: Whether the directory already existed
        error_message: Optional error message if creation failed
        permissions_set: Whether permissions were successfully set
    """
    path: Path
    created: bool
    already_existed: bool
    error_message: Optional[str] = None
    permissions_set: bool = True
    
    @property
    def is_successful(self) -> bool:
        """
        Check if directory creation was successful.
        
        Returns:
            True if directory was created or already existed
        """
        return self.created or self.already_existed


class DirectoryCreator:
    """
    Creator for missing directories with proper error handling.
    """
    
    def __init__(self, default_permissions: int = 0o755):
        """
        Initialize DirectoryCreator.
        
        Args:
            default_permissions: Default permissions for created directories (octal)
        """
        self.default_permissions = default_permissions
    
    def create_directory(self, path: Path, permissions: Optional[int] = None) -> CreationResult:
        """
        Create a single directory with proper error handling.
        
        Args:
            path: Path object for directory to create
            permissions: Optional permissions to set (defaults to instance default)
            
        Returns:
            CreationResult with creation details
        """
        
        # Initialize result
        result = CreationResult(
            path=path,
            created=False,
            already_existed=False
        )
        
        try:
            # Check if directory already exists
            if path.exists():
                if path.is_dir():
                    result.already_existed = True
                    
                    # Verify permissions if directory exists
                    if not self._check_directory_permissions(path):
                        logger.warning(f"Existing directory has insufficient permissions: {path}")
                        result.error_message = f"Directory exists but has insufficient permissions: {path}"
                        result.permissions_set = False
                else:
                    result.error_message = f"Path exists but is not a directory: {path}"
                    logger.error(result.error_message)
                    return result
            else:
                # Create the directory
                path.mkdir(parents=True, exist_ok=True)
                result.created = True
                logger.info(f"Successfully created directory: {path}")
                
                # Set permissions if specified
                if permissions is not None:
                    self._set_permissions(path, permissions, result)
                elif self.default_permissions is not None:
                    self._set_permissions(path, self.default_permissions, result)
                    
        except PermissionError as e:
            result.error_message = f"Permission denied creating directory {path}: {str(e)}"
            logger.error(result.error_message)
        except OSError as e:
            result.error_message = f"OS error creating directory {path}: {str(e)}"
            logger.error(result.error_message)
        except Exception as e:
            result.error_message = f"Unexpected error creating directory {path}: {str(e)}"
            logger.error(result.error_message)
            
        return result
    
    def create_all_directories(self, config: DirectoryConfig) -> List[CreationResult]:
        """
        Create all missing directories from the configuration.
        
        Args:
            config: DirectoryConfig instance with directories to create
            
        Returns:
            List of CreationResult objects for each directory
        """
        logger.info("Creating all missing directories from configuration")
        
        results = []
        directory_dict = config.to_dict()
        
        for name, path in directory_dict.items():
            result = self.create_directory(path)
            results.append(result)
            
            if result.is_successful:
                if result.created:
                    logger.info(f"Created directory for {name}: {path}")
            else:
                logger.error(f"Failed to create directory for {name}: {path} - {result.error_message}")
        
        return results
    
    def ensure_directory_structure(self, config: DirectoryConfig) -> bool:
        """
        Ensure complete directory structure exists and is accessible.
        
        Args:
            config: DirectoryConfig instance to ensure
            
        Returns:
            True if all directories are ready, False if any failed
        """
        logger.info("Ensuring complete directory structure")
        
        creation_results = self.create_all_directories(config)
        
        # Check if all directories were successfully created or already existed
        all_successful = all(result.is_successful for result in creation_results)
        
        if all_successful:
            logger.info("All directories are ready")
        else:
            failed_dirs = [
                result.path for result in creation_results 
                if not result.is_successful
            ]
            logger.error(f"Failed to ensure directories: {failed_dirs}")
        
        return all_successful
    
    def _set_permissions(self, path: Path, permissions: int, result: CreationResult) -> None:
        """
        Set permissions on a directory.
        
        Args:
            path: Directory path
            permissions: Permissions to set (octal)
            result: CreationResult to update
        """
        try:
            os.chmod(path, permissions)
            result.permissions_set = True
        except (OSError, PermissionError) as e:
            logger.warning(f"Failed to set permissions on {path}: {e}")
            result.permissions_set = False
            if result.error_message:
                result.error_message += f" (Permission setting failed: {e})"
            else:
                result.error_message = f"Failed to set permissions: {e}"
    
    def _check_directory_permissions(self, path: Path) -> bool:
        """
        Check if directory has adequate permissions for the application.
        
        Args:
            path: Directory path to check
            
        Returns:
            True if permissions are adequate
        """
        try:
            # Check read, write, and execute permissions
            return (os.access(path, os.R_OK) and 
                   os.access(path, os.W_OK) and 
                   os.access(path, os.X_OK))
        except (OSError, PermissionError):
            return False
    
    def get_creation_summary(self, results: List[CreationResult]) -> dict:
        """
        Get a summary of directory creation results.
        
        Args:
            results: List of CreationResult objects
            
        Returns:
            Dictionary with creation summary
        """
        summary = {
            'total_directories': len(results),
            'created_directories': 0,
            'existing_directories': 0,
            'failed_directories': 0,
            'permission_issues': 0,
            'successful_operations': 0,
            'errors': []
        }
        
        for result in results:
            if result.created:
                summary['created_directories'] += 1
            elif result.already_existed:
                summary['existing_directories'] += 1
            
            if result.is_successful:
                summary['successful_operations'] += 1
            else:
                summary['failed_directories'] += 1
            
            if not result.permissions_set:
                summary['permission_issues'] += 1
            
            if result.error_message:
                summary['errors'].append({
                    'path': str(result.path),
                    'message': result.error_message
                })
        
        return summary
    
    def cleanup_empty_directories(self, config: DirectoryConfig, dry_run: bool = True) -> List[Path]:
        """
        Clean up empty directories (utility function for maintenance).
        
        Args:
            config: DirectoryConfig instance
            dry_run: If True, only report what would be deleted
            
        Returns:
            List of directories that were (or would be) removed
        """
        logger.info(f"Cleaning up empty directories (dry_run={dry_run})")
        
        removed_dirs = []
        directory_dict = config.to_dict()
        
        for name, path in directory_dict.items():
            try:
                if path.exists() and path.is_dir():
                    # Check if directory is empty
                    if not any(path.iterdir()):
                        if dry_run:
                            logger.info(f"Would remove empty directory {name}: {path}")
                            removed_dirs.append(path)
                        else:
                            path.rmdir()
                            logger.info(f"Removed empty directory {name}: {path}")
                            removed_dirs.append(path)
            except (OSError, PermissionError) as e:
                logger.warning(f"Could not process directory {name} ({path}): {e}")
        
        return removed_dirs