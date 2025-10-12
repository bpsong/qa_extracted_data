"""
Unit tests for configuration loader module.
"""

import pytest
import tempfile
import yaml
from pathlib import Path
from unittest.mock import patch, mock_open

from utils.config_loader import (
    load_config, validate_config, get_directory_config, 
    get_default_config, deep_merge, save_config, get_config_summary
)
from utils.directory_config import DirectoryConfig


class TestDeepMerge:
    """Test cases for deep_merge function."""
    
    def test_deep_merge_simple_dicts(self):
        """Test deep merging of simple dictionaries."""
        base = {'a': 1, 'b': 2}
        update = {'b': 3, 'c': 4}
        
        result = deep_merge(base, update)
        
        assert result == {'a': 1, 'b': 3, 'c': 4}
        # Ensure original dicts are not modified
        assert base == {'a': 1, 'b': 2}
        assert update == {'b': 3, 'c': 4}
    
    def test_deep_merge_nested_dicts(self):
        """Test deep merging of nested dictionaries."""
        base = {
            'app': {'name': 'Base App', 'version': '1.0'},
            'directories': {'input': 'base_input', 'output': 'base_output'}
        }
        update = {
            'app': {'name': 'Updated App'},
            'directories': {'input': 'updated_input', 'logs': 'new_logs'}
        }
        
        result = deep_merge(base, update)
        
        expected = {
            'app': {'name': 'Updated App', 'version': '1.0'},
            'directories': {'input': 'updated_input', 'output': 'base_output', 'logs': 'new_logs'}
        }
        
        assert result == expected
    
    def test_deep_merge_empty_dicts(self):
        """Test deep merging with empty dictionaries."""
        base = {'a': 1, 'b': 2}
        empty = {}
        
        result1 = deep_merge(base, empty)
        result2 = deep_merge(empty, base)
        
        assert result1 == base
        assert result2 == base
    
    def test_deep_merge_non_dict_values(self):
        """Test deep merging when values are not dictionaries."""
        base = {'a': {'nested': 1}, 'b': [1, 2, 3]}
        update = {'a': {'nested': 2}, 'b': [4, 5, 6]}
        
        result = deep_merge(base, update)
        
        assert result == {'a': {'nested': 2}, 'b': [4, 5, 6]}


class TestGetDefaultConfig:
    """Test cases for get_default_config function."""
    
    def test_get_default_config_structure(self):
        """Test that default config has expected structure."""
        config = get_default_config()
        
        required_sections = ['app', 'schema', 'directories', 'ui', 'processing']
        for section in required_sections:
            assert section in config
        
        # Check directories section has all required directories
        required_dirs = ['json_docs', 'corrected', 'audits', 'pdf_docs', 'locks']
        for dir_name in required_dirs:
            assert dir_name in config['directories']
    
    def test_get_default_config_values(self):
        """Test that default config has expected values."""
        config = get_default_config()
        
        assert config['app']['name'] == 'JSON QA Webapp'
        assert config['app']['version'] == '1.0.0'
        assert config['directories']['json_docs'] == 'json_docs'
        assert config['directories']['corrected'] == 'corrected'
        assert config['processing']['lock_timeout'] == 60


class TestLoadConfig:
    """Test cases for load_config function."""
    
    def test_load_config_file_not_exists(self):
        """Test loading config when file doesn't exist."""
        with patch('pathlib.Path.exists', return_value=False):
            config = load_config(Path('nonexistent.yaml'))
            
            # Should return default config
            default_config = get_default_config()
            assert config == default_config
    
    def test_load_config_valid_file(self):
        """Test loading config from valid YAML file."""
        yaml_content = """
app:
  name: "Test App"
  version: "2.0.0"
directories:
  json_docs: "custom_input"
  corrected: "custom_output"
"""
        
        with patch('builtins.open', mock_open(read_data=yaml_content)):
            with patch('pathlib.Path.exists', return_value=True):
                config = load_config(Path('test.yaml'))
                
                assert config['app']['name'] == 'Test App'
                assert config['app']['version'] == '2.0.0'
                assert config['directories']['json_docs'] == 'custom_input'
                assert config['directories']['corrected'] == 'custom_output'
                # Should have defaults for missing values
                assert config['directories']['audits'] == 'audits'
    
    def test_load_config_invalid_yaml(self):
        """Test loading config with invalid YAML."""
        invalid_yaml = "invalid: yaml: content: ["
        
        with patch('builtins.open', mock_open(read_data=invalid_yaml)):
            with patch('pathlib.Path.exists', return_value=True):
                config = load_config(Path('invalid.yaml'))
                
                # Should return default config
                default_config = get_default_config()
                assert config == default_config
    
    def test_load_config_empty_file(self):
        """Test loading config from empty file."""
        with patch('builtins.open', mock_open(read_data="")):
            with patch('pathlib.Path.exists', return_value=True):
                config = load_config(Path('empty.yaml'))
                
                # Should return default config
                default_config = get_default_config()
                assert config == default_config
    
    def test_load_config_non_dict_content(self):
        """Test loading config with non-dictionary content."""
        yaml_content = "- item1\n- item2\n- item3"
        
        with patch('builtins.open', mock_open(read_data=yaml_content)):
            with patch('pathlib.Path.exists', return_value=True):
                config = load_config(Path('list.yaml'))
                
                # Should return default config
                default_config = get_default_config()
                assert config == default_config
    
    def test_load_config_io_error(self):
        """Test loading config when IO error occurs."""
        with patch('builtins.open', side_effect=IOError("Permission denied")):
            with patch('pathlib.Path.exists', return_value=True):
                config = load_config(Path('protected.yaml'))
                
                # Should return default config
                default_config = get_default_config()
                assert config == default_config


