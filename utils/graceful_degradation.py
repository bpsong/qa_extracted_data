"""
Graceful degradation mechanisms for directory configuration failures.

This module provides fallback logic and recovery mechanisms when
directory configuration fails or is partially invalid.
"""

import logging
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple
from copy import deepcopy

from .directory_config import DirectoryConfig
from .directory_exceptions import (
    DirectoryConfigError, ConfigurationLoadError, DirectoryValidationError,
    DirectoryCreationError, DirectoryPermissionError
)
from .config_loader import get_default_config, load_config
from .directory_validator import DirectoryValidator, ValidationResult
from .directory_creator import DirectoryCreator, CreationResult

logger = logging.getLogger(__name__)


class GracefulDegradationManager:
    """
    Manager for handling graceful degradation of directory configuration.
    """
    
    def __init__(self):
        self.fallback_applied = False
        self.degradation_log = []
        self.recovery_attempts = []
    
    def handle_configuration_failure(self, error: Exception, 
                                   context: str = "configuration_load") -> DirectoryConfig:
        """
        Handle configuration loading failure with graceful fallback.
        
        Args:
            error: The configuration loading error
            context: Context where the error occurred
            
        Returns:
            DirectoryConfig instance (either recovered or default)
        """
        logger.warning(f"Configuration failure in {context}, attempting graceful degradation")
        
        self.degradation_log.append({
            'context': context,
            'error_type': type(error).__name__,
            'error_message': str(error),
            'fallback_applied': True
        })
        
        try:
            # Attempt to load partial configuration
            partial_config = self._attempt_partial_config_recovery()
            if partial_config:
                logger.info("Successfully recovered partial configuration")
                return DirectoryConfig.from_config(partial_config)
        
        except Exception as recovery_error:
            logger.warning(f"Partial recovery failed: {recovery_error}")
        
        # Fall back to complete defaults
        logger.info("Using complete default configuration")
        self.fallback_applied = True
        default_config = get_default_config()
        return DirectoryConfig.from_config(default_config)
    
    def handle_validation_failure(self, config: DirectoryConfig, 
                                validation_results: List[ValidationResult]) -> DirectoryConfig:
        """
        Handle directory validation failures with selective fallback.
        
        Args:
            config: Original DirectoryConfig
            validation_results: List of validation results
            
        Returns:
            DirectoryConfig with problematic paths replaced by defaults
        """
        logger.info("Handling validation failures with selective fallback")
        
        # Identify failed validations that are actually problematic
        # Only apply fallback for paths that exist but have permission issues
        # or paths that are invalid format - not just missing directories
        critical_failures = []
        for result in validation_results:
            if not result.is_ready:
                # Only treat as critical if path exists but has issues, or path format is invalid
                if (result.exists and not (result.is_readable and result.is_writable)) or not result.is_valid:
                    critical_failures.append(result)
                # For non-existent directories, we'll try to create them instead of falling back
        
        if not critical_failures:
            return config  # No critical failures to handle
        
        # Create a new config with fallbacks for failed directories
        config_dict = config.to_dict()
        default_config = get_default_config()
        default_dirs = default_config['directories']
        
        recovery_applied = False
        
        for result in critical_failures:
            # Find which directory failed
            for dir_name, dir_path in config_dict.items():
                if dir_path == result.path:
                    logger.warning(f"Applying fallback for directory {dir_name}: {dir_path} -> {default_dirs[dir_name]}")
                    config_dict[dir_name] = Path(default_dirs[dir_name])
                    recovery_applied = True
                    
                    self.recovery_attempts.append({
                        'directory': dir_name,
                        'original_path': str(result.path),
                        'fallback_path': default_dirs[dir_name],
                        'reason': result.error_message or 'Critical validation failed'
                    })
                    break
        
        if recovery_applied:
            self.fallback_applied = True
            # Create new DirectoryConfig with recovered paths
            recovered_config = DirectoryConfig(
                json_docs=config_dict['json_docs'],
                corrected=config_dict['corrected'],
                audits=config_dict['audits'],
                pdf_docs=config_dict['pdf_docs'],
                locks=config_dict['locks']
            )
            return recovered_config
        
        return config
    
    def handle_creation_failure(self, config: DirectoryConfig, 
                              creation_results: List[CreationResult]) -> Tuple[DirectoryConfig, bool]:
        """
        Handle directory creation failures with recovery attempts.
        
        Args:
            config: DirectoryConfig with creation failures
            creation_results: List of creation results
            
        Returns:
            Tuple of (recovered_config, success_flag)
        """
        logger.info("Handling directory creation failures")
        
        failed_creations = [r for r in creation_results if not r.is_successful]
        
        if not failed_creations:
            return config, True  # No failures to handle
        
        # Try alternative approaches for failed directories
        config_dict = config.to_dict()
        default_config = get_default_config()
        default_dirs = default_config['directories']
        
        creator = DirectoryCreator()
        recovery_success = True
        
        for result in failed_creations:
            # Find which directory failed
            for dir_name, dir_path in config_dict.items():
                if dir_path == result.path:
                    logger.info(f"Attempting recovery for directory {dir_name}")
                    
                    # Try creating in default location
                    default_path = Path(default_dirs[dir_name])
                    recovery_result = creator.create_directory(default_path)
                    
                    if recovery_result.is_successful:
                        logger.info(f"Recovery successful: {dir_name} -> {default_path}")
                        config_dict[dir_name] = default_path
                        
                        self.recovery_attempts.append({
                            'directory': dir_name,
                            'original_path': str(result.path),
                            'fallback_path': str(default_path),
                            'reason': result.error_message or 'Creation failed',
                            'recovery_successful': True
                        })
                    else:
                        logger.error(f"Recovery failed for directory {dir_name}")
                        recovery_success = False
                        
                        self.recovery_attempts.append({
                            'directory': dir_name,
                            'original_path': str(result.path),
                            'fallback_path': str(default_path),
                            'reason': result.error_message or 'Creation failed',
                            'recovery_successful': False
                        })
                    break
        
        if self.recovery_attempts:
            self.fallback_applied = True
            
        # Create recovered config
        recovered_config = DirectoryConfig(
            json_docs=config_dict['json_docs'],
            corrected=config_dict['corrected'],
            audits=config_dict['audits'],
            pdf_docs=config_dict['pdf_docs'],
            locks=config_dict['locks']
        )
        
        return recovered_config, recovery_success
    
    def handle_permission_issues(self, config: DirectoryConfig) -> DirectoryConfig:
        """
        Handle permission issues by attempting alternative locations.
        
        Args:
            config: DirectoryConfig with potential permission issues
            
        Returns:
            DirectoryConfig with alternative paths if needed
        """
        logger.info("Checking for permission issues and applying alternatives")
        
        validator = DirectoryValidator()
        config_dict = config.to_dict()
        default_config = get_default_config()
        default_dirs = default_config['directories']
        
        permission_fixes_applied = False
        
        for dir_name, dir_path in config_dict.items():
            permissions = validator.check_permissions(dir_path)
            
            if dir_path.exists() and not (permissions['readable'] and permissions['writable']):
                logger.warning(f"Permission issues detected for {dir_name}: {dir_path}")
                
                # Try default location as alternative
                default_path = Path(default_dirs[dir_name])
                default_permissions = validator.check_permissions(default_path)
                
                if (not default_path.exists() or 
                    (default_permissions['readable'] and default_permissions['writable'])):
                    
                    logger.info(f"Using alternative location for {dir_name}: {default_path}")
                    config_dict[dir_name] = default_path
                    permission_fixes_applied = True
                    
                    self.recovery_attempts.append({
                        'directory': dir_name,
                        'original_path': str(dir_path),
                        'fallback_path': str(default_path),
                        'reason': 'Permission issues',
                        'recovery_successful': True
                    })
        
        if permission_fixes_applied:
            self.fallback_applied = True
            
            # Create new config with fixed paths
            recovered_config = DirectoryConfig(
                json_docs=config_dict['json_docs'],
                corrected=config_dict['corrected'],
                audits=config_dict['audits'],
                pdf_docs=config_dict['pdf_docs'],
                locks=config_dict['locks']
            )
            return recovered_config
        
        return config
    
    def _attempt_partial_config_recovery(self) -> Optional[Dict[str, Any]]:
        """
        Attempt to recover partial configuration from config file.
        
        Returns:
            Partial configuration dictionary or None if recovery fails
        """
        try:
            config_path = Path("config.yaml")
            if not config_path.exists():
                return None
            
            # Try to load raw YAML content
            import yaml
            with open(config_path, 'r', encoding='utf-8') as f:
                raw_content = f.read()
            
            # Attempt to parse YAML
            partial_config = yaml.safe_load(raw_content)
            
            if not isinstance(partial_config, dict):
                return None
            
            # Merge with defaults for missing sections
            default_config = get_default_config()
            
            # Only use directories section if it exists and is valid
            if 'directories' in partial_config and isinstance(partial_config['directories'], dict):
                # Validate each directory entry
                valid_dirs = {}
                default_dirs = default_config['directories']
                
                for dir_name in default_dirs.keys():
                    if (dir_name in partial_config['directories'] and 
                        isinstance(partial_config['directories'][dir_name], str)):
                        valid_dirs[dir_name] = partial_config['directories'][dir_name]
                    else:
                        valid_dirs[dir_name] = default_dirs[dir_name]
                
                # Create partial config with recovered directories
                recovered_config = deepcopy(default_config)
                recovered_config['directories'] = valid_dirs
                
                # Add other valid sections from partial config
                for section in ['app', 'schema', 'ui', 'processing']:
                    if (section in partial_config and 
                        isinstance(partial_config[section], dict)):
                        recovered_config[section].update(partial_config[section])
                
                return recovered_config
            
            return None
            
        except Exception as e:
            logger.warning(f"Partial config recovery failed: {e}")
            return None
    
    def get_degradation_summary(self) -> Dict[str, Any]:
        """
        Get summary of degradation actions taken.
        
        Returns:
            Dictionary with degradation summary
        """
        return {
            'fallback_applied': self.fallback_applied,
            'degradation_events': len(self.degradation_log),
            'recovery_attempts': len(self.recovery_attempts),
            'successful_recoveries': len([r for r in self.recovery_attempts 
                                        if r.get('recovery_successful', False)]),
            'degradation_log': self.degradation_log,
            'recovery_attempts': self.recovery_attempts
        }
    
    def create_user_guidance(self) -> List[str]:
        """
        Create user guidance based on degradation actions taken.
        
        Returns:
            List of user guidance messages
        """
        guidance = []
        
        if not self.fallback_applied:
            guidance.append("✅ Directory configuration loaded successfully")
            return guidance
        
        guidance.append("⚠️ Configuration issues were detected and automatic fallbacks were applied:")
        
        for attempt in self.recovery_attempts:
            if attempt.get('recovery_successful', False):
                guidance.append(f"  • {attempt['directory']}: Using fallback location '{attempt['fallback_path']}'")
            else:
                guidance.append(f"  • {attempt['directory']}: Failed to create directory (reason: {attempt['reason']})")
        
        guidance.append("")
        guidance.append("💡 To resolve these issues:")
        guidance.append("  • Check your config.yaml file for correct directory paths")
        guidance.append("  • Verify directory permissions and accessibility")
        guidance.append("  • Ensure parent directories exist")
        guidance.append("  • Consider using absolute paths instead of relative paths")
        
        return guidance


