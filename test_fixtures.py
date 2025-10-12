"""
Test fixtures and mock configurations for directory configuration tests.

Provides reusable test data, fixtures, and utilities for testing
the configurable directories feature.
"""

import pytest
import tempfile
import yaml
import json
from pathlib import Path
from typing import Dict, Any, List, Optional
from unittest.mock import MagicMock

from utils.directory_config import DirectoryConfig
from utils.directory_validator import ValidationResult
from utils.directory_creator import CreationResult


class ConfigurationFixtures:
    """Fixtures for various configuration scenarios."""
    
    @staticmethod
    def get_minimal_config() -> Dict[str, Any]:
        """Get minimal valid configuration."""
        return {
            'app': {'name': 'Test App', 'version': '1.0.0'},
            'directories': {
                'json_docs': 'json_docs',
                'corrected': 'corrected',
                'audits': 'audits',
                'pdf_docs': 'pdf_docs',
                'locks': 'locks'
            }
        }
    
    @staticmethod
    def get_complete_config() -> Dict[str, Any]:
        """Get complete configuration with all sections."""
        return {
            'app': {
                'name': 'JSON QA Webapp',
                'version': '2.0.0',
                'debug': True
            },
            'schema': {
                'primary_schema': 'invoice_schema.yaml',
                'fallback_schema': 'default_schema.yaml'
            },
            'directories': {
                'json_docs': 'custom_input',
                'corrected': 'custom_output',
                'audits': 'custom_audits',
                'pdf_docs': 'custom_pdfs',
                'locks': 'custom_locks'
            },
            'ui': {
                'page_title': 'Custom QA Tool',
                'sidebar_title': 'Custom Navigation'
            },
            'processing': {
                'lock_timeout': 120,
                'max_file_size': 25
            }
        }
    
    @staticmethod
    def get_partial_config() -> Dict[str, Any]:
        """Get partial configuration (missing some directories)."""
        return {
            'app': {'name': 'Partial App'},
            'directories': {
                'json_docs': 'custom_input',
                'corrected': 'custom_output'
                # Missing audits, pdf_docs, locks
            },
            'processing': {'lock_timeout': 90}
        }
    
    @staticmethod
    def get_invalid_config() -> Dict[str, Any]:
        """Get configuration with invalid values."""
        return {
            'app': {'name': 'Invalid App'},
            'directories': {
                'json_docs': 123,  # Should be string
                'corrected': None,   # Should be string
                'audits': '',        # Empty string
                'pdf_docs': 'valid_path',
                'locks': ['invalid', 'list']  # Should be string
            },
            'processing': {
                'lock_timeout': -5,  # Should be positive
                'max_file_size': 'invalid'  # Should be number
            }
        }
    
    @staticmethod
    def get_absolute_paths_config(base_path: Path) -> Dict[str, Any]:
        """Get configuration with absolute paths."""
        return {
            'directories': {
                'json_docs': str(base_path / 'abs_input'),
                'corrected': str(base_path / 'abs_output'),
                'audits': str(base_path / 'abs_audits'),
                'pdf_docs': str(base_path / 'abs_pdfs'),
                'locks': str(base_path / 'abs_locks')
            }
        }
    
    @staticmethod
    def get_relative_paths_config() -> Dict[str, Any]:
        """Get configuration with relative paths."""
        return {
            'directories': {
                'json_docs': './rel_input',
                'corrected': '../rel_output',
                'audits': 'logs/audits',
                'pdf_docs': './documents/pdfs',
                'locks': 'temp/locks'
            }
        }
    
    @staticmethod
    def get_problematic_paths_config() -> Dict[str, Any]:
        """Get configuration with problematic paths (for testing error handling)."""
        return {
            'directories': {
                'json_docs': '/root/restricted',  # Likely no permission
                'corrected': '/usr/bin/ls',         # File, not directory
                'audits': '/nonexistent/deep/path', # Parent doesn't exist
                'pdf_docs': '',                     # Empty path
                'locks': '/dev/null'                # Special file
            }
        }


