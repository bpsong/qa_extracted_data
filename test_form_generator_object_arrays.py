"""
Unit tests for FormGenerator object array integration.
Tests the enhanced object array editing functionality integrated into the main FormGenerator.
"""

import pytest
import streamlit as st
from unittest.mock import patch, MagicMock, call
from datetime import datetime, date
import json
import pandas as pd
import numpy as np

# Import the module to test
from utils.form_generator import FormGenerator
from utils.session_manager import SessionManager
from utils.submission_handler import SubmissionHandler


class TestFormGeneratorObjectArrays:
    """Test class for FormGenerator object array integration."""
    
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
    @patch('streamlit.data_editor')
    def test_render_object_array_editor_basic_functionality(self, mock_data_editor, mock_success, 
                                                           mock_container, mock_markdown, 
                                                           mock_columns, mock_button, mock_info):
        """Test basic object array editor functionality."""
        # Setup mocks
        mock_container.return_value.__enter__ = MagicMock()
        mock_container.return_value.__exit__ = MagicMock()
        mock_columns.return_value = [MagicMock(), MagicMock()]
        mock_button.return_value = False
        
        # Mock data_editor to return DataFrame
        test_data = [{"name": "Item 1", "quantity": 5}, {"name": "Item 2", "quantity": 10}]
        mock_df = pd.DataFrame(test_data)
        mock_data_editor.return_value = mock_df
        
        # Test data
        field_name = "line_items"
        field_config = {
            "type": "array",
            "label": "Line Items",
            "items": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "label": "Item Name"},
                    "quantity": {"type": "integer", "label": "Quantity", "min_value": 1}
                }
            }
        }
        current_value = test_data
        
        # Call the method
        result = FormGenerator._render_object_array_editor(field_name, field_config, current_value)
        
        # Verify basic structure
        assert isinstance(result, list)
        assert len(result) == 2
        assert result[0]["name"] == "Item 1"
        assert result[1]["quantity"] == 10
        
        # Verify UI elements were called
        mock_info.assert_called_once()
        mock_container.assert_called_once()
        mock_columns.assert_called()
        mock_markdown.assert_called()
        mock_data_editor.assert_called_once()
    
    @patch('streamlit.info')
    @patch('streamlit.button')
    @patch('streamlit.columns')
    @patch('streamlit.markdown')
    @patch('streamlit.container')
    @patch('streamlit.success')
    @patch('streamlit.data_editor')
    @patch('streamlit.rerun')
    def test_render_object_array_editor_add_row(self, mock_rerun, mock_data_editor, mock_success, 
                                               mock_container, mock_markdown, mock_columns, 
                                               mock_button, mock_info):
        """Test adding rows to object array."""
        # Setup mocks
        mock_container.return_value.__enter__ = MagicMock()
        mock_container.return_value.__exit__ = MagicMock()
        mock_columns.return_value = [MagicMock(), MagicMock()]
        
        # Mock button to return True for add button
        def button_side_effect(*args, **kwargs):
            if 'Add Row' in args:
                return True
            return False
        mock_button.side_effect = button_side_effect
        
        # Mock data_editor
        test_data = [{"name": "Item 1", "quantity": 5}]
        mock_df = pd.DataFrame(test_data)
        mock_data_editor.return_value = mock_df
        
        # Test data
        field_name = "line_items"
        field_config = {
            "type": "array",
            "label": "Line Items",
            "items": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "label": "Item Name"},
                    "quantity": {"type": "integer", "label": "Quantity", "min_value": 1}
                }
            }
        }
        current_value = test_data
        
        # Call the method
        result = FormGenerator._render_object_array_editor(field_name, field_config, current_value)
        
        # Verify rerun was called (indicating add operation)
        mock_rerun.assert_called_once()
    
    @patch('streamlit.info')
    @patch('streamlit.button')
    @patch('streamlit.columns')
    @patch('streamlit.markdown')
    @patch('streamlit.container')
    @patch('streamlit.success')
    @patch('streamlit.data_editor')
    @patch('streamlit.selectbox')
    @patch('streamlit.rerun')
    def test_render_object_array_editor_delete_row(self, mock_rerun, mock_selectbox, mock_data_editor, 
                                                  mock_success, mock_container, mock_markdown, 
                                                  mock_columns, mock_button, mock_info):
        """Test deleting rows from object array."""
        # Setup mocks
        mock_container.return_value.__enter__ = MagicMock()
        mock_container.return_value.__exit__ = MagicMock()
        mock_columns.return_value = [MagicMock(), MagicMock()]
        mock_selectbox.return_value = 1  # Select row 1 for deletion
        
        # Mock button to return True for delete button
        def button_side_effect(*args, **kwargs):
            if 'Delete Selected Row' in args:
                return True
            return False
        mock_button.side_effect = button_side_effect
        
        # Mock data_editor
        test_data = [{"name": "Item 1", "quantity": 5}, {"name": "Item 2", "quantity": 10}]
        mock_df = pd.DataFrame(test_data)
        mock_data_editor.return_value = mock_df
        
        # Test data
        field_name = "line_items"
        field_config = {
            "type": "array",
            "label": "Line Items",
            "items": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "label": "Item Name"},
                    "quantity": {"type": "integer", "label": "Quantity", "min_value": 1}
                }
            }
        }
        current_value = test_data
        
        # Call the method
        result = FormGenerator._render_object_array_editor(field_name, field_config, current_value)
        
        # Verify delete operation was triggered
        mock_selectbox.assert_called_once()
        mock_rerun.assert_called_once()
        # The success message might be called multiple times (delete + validation), so check if it was called
        mock_success.assert_called()
    
    @patch('streamlit.info')
    def test_render_object_array_editor_empty_array(self, mock_info):
        """Test rendering object array editor with empty array."""
        # Test data
        field_name = "line_items"
        field_config = {
            "type": "array",
            "label": "Line Items",
            "items": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "label": "Item Name"},
                    "quantity": {"type": "integer", "label": "Quantity", "min_value": 1}
                }
            }
        }
        current_value = []
        
        with patch('streamlit.container') as mock_container:
            mock_container.return_value.__enter__ = MagicMock()
            mock_container.return_value.__exit__ = MagicMock()
            
            with patch('streamlit.columns') as mock_columns:
                mock_columns.return_value = [MagicMock(), MagicMock()]
                
                with patch('streamlit.button') as mock_button:
                    mock_button.return_value = False
                    
                    with patch('streamlit.markdown') as mock_markdown:
                        # Call the method
                        result = FormGenerator._render_object_array_editor(field_name, field_config, current_value)
                        
                        # Verify empty array handling
                        assert result == []
                        mock_info.assert_called()
                        # Should show "No items in array" message
                        info_calls = mock_info.call_args_list
                        assert any("No items in array" in str(call) for call in info_calls)
    
    def test_generate_column_config_string_properties(self):
        """Test column configuration generation for string properties."""
        properties = {
            "name": {
                "type": "string",
                "label": "Item Name",
                "help": "Name of the item",
                "required": True,
                "max_length": 100
            }
        }
        
        config = FormGenerator._generate_column_config(properties)
        
        assert "name" in config
        # We can't directly test st.column_config objects, but we can verify the function runs
        assert config["name"] is not None
    
    def test_generate_column_config_number_properties(self):
        """Test column configuration generation for number properties."""
        properties = {
            "price": {
                "type": "number",
                "label": "Price",
                "help": "Item price",
                "required": True,
                "min_value": 0,
                "max_value": 1000,
                "step": 0.01
            }
        }
        
        config = FormGenerator._generate_column_config(properties)
        
        assert "price" in config
        assert config["price"] is not None
    
    def test_generate_column_config_integer_properties(self):
        """Test column configuration generation for integer properties."""
        properties = {
            "quantity": {
                "type": "integer",
                "label": "Quantity",
                "help": "Item quantity",
                "required": True,
                "min_value": 1,
                "max_value": 100,
                "step": 1
            }
        }
        
        config = FormGenerator._generate_column_config(properties)
        
        assert "quantity" in config
        assert config["quantity"] is not None
    
    def test_generate_column_config_boolean_properties(self):
        """Test column configuration generation for boolean properties."""
        properties = {
            "is_active": {
                "type": "boolean",
                "label": "Active",
                "help": "Is item active",
                "required": False
            }
        }
        
        config = FormGenerator._generate_column_config(properties)
        
        assert "is_active" in config
        assert config["is_active"] is not None
    
    def test_generate_column_config_date_properties(self):
        """Test column configuration generation for date properties."""
        properties = {
            "due_date": {
                "type": "date",
                "label": "Due Date",
                "help": "Item due date",
                "required": False
            }
        }
        
        config = FormGenerator._generate_column_config(properties)
        
        assert "due_date" in config
        assert config["due_date"] is not None
    
    def test_create_default_object(self):
        """Test creation of default objects with appropriate default values."""
        properties = {
            "name": {"type": "string", "label": "Item Name"},
            "quantity": {"type": "integer", "label": "Quantity", "min_value": 1},
            "price": {"type": "number", "label": "Price", "min_value": 0},
            "is_active": {"type": "boolean", "label": "Active"},
            "due_date": {"type": "date", "label": "Due Date"}
        }
        
        default_obj = FormGenerator._create_default_object(properties)
        
        # Check that all properties are present
        for prop_name in properties.keys():
            assert prop_name in default_obj
        
        # Check default values by type (respecting constraints)
        assert default_obj["name"] == ""  # string
        assert default_obj["quantity"] == 1  # integer with min_value: 1
        assert default_obj["price"] == 0.0  # number with min_value: 0
        assert default_obj["is_active"] is False  # boolean
        assert isinstance(default_obj["due_date"], str)  # date (as string)
    
    def test_create_default_object_with_negative_minima(self):
        """Test creation of default objects with negative minimum values."""
        properties = {
            "temperature": {"type": "number", "min_value": -10.0},
            "offset": {"type": "integer", "min_value": -5}
        }
        
        default_obj = FormGenerator._create_default_object(properties)
        
        # Check that negative minima are respected
        assert default_obj["temperature"] == -10.0
        assert default_obj["offset"] == -5
    
    def test_clean_object_array_with_nan(self):
        """Test cleaning object array with NaN values."""
        # Create array with pandas NaN values
        dirty_array = [
            {
                "name": "Item 1",
                "quantity": np.nan,
                "price": 150.0,
                "is_active": True
            },
            {
                "name": pd.NA,
                "quantity": 5,
                "price": np.nan,
                "is_active": False
            }
        ]
        
        cleaned_array = FormGenerator._clean_object_array(dirty_array)
        
        # Check that NaN values are converted to None
        assert cleaned_array[0]["name"] == "Item 1"
        assert cleaned_array[0]["quantity"] is None
        assert cleaned_array[0]["price"] == 150.0
        assert cleaned_array[0]["is_active"] is True
        
        assert cleaned_array[1]["name"] is None
        assert cleaned_array[1]["quantity"] == 5
        assert cleaned_array[1]["price"] is None
        assert cleaned_array[1]["is_active"] is False
    
    def test_clean_object_array_with_numpy_types(self):
        """Test cleaning object array with numpy types."""
        dirty_array = [
            {
                "quantity": np.int64(5),
                "price": np.float64(150.5),
                "name": "Item 1"
            }
        ]
        
        cleaned_array = FormGenerator._clean_object_array(dirty_array)
        
        # Check that numpy types are converted to Python types
        assert cleaned_array[0]["quantity"] == 5
        assert isinstance(cleaned_array[0]["quantity"], int)
        assert cleaned_array[0]["price"] == 150.5
        assert isinstance(cleaned_array[0]["price"], float)
        assert cleaned_array[0]["name"] == "Item 1"
    
    def test_validate_object_item_valid(self):
        """Test validation of valid object items."""
        properties = {
            "name": {"type": "string", "required": True, "min_length": 1},
            "quantity": {"type": "integer", "required": True, "min_value": 1},
            "price": {"type": "number", "required": False, "min_value": 0},
            "is_active": {"type": "boolean", "required": False}
        }
        
        valid_item = {
            "name": "Item 1",
            "quantity": 5,
            "price": 150.0,
            "is_active": True
        }
        
        errors = FormGenerator._validate_object_item("line_items[0]", valid_item, properties)
        assert errors == []
    
    def test_validate_object_item_missing_required(self):
        """Test validation of object items with missing required properties."""
        properties = {
            "name": {"type": "string", "required": True, "min_length": 1},
            "quantity": {"type": "integer", "required": True, "min_value": 1}
        }
        
        invalid_item = {
            "quantity": 5
            # Missing required "name"
        }
        
        errors = FormGenerator._validate_object_item("line_items[0]", invalid_item, properties)
        
        assert len(errors) == 1
        assert "line_items[0].name" in errors[0]
        assert "is required" in errors[0]
    
    def test_validate_object_item_empty_required(self):
        """Test validation of object items with empty required properties."""
        properties = {
            "name": {"type": "string", "required": True, "min_length": 1},
            "quantity": {"type": "integer", "required": True, "min_value": 1}
        }
        
        invalid_item = {
            "name": "",  # Empty required field
            "quantity": 5
        }
        
        errors = FormGenerator._validate_object_item("line_items[0]", invalid_item, properties)
        
        assert len(errors) == 1
        assert "line_items[0].name" in errors[0]
        assert "is required" in errors[0]
    
    def test_validate_object_item_constraint_violations(self):
        """Test validation of object items with constraint violations."""
        properties = {
            "name": {"type": "string", "required": True, "min_length": 3},
            "quantity": {"type": "integer", "required": True, "min_value": 1},
            "price": {"type": "number", "required": False, "min_value": 0}
        }
        
        invalid_item = {
            "name": "AB",  # Too short
            "quantity": 0,  # Below minimum
            "price": -10.0  # Below minimum
        }
        
        errors = FormGenerator._validate_object_item("line_items[0]", invalid_item, properties)
        
        assert len(errors) == 3
        error_text = " ".join(errors)
        assert "line_items[0].name" in error_text
        assert "must be at least 3 characters" in error_text
        assert "line_items[0].quantity" in error_text
        assert "must be at least 1" in error_text
        assert "line_items[0].price" in error_text
        assert "must be at least 0" in error_text
    
    def test_validate_object_item_optional_fields(self):
        """Test validation of object items with missing optional fields."""
        properties = {
            "name": {"type": "string", "required": True, "min_length": 1},
            "quantity": {"type": "integer", "required": True, "min_value": 1},
            "price": {"type": "number", "required": False, "min_value": 0},
            "is_active": {"type": "boolean", "required": False}
        }
        
        valid_item = {
            "name": "Item 1",
            "quantity": 5
            # Missing optional fields: price, is_active
        }
        
        errors = FormGenerator._validate_object_item("line_items[0]", valid_item, properties)
        assert errors == []  # Should be valid since optional fields are missing
    
    def test_validate_object_array_multiple_objects(self):
        """Test validation of entire object arrays."""
        properties = {
            "name": {"type": "string", "required": True, "min_length": 1},
            "quantity": {"type": "integer", "required": True, "min_value": 1}
        }
        
        items_config = {"properties": properties}
        
        # Valid array
        valid_array = [
            {"name": "Item 1", "quantity": 5},
            {"name": "Item 2", "quantity": 10}
        ]
        errors = FormGenerator._validate_object_array("line_items", valid_array, items_config)
        assert errors == []
        
        # Array with mixed valid/invalid objects
        mixed_array = [
            {"name": "Item 1", "quantity": 5},  # Valid
            {"name": "", "quantity": -1}  # Invalid - empty name and negative quantity
        ]
        
        errors = FormGenerator._validate_object_array("line_items", mixed_array, items_config)
        assert len(errors) == 2  # Empty name and negative quantity
        
        # Check error messages contain array indices
        error_text = " ".join(errors)
        assert "line_items[1]" in error_text
    
    def test_validate_object_array_empty(self):
        """Test validation of empty object arrays."""
        properties = {
            "name": {"type": "string", "required": True}
        }
        items_config = {"properties": properties}
        
        errors = FormGenerator._validate_object_array("line_items", [], items_config)
        assert errors == []
    
    def test_validate_object_array_with_none_values(self):
        """Test validation of object arrays with None values."""
        properties = {
            "name": {"type": "string", "required": True},
            "quantity": {"type": "integer", "required": True, "min_value": 1}
        }
        items_config = {"properties": properties}
        
        array_with_none = [
            {
                "name": "Item 1",
                "quantity": None  # None value for required field
            }
        ]
        
        errors = FormGenerator._validate_object_array("line_items", array_with_none, items_config)
        assert len(errors) == 1
        assert "quantity" in errors[0]
        assert "is required" in errors[0]
    
    @patch('utils.form_generator.FormGenerator._render_object_array_editor')
    def test_render_array_editor_delegates_to_object(self, mock_object_editor):
        """Test that _render_array_editor delegates to object editor for object arrays."""
        mock_object_editor.return_value = [{"name": "Item 1"}]
        
        field_config = {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {"name": {"type": "string"}}
            }
        }
        current_value = []
        
        result = FormGenerator._render_array_editor("test_field", field_config, current_value)
        
        assert result == [{"name": "Item 1"}]
        mock_object_editor.assert_called_once_with("test_field", field_config, current_value)


