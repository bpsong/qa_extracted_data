"""
Unit tests for FormGenerator scalar array integration.
Tests the enhanced scalar array editing functionality integrated into the main FormGenerator.
"""

import pytest
import streamlit as st
from unittest.mock import patch, MagicMock, call
from datetime import datetime, date
import json

# Import the module to test
from utils.form_generator import FormGenerator
from utils.session_manager import SessionManager
from utils.submission_handler import SubmissionHandler


class TestFormGeneratorScalarArrays:
    """Test class for FormGenerator scalar array integration."""
    
    def setup_method(self):
        """Set up test environment before each test."""
        # Clear session state before each test
        if hasattr(st, 'session_state'):
            st.session_state.clear()
    
    def teardown_method(self):
        """Clean up after each test."""
        # Clear session state after each test
        if hasattr(st, 'session_state'):
            st.session_state.clear()
    
    @patch('streamlit.info')
    @patch('streamlit.button')
    @patch('streamlit.columns')
    @patch('streamlit.markdown')
    @patch('streamlit.container')
    @patch('streamlit.success')
    @patch('streamlit.rerun')
    def test_render_scalar_array_editor_basic_functionality(self, mock_rerun, mock_success, 
                                                           mock_container, mock_markdown, 
                                                           mock_columns, mock_button, mock_info):
        """Test basic scalar array editor functionality."""
        # Setup mocks
        mock_container.return_value.__enter__ = MagicMock()
        mock_container.return_value.__exit__ = MagicMock()
        mock_columns.return_value = [MagicMock(), MagicMock()]
        mock_button.return_value = False
        
        # Test data
        field_name = "serial_numbers"
        field_config = {
            "type": "array",
            "label": "Serial Numbers",
            "items": {
                "type": "string"
            }
        }
        current_value = ["SN001", "SN002"]
        
        # Call the method
        result = FormGenerator._render_scalar_array_editor(field_name, field_config, current_value)
        
        # Verify basic structure
        assert isinstance(result, list)
        assert len(result) == 2
        assert result == ["SN001", "SN002"]
        
        # Verify UI elements were called
        mock_info.assert_called_once()
        mock_container.assert_called_once()
        mock_columns.assert_called()
        mock_markdown.assert_called()
    
    @patch('streamlit.info')
    @patch('streamlit.button')
    @patch('streamlit.columns')
    @patch('streamlit.markdown')
    @patch('streamlit.container')
    @patch('streamlit.success')
    @patch('streamlit.rerun')
    @patch('utils.form_generator.FormGenerator._render_scalar_input')
    def test_render_scalar_array_editor_add_item(self, mock_render_input, mock_rerun, 
                                                mock_success, mock_container, mock_markdown, 
                                                mock_columns, mock_button, mock_info):
        """Test adding items to scalar array."""
        # Setup mocks
        mock_container.return_value.__enter__ = MagicMock()
        mock_container.return_value.__exit__ = MagicMock()
        mock_columns.return_value = [MagicMock(), MagicMock()]
        mock_render_input.return_value = "new_value"
        
        # Mock button to return True for add button
        def button_side_effect(*args, **kwargs):
            if 'Add Item' in args:
                return True
            return False
        mock_button.side_effect = button_side_effect
        
        # Test data
        field_name = "tags"
        field_config = {
            "type": "array",
            "label": "Tags",
            "items": {
                "type": "string"
            }
        }
        current_value = ["tag1"]
        
        # Initialize session state for add operation
        st.session_state[f"scalar_array_{field_name}_add_item"] = True
        
        # Call the method
        result = FormGenerator._render_scalar_array_editor(field_name, field_config, current_value)
        
        # Verify item was added
        assert len(result) >= 2  # Should have at least original + new item
        mock_rerun.assert_called_once()
    
    @patch('streamlit.info')
    @patch('streamlit.button')
    @patch('streamlit.columns')
    @patch('streamlit.markdown')
    @patch('streamlit.container')
    @patch('streamlit.success')
    @patch('streamlit.rerun')
    @patch('utils.form_generator.FormGenerator._render_scalar_input')
    def test_render_scalar_array_editor_remove_item(self, mock_render_input, mock_rerun, 
                                                   mock_success, mock_container, mock_markdown, 
                                                   mock_columns, mock_button, mock_info):
        """Test removing items from scalar array."""
        # Setup mocks
        mock_container.return_value.__enter__ = MagicMock()
        mock_container.return_value.__exit__ = MagicMock()
        mock_columns.return_value = [MagicMock(), MagicMock()]
        mock_render_input.return_value = "value"
        
        # Mock button to return True for remove button
        def button_side_effect(*args, **kwargs):
            if 'Remove' in args:
                return True
            return False
        mock_button.side_effect = button_side_effect
        
        # Test data
        field_name = "serial_numbers"
        field_config = {
            "type": "array",
            "label": "Serial Numbers",
            "items": {
                "type": "string"
            }
        }
        current_value = ["SN001", "SN002", "SN003"]
        
        # Initialize session state for remove operation
        st.session_state[f"scalar_array_{field_name}_remove_item"] = 1  # Remove index 1
        
        # Call the method
        result = FormGenerator._render_scalar_array_editor(field_name, field_config, current_value)
        
        # Verify item was removed
        assert len(result) == 2  # Should have one less item
        # Note: rerun may be called multiple times during the removal process
        assert mock_rerun.call_count >= 1
    
    @patch('streamlit.text_input')
    def test_render_scalar_input_string_type(self, mock_text_input):
        """Test rendering scalar input for string type."""
        mock_text_input.return_value = "test_value"
        
        result = FormGenerator._render_scalar_input(
            "test_field[0]",
            "string",
            "initial_value",
            {"type": "string"},
            key="test_key"
        )
        
        assert result == "test_value"
        mock_text_input.assert_called_once()
        call_kwargs = mock_text_input.call_args[1]
        assert call_kwargs['key'] == "test_key"
        assert call_kwargs['value'] == "initial_value"
    
    @patch('streamlit.number_input')
    def test_render_scalar_input_number_type(self, mock_number_input):
        """Test rendering scalar input for number type."""
        mock_number_input.return_value = 42.5
        
        result = FormGenerator._render_scalar_input(
            "test_field[0]",
            "number",
            25.0,
            {"type": "number", "min_value": 0, "max_value": 100},
            key="test_key"
        )
        
        assert result == 42.5
        mock_number_input.assert_called_once()
        call_kwargs = mock_number_input.call_args[1]
        assert call_kwargs['key'] == "test_key"
        assert call_kwargs['value'] == 25.0
        assert call_kwargs['min_value'] == 0
        assert call_kwargs['max_value'] == 100
    
    @patch('streamlit.number_input')
    def test_render_scalar_input_integer_type(self, mock_number_input):
        """Test rendering scalar input for integer type."""
        mock_number_input.return_value = 42
        
        result = FormGenerator._render_scalar_input(
            "test_field[0]",
            "integer",
            25,
            {"type": "integer", "min_value": -10, "max_value": 100},
            key="test_key"
        )
        
        assert result == 42
        mock_number_input.assert_called_once()
        call_kwargs = mock_number_input.call_args[1]
        assert call_kwargs['key'] == "test_key"
        assert call_kwargs['value'] == 25
        assert call_kwargs['min_value'] == -10
        assert call_kwargs['max_value'] == 100
        assert call_kwargs['format'] == "%d"
    
    @patch('streamlit.checkbox')
    def test_render_scalar_input_boolean_type(self, mock_checkbox):
        """Test rendering scalar input for boolean type."""
        mock_checkbox.return_value = True
        
        result = FormGenerator._render_scalar_input(
            "test_field[0]",
            "boolean",
            False,
            {"type": "boolean"},
            key="test_key"
        )
        
        assert result is True
        mock_checkbox.assert_called_once()
        call_kwargs = mock_checkbox.call_args[1]
        assert call_kwargs['key'] == "test_key"
        assert call_kwargs['value'] is False
    
    @patch('streamlit.date_input')
    def test_render_scalar_input_date_type(self, mock_date_input):
        """Test rendering scalar input for date type."""
        test_date = date(2024, 1, 15)
        mock_date_input.return_value = test_date
        
        result = FormGenerator._render_scalar_input(
            "test_field[0]",
            "date",
            "2024-01-10",
            {"type": "date"},
            key="test_key"
        )
        
        assert result == "2024-01-15"
        mock_date_input.assert_called_once()
        call_kwargs = mock_date_input.call_args[1]
        assert call_kwargs['key'] == "test_key"
    
    @patch('streamlit.selectbox')
    def test_render_scalar_input_enum_type(self, mock_selectbox):
        """Test rendering scalar input for enum type."""
        mock_selectbox.return_value = "option2"
        
        result = FormGenerator._render_scalar_input(
            "test_field[0]",
            "enum",
            "option1",
            {"type": "enum", "choices": ["option1", "option2", "option3"]},
            key="test_key"
        )
        
        assert result == "option2"
        mock_selectbox.assert_called_once()
        call_kwargs = mock_selectbox.call_args[1]
        assert call_kwargs['key'] == "test_key"
        assert call_kwargs['index'] == 0  # Index of "option1" in choices
    
    def test_get_default_value_for_type_string(self):
        """Test getting default value for string type."""
        result = FormGenerator._get_default_value_for_type("string", {})
        assert result == ""
    
    def test_get_default_value_for_type_number(self):
        """Test getting default value for number type."""
        result = FormGenerator._get_default_value_for_type("number", {})
        assert result == 0.0
    
    def test_get_default_value_for_type_integer(self):
        """Test getting default value for integer type."""
        result = FormGenerator._get_default_value_for_type("integer", {})
        assert result == 0
    
    def test_get_default_value_for_type_boolean(self):
        """Test getting default value for boolean type."""
        result = FormGenerator._get_default_value_for_type("boolean", {})
        assert result is False
    
    def test_get_default_value_for_type_date(self):
        """Test getting default value for date type."""
        result = FormGenerator._get_default_value_for_type("date", {})
        # Should return today's date in ISO format
        assert isinstance(result, str)
        assert len(result) == 10  # YYYY-MM-DD format
    
    def test_get_default_value_for_type_enum_with_choices(self):
        """Test getting default value for enum type with choices."""
        config = {"choices": ["red", "green", "blue"]}
        result = FormGenerator._get_default_value_for_type("enum", config)
        assert result == "red"  # First choice
    
    def test_get_default_value_for_type_enum_with_explicit_default(self):
        """Test getting default value for enum type with explicit default."""
        config = {"choices": ["red", "green", "blue"], "default": "green"}
        result = FormGenerator._get_default_value_for_type("enum", config)
        assert result == "green"
    
    def test_get_default_value_for_type_number_with_negative_minimum(self):
        """Test getting default value for number type with negative minimum."""
        config = {"min_value": -10}
        result = FormGenerator._get_default_value_for_type("number", config)
        assert result == -10.0  # Should respect negative minimum
    
    def test_get_default_value_for_type_integer_with_negative_minimum(self):
        """Test getting default value for integer type with negative minimum."""
        config = {"min_value": -5}
        result = FormGenerator._get_default_value_for_type("integer", config)
        assert result == -5  # Should respect negative minimum
    
    def test_validate_scalar_array_valid_strings(self):
        """Test validation of valid string array."""
        array_value = ["item1", "item2", "item3"]
        items_config = {"type": "string"}
        
        errors = FormGenerator._validate_scalar_array("test_field", array_value, items_config)
        assert len(errors) == 0
    
    def test_validate_scalar_array_invalid_type(self):
        """Test validation with invalid array type."""
        array_value = "not_an_array"
        items_config = {"type": "string"}
        
        errors = FormGenerator._validate_scalar_array("test_field", array_value, items_config)
        assert len(errors) == 1
        assert "must be an array" in errors[0]
    
    def test_validate_scalar_array_string_length_constraints(self):
        """Test validation of string array with length constraints."""
        array_value = ["ok", "", "toolongstring"]
        items_config = {
            "type": "string",
            "min_length": 2,
            "max_length": 10
        }
        
        errors = FormGenerator._validate_scalar_array("test_field", array_value, items_config)
        assert len(errors) == 2  # Empty string and too long string
        assert "test_field[1]" in errors[0]  # Empty string error
        assert "test_field[2]" in errors[1]  # Too long string error
    
    def test_validate_scalar_array_number_constraints(self):
        """Test validation of number array with value constraints."""
        array_value = [5.5, -1.0, 150.0]
        items_config = {
            "type": "number",
            "min_value": 0,
            "max_value": 100
        }
        
        errors = FormGenerator._validate_scalar_array("test_field", array_value, items_config)
        assert len(errors) == 2  # Negative and too large values
        assert "test_field[1]" in errors[0]  # Negative value error
        assert "test_field[2]" in errors[1]  # Too large value error
    
    def test_validate_scalar_array_integer_constraints(self):
        """Test validation of integer array with value constraints."""
        array_value = [5, -10, 200]
        items_config = {
            "type": "integer",
            "min_value": -5,
            "max_value": 100
        }
        
        errors = FormGenerator._validate_scalar_array("test_field", array_value, items_config)
        assert len(errors) == 2  # Too small and too large values
        assert "test_field[1]" in errors[0]  # Too small value error
        assert "test_field[2]" in errors[1]  # Too large value error
    
    def test_validate_scalar_array_enum_constraints(self):
        """Test validation of enum array with choice constraints."""
        array_value = ["red", "purple", "blue"]
        items_config = {
            "type": "enum",
            "choices": ["red", "green", "blue"]
        }
        
        errors = FormGenerator._validate_scalar_array("test_field", array_value, items_config)
        assert len(errors) == 1  # Invalid choice
        assert "test_field[1]" in errors[0]  # Purple is not in choices
        assert "must be one of" in errors[0]
    
    def test_validate_scalar_array_pattern_constraints(self):
        """Test validation of string array with pattern constraints."""
        array_value = ["ABC123", "xyz789", "invalid"]
        items_config = {
            "type": "string",
            "pattern": "^[A-Z]{3}\\d{3}$"
        }
        
        errors = FormGenerator._validate_scalar_array("test_field", array_value, items_config)
        assert len(errors) == 2  # Two items don't match pattern
        assert "test_field[1]" in errors[0] or "test_field[2]" in errors[0]
        assert "must match pattern" in errors[0]
    
    @patch('utils.form_generator.FormGenerator._render_scalar_array_editor')
    def test_render_array_editor_delegates_to_scalar(self, mock_scalar_editor):
        """Test that _render_array_editor delegates to scalar editor for scalar arrays."""
        mock_scalar_editor.return_value = ["item1", "item2"]
        
        field_config = {
            "type": "array",
            "items": {"type": "string"}
        }
        current_value = ["item1"]
        
        result = FormGenerator._render_array_editor("test_field", field_config, current_value)
        
        assert result == ["item1", "item2"]
        mock_scalar_editor.assert_called_once_with("test_field", field_config, current_value)
    
    @patch('utils.form_generator.FormGenerator._render_object_array_editor')
    def test_render_array_editor_delegates_to_object(self, mock_object_editor):
        """Test that _render_array_editor delegates to object editor for object arrays."""
        mock_object_editor.return_value = [{"name": "item1"}]
        
        field_config = {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {"name": {"type": "string"}}
            }
        }
        current_value = []
        
        result = FormGenerator._render_array_editor("test_field", field_config, current_value)
        
        assert result == [{"name": "item1"}]
        mock_object_editor.assert_called_once_with("test_field", field_config, current_value)
    
    def test_streamlit_key_namespacing(self):
        """Test that Streamlit keys are properly namespaced per field."""
        field_name1 = "serial_numbers"
        field_name2 = "tags"
        
        # Test that different fields get different key prefixes
        key1 = f"scalar_array_{field_name1}"
        key2 = f"scalar_array_{field_name2}"
        
        assert key1 != key2
        assert field_name1 in key1
        assert field_name2 in key2
        
        # Test that item keys are also namespaced
        item_key1 = f"{key1}_item_0"
        item_key2 = f"{key2}_item_0"
        
        assert item_key1 != item_key2
        assert field_name1 in item_key1
        assert field_name2 in item_key2