class MockDataFixtures:
    """Fixtures for mock data and objects."""
    
    @staticmethod
    def create_mock_validation_results(success_count: int = 3, 
                                     failure_count: int = 2) -> List[ValidationResult]:
        """Create mock validation results."""
        results = []
        
        # Successful validations
        for i in range(success_count):
            results.append(ValidationResult(
                path=Path(f'/success/path/{i}'),
                is_valid=True,
                exists=True,
                is_writable=True,
                is_readable=True
            ))
        
        # Failed validations
        for i in range(failure_count):
            results.append(ValidationResult(
                path=Path(f'/failed/path/{i}'),
                is_valid=True,
                exists=False,
                is_writable=False,
                is_readable=False,
                error_message=f'Validation failed for path {i}'
            ))
        
        return results
    
    @staticmethod
    def create_mock_creation_results(created_count: int = 2, 
                                   existed_count: int = 2,
                                   failed_count: int = 1) -> List[CreationResult]:
        """Create mock creation results."""
        results = []
        
        # Successfully created
        for i in range(created_count):
            results.append(CreationResult(
                path=Path(f'/created/path/{i}'),
                created=True,
                already_existed=False
            ))
        
        # Already existed
        for i in range(existed_count):
            results.append(CreationResult(
                path=Path(f'/existed/path/{i}'),
                created=False,
                already_existed=True
            ))
        
        # Failed to create
        for i in range(failed_count):
            results.append(CreationResult(
                path=Path(f'/failed/path/{i}'),
                created=False,
                already_existed=False,
                error_message=f'Creation failed for path {i}'
            ))
        
        return results
    
    @staticmethod
    def create_mock_directory_config(base_path: Optional[Path] = None) -> DirectoryConfig:
        """Create mock DirectoryConfig for testing."""
        if base_path is None:
            base_path = Path('/mock/base')
        
        return DirectoryConfig(
            json_docs=base_path / 'mock_input',
            corrected=base_path / 'mock_output',
            audits=base_path / 'mock_audits',
            pdf_docs=base_path / 'mock_pdfs',
            locks=base_path / 'mock_locks'
        )


class TestFileFixtures:
    """Fixtures for creating test files and directories."""
    
    @staticmethod
    def create_config_file(config_data: Dict[str, Any], 
                          file_path: Path) -> Path:
        """Create a YAML config file with given data."""
        with open(file_path, 'w') as f:
            yaml.dump(config_data, f, default_flow_style=False, indent=2)
        return file_path
    
    @staticmethod
    def create_invalid_yaml_file(file_path: Path) -> Path:
        """Create an invalid YAML file for testing error handling."""
        with open(file_path, 'w') as f:
            f.write("invalid: yaml: content: [\n  - unclosed list")
        return file_path
    
    @staticmethod
    def create_empty_config_file(file_path: Path) -> Path:
        """Create an empty config file."""
        file_path.touch()
        return file_path
    
    @staticmethod
    def create_json_docs_files(directory: Path, count: int = 3) -> List[Path]:
        """Create sample JSON files for testing."""
        directory.mkdir(parents=True, exist_ok=True)
        files = []
        
        for i in range(count):
            file_path = directory / f'sample_{i}.json'
            sample_data = {
                'id': i,
                'name': f'Sample {i}',
                'data': {'value': i * 10, 'active': True}
            }
            
            with open(file_path, 'w') as f:
                json.dump(sample_data, f, indent=2)
            
            files.append(file_path)
        
        return files
    
    @staticmethod
    def create_directory_structure(base_path: Path, 
                                 structure: Dict[str, Any]) -> Dict[str, Path]:
        """Create a directory structure from a nested dictionary."""
        created_paths = {}
        
        def create_recursive(current_path: Path, current_structure: Dict[str, Any]):
            for name, content in current_structure.items():
                item_path = current_path / name
                
                if isinstance(content, dict):
                    # It's a directory
                    item_path.mkdir(parents=True, exist_ok=True)
                    created_paths[name] = item_path
                    create_recursive(item_path, content)
                else:
                    # It's a file
                    item_path.parent.mkdir(parents=True, exist_ok=True)
                    if isinstance(content, str):
                        item_path.write_text(content)
                    elif isinstance(content, dict):
                        with open(item_path, 'w') as f:
                            json.dump(content, f, indent=2)
                    created_paths[name] = item_path
        
        create_recursive(base_path, structure)
        return created_paths