class TestFormGeneratorObjectArrayIntegration:
    """Integration tests for object arrays with existing form generation workflow."""
    
    def setup_method(self):
        """Set up test environment before each test."""
        if hasattr(st, 'session_state'):
            st.session_state.clear()
    
    def teardown_method(self):
        """Clean up after each test."""
        if hasattr(st, 'session_state'):
            st.session_state.clear()
    
    @patch('utils.form_generator.FormGenerator._render_object_array_editor')
    @patch('streamlit.form')
    @patch('streamlit.subheader')
    @patch('streamlit.columns')
    @patch('streamlit.form_submit_button')
    def test_render_dynamic_form_with_object_arrays(self, mock_submit_button, mock_columns, 
                                                  mock_subheader, mock_form, mock_object_editor):
        """Test rendering dynamic form with object array fields."""
        # Setup mocks
        mock_form.return_value.__enter__ = MagicMock()
        mock_form.return_value.__exit__ = MagicMock()
        mock_columns.return_value = [MagicMock(), MagicMock()]
        mock_submit_button.return_value = False
        mock_object_editor.return_value = [{"name": "Item 1", "quantity": 5}]
        
        # Test schema with object array
        schema = {
            "fields": {
                "supplier_name": {
                    "type": "string",
                    "label": "Supplier Name",
                    "required": True
                },
                "line_items": {
                    "type": "array",
                    "label": "Line Items",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string", "required": True},
                            "quantity": {"type": "integer", "required": True, "min_value": 1}
                        }
                    }
                }
            }
        }
        
        current_data = {
            "supplier_name": "Test Company",
            "line_items": [{"name": "Item 1", "quantity": 5}]
        }
        
        # Call the method
        result = FormGenerator.render_dynamic_form(schema, current_data)
        
        # Verify object array editor was called
        mock_object_editor.assert_called_once()
        
        # Verify result contains array data
        assert "line_items" in result
        assert result["line_items"] == [{"name": "Item 1", "quantity": 5}]
    
    @patch('utils.submission_handler.SubmissionHandler._validate_submission_data')
    @patch('streamlit.form')
    @patch('streamlit.subheader')
    @patch('streamlit.columns')
    @patch('streamlit.form_submit_button')
    @patch('streamlit.success')
    def test_validation_integration_with_object_arrays(self, mock_success, mock_submit_button, 
                                                     mock_columns, mock_subheader, mock_form, 
                                                     mock_validate):
        """Test validation integration with object array fields."""
        # Setup mocks
        mock_form.return_value.__enter__ = MagicMock()
        mock_form.return_value.__exit__ = MagicMock()
        mock_columns.return_value = [MagicMock(), MagicMock()]
        mock_submit_button.return_value = True  # Simulate validate button click
        mock_validate.return_value = []  # No validation errors
        
        # Test schema with object array
        schema = {
            "fields": {
                "line_items": {
                    "type": "array",
                    "label": "Line Items",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string", "required": True, "min_length": 1},
                            "quantity": {"type": "integer", "required": True, "min_value": 1}
                        }
                    }
                }
            }
        }
        
        current_data = {"line_items": [{"name": "Item 1", "quantity": 5}]}
        
        # Mock SessionManager methods
        with patch.object(SessionManager, 'get_model_class', return_value=MagicMock()):
            with patch.object(SessionManager, 'set_form_data'):
                with patch.object(SessionManager, 'clear_validation_errors'):
                    # Call the method
                    result = FormGenerator.render_dynamic_form(schema, current_data)
                    
                    # Verify validation was called
                    mock_validate.assert_called_once()
                    mock_success.assert_called_with("Data validated successfully")
    
    @patch('utils.submission_handler.SubmissionHandler._validate_submission_data')
    @patch('streamlit.form')
    @patch('streamlit.subheader')
    @patch('streamlit.columns')
    @patch('streamlit.form_submit_button')
    @patch('streamlit.error')
    def test_validation_errors_with_object_arrays(self, mock_error, mock_submit_button, 
                                                 mock_columns, mock_subheader, mock_form, 
                                                 mock_validate):
        """Test validation error handling with object array fields."""
        # Setup mocks
        mock_form.return_value.__enter__ = MagicMock()
        mock_form.return_value.__exit__ = MagicMock()
        mock_columns.return_value = [MagicMock(), MagicMock()]
        mock_submit_button.return_value = True  # Simulate validate button click
        mock_validate.return_value = [
            "line_items[0].name is required",
            "line_items[1].quantity must be at least 1"
        ]
        
        # Test schema with object array
        schema = {
            "fields": {
                "line_items": {
                    "type": "array",
                    "label": "Line Items",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string", "required": True, "min_length": 1},
                            "quantity": {"type": "integer", "required": True, "min_value": 1}
                        }
                    }
                }
            }
        }
        
        current_data = {"line_items": [{"name": "", "quantity": 5}, {"name": "Item 2", "quantity": 0}]}
        
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
    
    def test_collect_current_form_data_with_object_arrays(self):
        """Test collecting form data with object array fields."""
        # Setup session state with array data
        st.session_state["field_line_items"] = None  # Regular field value
        st.session_state["array_line_items"] = [
            {"name": "Item 1", "quantity": 5},
            {"name": "Item 2", "quantity": 10}
        ]  # Array field value
        
        schema = {
            "fields": {
                "line_items": {
                    "type": "array",
                    "label": "Line Items",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "quantity": {"type": "integer"}
                        }
                    }
                }
            }
        }
        
        # Call the method
        result = FormGenerator.collect_current_form_data(schema)
        
        # Verify array data was collected
        assert "line_items" in result
        assert result["line_items"] == [
            {"name": "Item 1", "quantity": 5},
            {"name": "Item 2", "quantity": 10}
        ]
    
    def test_collect_current_form_data_with_json_object_array(self):
        """Test collecting form data with JSON-encoded object array fields."""
        # Setup session state with JSON array data
        st.session_state["field_line_items"] = None
        st.session_state["json_array_line_items"] = '[{"name": "Item 1", "quantity": 5}, {"name": "Item 2", "quantity": 10}]'
        
        schema = {
            "fields": {
                "line_items": {
                    "type": "array",
                    "label": "Line Items",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "quantity": {"type": "integer"}
                        }
                    }
                }
            }
        }
        
        # Call the method
        result = FormGenerator.collect_current_form_data(schema)
        
        # Verify JSON array data was parsed and collected
        assert "line_items" in result
        assert result["line_items"] == [
            {"name": "Item 1", "quantity": 5},
            {"name": "Item 2", "quantity": 10}
        ]


