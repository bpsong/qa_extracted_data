"""
Unit tests for directory validator module.
"""

import pytest
import tempfile
import os
from pathlib import Path
from unittest.mock import patch, MagicMock

from utils.directory_validator import DirectoryValidator, ValidationResult
from utils.directory_config import DirectoryConfig


class TestValidationResult:
    """Test cases for ValidationResult class."""
    
    def test_validation_result_ready_when_all_valid(self):
        """Test ValidationResult.is_ready when all conditions are met."""
        result = ValidationResult(
            path=Path('/test/path'),
            is_valid=True,
            exists=True,
            is_writable=True,
            is_readable=True
        )
        
        assert result.is_ready is True
    
    def test_validation_result_not_ready_when_invalid_path(self):
        """Test ValidationResult.is_ready when path is invalid."""
        result = ValidationResult(
            path=Path('/test/path'),
            is_valid=False,
            exists=True,
            is_writable=True,
            is_readable=True
        )
        
        assert result.is_ready is False
    
    def test_validation_result_not_ready_when_not_exists(self):
        """Test ValidationResult.is_ready when directory doesn't exist."""
        result = ValidationResult(
            path=Path('/test/path'),
            is_valid=True,
            exists=False,
            is_writable=True,
            is_readable=True
        )
        
        assert result.is_ready is False
    
    def test_validation_result_not_ready_when_not_writable(self):
        """Test ValidationResult.is_ready when directory is not writable."""
        result = ValidationResult(
            path=Path('/test/path'),
            is_valid=True,
            exists=True,
            is_writable=False,
            is_readable=True
        )
        
        assert result.is_ready is False