@pytest.fixture
def temp_workspace():
    """Pytest fixture for temporary workspace."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield Path(temp_dir)


@pytest.fixture
def minimal_config():
    """Pytest fixture for minimal configuration."""
    return ConfigurationFixtures.get_minimal_config()


@pytest.fixture
def complete_config():
    """Pytest fixture for complete configuration."""
    return ConfigurationFixtures.get_complete_config()


@pytest.fixture
def partial_config():
    """Pytest fixture for partial configuration."""
    return ConfigurationFixtures.get_partial_config()


@pytest.fixture
def invalid_config():
    """Pytest fixture for invalid configuration."""
    return ConfigurationFixtures.get_invalid_config()


@pytest.fixture
def mock_validation_results():
    """Pytest fixture for mock validation results."""
    return MockDataFixtures.create_mock_validation_results()


@pytest.fixture
def mock_creation_results():
    """Pytest fixture for mock creation results."""
    return MockDataFixtures.create_mock_creation_results()


@pytest.fixture
def mock_directory_config(temp_workspace):
    """Pytest fixture for mock DirectoryConfig."""
    return MockDataFixtures.create_mock_directory_config(temp_workspace)


@pytest.fixture
def config_file_with_data(temp_workspace, complete_config):
    """Pytest fixture for config file with complete data."""
    config_file = temp_workspace / 'config.yaml'
    return TestFileFixtures.create_config_file(complete_config, config_file)


@pytest.fixture
def invalid_yaml_file(temp_workspace):
    """Pytest fixture for invalid YAML file."""
    config_file = temp_workspace / 'invalid.yaml'
    return TestFileFixtures.create_invalid_yaml_file(config_file)


@pytest.fixture
def json_docs_files(temp_workspace):
    """Pytest fixture for sample JSON files."""
    json_dir = temp_workspace / 'json_docs'
    return TestFileFixtures.create_json_docs_files(json_dir)


@pytest.fixture
def directory_structure(temp_workspace):
    """Pytest fixture for complex directory structure."""
    structure = {
        'input': {
            'json_files': {},
            'archives': {}
        },
        'output': {
            'processed': {},
            'failed': {}
        },
        'logs': {
            'audit.log': 'Sample audit log content',
            'error.log': 'Sample error log content'
        },
        'config': {
            'schemas': {
                'invoice.yaml': 'schema: invoice',
                'receipt.yaml': 'schema: receipt'
            }
        }
    }
    
    return TestFileFixtures.create_directory_structure(temp_workspace, structure)


class TestUtilities:
    """Utility functions for tests."""
    
    @staticmethod
    def assert_directory_exists_and_writable(path: Path):
        """Assert that directory exists and is writable."""
        assert path.exists(), f"Directory does not exist: {path}"
        assert path.is_dir(), f"Path is not a directory: {path}"
        
        # Test writability by creating a temporary file
        test_file = path / '.test_write'
        try:
            test_file.write_text('test')
            test_file.unlink()
        except Exception as e:
            pytest.fail(f"Directory is not writable: {path} - {e}")
    
    @staticmethod
    def assert_config_has_required_sections(config: Dict[str, Any]):
        """Assert that config has all required sections."""
        required_sections = ['app', 'directories']
        for section in required_sections:
            assert section in config, f"Missing required section: {section}"
        
        required_dirs = ['json_docs', 'corrected', 'audits', 'pdf_docs', 'locks']
        for dir_name in required_dirs:
            assert dir_name in config['directories'], f"Missing required directory: {dir_name}"
    
    @staticmethod
    def create_readonly_directory(path: Path):
        """Create a read-only directory for testing permission issues."""
        path.mkdir(parents=True, exist_ok=True)
        
        # Make directory read-only (Unix-like systems)
        import os
        import stat
        if os.name != 'nt':  # Not Windows
            path.chmod(stat.S_IRUSR | stat.S_IXUSR)  # Read and execute only
    
    @staticmethod
    def restore_directory_permissions(path: Path):
        """Restore normal permissions to a directory."""
        import os
        import stat
        if os.name != 'nt' and path.exists():  # Not Windows
            path.chmod(stat.S_IRWXU)  # Full permissions for owner


# Example usage and test data
SAMPLE_CONFIGURATIONS = {
    'production': {
        'app': {'name': 'Production QA', 'version': '1.0.0', 'debug': False},
        'directories': {
            'json_docs': '/app/data/input',
            'corrected': '/app/data/output',
            'audits': '/app/logs/audits',
            'pdf_docs': '/app/data/documents',
            'locks': '/tmp/qa_locks'
        },
        'processing': {'lock_timeout': 30, 'max_file_size': 50}
    },
    
    'development': {
        'app': {'name': 'Dev QA', 'version': '1.0.0-dev', 'debug': True},
        'directories': {
            'json_docs': './dev_input',
            'corrected': './dev_output',
            'audits': './dev_logs',
            'pdf_docs': './dev_docs',
            'locks': './dev_locks'
        },
        'processing': {'lock_timeout': 120, 'max_file_size': 10}
    },
    
    'testing': {
        'app': {'name': 'Test QA', 'version': '1.0.0-test', 'debug': True},
        'directories': {
            'json_docs': '/tmp/test_input',
            'corrected': '/tmp/test_output',
            'audits': '/tmp/test_audits',
            'pdf_docs': '/tmp/test_docs',
            'locks': '/tmp/test_locks'
        },
        'processing': {'lock_timeout': 60, 'max_file_size': 5}
    }
}


def get_sample_configuration(environment: str) -> Dict[str, Any]:
    """Get sample configuration for specific environment."""
    return SAMPLE_CONFIGURATIONS.get(environment, ConfigurationFixtures.get_minimal_config())


if __name__ == '__main__':
    # Example of using fixtures programmatically
    fixtures = ConfigurationFixtures()
    
    print("Minimal config:")
    print(yaml.dump(fixtures.get_minimal_config(), indent=2))
    
    print("\nComplete config:")
    print(yaml.dump(fixtures.get_complete_config(), indent=2))
    
    print("\nProduction config:")
    print(yaml.dump(get_sample_configuration('production'), indent=2))