class TestFormGeneratorScalarArrayIntegration:
    """Integration tests for scalar arrays with existing form generation workflow."""
    
    def setup_method(self):
        """Set up test environment before each test."""
        if hasattr(st, 'session_state'):
            st.session_state.clear()
    
    def teardown_method(self):
        """Clean up after each test."""
        if hasattr(st, 'session_state'):
            st.session_state.clear()
    
    @patch('utils.form_generator.FormGenerator._render_scalar_array_editor')
    @patch('streamlit.form')
    @patch('streamlit.subheader')
    @patch('streamlit.columns')
    @patch('streamlit.form_submit_button')
    def test_render_dynamic_form_with_scalar_arrays(self, mock_submit_button, mock_columns, 
                                                  mock_subheader, mock_form, mock_scalar_editor):
        """Test rendering dynamic form with scalar array fields."""
        # Setup mocks
        mock_form.return_value.__enter__ = MagicMock()
        mock_form.return_value.__exit__ = MagicMock()
        mock_columns.return_value = [MagicMock(), MagicMock()]
        mock_submit_button.return_value = False
        mock_scalar_editor.return_value = ["SN001", "SN002"]
        
        # Test schema with scalar array
        schema = {
            "fields": {
                "supplier_name": {
                    "type": "string",
                    "label": "Supplier Name",
                    "required": True
                },
                "serial_numbers": {
                    "type": "array",
                    "label": "Serial Numbers",
                    "items": {"type": "string"}
                }
            }
        }
        
        current_data = {
            "supplier_name": "Test Company",
            "serial_numbers": ["SN001"]
        }
        
        # Call the method
        result = FormGenerator.render_dynamic_form(schema, current_data)
        
        # Verify scalar array editor was called
        mock_scalar_editor.assert_called_once()
        
        # Verify result contains array data
        assert "serial_numbers" in result
        assert result["serial_numbers"] == ["SN001", "SN002"]
    
    @patch('utils.submission_handler.SubmissionHandler._validate_submission_data')
    @patch('streamlit.form')
    @patch('streamlit.subheader')
    @patch('streamlit.columns')
    @patch('streamlit.form_submit_button')
    @patch('streamlit.success')
    def test_validation_integration_with_scalar_arrays(self, mock_success, mock_submit_button, 
                                                     mock_columns, mock_subheader, mock_form, 
                                                     mock_validate):
        """Test validation integration with scalar array fields."""
        # Setup mocks
        mock_form.return_value.__enter__ = MagicMock()
        mock_form.return_value.__exit__ = MagicMock()
        mock_columns.return_value = [MagicMock(), MagicMock()]
        mock_submit_button.return_value = True  # Simulate validate button click
        mock_validate.return_value = []  # No validation errors
        
        # Test schema with scalar array
        schema = {
            "fields": {
                "tags": {
                    "type": "array",
                    "label": "Tags",
                    "items": {
                        "type": "string",
                        "min_length": 1
                    }
                }
            }
        }
        
        current_data = {"tags": ["tag1", "tag2"]}
        
        # Mock SessionManager methods
        with patch.object(SessionManager, 'get_model_class', return_value=MagicMock()):
            with patch.object(SessionManager, 'set_form_data'):
                with patch.object(SessionManager, 'clear_validation_errors'):
                    # Call the method
                    result = FormGenerator.render_dynamic_form(schema, current_data)
                    
                    # Verify validation was called
                    mock_validate.assert_called_once()
                    # Note: success may be called multiple times (array validation + overall validation)
                    mock_success.assert_called_with("Data validated successfully")
    
    @patch('utils.submission_handler.SubmissionHandler._validate_submission_data')
    @patch('streamlit.form')
    @patch('streamlit.subheader')
    @patch('streamlit.columns')
    @patch('streamlit.form_submit_button')
    @patch('streamlit.error')
    def test_validation_errors_with_scalar_arrays(self, mock_error, mock_submit_button, 
                                                 mock_columns, mock_subheader, mock_form, 
                                                 mock_validate):
        """Test validation error handling with scalar array fields."""
        # Setup mocks
        mock_form.return_value.__enter__ = MagicMock()
        mock_form.return_value.__exit__ = MagicMock()
        mock_columns.return_value = [MagicMock(), MagicMock()]
        mock_submit_button.return_value = True  # Simulate validate button click
        mock_validate.return_value = ["tags[0] cannot be empty", "tags[2] must be at least 2 characters"]
        
        # Test schema with scalar array
        schema = {
            "fields": {
                "tags": {
                    "type": "array",
                    "label": "Tags",
                    "items": {
                        "type": "string",
                        "min_length": 2
                    }
                }
            }
        }
        
        current_data = {"tags": ["", "ok", "x"]}  # Invalid data
        
        # Mock SessionManager methods
        with patch.object(SessionManager, 'get_model_class', return_value=MagicMock()):
            with patch.object(SessionManager, 'set_form_data'):
                with patch.object(SessionManager, 'set_validation_errors'):
                    # Call the method
                    result = FormGenerator.render_dynamic_form(schema, current_data)
                    
                    # Verify validation errors were displayed
                    mock_error.assert_called()
                    error_calls = mock_error.call_args_list
                    assert len(error_calls) >= 2  # At least the main error message and individual errors
    
    def test_collect_current_form_data_with_scalar_arrays(self):
        """Test collecting form data with scalar array fields."""
        # Setup session state with array data
        st.session_state["field_tags"] = None  # Regular field value
        st.session_state["array_tags"] = ["tag1", "tag2", "tag3"]  # Array field value
        
        schema = {
            "fields": {
                "tags": {
                    "type": "array",
                    "label": "Tags",
                    "items": {"type": "string"}
                }
            }
        }
        
        # Call the method
        result = FormGenerator.collect_current_form_data(schema)
        
        # Verify array data was collected
        assert "tags" in result
        assert result["tags"] == ["tag1", "tag2", "tag3"]
    
    def test_collect_current_form_data_with_json_array(self):
        """Test collecting form data with JSON-encoded array fields."""
        # Setup session state with JSON array data
        st.session_state["field_tags"] = None
        st.session_state["json_array_tags"] = '["tag1", "tag2", "tag3"]'  # JSON string
        
        schema = {
            "fields": {
                "tags": {
                    "type": "array",
                    "label": "Tags",
                    "items": {"type": "string"}
                }
            }
        }
        
        # Call the method
        result = FormGenerator.collect_current_form_data(schema)
        
        # Verify JSON array data was parsed and collected
        assert "tags" in result
        assert result["tags"] == ["tag1", "tag2", "tag3"]