class TestDirectoryValidator:
    """Test cases for DirectoryValidator class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.validator = DirectoryValidator()
    
    def test_validate_path_existing_directory(self):
        """Test validating an existing, accessible directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            result = self.validator.validate_path(temp_path)
            
            assert result.path == temp_path
            assert result.is_valid is True
            assert result.exists is True
            assert result.is_readable is True
            assert result.is_writable is True
            assert result.is_ready is True
            assert result.error_message is None
    
    def test_validate_path_nonexistent_directory(self):
        """Test validating a non-existent directory."""
        nonexistent_path = Path('/this/path/does/not/exist')
        
        result = self.validator.validate_path(nonexistent_path)
        
        assert result.path == nonexistent_path
        assert result.is_valid is True  # Path format is valid
        assert result.exists is False
        assert result.is_ready is False
        assert result.error_message is not None
        assert 'does not exist' in result.error_message
    
    def test_validate_path_file_instead_of_directory(self):
        """Test validating a path that points to a file, not directory."""
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            temp_path = Path(temp_file.name)
            
        try:
            result = self.validator.validate_path(temp_path)
            
            assert result.path == temp_path
            assert result.is_valid is True
            assert result.exists is True
            assert result.is_ready is False
            assert result.error_message is not None
            assert 'not a directory' in result.error_message
        finally:
            # Clean up - use try/except for Windows compatibility
            try:
                temp_path.unlink()
            except (PermissionError, FileNotFoundError):
                pass  # File may be locked on Windows
    
    def test_validate_path_invalid_path_format(self):
        """Test validating an invalid path format."""
        # Create a path that will cause resolution to fail
        with patch('pathlib.Path.resolve') as mock_resolve:
            mock_resolve.side_effect = OSError("Invalid path")
            
            invalid_path = Path('/invalid\x00path')
            result = self.validator.validate_path(invalid_path)
            
            assert result.path == invalid_path
            assert result.is_valid is False
            assert result.is_ready is False
            assert result.error_message is not None
    
    def test_validate_all_paths_mixed_results(self):
        """Test validating all paths in a DirectoryConfig with mixed results."""
        with tempfile.TemporaryDirectory() as temp_dir:
            existing_path = Path(temp_dir)
            nonexistent_path = Path('/this/does/not/exist')
            
            config = DirectoryConfig(
                json_docs=existing_path,
                corrected=existing_path,
                audits=nonexistent_path,
                pdf_docs=nonexistent_path,
                locks=existing_path
            )
            
            results = self.validator.validate_all_paths(config)
            
            assert len(results) == 5
            
            # Check that existing paths are ready
            ready_results = [r for r in results if r.is_ready]
            not_ready_results = [r for r in results if not r.is_ready]
            
            assert len(ready_results) == 3  # json_docs, corrected, locks
            assert len(not_ready_results) == 2  # audits, pdf_docs
    
    def test_check_permissions_existing_directory(self):
        """Test checking permissions on an existing directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            permissions = self.validator.check_permissions(temp_path)
            
            assert permissions['exists'] is True
            assert permissions['is_directory'] is True
            assert permissions['readable'] is True
            assert permissions['writable'] is True
            assert permissions['executable'] is True
    
    def test_check_permissions_nonexistent_path(self):
        """Test checking permissions on non-existent path."""
        nonexistent_path = Path('/this/does/not/exist')
        
        permissions = self.validator.check_permissions(nonexistent_path)
        
        assert permissions['exists'] is False
        assert permissions['is_directory'] is False
        assert permissions['readable'] is False
        assert permissions['writable'] is False
        assert permissions['executable'] is False
    
    def test_check_permissions_file_instead_of_directory(self):
        """Test checking permissions on a file instead of directory."""
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            temp_path = Path(temp_file.name)
            
        try:
            permissions = self.validator.check_permissions(temp_path)
            
            assert permissions['exists'] is True
            assert permissions['is_directory'] is False
            assert permissions['readable'] is False  # Not applicable to files in this context
            assert permissions['writable'] is False
            assert permissions['executable'] is False
        finally:
            # Clean up - use try/except for Windows compatibility
            try:
                temp_path.unlink()
            except (PermissionError, FileNotFoundError):
                pass  # File may be locked on Windows
    
    @patch('os.access')
    def test_check_readable_permission_denied(self, mock_access):
        """Test _check_readable when permission is denied."""
        mock_access.return_value = False
        
        test_path = Path('/test/path')
        result = self.validator._check_readable(test_path)
        
        assert result is False
        mock_access.assert_called_once_with(test_path, os.R_OK)
    
    @patch('os.access')
    def test_check_writable_permission_denied(self, mock_access):
        """Test _check_writable when permission is denied."""
        mock_access.return_value = False
        
        test_path = Path('/test/path')
        result = self.validator._check_writable(test_path)
        
        assert result is False
        mock_access.assert_called_once_with(test_path, os.W_OK)
    
    @patch('os.access')
    def test_check_executable_permission_denied(self, mock_access):
        """Test _check_executable when permission is denied."""
        mock_access.return_value = False
        
        test_path = Path('/test/path')
        result = self.validator._check_executable(test_path)
        
        assert result is False
        mock_access.assert_called_once_with(test_path, os.X_OK)
    
    def test_get_validation_summary_all_ready(self):
        """Test validation summary when all directories are ready."""
        results = [
            ValidationResult(Path('/path1'), True, True, True, True),
            ValidationResult(Path('/path2'), True, True, True, True),
            ValidationResult(Path('/path3'), True, True, True, True)
        ]
        
        summary = self.validator.get_validation_summary(results)
        
        assert summary['total_directories'] == 3
        assert summary['valid_paths'] == 3
        assert summary['existing_directories'] == 3
        assert summary['ready_directories'] == 3
        assert summary['permission_issues'] == 0
        assert summary['missing_directories'] == 0
        assert summary['invalid_paths'] == 0
        assert len(summary['errors']) == 0
    
    def test_get_validation_summary_mixed_results(self):
        """Test validation summary with mixed results."""
        results = [
            ValidationResult(Path('/path1'), True, True, True, True),  # Ready
            ValidationResult(Path('/path2'), True, False, False, False, 'Does not exist'),  # Missing
            ValidationResult(Path('/path3'), True, True, False, True, 'Not writable'),  # Permission issue
            ValidationResult(Path('/path4'), False, False, False, False, 'Invalid path')  # Invalid
        ]
        
        summary = self.validator.get_validation_summary(results)
        
        assert summary['total_directories'] == 4
        assert summary['valid_paths'] == 3
        assert summary['existing_directories'] == 2
        assert summary['ready_directories'] == 1
        assert summary['permission_issues'] == 1
        assert summary['missing_directories'] == 2
        assert summary['invalid_paths'] == 1
        assert len(summary['errors']) == 3  # Three results have error messages
    
    def test_validate_path_with_parent_writable(self):
        """Test validating non-existent path with writable parent."""
        with tempfile.TemporaryDirectory() as temp_dir:
            parent_path = Path(temp_dir)
            nonexistent_child = parent_path / 'nonexistent_child'
            
            result = self.validator.validate_path(nonexistent_child)
            
            assert result.is_valid is True
            assert result.exists is False
            assert result.error_message is not None
            assert 'can be created' in result.error_message
    
    def test_validate_path_with_parent_not_writable(self):
        """Test validating non-existent path with non-writable parent."""
        # Use a system directory that typically isn't writable
        system_path = Path('/usr/nonexistent_directory')
        
        result = self.validator.validate_path(system_path)
        
        assert result.is_valid is True
        assert result.exists is False
        assert result.error_message is not None


if __name__ == '__main__':
    pytest.main([__file__])