def apply_graceful_degradation(config_error: Optional[Exception] = None) -> DirectoryConfig:
    """
    Apply graceful degradation for directory configuration.
    
    Args:
        config_error: Optional configuration error that triggered degradation
        
    Returns:
        DirectoryConfig instance with fallbacks applied as needed
    """
    manager = GracefulDegradationManager()
    
    try:
        # Try to load configuration
        if config_error:
            config = manager.handle_configuration_failure(config_error)
        else:
            try:
                raw_config = load_config()
                config = DirectoryConfig.from_config(raw_config)
            except Exception as e:
                config = manager.handle_configuration_failure(e)
        
        # Validate directories
        validator = DirectoryValidator()
        validation_results = validator.validate_all_paths(config)
        
        # Handle validation failures
        config = manager.handle_validation_failure(config, validation_results)
        
        # Handle permission issues
        config = manager.handle_permission_issues(config)
        
        # Attempt to create directories
        creator = DirectoryCreator()
        creation_results = creator.create_all_directories(config)
        
        # Handle creation failures
        config, creation_success = manager.handle_creation_failure(config, creation_results)
        
        # Log degradation summary
        summary = manager.get_degradation_summary()
        if summary['fallback_applied']:
            logger.info("Graceful degradation applied successfully")
            logger.info(f"Degradation summary: {summary}")
        
        return config
        
    except Exception as e:
        logger.error(f"Graceful degradation failed: {e}")
        # Last resort: use complete defaults
        logger.info("Using complete default configuration as last resort")
        default_config = get_default_config()
        return DirectoryConfig.from_config(default_config)