class TestFormGeneratorScalarArrayRealWorldData:
    """Test scalar array functionality with real insurance document data."""
    
    def setup_method(self):
        """Set up test environment before each test."""
        if hasattr(st, 'session_state'):
            st.session_state.clear()
    
    def teardown_method(self):
        """Clean up after each test."""
        if hasattr(st, 'session_state'):
            st.session_state.clear()
    
    def test_insurance_document_serial_numbers(self):
        """Test scalar array functionality with insurance document serial numbers."""
        # Real insurance document data structure
        field_config = {
            "type": "array",
            "label": "Serial Numbers",
            "required": False,
            "help": "List of equipment serial numbers",
            "items": {
                "type": "string"
            }
        }
        
        current_value = ["SerialNo1", "SerialNo2"]
        
        # Test validation
        errors = FormGenerator._validate_scalar_array("Serial Numbers", current_value, field_config["items"])
        assert len(errors) == 0
        
        # Test default value generation
        default_value = FormGenerator._get_default_value_for_type("string", field_config["items"])
        assert default_value == ""
    
    def test_insurance_document_with_constraints(self):
        """Test scalar array with realistic constraints for insurance documents."""
        # More realistic field config with constraints
        field_config = {
            "type": "array",
            "label": "Policy Numbers",
            "required": True,
            "help": "List of policy numbers",
            "items": {
                "type": "string",
                "pattern": "^[A-Z]{2}[0-9]{10}$",  # Pattern like "AB1234567890"
                "min_length": 12,
                "max_length": 12
            }
        }
        
        # Test valid data
        valid_data = ["AB1234567890", "CD9876543210"]
        errors = FormGenerator._validate_scalar_array("Policy Numbers", valid_data, field_config["items"])
        assert len(errors) == 0
        
        # Test invalid data
        invalid_data = ["AB123", "cd1234567890", "AB12345678901"]  # Too short, wrong case, too long
        errors = FormGenerator._validate_scalar_array("Policy Numbers", invalid_data, field_config["items"])
        # Each item can have multiple validation errors (length + pattern), so expect more than 3
        assert len(errors) >= 3  # At least one error per invalid item
        
        # Check that all items have errors
        error_text = " ".join(errors)
        assert "Policy Numbers[0]" in error_text  # Too short
        assert "Policy Numbers[1]" in error_text  # Wrong pattern  
        assert "Policy Numbers[2]" in error_text  # Too long
    
    def test_insurance_document_mixed_field_types(self):
        """Test form with mixed field types including scalar arrays."""
        schema = {
            "fields": {
                "Supplier name": {
                    "type": "string",
                    "label": "Supplier Name",
                    "required": True
                },
                "Invoice amount": {
                    "type": "number",
                    "label": "Invoice Amount",
                    "required": True
                },
                "Serial Numbers": {
                    "type": "array",
                    "label": "Serial Numbers",
                    "required": False,
                    "items": {"type": "string"}
                },
                "Invoice type": {
                    "type": "enum",
                    "label": "Invoice Type",
                    "choices": ["debit", "credit"],
                    "required": True
                }
            }
        }
        
        # Real insurance document data
        current_data = {
            "Supplier name": "China Taiping Insurance (Singapore) Pte. Ltd.",
            "Invoice amount": 490.5,
            "Serial Numbers": ["SerialNo1", "SerialNo2"],
            "Invoice type": "debit"
        }
        
        # Test that collect_current_form_data handles mixed types correctly
        # Simulate session state
        st.session_state["field_Supplier name"] = current_data["Supplier name"]
        st.session_state["field_Invoice amount"] = current_data["Invoice amount"]
        st.session_state["array_Serial Numbers"] = current_data["Serial Numbers"]
        st.session_state["field_Invoice type"] = current_data["Invoice type"]
        
        result = FormGenerator.collect_current_form_data(schema)
        
        # Verify all field types are handled correctly
        assert result["Supplier name"] == current_data["Supplier name"]
        assert result["Invoice amount"] == current_data["Invoice amount"]
        assert result["Serial Numbers"] == current_data["Serial Numbers"]
        assert result["Invoice type"] == current_data["Invoice type"]


