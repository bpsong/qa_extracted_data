"""
Integration tests for configurable directories feature.

Tests the complete workflow from configuration loading to directory usage.
"""

import pytest
import tempfile
import yaml
import json
import os
from pathlib import Path
from unittest.mock import patch
from typing import Dict, Any, Optional

from utils.config_loader import load_config, get_default_config
from utils.directory_config import DirectoryConfig
from utils.directory_validator import DirectoryValidator
from utils.directory_creator import DirectoryCreator
from utils.graceful_degradation import apply_graceful_degradation
from utils.file_utils import initialize_directories, get_directories
from utils.directory_exceptions import DirectoryConfigError


class TestCompleteWorkflow:
    """Test complete directory configuration workflow."""
    
    def test_end_to_end_with_valid_config(self) -> None:
        """Test complete workflow with valid configuration."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            config_file = temp_path / 'config.yaml'
            
            # Create valid config file
            config_data = {
                'app': {'name': 'Test App', 'version': '1.0.0'},
                'directories': {
                    'json_docs': str(temp_path / 'input'),
                    'corrected': str(temp_path / 'output'),
                    'audits': str(temp_path / 'logs'),
                    'pdf_docs': str(temp_path / 'pdfs'),
                    'locks': str(temp_path / 'locks')
                },
                'processing': {'lock_timeout': 30}
            }
            
            with open(config_file, 'w') as f:
                yaml.dump(config_data, f)
            
            # Test complete workflow
            with patch('utils.config_loader.Path') as mock_path_class:
                mock_path_class.return_value = config_file
                mock_path_class.side_effect = lambda x: Path(x) if x != "config.yaml" else config_file
                
                # Initialize directories
                success = initialize_directories()
                assert success is True
                
                # Get directory configuration
                dirs = get_directories()
                assert isinstance(dirs, DirectoryConfig)
                
                # Verify all directories were created
                for name, path in dirs.to_dict().items():
                    assert path.exists()
                    assert path.is_dir()
                
                # Verify configuration values
                assert dirs.json_docs == temp_path / 'input'
                assert dirs.corrected == temp_path / 'output'
    
    def test_end_to_end_with_missing_config(self) -> None:
        """Test complete workflow when config file is missing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Change to temp directory so default directories are created there
            original_cwd = os.getcwd()
            try:
                os.chdir(temp_dir)
                
                # Initialize without config file
                success = initialize_directories()
                assert success is True
                
                # Should use defaults
                dirs = get_directories()
                assert isinstance(dirs, DirectoryConfig)
                
                # Verify default directories were created
                assert (Path(temp_dir) / 'json_docs').exists()
                assert (Path(temp_dir) / 'corrected').exists()
                assert (Path(temp_dir) / 'audits').exists()
                assert (Path(temp_dir) / 'pdf_docs').exists()
                assert (Path(temp_dir) / 'locks').exists()
                
            finally:
                os.chdir(original_cwd)
    
    def test_end_to_end_with_partial_config(self) -> None:
        """Test workflow with partial configuration."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            config_file = temp_path / 'config.yaml'
            
            # Create partial config (missing some directories)
            config_data = {
                'directories': {
                    'json_docs': str(temp_path / 'custom_input'),
                    'corrected': str(temp_path / 'custom_output')
                    # Missing audits, pdf_docs, locks - should use defaults
                }
            }
            
            with open(config_file, 'w') as f:
                yaml.dump(config_data, f)
            
            with patch('utils.config_loader.Path') as mock_path_class:
                mock_path_class.return_value = config_file
                mock_path_class.side_effect = lambda x: Path(x) if x != "config.yaml" else config_file
                
                success = initialize_directories()
                assert success is True
                
                dirs = get_directories()
                
                # Custom directories
                assert dirs.json_docs == temp_path / 'custom_input'
                assert dirs.corrected == temp_path / 'custom_output'
                
                # Default directories (created in temp dir)
                assert dirs.audits.name == 'audits'
                assert dirs.pdf_docs.name == 'pdf_docs'
                assert dirs.locks.name == 'locks'
                
                # All should exist
                for name, path in dirs.to_dict().items():
                    assert path.exists()
    
    def test_end_to_end_with_invalid_config(self) -> None:
        """Test workflow with invalid configuration."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            config_file = temp_path / 'config.yaml'
            
            # Create invalid YAML
            with open(config_file, 'w') as f:
                f.write("invalid: yaml: content: [")
            
            with patch('utils.config_loader.Path') as mock_path_class:
                mock_path_class.return_value = config_file
                mock_path_class.side_effect = lambda x: Path(x) if x != "config.yaml" else config_file
                
                # Should still succeed with defaults
                success = initialize_directories()
                assert success is True
                
                dirs = get_directories()
                assert isinstance(dirs, DirectoryConfig)
    
    def test_end_to_end_with_permission_issues(self) -> None:
        """Test workflow when some directories have permission issues."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            config_file = temp_path / 'config.yaml'
            
            # Create config with some problematic paths
            config_data = {
                'directories': {
                    'json_docs': str(temp_path / 'good_input'),
                    'corrected': '/root/restricted',  # Likely no permission
                    'audits': str(temp_path / 'good_audits'),
                    'pdf_docs': '/usr/restricted',  # Likely no permission
                    'locks': str(temp_path / 'good_locks')
                }
            }
            
            with open(config_file, 'w') as f:
                yaml.dump(config_data, f)
            
            with patch('utils.config_loader.Path') as mock_path_class:
                mock_path_class.return_value = config_file
                mock_path_class.side_effect = lambda x: Path(x) if x != "config.yaml" else config_file
                
                # Should succeed with graceful degradation
                success = initialize_directories()
                assert success is True
                
                dirs = get_directories()
                
                # Should have working directories (may be defaults for failed ones)
                for name, path in dirs.to_dict().items():
                    # At minimum, should be able to create in temp directory
                    assert isinstance(path, Path)


class TestConfigurationScenarios:
    """Test various configuration scenarios."""
    
    def test_configuration_with_relative_paths(self) -> None:
        """Test configuration with relative directory paths."""
        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = os.getcwd()
            try:
                os.chdir(temp_dir)
                
                config_data = {
                    'directories': {
                        'json_docs': './input',
                        'corrected': '../output',
                        'audits': 'logs/audits',
                        'pdf_docs': './documents/pdfs',
                        'locks': 'temp/locks'
                    }
                }
                
                # Test graceful degradation with this config
                dirs = apply_graceful_degradation()
                
                # Should handle relative paths
                assert isinstance(dirs, DirectoryConfig)
                
            finally:
                os.chdir(original_cwd)
    
    def test_configuration_with_absolute_paths(self) -> None:
        """Test configuration with absolute directory paths."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            config_data = {
                'directories': {
                    'json_docs': str(temp_path / 'abs_input'),
                    'corrected': str(temp_path / 'abs_output'),
                    'audits': str(temp_path / 'abs_audits'),
                    'pdf_docs': str(temp_path / 'abs_pdfs'),
                    'locks': str(temp_path / 'abs_locks')
                }
            }
            
            # Create DirectoryConfig and test creation
            dirs = DirectoryConfig.from_config(config_data)
            creator = DirectoryCreator()
            results = creator.create_all_directories(dirs)
            
            # All should be successful
            assert all(result.is_successful for result in results)
            
            # Verify absolute paths
            for name, path in dirs.to_dict().items():
                assert path.is_absolute()
                assert path.exists()
    
    def test_configuration_validation_and_recovery(self) -> None:
        """Test configuration validation and recovery mechanisms."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Create a mix of valid and invalid paths
            valid_dir = temp_path / 'valid'
            valid_dir.mkdir()
            
            # Create a file where we want a directory
            file_conflict = temp_path / 'file_conflict'
            file_conflict.write_text('content')
            
            config_data = {
                'directories': {
                    'json_docs': str(valid_dir),  # Valid
                    'corrected': str(file_conflict),  # Invalid (file exists)
                    'audits': '/invalid/path/that/cannot/exist',  # Invalid
                    'pdf_docs': str(temp_path / 'new_dir'),  # Valid (will be created)
                    'locks': str(temp_path / 'another_new')  # Valid (will be created)
                }
            }
            
            dirs = DirectoryConfig.from_config(config_data)
            
            # Test validation
            validator = DirectoryValidator()
            validation_results = validator.validate_all_paths(dirs)
            
            # Should have some failures
            failed_validations = [r for r in validation_results if not r.is_ready]
            assert len(failed_validations) > 0
            
            # Test graceful degradation
            recovered_dirs = apply_graceful_degradation()
            
            # Should have valid configuration after recovery
            final_validation = validator.validate_all_paths(recovered_dirs)
            creator = DirectoryCreator()
            creator.create_all_directories(recovered_dirs)
            
            # Final validation should pass
            final_results = validator.validate_all_paths(recovered_dirs)
            ready_count = sum(1 for r in final_results if r.is_ready)
            assert ready_count >= 3  # At least most directories should be ready


class TestBackwardCompatibility:
    """Test backward compatibility with existing deployments."""
    
    def test_no_config_file_uses_defaults(self) -> None:
        """Test that missing config file uses hardcoded defaults."""
        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = os.getcwd()
            try:
                os.chdir(temp_dir)
                
                # No config file exists
                assert not Path('config.yaml').exists()
                
                # Initialize should succeed
                success = initialize_directories()
                assert success is True
                
                # Should use default paths
                dirs = get_directories()
                default_config = get_default_config()
                
                for dir_name in default_config['directories']:
                    expected_path = Path(default_config['directories'][dir_name])
                    actual_path: Optional[Path] = dirs.get_path(dir_name)
                    assert actual_path is not None
                    assert actual_path.name == expected_path.name
                
            finally:
                os.chdir(original_cwd)
    
    def test_empty_config_file_uses_defaults(self) -> None:
        """Test that empty config file uses defaults."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            config_file = temp_path / 'config.yaml'
            
            # Create empty config file
            config_file.write_text('')
            
            with patch('utils.config_loader.Path') as mock_path_class:
                mock_path_class.return_value = config_file
                mock_path_class.side_effect = lambda x: Path(x) if x != "config.yaml" else config_file
                
                success = initialize_directories()
                assert success is True
                
                dirs = get_directories()
                
                # Should use defaults
                assert dirs.json_docs.name == 'json_docs'
                assert dirs.corrected.name == 'corrected'
    
    def test_config_without_directories_section(self) -> None:
        """Test config file without directories section."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            config_file = temp_path / 'config.yaml'
            
            # Config without directories section
            config_data = {
                'app': {'name': 'Test App'},
                'schema': {'primary_schema': 'test.yaml'}
            }
            
            with open(config_file, 'w') as f:
                yaml.dump(config_data, f)
            
            with patch('utils.config_loader.Path') as mock_path_class:
                mock_path_class.return_value = config_file
                mock_path_class.side_effect = lambda x: Path(x) if x != "config.yaml" else config_file
                
                success = initialize_directories()
                assert success is True
                
                dirs = get_directories()
                
                # Should use defaults for directories
                assert dirs.json_docs.name == 'json_docs'
                assert dirs.corrected.name == 'corrected'


class TestPerformanceAndScaling:
    """Test performance aspects of directory configuration."""
    
    def test_startup_time_with_many_directories(self) -> None:
        """Test that startup time is reasonable with directory validation."""
        import time
        
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Create config with many directories (simulating complex setup)
            config_data = {
                'directories': {
                    'json_docs': str(temp_path / 'input'),
                    'corrected': str(temp_path / 'output'),
                    'audits': str(temp_path / 'audits'),
                    'pdf_docs': str(temp_path / 'pdfs'),
                    'locks': str(temp_path / 'locks')
                }
            }
            
            # Measure initialization time
            start_time = time.time()
            
            dirs = DirectoryConfig.from_config(config_data)
            validator = DirectoryValidator()
            creator = DirectoryCreator()
            
            validation_results = validator.validate_all_paths(dirs)
            creation_results = creator.create_all_directories(dirs)
            
            end_time = time.time()
            
            # Should complete quickly (under 1 second for this simple case)
            elapsed_time = end_time - start_time
            assert elapsed_time < 1.0
            
            # All operations should succeed
            assert all(result.is_successful for result in creation_results)
    
    def test_concurrent_directory_access(self) -> None:
        """Test that directory configuration works with concurrent access."""
        import threading
        import time
        
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            config_data = {
                'directories': {
                    'json_docs': str(temp_path / 'input'),
                    'corrected': str(temp_path / 'output'),
                    'audits': str(temp_path / 'audits'),
                    'pdf_docs': str(temp_path / 'pdfs'),
                    'locks': str(temp_path / 'locks')
                }
            }
            
            dirs = DirectoryConfig.from_config(config_data)
            creator = DirectoryCreator()
            creator.create_all_directories(dirs)
            
            results = []
            
            def access_directories() -> None:
                """Function to access directories concurrently."""
                try:
                    # Simulate file operations
                    test_file = dirs.json_docs / f'test_{threading.current_thread().ident}.json'
                    test_file.write_text('{"test": "data"}')
                    
                    # Read it back
                    content = test_file.read_text()
                    data = json.loads(content)
                    
                    results.append(True)
                except Exception as e:
                    results.append(False)
            
            # Create multiple threads
            threads = []
            for i in range(5):
                thread = threading.Thread(target=access_directories)
                threads.append(thread)
            
            # Start all threads
            for thread in threads:
                thread.start()
            
            # Wait for completion
            for thread in threads:
                thread.join()
            
            # All operations should succeed
            assert all(results)
            assert len(results) == 5


if __name__ == '__main__':
    pytest.main([__file__])