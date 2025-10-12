"""
Unit tests for directory creator module.
"""

import pytest
import tempfile
import os
import stat
from pathlib import Path
from unittest.mock import patch, MagicMock

from utils.directory_creator import DirectoryCreator, CreationResult
from utils.directory_config import DirectoryConfig


class TestCreationResult:
    """Test cases for CreationResult class."""
    
    def test_creation_result_successful_when_created(self):
        """Test CreationResult.is_successful when directory was created."""
        result = CreationResult(
            path=Path('/test/path'),
            created=True,
            already_existed=False
        )
        
        assert result.is_successful is True
    
    def test_creation_result_successful_when_already_existed(self):
        """Test CreationResult.is_successful when directory already existed."""
        result = CreationResult(
            path=Path('/test/path'),
            created=False,
            already_existed=True
        )
        
        assert result.is_successful is True
    
    def test_creation_result_not_successful_when_failed(self):
        """Test CreationResult.is_successful when creation failed."""
        result = CreationResult(
            path=Path('/test/path'),
            created=False,
            already_existed=False,
            error_message='Creation failed'
        )
        
        assert result.is_successful is False


class TestDirectoryCreator:
    """Test cases for DirectoryCreator class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.creator = DirectoryCreator()
    
    def test_create_directory_new_directory(self):
        """Test creating a new directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            new_dir_path = Path(temp_dir) / 'new_directory'
            
            result = self.creator.create_directory(new_dir_path)
            
            assert result.path == new_dir_path
            assert result.created is True
            assert result.already_existed is False
            assert result.is_successful is True
            assert result.error_message is None
            assert new_dir_path.exists()
            assert new_dir_path.is_dir()
    
    def test_create_directory_already_exists(self):
        """Test creating a directory that already exists."""
        with tempfile.TemporaryDirectory() as temp_dir:
            existing_path = Path(temp_dir)
            
            result = self.creator.create_directory(existing_path)
            
            assert result.path == existing_path
            assert result.created is False
            assert result.already_existed is True
            assert result.is_successful is True
            assert result.error_message is None
    
    def test_create_directory_with_parents(self):
        """Test creating a directory with parent directories."""
        with tempfile.TemporaryDirectory() as temp_dir:
            nested_path = Path(temp_dir) / 'parent' / 'child' / 'grandchild'
            
            result = self.creator.create_directory(nested_path)
            
            assert result.created is True
            assert result.is_successful is True
            assert nested_path.exists()
            assert nested_path.is_dir()
            assert nested_path.parent.exists()
            assert nested_path.parent.parent.exists()
    
    def test_create_directory_file_exists_at_path(self):
        """Test creating directory when a file exists at the same path."""
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            file_path = Path(temp_file.name)
            
        try:
            result = self.creator.create_directory(file_path)
            
            assert result.created is False
            assert result.already_existed is False
            assert result.is_successful is False
            assert result.error_message is not None
            assert 'not a directory' in result.error_message
        finally:
            # Clean up - use try/except for Windows compatibility
            try:
                file_path.unlink()
            except (PermissionError, FileNotFoundError):
                pass  # File may be locked on Windows
    
    @patch('pathlib.Path.mkdir')
    def test_create_directory_permission_error(self, mock_mkdir):
        """Test creating directory when permission is denied."""
        mock_mkdir.side_effect = PermissionError("Permission denied")
        
        test_path = Path('/test/path')
        result = self.creator.create_directory(test_path)
        
        assert result.created is False
        assert result.is_successful is False
        assert result.error_message is not None
        assert 'Permission denied' in result.error_message
    
    @patch('pathlib.Path.mkdir')
    def test_create_directory_os_error(self, mock_mkdir):
        """Test creating directory when OS error occurs."""
        mock_mkdir.side_effect = OSError("Disk full")
        
        test_path = Path('/test/path')
        result = self.creator.create_directory(test_path)
        
        assert result.created is False
        assert result.is_successful is False
        assert result.error_message is not None
        assert 'OS error' in result.error_message
    
    def test_create_directory_with_custom_permissions(self):
        """Test creating directory with custom permissions."""
        with tempfile.TemporaryDirectory() as temp_dir:
            new_dir_path = Path(temp_dir) / 'new_directory'
            custom_permissions = 0o750
            
            result = self.creator.create_directory(new_dir_path, custom_permissions)
            
            assert result.created is True
            assert result.is_successful is True
            assert result.permissions_set is True
            
            # Check permissions (may vary by system)
            if os.name != 'nt':  # Skip on Windows
                actual_permissions = new_dir_path.stat().st_mode & 0o777
                assert actual_permissions == custom_permissions
    
    def test_create_all_directories_success(self):
        """Test creating all directories from DirectoryConfig successfully."""
        with tempfile.TemporaryDirectory() as temp_dir:
            base_path = Path(temp_dir)
            
            config = DirectoryConfig(
                json_docs=base_path / 'input',
                corrected=base_path / 'output',
                audits=base_path / 'audits',
                pdf_docs=base_path / 'pdfs',
                locks=base_path / 'locks'
            )
            
            results = self.creator.create_all_directories(config)
            
            assert len(results) == 5
            assert all(result.is_successful for result in results)
            assert all(result.created for result in results)
            
            # Verify all directories exist
            for name, path in config.to_dict().items():
                assert path.exists()
                assert path.is_dir()
    
    def test_create_all_directories_mixed_results(self):
        """Test creating directories with some already existing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            base_path = Path(temp_dir)
            
            # Create some directories beforehand
            existing_dir = base_path / 'existing'
            existing_dir.mkdir()
            
            config = DirectoryConfig(
                json_docs=existing_dir,  # Already exists
                corrected=base_path / 'new_output',  # New
                audits=base_path / 'new_audits',  # New
                pdf_docs=existing_dir,  # Already exists
                locks=base_path / 'new_locks'  # New
            )
            
            results = self.creator.create_all_directories(config)
            
            assert len(results) == 5
            assert all(result.is_successful for result in results)
            
            # Check creation status
            created_count = sum(1 for result in results if result.created)
            existed_count = sum(1 for result in results if result.already_existed)
            
            assert created_count == 3  # new_output, new_audits, new_locks
            assert existed_count == 2  # existing (appears twice)
    
    def test_ensure_directory_structure_success(self):
        """Test ensuring complete directory structure."""
        with tempfile.TemporaryDirectory() as temp_dir:
            base_path = Path(temp_dir)
            
            config = DirectoryConfig(
                json_docs=base_path / 'input',
                corrected=base_path / 'output',
                audits=base_path / 'audits',
                pdf_docs=base_path / 'pdfs',
                locks=base_path / 'locks'
            )
            
            success = self.creator.ensure_directory_structure(config)
            
            assert success is True
            
            # Verify all directories exist
            for name, path in config.to_dict().items():
                assert path.exists()
                assert path.is_dir()
    
    @patch('utils.directory_creator.DirectoryCreator.create_directory')
    def test_ensure_directory_structure_failure(self, mock_create):
        """Test ensuring directory structure when some creations fail."""
        # Mock some successful and some failed creations
        mock_results = [
            CreationResult(Path('/path1'), True, False),  # Success
            CreationResult(Path('/path2'), False, False, 'Failed'),  # Failure
            CreationResult(Path('/path3'), True, False),  # Success
            CreationResult(Path('/path4'), False, False, 'Failed'),  # Failure
            CreationResult(Path('/path5'), True, False)   # Success
        ]
        mock_create.side_effect = mock_results
        
        config = DirectoryConfig(
            json_docs=Path('/path1'),
            corrected=Path('/path2'),
            audits=Path('/path3'),
            pdf_docs=Path('/path4'),
            locks=Path('/path5')
        )
        
        success = self.creator.ensure_directory_structure(config)
        
        assert success is False  # Should fail due to some failed creations
    
    def test_get_creation_summary_all_successful(self):
        """Test creation summary when all operations are successful."""
        results = [
            CreationResult(Path('/path1'), True, False),   # Created
            CreationResult(Path('/path2'), False, True),   # Already existed
            CreationResult(Path('/path3'), True, False),   # Created
        ]
        
        summary = self.creator.get_creation_summary(results)
        
        assert summary['total_directories'] == 3
        assert summary['created_directories'] == 2
        assert summary['existing_directories'] == 1
        assert summary['failed_directories'] == 0
        assert summary['successful_operations'] == 3
        assert summary['permission_issues'] == 0
        assert len(summary['errors']) == 0
    
    def test_get_creation_summary_with_failures(self):
        """Test creation summary with some failures."""
        results = [
            CreationResult(Path('/path1'), True, False),   # Created
            CreationResult(Path('/path2'), False, False, 'Permission denied'),  # Failed
            CreationResult(Path('/path3'), False, True),   # Already existed
            CreationResult(Path('/path4'), False, False, 'Disk full', False),  # Failed with permission issue
        ]
        
        summary = self.creator.get_creation_summary(results)
        
        assert summary['total_directories'] == 4
        assert summary['created_directories'] == 1
        assert summary['existing_directories'] == 1
        assert summary['failed_directories'] == 2
        assert summary['successful_operations'] == 2
        assert summary['permission_issues'] == 1
        assert len(summary['errors']) == 2
    
    def test_cleanup_empty_directories_dry_run(self):
        """Test cleanup of empty directories in dry run mode."""
        with tempfile.TemporaryDirectory() as temp_dir:
            base_path = Path(temp_dir)
            
            # Create some directories, some empty, some with files
            empty_dir1 = base_path / 'empty1'
            empty_dir2 = base_path / 'empty2'
            non_empty_dir = base_path / 'non_empty'
            
            empty_dir1.mkdir()
            empty_dir2.mkdir()
            non_empty_dir.mkdir()
            
            # Add a file to non_empty_dir
            (non_empty_dir / 'file.txt').write_text('content')
            
            config = DirectoryConfig(
                json_docs=empty_dir1,
                corrected=empty_dir2,
                audits=non_empty_dir,
                pdf_docs=base_path / 'nonexistent',  # Doesn't exist
                locks=empty_dir1  # Duplicate, but that's ok
            )
            
            removed_dirs = self.creator.cleanup_empty_directories(config, dry_run=True)
            
            # Should identify empty directories but not remove them
            # Note: empty_dir1 appears twice in config (json_docs and locks)
            assert len(removed_dirs) == 3  # empty_dir1 (twice) + empty_dir2
            assert empty_dir1.exists()  # Still exists (dry run)
            assert empty_dir2.exists()  # Still exists (dry run)
            assert non_empty_dir.exists()  # Should not be marked for removal
    
    def test_cleanup_empty_directories_actual_removal(self):
        """Test actual cleanup of empty directories."""
        with tempfile.TemporaryDirectory() as temp_dir:
            base_path = Path(temp_dir)
            
            # Create empty directories
            empty_dir1 = base_path / 'empty1'
            empty_dir2 = base_path / 'empty2'
            
            empty_dir1.mkdir()
            empty_dir2.mkdir()
            
            config = DirectoryConfig(
                json_docs=empty_dir1,
                corrected=empty_dir2,
                audits=base_path / 'nonexistent',
                pdf_docs=base_path / 'nonexistent2',
                locks=base_path / 'nonexistent3'
            )
            
            removed_dirs = self.creator.cleanup_empty_directories(config, dry_run=False)
            
            # Should remove empty directories
            assert len(removed_dirs) == 2
            assert not empty_dir1.exists()  # Should be removed
            assert not empty_dir2.exists()  # Should be removed


if __name__ == '__main__':
    pytest.main([__file__])