"""
Unit tests for array synchronization functionality in FormGenerator.

Tests the _sync_array_to_session method and its integration with scalar and object
array editors to ensure proper session state and SessionManager synchronization.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import streamlit as st
from typing import Dict, Any, List

# Import the modules to test
from utils.form_generator import FormGenerator
from utils.session_manager import SessionManager


class TestArraySynchronization:
    """Test class for array synchronization functionality."""
    
    def setup_method(self):
        """Set up test fixtures before each test method."""
        # Mock streamlit session state - create fresh dict for each test
        self.mock_session_state = {}
        
        # Mock SessionManager methods - create fresh dict for each test
        self.mock_form_data = {}
        
        # Patch streamlit session state
        self.session_state_patcher = patch('streamlit.session_state', self.mock_session_state)
        self.session_state_patcher.start()
        
        # Patch SessionManager methods with fresh mocks for each test
        self.get_form_data_patcher = patch.object(
            SessionManager, 'get_form_data', 
            return_value=self.mock_form_data
        )
        self.set_form_data_patcher = patch.object(
            SessionManager, 'set_form_data',
            side_effect=self._mock_set_form_data
        )
        
        self.get_form_data_mock = self.get_form_data_patcher.start()
        self.set_form_data_mock = self.set_form_data_patcher.start()
    
    def teardown_method(self):
        """Clean up after each test method."""
        self.session_state_patcher.stop()
        self.get_form_data_patcher.stop()
        self.set_form_data_patcher.stop()
    
    def _mock_set_form_data(self, data: Dict[str, Any]):
        """Mock implementation of SessionManager.set_form_data."""
        # Update the mock form data with the new data
        self.mock_form_data.update(data)
    
    def test_sync_array_to_session_updates_session_state(self):
        """Test that _sync_array_to_session updates session state correctly."""
        # Arrange
        field_name = "test_array"
        array_value = ["item1", "item2", "item3"]
        expected_field_key = f"field_{field_name}"
        
        # Act
        FormGenerator._sync_array_to_session(field_name, array_value)
        
        # Assert
        assert expected_field_key in self.mock_session_state
        assert self.mock_session_state[expected_field_key] == array_value
    
    def test_sync_array_to_session_updates_session_manager(self):
        """Test that _sync_array_to_session updates SessionManager form data correctly."""
        # Arrange
        field_name = "test_array"
        array_value = ["item1", "item2", "item3"]
        initial_form_data = {"other_field": "value"}
        self.mock_form_data.update(initial_form_data)
        
        # Act
        FormGenerator._sync_array_to_session(field_name, array_value)
        
        # Assert
        self.get_form_data_mock.assert_called_once()
        self.set_form_data_mock.assert_called_once()
        
        # Check that the form data was updated with the array
        expected_form_data = initial_form_data.copy()
        expected_form_data[field_name] = array_value
        assert self.mock_form_data == expected_form_data
    
    def test_sync_array_to_session_with_empty_array(self):
        """Test synchronization with empty arrays."""
        # Arrange
        field_name = "empty_array"
        array_value = []
        
        # Act
        FormGenerator._sync_array_to_session(field_name, array_value)
        
        # Assert
        assert self.mock_session_state[f"field_{field_name}"] == []
        assert self.mock_form_data[field_name] == []
    
    def test_sync_array_to_session_with_mixed_types(self):
        """Test synchronization with arrays containing mixed data types."""
        # Arrange
        field_name = "mixed_array"
        array_value = ["string", 42, True, None]
        
        # Act
        FormGenerator._sync_array_to_session(field_name, array_value)
        
        # Assert
        assert self.mock_session_state[f"field_{field_name}"] == array_value
        assert self.mock_form_data[field_name] == array_value
    
    def test_sync_array_to_session_overwrites_existing_data(self):
        """Test that synchronization overwrites existing array data."""
        # Arrange
        field_name = "test_array"
        old_array = ["old1", "old2"]
        new_array = ["new1", "new2", "new3"]
        
        # Set up initial state
        self.mock_session_state[f"field_{field_name}"] = old_array
        self.mock_form_data[field_name] = old_array
        
        # Act
        FormGenerator._sync_array_to_session(field_name, new_array)
        
        # Assert
        assert self.mock_session_state[f"field_{field_name}"] == new_array
        assert self.mock_form_data[field_name] == new_array
    
    def test_sync_array_preserves_other_form_data(self):
        """Test that synchronization preserves other form data fields."""
        # Arrange
        field_name = "test_array"
        array_value = ["item1", "item2"]
        existing_data = {
            "other_field": "value",
            "another_field": 42,
            "nested_field": {"key": "value"}
        }
        self.mock_form_data.update(existing_data)
        
        # Act
        FormGenerator._sync_array_to_session(field_name, array_value)
        
        # Assert
        # Check that existing data is preserved
        for key, value in existing_data.items():
            assert self.mock_form_data[key] == value
        
        # Check that new array data is added
        assert self.mock_form_data[field_name] == array_value
    
    @patch('utils.form_generator.logger')
    def test_sync_array_logs_debug_message(self, mock_logger):
        """Test that synchronization logs appropriate debug messages."""
        # Arrange
        field_name = "test_array"
        array_value = ["item1", "item2", "item3"]
        
        # Act
        FormGenerator._sync_array_to_session(field_name, array_value)
        
        # Assert
        mock_logger.debug.assert_called_once()
        log_message = mock_logger.debug.call_args[0][0]
        assert field_name in log_message
        assert "3 items" in log_message


if __name__ == "__main__":
    pytest.main([__file__])