"""
Unit tests for array reset functionality in EditView.

Tests the _handle_reset() method to ensure it properly:
- Clears all scalar array editor state
- Clears all object array editor state  
- Restores original array values
- Restores original array sizes
- Shows no changes in diff after reset

Requirements: 2.1, 2.2, 2.3, 2.4, 2.5
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import streamlit as st
from typing import Dict, Any, List

# Import the modules to test
from utils.edit_view import EditView
from utils.session_manager import SessionManager
from utils.file_utils import load_json_file


class TestArrayResetFunctionality:
    """Test array reset functionality in EditView."""
    
    def setup_method(self):
        """Set up test fixtures before each test."""
        # Mock streamlit session state
        self.mock_session_state = {}
        
        # Mock SessionManager methods
        self.mock_form_data = {}
        self.mock_original_data = {}
        self.mock_schema = {}
        
        # Patch streamlit session state
        self.session_state_patcher = patch('streamlit.session_state', self.mock_session_state)
        self.session_state_patcher.start()
        
        # Patch SessionManager methods using the module path
        self.get_schema_patcher = patch('utils.edit_view.SessionManager.get_schema')
        self.get_current_file_patcher = patch('utils.edit_view.SessionManager.get_current_file')
        self.set_original_data_patcher = patch('utils.edit_view.SessionManager.set_original_data')
        self.set_form_data_patcher = patch('utils.edit_view.SessionManager.set_form_data')
        self.clear_validation_errors_patcher = patch('utils.edit_view.SessionManager.clear_validation_errors')
        
        # Start all SessionManager patches
        self.get_schema_mock = self.get_schema_patcher.start()
        self.get_current_file_mock = self.get_current_file_patcher.start()
        self.set_original_data_mock = self.set_original_data_patcher.start()
        self.set_form_data_mock = self.set_form_data_patcher.start()
        self.clear_validation_errors_mock = self.clear_validation_errors_patcher.start()
        
        # Configure the mocks to return appropriate values
        self.get_schema_mock.return_value = self.mock_schema
        self.get_current_file_mock.return_value = 'test_file.json'
        
        # Patch file loading
        self.load_json_file_patcher = patch('utils.edit_view.load_json_file')
        self.load_json_file_mock = self.load_json_file_patcher.start()
        
        # Patch Streamlit UI components
        self.st_rerun_patcher = patch('streamlit.rerun')
        self.st_rerun_mock = self.st_rerun_patcher.start()
        
        # Patch Notify
        self.notify_success_patcher = patch('utils.edit_view.Notify.success')
        self.notify_warn_patcher = patch('utils.edit_view.Notify.warn')
        self.notify_error_patcher = patch('utils.edit_view.Notify.error')
        
        self.notify_success_mock = self.notify_success_patcher.start()
        self.notify_warn_mock = self.notify_warn_patcher.start()
        self.notify_error_mock = self.notify_error_patcher.start()
    
    def teardown_method(self):
        """Clean up after each test."""
        # Stop all patches
        self.session_state_patcher.stop()
        self.get_schema_patcher.stop()
        self.get_current_file_patcher.stop()
        self.set_original_data_patcher.stop()
        self.set_form_data_patcher.stop()
        self.clear_validation_errors_patcher.stop()
        self.load_json_file_patcher.stop()
        self.st_rerun_patcher.stop()
        self.notify_success_patcher.stop()
        self.notify_warn_patcher.stop()
        self.notify_error_patcher.stop()
    
    def test_reset_clears_scalar_array_editor_state(self):
        """Test reset clears all scalar array editor state."""
        # Arrange
        schema = {
            'fields': {
                'test_array': {
                    'type': 'array',
                    'items': {'type': 'string'}
                }
            }
        }
        original_data = {
            'test_array': ['item1', 'item2']
        }
        
        # Set up session state with scalar array editor keys
        self.mock_session_state.update({
            'field_test_array': ['modified1', 'modified2', 'modified3'],
            'scalar_array_test_array_size': 3,
            'scalar_array_test_array_item_0': 'modified1',
            'scalar_array_test_array_item_1': 'modified2',
            'scalar_array_test_array_item_2': 'modified3',
            'other_field': 'should_remain'
        })
        
        self.get_schema_mock.return_value = schema
        self.load_json_file_mock.return_value = original_data
        
        # Act
        EditView._handle_reset()
        
        # Assert - scalar array editor keys should be cleared and reset
        assert self.mock_session_state['field_test_array'] == ['item1', 'item2']
        assert self.mock_session_state['scalar_array_test_array_size'] == 2
        
        # Individual item keys should be cleared (not present)
        assert 'scalar_array_test_array_item_0' not in self.mock_session_state
        assert 'scalar_array_test_array_item_1' not in self.mock_session_state
        assert 'scalar_array_test_array_item_2' not in self.mock_session_state
        
        # Non-array fields should remain
        assert self.mock_session_state['other_field'] == 'should_remain'
    
    def test_reset_clears_object_array_editor_state(self):
        """Test reset clears all object array editor state."""
        # Arrange
        schema = {
            'fields': {
                'object_array': {
                    'type': 'array',
                    'items': {
                        'type': 'object',
                        'properties': {
                            'name': {'type': 'string'},
                            'age': {'type': 'number'}
                        }
                    }
                }
            }
        }
        original_data = {
            'object_array': [
                {'name': 'John', 'age': 30},
                {'name': 'Jane', 'age': 25}
            ]
        }
        
        # Set up session state with object array editor keys
        self.mock_session_state.update({
            'field_object_array': [
                {'name': 'Modified John', 'age': 35},
                {'name': 'Modified Jane', 'age': 28},
                {'name': 'New Person', 'age': 40}
            ],
            'data_editor_object_array': [
                {'name': 'Modified John', 'age': 35},
                {'name': 'Modified Jane', 'age': 28},
                {'name': 'New Person', 'age': 40}
            ],
            'add_row_object_array': True,
            'delete_row_object_array': True,
            'delete_row_select_object_array': [2],
            'other_field': 'should_remain'
        })
        
        self.get_schema_mock.return_value = schema
        self.load_json_file_mock.return_value = original_data
        
        # Act
        EditView._handle_reset()
        
        # Assert - object array editor keys should be cleared and reset
        assert self.mock_session_state['field_object_array'] == original_data['object_array']
        assert self.mock_session_state['data_editor_object_array'] == original_data['object_array']
        
        # Control keys should be cleared (not present)
        assert 'add_row_object_array' not in self.mock_session_state
        assert 'delete_row_object_array' not in self.mock_session_state
        assert 'delete_row_select_object_array' not in self.mock_session_state
        
        # Non-array fields should remain
        assert self.mock_session_state['other_field'] == 'should_remain'
    
    def test_reset_restores_original_array_values(self):
        """Test reset restores original array values."""
        # Arrange
        schema = {
            'fields': {
                'scalar_array': {
                    'type': 'array',
                    'items': {'type': 'string'}
                },
                'object_array': {
                    'type': 'array',
                    'items': {
                        'type': 'object',
                        'properties': {
                            'id': {'type': 'number'},
                            'value': {'type': 'string'}
                        }
                    }
                }
            }
        }
        original_data = {
            'scalar_array': ['original1', 'original2'],
            'object_array': [
                {'id': 1, 'value': 'original_value1'},
                {'id': 2, 'value': 'original_value2'}
            ]
        }
        
        # Set up session state with modified values
        self.mock_session_state.update({
            'field_scalar_array': ['modified1', 'modified2', 'modified3'],
            'field_object_array': [
                {'id': 1, 'value': 'modified_value1'},
                {'id': 3, 'value': 'new_value'}
            ]
        })
        
        self.get_schema_mock.return_value = schema
        self.load_json_file_mock.return_value = original_data
        
        # Act
        EditView._handle_reset()
        
        # Assert - arrays should be restored to original values
        assert self.mock_session_state['field_scalar_array'] == original_data['scalar_array']
        assert self.mock_session_state['field_object_array'] == original_data['object_array']
        
        # SessionManager should be updated with original data
        self.set_original_data_mock.assert_called_once_with(original_data)
        self.set_form_data_mock.assert_called_with(original_data.copy())
    
    def test_reset_restores_original_array_sizes(self):
        """Test reset restores original array sizes."""
        # Arrange
        schema = {
            'fields': {
                'small_array': {
                    'type': 'array',
                    'items': {'type': 'string'}
                },
                'large_array': {
                    'type': 'array',
                    'items': {'type': 'number'}
                }
            }
        }
        original_data = {
            'small_array': ['a', 'b'],  # Size 2
            'large_array': [1, 2, 3, 4, 5]  # Size 5
        }
        
        # Set up session state with different sizes
        self.mock_session_state.update({
            'scalar_array_small_array_size': 5,  # Modified to larger size
            'scalar_array_large_array_size': 2,  # Modified to smaller size
            'field_small_array': ['a', 'b', 'c', 'd', 'e'],
            'field_large_array': [1, 2]
        })
        
        self.get_schema_mock.return_value = schema
        self.load_json_file_mock.return_value = original_data
        
        # Act
        EditView._handle_reset()
        
        # Assert - array size widgets should be restored to original sizes
        assert self.mock_session_state['scalar_array_small_array_size'] == 2
        assert self.mock_session_state['scalar_array_large_array_size'] == 5
        
        # Array values should also be restored
        assert self.mock_session_state['field_small_array'] == original_data['small_array']
        assert self.mock_session_state['field_large_array'] == original_data['large_array']
    
    def test_reset_with_empty_arrays(self):
        """Test reset works correctly with empty arrays."""
        # Arrange
        schema = {
            'fields': {
                'empty_array': {
                    'type': 'array',
                    'items': {'type': 'string'}
                }
            }
        }
        original_data = {
            'empty_array': []
        }
        
        # Set up session state with non-empty array
        self.mock_session_state.update({
            'field_empty_array': ['added_item1', 'added_item2'],
            'scalar_array_empty_array_size': 2
        })
        
        self.get_schema_mock.return_value = schema
        self.load_json_file_mock.return_value = original_data
        
        # Act
        EditView._handle_reset()
        
        # Assert - empty array should be restored
        assert self.mock_session_state['field_empty_array'] == []
        assert self.mock_session_state['scalar_array_empty_array_size'] == 0
    
    def test_reset_with_mixed_field_types(self):
        """Test reset works with mixed field types including arrays."""
        # Arrange
        schema = {
            'fields': {
                'string_field': {'type': 'string'},
                'number_field': {'type': 'number'},
                'array_field': {
                    'type': 'array',
                    'items': {'type': 'string'}
                },
                'date_field': {'type': 'date'}
            }
        }
        original_data = {
            'string_field': 'original_string',
            'number_field': 42,
            'array_field': ['original_item'],
            'date_field': '2023/01/01'
        }
        
        # Set up session state with modified values
        self.mock_session_state.update({
            'field_string_field': 'modified_string',
            'field_number_field': 99,
            'field_array_field': ['modified_item1', 'modified_item2'],
            'scalar_array_array_field_size': 2,
            'field_date_field': '2023/12/31'
        })
        
        self.get_schema_mock.return_value = schema
        self.load_json_file_mock.return_value = original_data
        
        # Act
        EditView._handle_reset()
        
        # Assert - all fields should be restored
        assert self.mock_session_state['field_string_field'] == 'original_string'
        assert self.mock_session_state['field_number_field'] == 42
        assert self.mock_session_state['field_array_field'] == ['original_item']
        assert self.mock_session_state['scalar_array_array_field_size'] == 1
        assert self.mock_session_state['field_date_field'] == '2023/01/01'
    
    def test_reset_calls_session_manager_methods(self):
        """Test reset calls appropriate SessionManager methods."""
        # Arrange
        schema = {
            'fields': {
                'test_array': {
                    'type': 'array',
                    'items': {'type': 'string'}
                }
            }
        }
        original_data = {
            'test_array': ['item1', 'item2']
        }
        
        self.get_schema_mock.return_value = schema
        self.load_json_file_mock.return_value = original_data
        
        # Act
        EditView._handle_reset()
        
        # Assert - SessionManager methods should be called
        self.set_original_data_mock.assert_called_once_with(original_data)
        self.set_form_data_mock.assert_called_with(original_data.copy())
        self.clear_validation_errors_mock.assert_called_once()
        
        # UI should be updated
        self.st_rerun_mock.assert_called_once()
        self.notify_success_mock.assert_called_once_with("🔄 Form reset to original data")
    
    def test_reset_handles_missing_schema(self):
        """Test reset handles missing schema gracefully."""
        # Arrange
        self.get_schema_mock.return_value = None
        
        # Act
        EditView._handle_reset()
        
        # Assert - should warn about missing schema
        self.notify_warn_mock.assert_called_once_with("Schema required to reset form")
        
        # Should not proceed with reset operations
        self.load_json_file_mock.assert_not_called()
        self.set_original_data_mock.assert_not_called()
        self.st_rerun_mock.assert_not_called()
    
    def test_reset_handles_missing_original_data(self):
        """Test reset handles missing original data gracefully."""
        # Arrange
        schema = {
            'fields': {
                'test_field': {'type': 'string'}
            }
        }
        self.get_schema_mock.return_value = schema
        self.load_json_file_mock.return_value = None
        
        # Act
        EditView._handle_reset()
        
        # Assert - should error about missing data
        self.notify_error_mock.assert_called_once_with("No original data available")
        
        # Should not proceed with session state updates
        self.set_original_data_mock.assert_not_called()
        self.st_rerun_mock.assert_not_called()
    
    def test_reset_handles_file_loading_error(self):
        """Test reset handles file loading errors gracefully."""
        # Arrange
        schema = {
            'fields': {
                'test_field': {'type': 'string'}
            }
        }
        self.get_schema_mock.return_value = schema
        self.load_json_file_mock.side_effect = Exception("File not found")
        
        # Act
        EditView._handle_reset()
        
        # Assert - should handle error gracefully
        self.notify_error_mock.assert_called_once_with("Operation failed")
        
        # Should not proceed with session state updates
        self.set_original_data_mock.assert_not_called()
        self.st_rerun_mock.assert_not_called()
    
    def test_reset_clears_comprehensive_array_keys(self):
        """Test reset clears all possible array-related session state keys."""
        # Arrange
        schema = {
            'fields': {
                'test_array': {
                    'type': 'array',
                    'items': {'type': 'string'}
                }
            }
        }
        original_data = {
            'test_array': ['item1'],
            'other': 'should_remain'  # Add this field to original data so it gets restored
        }
        
        # Set up session state with comprehensive array keys
        self.mock_session_state.update({
            # Field keys
            'field_test_array': ['modified'],
            'array_test_array': ['old_style'],
            'json_array_test_array': ['json_style'],
            
            # Scalar array editor keys
            'scalar_array_test_array_size': 3,
            'scalar_array_test_array_item_0': 'item0',
            'scalar_array_test_array_item_1': 'item1',
            'scalar_array_test_array_item_2': 'item2',
            
            # Object array editor keys
            'data_editor_test_array': [{'data': 'editor'}],
            'add_row_test_array': True,
            'delete_row_test_array': True,
            'delete_row_select_test_array': [0],
            
            # Non-array keys (should remain)
            'other_key': 'should_remain',
            'field_other': 'should_remain'
        })
        
        self.get_schema_mock.return_value = schema
        self.load_json_file_mock.return_value = original_data
        
        # Act
        EditView._handle_reset()
        
        # Assert - all array-related keys should be cleared or reset
        # Field keys should be reset to original values
        assert self.mock_session_state['field_test_array'] == ['item1']
        
        # Old-style array keys should be cleared
        assert 'array_test_array' not in self.mock_session_state
        assert 'json_array_test_array' not in self.mock_session_state
        
        # Scalar array editor keys should be cleared/reset
        assert self.mock_session_state['scalar_array_test_array_size'] == 1
        assert 'scalar_array_test_array_item_0' not in self.mock_session_state
        assert 'scalar_array_test_array_item_1' not in self.mock_session_state
        assert 'scalar_array_test_array_item_2' not in self.mock_session_state
        
        # Object array editor keys should be cleared
        assert 'data_editor_test_array' not in self.mock_session_state
        assert 'add_row_test_array' not in self.mock_session_state
        assert 'delete_row_test_array' not in self.mock_session_state
        assert 'delete_row_select_test_array' not in self.mock_session_state
        
        # Non-array keys should remain
        assert self.mock_session_state['other_key'] == 'should_remain'
        assert self.mock_session_state['field_other'] == 'should_remain'


if __name__ == "__main__":
    pytest.main([__file__])