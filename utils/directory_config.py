"""
Directory configuration management for the JSON QA webapp.

This module provides data models and utilities for managing configurable
directory paths throughout the application.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional
import logging

logger = logging.getLogger(__name__)


@dataclass
class DirectoryConfig:
    """
    Directory configuration model that holds all configurable directory paths.
    
    Attributes:
        json_docs: Path to directory containing input JSON files
        corrected: Path to directory for validated/corrected JSON files
        audits: Path to directory for audit logs
        pdf_docs: Path to directory for PDF documents
        locks: Path to directory for file locking
    """
    json_docs: Path
    corrected: Path
    audits: Path
    pdf_docs: Path
    locks: Path
    
    @classmethod
    def from_config(cls, config: dict) -> 'DirectoryConfig':
        """
        Create DirectoryConfig from configuration dictionary.
        
        Args:
            config: Configuration dictionary containing directories section
            
        Returns:
            DirectoryConfig instance with paths from config or defaults
            
        Example:
            config = {'directories': {'json_docs': 'custom_input'}}
            dir_config = DirectoryConfig.from_config(config)
        """
        directories = config.get('directories', {})
        
        return cls(
            json_docs=Path(directories.get('json_docs', 'json_docs')),
            corrected=Path(directories.get('corrected', 'corrected')),
            audits=Path(directories.get('audits', 'audits')),
            pdf_docs=Path(directories.get('pdf_docs', 'pdf_docs')),
            locks=Path(directories.get('locks', 'locks'))
        )
    
    def to_dict(self) -> Dict[str, Path]:
        """
        Convert DirectoryConfig to dictionary for easy access.
        
        Returns:
            Dictionary mapping directory names to Path objects
        """
        return {
            'json_docs': self.json_docs,
            'corrected': self.corrected,
            'audits': self.audits,
            'pdf_docs': self.pdf_docs,
            'locks': self.locks
        }
    
    def validate_paths(self) -> Dict[str, bool]:
        """
        Validate that all directory paths are valid path formats.
        
        Returns:
            Dictionary mapping directory names to validation status
        """
        validation_results = {}
        
        for name, path in self.to_dict().items():
            try:
                # Check if path is valid by attempting to resolve it
                resolved_path = path.resolve()
                validation_results[name] = True
            except (OSError, ValueError) as e:
                validation_results[name] = False
                logger.warning(f"Path validation failed for {name}: {path} - {e}")
        
        return validation_results
    
    def get_path(self, directory_type: str) -> Optional[Path]:
        """
        Get path for a specific directory type.
        
        Args:
            directory_type: Name of the directory type (e.g., 'json_docs')
            
        Returns:
            Path object for the directory or None if not found
        """
        directory_map = self.to_dict()
        return directory_map.get(directory_type)
    
    def __str__(self) -> str:
        """String representation of directory configuration."""
        paths = []
        for name, path in self.to_dict().items():
            paths.append(f"{name}: {path}")
        return f"DirectoryConfig({', '.join(paths)})"