class TestValidateConfig:
    """Test cases for validate_config function."""
    
    def test_validate_config_valid_complete(self):
        """Test validating a complete, valid configuration."""
        config = get_default_config()
        
        result = validate_config(config)
        
        assert result is True
    
    def test_validate_config_missing_sections(self):
        """Test validating config with missing required sections."""
        config = {
            'app': {'name': 'Test', 'version': '1.0'},
            # Missing schema, directories, ui, processing
        }
        
        result = validate_config(config)
        
        assert result is False
    
    def test_validate_config_missing_directories(self):
        """Test validating config with missing directory entries."""
        config = get_default_config()
        del config['directories']['json_docs']  # Remove required directory
        
        result = validate_config(config)
        
        assert result is False
    
    def test_validate_config_invalid_directory_type(self):
        """Test validating config with non-string directory paths."""
        config = get_default_config()
        config['directories']['json_docs'] = 123  # Should be string
        
        result = validate_config(config)
        
        assert result is False
    
    def test_validate_config_invalid_lock_timeout(self):
        """Test validating config with invalid lock timeout."""
        config = get_default_config()
        config['processing']['lock_timeout'] = -5  # Should be positive
        
        result = validate_config(config)
        
        assert result is False
    
    def test_validate_config_invalid_max_file_size(self):
        """Test validating config with invalid max file size."""
        config = get_default_config()
        config['processing']['max_file_size'] = "invalid"  # Should be number
        
        result = validate_config(config)
        
        assert result is False
    
    def test_validate_config_missing_app_fields(self):
        """Test validating config with missing app fields."""
        config = get_default_config()
        del config['app']['name']  # Remove required field
        
        result = validate_config(config)
        
        assert result is False


class TestGetDirectoryConfig:
    """Test cases for get_directory_config function."""
    
    def test_get_directory_config_valid(self):
        """Test getting DirectoryConfig from valid config."""
        config = {
            'directories': {
                'json_docs': 'custom_input',
                'corrected': 'custom_output',
                'audits': 'custom_audits',
                'pdf_docs': 'custom_pdfs',
                'locks': 'custom_locks'
            }
        }
        
        dir_config = get_directory_config(config)
        
        assert isinstance(dir_config, DirectoryConfig)
        assert dir_config.json_docs == Path('custom_input')
        assert dir_config.corrected == Path('custom_output')
    
    def test_get_directory_config_invalid_falls_back(self):
        """Test getting DirectoryConfig when config is invalid."""
        invalid_config = {'invalid': 'config'}
        
        # Should not raise exception, should fall back to defaults
        dir_config = get_directory_config(invalid_config)
        
        assert isinstance(dir_config, DirectoryConfig)
        assert dir_config.json_docs == Path('json_docs')


class TestSaveConfig:
    """Test cases for save_config function."""
    
    def test_save_config_success(self):
        """Test saving config successfully."""
        config = get_default_config()
        
        with patch('builtins.open', mock_open()) as mock_file:
            with patch('yaml.dump') as mock_dump:
                result = save_config(config)
                
                assert result is True
                mock_file.assert_called_once()
                mock_dump.assert_called_once()
    
    def test_save_config_io_error(self):
        """Test saving config when IO error occurs."""
        config = get_default_config()
        
        with patch('builtins.open', side_effect=IOError("Permission denied")):
            result = save_config(config)
            
            assert result is False
    
    def test_save_config_custom_path(self):
        """Test saving config to custom path."""
        config = get_default_config()
        custom_path = Path('custom_config.yaml')
        
        with patch('builtins.open', mock_open()) as mock_file:
            with patch('yaml.dump'):
                save_config(config, custom_path)
                
                # Check that custom path was used
                mock_file.assert_called_with(custom_path, 'w', encoding='utf-8')


class TestGetConfigSummary:
    """Test cases for get_config_summary function."""
    
    def test_get_config_summary_complete(self):
        """Test getting summary from complete config."""
        config = {
            'app': {'name': 'Test App', 'version': '2.0.0', 'debug': True},
            'schema': {'primary_schema': 'test_schema.yaml'},
            'directories': {
                'json_docs': 'input',
                'corrected': 'output',
                'audits': 'logs'
            },
            'processing': {'lock_timeout': 120, 'max_file_size': 20}
        }
        
        summary = get_config_summary(config)
        
        assert summary['app_name'] == 'Test App'
        assert summary['app_version'] == '2.0.0'
        assert summary['debug_mode'] is True
        assert summary['primary_schema'] == 'test_schema.yaml'
        assert summary['lock_timeout'] == 120
        assert summary['max_file_size'] == 20
        assert 'input' in summary['directories']['json_docs']
    
    def test_get_config_summary_missing_fields(self):
        """Test getting summary from config with missing fields."""
        config = {}  # Empty config
        
        summary = get_config_summary(config)
        
        assert summary['app_name'] == 'Unknown'
        assert summary['app_version'] == 'Unknown'
        assert summary['debug_mode'] is False
        assert summary['primary_schema'] == 'Unknown'
        assert summary['lock_timeout'] == 60  # Default
        assert summary['max_file_size'] == 10  # Default


if __name__ == '__main__':
    pytest.main([__file__])