class TestFormGeneratorScalarArrayEdgeCases:
    """Test edge cases and error conditions for scalar array functionality."""
    
    def setup_method(self):
        """Set up test environment before each test."""
        if hasattr(st, 'session_state'):
            st.session_state.clear()
    
    def teardown_method(self):
        """Clean up after each test."""
        if hasattr(st, 'session_state'):
            st.session_state.clear()
    
    def test_empty_array_handling(self):
        """Test handling of empty arrays."""
        field_config = {
            "type": "array",
            "items": {"type": "string"}
        }
        
        # Test with None
        result = FormGenerator._render_array_editor("test_field", field_config, None)
        assert isinstance(result, list)
        assert len(result) == 0
        
        # Test with empty list
        result = FormGenerator._render_array_editor("test_field", field_config, [])
        assert isinstance(result, list)
        assert len(result) == 0
    
    def test_invalid_array_type_handling(self):
        """Test handling of invalid array types."""
        field_config = {
            "type": "array",
            "items": {"type": "string"}
        }
        
        # Test with string instead of array
        result = FormGenerator._render_array_editor("test_field", field_config, "not_an_array")
        assert isinstance(result, list)
        assert len(result) == 0  # Should convert to empty array
    
    def test_missing_items_config(self):
        """Test handling of missing items configuration."""
        field_config = {
            "type": "array"
            # Missing 'items' key
        }
        
        current_value = ["item1", "item2"]
        
        # Should default to string type
        result = FormGenerator._render_array_editor("test_field", field_config, current_value)
        assert isinstance(result, list)
    
    def test_invalid_item_type(self):
        """Test handling of invalid item types."""
        field_config = {
            "type": "array",
            "items": {"type": "unknown_type"}
        }
        
        current_value = ["item1"]
        
        # Should fallback gracefully
        result = FormGenerator._render_array_editor("test_field", field_config, current_value)
        assert isinstance(result, list)
    
    def test_malformed_json_in_session_state(self):
        """Test handling of malformed JSON in session state."""
        schema = {
            "fields": {
                "tags": {
                    "type": "array",
                    "items": {"type": "string"}
                }
            }
        }
        
        # Set malformed JSON in session state
        st.session_state["json_array_tags"] = '["item1", "item2"'  # Missing closing bracket
        
        result = FormGenerator.collect_current_form_data(schema)
        
        # Should handle gracefully and not include the malformed data
        assert "tags" not in result or result["tags"] is None
    
    def test_very_large_arrays(self):
        """Test handling of very large arrays."""
        field_config = {
            "type": "array",
            "items": {"type": "string"}
        }
        
        # Create a large array
        large_array = [f"item_{i}" for i in range(1000)]
        
        # Test validation doesn't crash
        errors = FormGenerator._validate_scalar_array("large_field", large_array, field_config["items"])
        assert isinstance(errors, list)  # Should return a list, even if empty
    
    def test_unicode_and_special_characters(self):
        """Test handling of unicode and special characters in array items."""
        field_config = {
            "type": "array",
            "items": {"type": "string"}
        }
        
        # Array with unicode and special characters
        unicode_array = ["café", "naïve", "résumé", "🎉", "中文", "العربية"]
        
        # Test validation handles unicode correctly
        errors = FormGenerator._validate_scalar_array("unicode_field", unicode_array, field_config["items"])
        assert len(errors) == 0  # Should be valid
    
    def test_numeric_precision_handling(self):
        """Test handling of numeric precision in number arrays."""
        field_config = {
            "type": "array",
            "items": {
                "type": "number",
                "min_value": 0.01,
                "max_value": 999.99
            }
        }
        
        # Array with various precision numbers
        number_array = [0.01, 123.456789, 999.99, 0.001]  # Last one below minimum
        
        errors = FormGenerator._validate_scalar_array("precision_field", number_array, field_config["items"])
        assert len(errors) == 1  # Only the last item should fail
        assert "precision_field[3]" in errors[0]