class TestFormGeneratorObjectArrayRealWorldData:
    """Test object array functionality with real purchase order data."""
    
    def setup_method(self):
        """Set up test environment before each test."""
        if hasattr(st, 'session_state'):
            st.session_state.clear()
    
    def teardown_method(self):
        """Clean up after each test."""
        if hasattr(st, 'session_state'):
            st.session_state.clear()
    
    def test_purchase_order_line_items(self):
        """Test object array functionality with purchase order line items."""
        # Real purchase order data structure
        properties = {
            "item_code": {
                "type": "string",
                "label": "Item Code",
                "required": True,
                "min_length": 3,
                "max_length": 10
            },
            "description": {
                "type": "string",
                "label": "Description",
                "required": True,
                "min_length": 1
            },
            "quantity": {
                "type": "integer",
                "label": "Quantity",
                "required": True,
                "min_value": 1
            },
            "unit_price": {
                "type": "number",
                "label": "Unit Price",
                "required": True,
                "min_value": 0
            },
            "total_price": {
                "type": "number",
                "label": "Total Price",
                "required": False
            }
        }
        
        # Test valid line items
        valid_items = [
            {
                "item_code": "ITM001",
                "description": "Office Chair",
                "quantity": 5,
                "unit_price": 150.00,
                "total_price": 750.00
            },
            {
                "item_code": "ITM002",
                "description": "Desk Lamp",
                "quantity": 10,
                "unit_price": 45.00,
                "total_price": 450.00
            }
        ]
        
        items_config = {"properties": properties}
        errors = FormGenerator._validate_object_array("line_items", valid_items, items_config)
        assert len(errors) == 0
        
        # Test default object creation
        default_obj = FormGenerator._create_default_object(properties)
        assert default_obj["item_code"] == ""
        assert default_obj["description"] == ""
        assert default_obj["quantity"] == 1  # Respects min_value: 1
        assert default_obj["unit_price"] == 0.0  # Respects min_value: 0
        assert default_obj["total_price"] == 0.0
    
    def test_purchase_order_with_constraints(self):
        """Test object array with realistic constraints for purchase orders."""
        properties = {
            "item_code": {
                "type": "string",
                "required": True,
                "pattern": "^ITM\\d{3}$",  # Pattern like "ITM001"
                "min_length": 6,
                "max_length": 6
            },
            "quantity": {
                "type": "integer",
                "required": True,
                "min_value": 1,
                "max_value": 1000
            },
            "unit_price": {
                "type": "number",
                "required": True,
                "min_value": 0.01,
                "max_value": 10000.00
            }
        }
        
        # Test valid data
        valid_data = [
            {"item_code": "ITM001", "quantity": 5, "unit_price": 150.00},
            {"item_code": "ITM002", "quantity": 10, "unit_price": 45.00}
        ]
        items_config = {"properties": properties}
        errors = FormGenerator._validate_object_array("line_items", valid_data, items_config)
        assert len(errors) == 0
        
        # Test invalid data
        invalid_data = [
            {"item_code": "INVALID", "quantity": 0, "unit_price": -10.00},  # All constraints violated
            {"item_code": "ITM999", "quantity": 1001, "unit_price": 20000.00}  # Max constraints violated
        ]
        errors = FormGenerator._validate_object_array("line_items", invalid_data, items_config)
        assert len(errors) > 0
        
        # Check that error messages contain array indices and property paths
        error_text = " ".join(errors)
        assert "line_items[0]" in error_text
        assert "line_items[1]" in error_text
    
    def test_mixed_property_types_validation(self):
        """Test validation with mixed property types in object arrays."""
        properties = {
            "name": {"type": "string", "required": True, "min_length": 1},
            "count": {"type": "integer", "required": True, "min_value": 0},
            "price": {"type": "number", "required": False, "min_value": 0},
            "active": {"type": "boolean", "required": False},
            "date": {"type": "date", "required": False}
        }
        
        # Valid mixed object
        valid_object = [
            {
                "name": "Test Item",
                "count": 5,
                "price": 99.99,
                "active": True,
                "date": "2024-01-15"
            }
        ]
        
        items_config = {"properties": properties}
        errors = FormGenerator._validate_object_array("items", valid_object, items_config)
        assert len(errors) == 0
        
        # Invalid mixed object
        invalid_object = [
            {
                "name": "",  # Empty required string
                "count": -1,  # Below minimum
                "price": -10,  # Below minimum
                "active": "not_boolean",  # Wrong type (will be caught by scalar validation)
                "date": "invalid-date"  # Invalid date format
            }
        ]
        
        errors = FormGenerator._validate_object_array("items", invalid_object, items_config)
        assert len(errors) > 0  # Should have multiple validation errors
    
    def test_pandas_dependency_handling(self):
        """Test that pandas dependency is properly handled for NaN cleanup."""
        # Test with pandas NaN values
        dirty_array = [
            {
                "name": "Item 1",
                "quantity": np.nan,
                "price": pd.NA
            }
        ]
        
        cleaned_array = FormGenerator._clean_object_array(dirty_array)
        
        # Verify NaN values are cleaned
        assert cleaned_array[0]["name"] == "Item 1"
        assert cleaned_array[0]["quantity"] is None
        assert cleaned_array[0]["price"] is None
    
    def test_manual_row_operations_integration(self):
        """Test manual row operations integration with SubmissionHandler."""
        # This test verifies that the enhanced object array editor integrates
        # properly with the existing validation and submission workflow
        
        properties = {
            "item_code": {"type": "string", "required": True},
            "quantity": {"type": "integer", "required": True, "min_value": 1}
        }
        
        # Test data that would come from manual row operations
        test_data = [
            {"item_code": "ITM001", "quantity": 5},
            {"item_code": "ITM002", "quantity": 10}
        ]
        
        # Test validation integration
        items_config = {"properties": properties}
        errors = FormGenerator._validate_object_array("line_items", test_data, items_config)
        assert len(errors) == 0
        
        # Test that cleaned data maintains integrity
        cleaned_data = FormGenerator._clean_object_array(test_data)
        assert len(cleaned_data) == 2
        assert cleaned_data[0]["item_code"] == "ITM001"
        assert cleaned_data[1]["quantity"] == 10


if __name__ == "__main__":
    # Run the tests
    pytest.main([__file__, "-v"])