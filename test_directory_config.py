"""
Unit tests for directory configuration module.
"""

import pytest
from pathlib import Path
from utils.directory_config import DirectoryConfig


class TestDirectoryConfig:
    """Test cases for DirectoryConfig class."""
    
    def test_from_config_with_complete_config(self):
        """Test loading DirectoryConfig from complete configuration."""
        config = {
            'directories': {
                'json_docs': 'custom_input',
                'corrected': 'custom_output',
                'audits': 'custom_audits',
                'pdf_docs': 'custom_pdfs',
                'locks': 'custom_locks'
            }
        }
        
        dir_config = DirectoryConfig.from_config(config)
        
        assert dir_config.json_docs == Path('custom_input')
        assert dir_config.corrected == Path('custom_output')
        assert dir_config.audits == Path('custom_audits')
        assert dir_config.pdf_docs == Path('custom_pdfs')
        assert dir_config.locks == Path('custom_locks')
    
    def test_from_config_with_partial_config(self):
        """Test loading DirectoryConfig with partial configuration uses defaults."""
        config = {
            'directories': {
                'json_docs': 'custom_input',
                'corrected': 'custom_output'
                # Missing audits, pdf_docs, locks
            }
        }
        
        dir_config = DirectoryConfig.from_config(config)
        
        assert dir_config.json_docs == Path('custom_input')
        assert dir_config.corrected == Path('custom_output')
        assert dir_config.audits == Path('audits')  # Default
        assert dir_config.pdf_docs == Path('pdf_docs')  # Default
        assert dir_config.locks == Path('locks')  # Default
    
    def test_from_config_with_empty_config(self):
        """Test loading DirectoryConfig with empty config uses all defaults."""
        config = {}
        
        dir_config = DirectoryConfig.from_config(config)
        
        assert dir_config.json_docs == Path('json_docs')
        assert dir_config.corrected == Path('corrected')
        assert dir_config.audits == Path('audits')
        assert dir_config.pdf_docs == Path('pdf_docs')
        assert dir_config.locks == Path('locks')
    
    def test_from_config_with_missing_directories_section(self):
        """Test loading DirectoryConfig when directories section is missing."""
        config = {
            'app': {'name': 'Test App'},
            'schema': {'primary_schema': 'test.yaml'}
        }
        
        dir_config = DirectoryConfig.from_config(config)
        
        assert dir_config.json_docs == Path('json_docs')
        assert dir_config.corrected == Path('corrected')
        assert dir_config.audits == Path('audits')
        assert dir_config.pdf_docs == Path('pdf_docs')
        assert dir_config.locks == Path('locks')
    
    def test_to_dict(self):
        """Test converting DirectoryConfig to dictionary."""
        dir_config = DirectoryConfig(
            json_docs=Path('test_input'),
            corrected=Path('test_output'),
            audits=Path('test_audits'),
            pdf_docs=Path('test_pdfs'),
            locks=Path('test_locks')
        )
        
        result = dir_config.to_dict()
        
        expected = {
            'json_docs': Path('test_input'),
            'corrected': Path('test_output'),
            'audits': Path('test_audits'),
            'pdf_docs': Path('test_pdfs'),
            'locks': Path('test_locks')
        }
        
        assert result == expected
    
    def test_validate_paths_with_valid_paths(self):
        """Test path validation with valid paths."""
        dir_config = DirectoryConfig(
            json_docs=Path('.'),  # Current directory should be valid
            corrected=Path('.'),
            audits=Path('.'),
            pdf_docs=Path('.'),
            locks=Path('.')
        )
        
        validation_results = dir_config.validate_paths()
        
        assert all(validation_results.values())
        assert len(validation_results) == 5
    
    def test_validate_paths_with_invalid_paths(self):
        """Test path validation behavior."""
        # Note: validate_paths() only checks if Path.resolve() succeeds
        # On most systems, even non-existent paths resolve successfully
        # This test verifies the method works as designed
        
        dir_config = DirectoryConfig(
            json_docs=Path('/nonexistent/path'),  # Valid format, doesn't exist
            corrected=Path('.'),  # Valid and exists
            audits=Path('relative/path'),  # Valid format
            pdf_docs=Path('.'),  # Valid and exists
            locks=Path('/another/nonexistent/path')  # Valid format
        )
        
        validation_results = dir_config.validate_paths()
        
        # All paths should be valid since they have valid formats
        # (validate_paths only checks format, not existence)
        assert validation_results['corrected'] is True
        assert validation_results['pdf_docs'] is True
        assert validation_results['json_docs'] is True  # Valid format
        assert validation_results['audits'] is True  # Valid format
        assert validation_results['locks'] is True  # Valid format
        
        # Test that the method returns results for all directories
        assert len(validation_results) == 5
        assert set(validation_results.keys()) == {'json_docs', 'corrected', 'audits', 'pdf_docs', 'locks'}
    
    def test_get_path_existing_directory(self):
        """Test getting path for existing directory type."""
        dir_config = DirectoryConfig(
            json_docs=Path('test_input'),
            corrected=Path('test_output'),
            audits=Path('test_audits'),
            pdf_docs=Path('test_pdfs'),
            locks=Path('test_locks')
        )
        
        assert dir_config.get_path('json_docs') == Path('test_input')
        assert dir_config.get_path('corrected') == Path('test_output')
        assert dir_config.get_path('audits') == Path('test_audits')
    
    def test_get_path_nonexistent_directory(self):
        """Test getting path for non-existent directory type."""
        dir_config = DirectoryConfig(
            json_docs=Path('test_input'),
            corrected=Path('test_output'),
            audits=Path('test_audits'),
            pdf_docs=Path('test_pdfs'),
            locks=Path('test_locks')
        )
        
        assert dir_config.get_path('nonexistent') is None
    
    def test_str_representation(self):
        """Test string representation of DirectoryConfig."""
        dir_config = DirectoryConfig(
            json_docs=Path('input'),
            corrected=Path('output'),
            audits=Path('audits'),
            pdf_docs=Path('pdfs'),
            locks=Path('locks')
        )
        
        str_repr = str(dir_config)
        
        assert 'DirectoryConfig(' in str_repr
        assert 'json_docs: input' in str_repr
        assert 'corrected: output' in str_repr
        assert 'audits: audits' in str_repr
        assert 'pdf_docs: pdfs' in str_repr
        assert 'locks: locks' in str_repr
    
    def test_from_config_with_absolute_paths(self):
        """Test loading DirectoryConfig with absolute paths."""
        config = {
            'directories': {
                'json_docs': '/absolute/path/input',
                'corrected': '/absolute/path/output',
                'audits': '/absolute/path/audits',
                'pdf_docs': '/absolute/path/pdfs',
                'locks': '/absolute/path/locks'
            }
        }
        
        dir_config = DirectoryConfig.from_config(config)
        
        assert dir_config.json_docs == Path('/absolute/path/input')
        assert dir_config.corrected == Path('/absolute/path/output')
        assert dir_config.audits == Path('/absolute/path/audits')
        assert dir_config.pdf_docs == Path('/absolute/path/pdfs')
        assert dir_config.locks == Path('/absolute/path/locks')
    
    def test_from_config_with_relative_paths(self):
        """Test loading DirectoryConfig with relative paths."""
        config = {
            'directories': {
                'json_docs': './relative/input',
                'corrected': '../relative/output',
                'audits': 'simple_relative',
                'pdf_docs': './pdfs',
                'locks': '../locks'
            }
        }
        
        dir_config = DirectoryConfig.from_config(config)
        
        assert dir_config.json_docs == Path('./relative/input')
        assert dir_config.corrected == Path('../relative/output')
        assert dir_config.audits == Path('simple_relative')
        assert dir_config.pdf_docs == Path('./pdfs')
        assert dir_config.locks == Path('../locks')


if __name__ == '__main__':
    pytest.main([__file__])