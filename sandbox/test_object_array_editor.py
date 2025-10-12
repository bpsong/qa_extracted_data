"""
Unit tests for sandbox object array editor functionality

Tests cover CRUD operations on object arrays, validation of object properties,
and column configuration for different property types.
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
import sys
import os
from datetime import datetime, date
import pandas as pd
import numpy as np

# Add sandbox to path for imports
sys.path.insert(0, os.path.dirname(__file__))

from array_sandbox_app import (
    generate_column_config,
    create_default_object,
    clean_object_array,
    validate_object_array,
    validate_object_item,
    render_object_array_editor
)


class TestObjectArrayEditor(unittest.TestCase):
    """Test cases for object array editor functionality"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.line_item_properties = {
            "item_code": {
                "type": "string",
                "label": "Item Code",
                "required": True,
                "help": "Product item code"
            },
            "description": {
                "type": "string",
                "label": "Description",
                "required": True,
                "help": "Item description"
            },
            "quantity": {
                "type": "integer",
                "label": "Quantity",
                "required": True,
                "help": "Number of items",
                "min_value": 1
            },
            "unit_price": {
                "type": "number",
                "label": "Unit Price",
                "required": True,
                "help": "Price per unit",
                "min_value": 0
            },
            "total_price": {
                "type": "number",
                "label": "Total Price",
                "required": False,
                "help": "Total price for this line item"
            },
            "is_taxable": {
                "type": "boolean",
                "label": "Taxable",
                "required": False,
                "help": "Whether item is taxable"
            },
            "delivery_date": {
                "type": "date",
                "label": "Delivery Date",
                "required": False,
                "help": "Expected delivery date"
            }
        }
        
        self.sample_line_items = [
            {
                "item_code": "ITM001",
                "description": "Office Chair",
                "quantity": 5,
                "unit_price": 150.00,
                "total_price": 750.00,
                "is_taxable": True,
                "delivery_date": "2024-02-01"
            },
            {
                "item_code": "ITM002",
                "description": "Desk Lamp",
                "quantity": 10,
                "unit_price": 45.00,
                "total_price": 450.00,
                "is_taxable": True,
                "delivery_date": "2024-02-15"
            }
        ]

    def test_generate_column_config_string(self):
        """Test column configuration generation for string properties"""
        properties = {
            "name": {
                "type": "string",
                "label": "Name",
                "help": "Item name",
                "required": True,
                "max_length": 100
            }
        }
        
        config = generate_column_config(properties)
        
        self.assertIn("name", config)
        # We can't directly test st.column_config objects, but we can verify the function runs
        self.assertIsNotNone(config["name"])

    def test_generate_column_config_number(self):
        """Test column configuration generation for number properties"""
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
        
        config = generate_column_config(properties)
        
        self.assertIn("price", config)
        self.assertIsNotNone(config["price"])

    def test_generate_column_config_integer(self):
        """Test column configuration generation for integer properties"""
        properties = {
            "count": {
                "type": "integer",
                "label": "Count",
                "help": "Item count",
                "required": True,
                "min_value": 1,
                "max_value": 100,
                "step": 1
            }
        }
        
        config = generate_column_config(properties)
        
        self.assertIn("count", config)
        self.assertIsNotNone(config["count"])

    def test_generate_column_config_boolean(self):
        """Test column configuration generation for boolean properties"""
        properties = {
            "active": {
                "type": "boolean",
                "label": "Active",
                "help": "Is active",
                "required": False
            }
        }
        
        config = generate_column_config(properties)
        
        self.assertIn("active", config)
        self.assertIsNotNone(config["active"])

    def test_generate_column_config_date(self):
        """Test column configuration generation for date properties"""
        properties = {
            "due_date": {
                "type": "date",
                "label": "Due Date",
                "help": "Due date",
                "required": False
            }
        }
        
        config = generate_column_config(properties)
        
        self.assertIn("due_date", config)
        self.assertIsNotNone(config["due_date"])

    def test_generate_column_config_unknown_type(self):
        """Test column configuration generation for unknown property types"""
        properties = {
            "unknown_field": {
                "type": "unknown_type",
                "label": "Unknown Field",
                "help": "Unknown field type",
                "required": False
            }
        }
        
        config = generate_column_config(properties)
        
        self.assertIn("unknown_field", config)
        self.assertIsNotNone(config["unknown_field"])

    def test_create_default_object(self):
        """Test creation of default objects with appropriate default values"""
        default_obj = create_default_object(self.line_item_properties)
        
        # Check that all properties are present
        for prop_name in self.line_item_properties.keys():
            self.assertIn(prop_name, default_obj)
        
        # Check default values by type
        self.assertEqual(default_obj["item_code"], "")  # string
        self.assertEqual(default_obj["description"], "")  # string
        self.assertEqual(default_obj["quantity"], 0)  # integer
        self.assertEqual(default_obj["unit_price"], 0.0)  # number
        self.assertEqual(default_obj["total_price"], 0.0)  # number
        self.assertEqual(default_obj["is_taxable"], False)  # boolean
        self.assertIsInstance(default_obj["delivery_date"], str)  # date (as string)

    def test_clean_object_array_with_nan(self):
        """Test cleaning object array with NaN values"""
        # Create array with pandas NaN values
        dirty_array = [
            {
                "item_code": "ITM001",
                "quantity": np.nan,
                "unit_price": 150.0,
                "is_taxable": True
            },
            {
                "item_code": pd.NA,
                "quantity": 5,
                "unit_price": np.nan,
                "is_taxable": False
            }
        ]
        
        cleaned_array = clean_object_array(dirty_array)
        
        # Check that NaN values are converted to None
        self.assertEqual(cleaned_array[0]["item_code"], "ITM001")
        self.assertIsNone(cleaned_array[0]["quantity"])
        self.assertEqual(cleaned_array[0]["unit_price"], 150.0)
        self.assertEqual(cleaned_array[0]["is_taxable"], True)
        
        self.assertIsNone(cleaned_array[1]["item_code"])
        self.assertEqual(cleaned_array[1]["quantity"], 5)
        self.assertIsNone(cleaned_array[1]["unit_price"])
        self.assertEqual(cleaned_array[1]["is_taxable"], False)

    def test_clean_object_array_with_numpy_types(self):
        """Test cleaning object array with numpy types"""
        dirty_array = [
            {
                "quantity": np.int64(5),
                "unit_price": np.float64(150.5),
                "item_code": "ITM001"
            }
        ]
        
        cleaned_array = clean_object_array(dirty_array)
        
        # Check that numpy types are converted to Python types
        self.assertEqual(cleaned_array[0]["quantity"], 5)
        self.assertIsInstance(cleaned_array[0]["quantity"], int)
        self.assertEqual(cleaned_array[0]["unit_price"], 150.5)
        self.assertIsInstance(cleaned_array[0]["unit_price"], float)
        self.assertEqual(cleaned_array[0]["item_code"], "ITM001")

    def test_validate_object_item_valid(self):
        """Test validation of valid object items"""
        valid_item = {
            "item_code": "ITM001",
            "description": "Office Chair",
            "quantity": 5,
            "unit_price": 150.00,
            "total_price": 750.00,
            "is_taxable": True,
            "delivery_date": "2024-02-01"
        }
        
        errors = validate_object_item("line_items[0]", valid_item, self.line_item_properties)
        self.assertEqual(errors, [])

    def test_validate_object_item_missing_required(self):
        """Test validation of object items with missing required properties"""
        invalid_item = {
            "description": "Office Chair",
            "quantity": 5,
            "unit_price": 150.00
            # Missing required "item_code"
        }
        
        errors = validate_object_item("line_items[0]", invalid_item, self.line_item_properties)
        
        self.assertEqual(len(errors), 1)
        self.assertIn("line_items[0].item_code", errors[0])
        self.assertIn("is required", errors[0])

    def test_validate_object_item_empty_required(self):
        """Test validation of object items with empty required properties"""
        invalid_item = {
            "item_code": "",  # Empty required field
            "description": "Office Chair",
            "quantity": 5,
            "unit_price": 150.00
        }
        
        errors = validate_object_item("line_items[0]", invalid_item, self.line_item_properties)
        
        self.assertEqual(len(errors), 1)
        self.assertIn("line_items[0].item_code", errors[0])
        self.assertIn("is required", errors[0])

    def test_validate_object_item_constraint_violations(self):
        """Test validation of object items with constraint violations"""
        invalid_item = {
            "item_code": "ITM001",
            "description": "Office Chair",
            "quantity": 0,  # Violates min_value: 1
            "unit_price": -10.00  # Violates min_value: 0
        }
        
        errors = validate_object_item("line_items[0]", invalid_item, self.line_item_properties)
        
        self.assertEqual(len(errors), 2)
        error_text = " ".join(errors)
        self.assertIn("line_items[0].quantity", error_text)
        self.assertIn("must be at least 1", error_text)
        self.assertIn("line_items[0].unit_price", error_text)
        self.assertIn("must be at least 0", error_text)

    def test_validate_object_item_optional_fields(self):
        """Test validation of object items with missing optional fields"""
        valid_item = {
            "item_code": "ITM001",
            "description": "Office Chair",
            "quantity": 5,
            "unit_price": 150.00
            # Missing optional fields: total_price, is_taxable, delivery_date
        }
        
        errors = validate_object_item("line_items[0]", valid_item, self.line_item_properties)
        self.assertEqual(errors, [])  # Should be valid since optional fields are missing

    def test_validate_object_array_multiple_objects(self):
        """Test validation of entire object arrays"""
        # Valid array
        errors = validate_object_array("line_items", self.sample_line_items, {"properties": self.line_item_properties})
        self.assertEqual(errors, [])
        
        # Array with mixed valid/invalid objects
        mixed_array = [
            self.sample_line_items[0],  # Valid
            {
                "item_code": "",  # Invalid - empty required field
                "description": "Invalid Item",
                "quantity": -1,  # Invalid - below minimum
                "unit_price": 50.00
            }
        ]
        
        errors = validate_object_array("line_items", mixed_array, {"properties": self.line_item_properties})
        self.assertEqual(len(errors), 2)  # Empty item_code and negative quantity
        
        # Check error messages contain array indices
        error_text = " ".join(errors)
        self.assertIn("line_items[1]", error_text)

    def test_validate_object_array_empty(self):
        """Test validation of empty object arrays"""
        errors = validate_object_array("line_items", [], {"properties": self.line_item_properties})
        self.assertEqual(errors, [])

    def test_validate_object_array_with_none_values(self):
        """Test validation of object arrays with None values"""
        array_with_none = [
            {
                "item_code": "ITM001",
                "description": None,  # None value for required field
                "quantity": 5,
                "unit_price": 150.00
            }
        ]
        
        errors = validate_object_array("line_items", array_with_none, {"properties": self.line_item_properties})
        self.assertEqual(len(errors), 1)
        self.assertIn("description", errors[0])
        self.assertIn("is required", errors[0])

    @patch('streamlit.data_editor')
    @patch('streamlit.button')
    @patch('streamlit.columns')
    @patch('streamlit.container')
    def test_render_object_array_editor_empty_array(self, mock_container, mock_columns, mock_button, mock_data_editor):
        """Test rendering object array editor with empty array"""
        # Mock Streamlit components with proper context manager support
        mock_container.return_value.__enter__ = Mock(return_value=None)
        mock_container.return_value.__exit__ = Mock(return_value=None)
        
        # Mock columns to return context manager objects
        mock_col1 = Mock()
        mock_col1.__enter__ = Mock(return_value=None)
        mock_col1.__exit__ = Mock(return_value=None)
        mock_col2 = Mock()
        mock_col2.__enter__ = Mock(return_value=None)
        mock_col2.__exit__ = Mock(return_value=None)
        mock_columns.return_value = [mock_col1, mock_col2]
        
        mock_button.return_value = False
        
        field_config = {
            "items": {
                "properties": self.line_item_properties
            }
        }
        
        result = render_object_array_editor("line_items", field_config, [])
        
        # Should return empty array
        self.assertEqual(result, [])
        
        # data_editor should not be called for empty arrays
        mock_data_editor.assert_not_called()

    @patch('streamlit.data_editor')
    @patch('streamlit.button')
    @patch('streamlit.columns')
    @patch('streamlit.container')
    @patch('streamlit.info')
    @patch('streamlit.success')
    def test_render_object_array_editor_with_data(self, mock_success, mock_info, mock_container, mock_columns, mock_button, mock_data_editor):
        """Test rendering object array editor with existing data"""
        # Mock Streamlit components with proper context manager support
        mock_container.return_value.__enter__ = Mock(return_value=None)
        mock_container.return_value.__exit__ = Mock(return_value=None)
        
        # Mock columns to return context manager objects
        mock_col1 = Mock()
        mock_col1.__enter__ = Mock(return_value=None)
        mock_col1.__exit__ = Mock(return_value=None)
        mock_col2 = Mock()
        mock_col2.__enter__ = Mock(return_value=None)
        mock_col2.__exit__ = Mock(return_value=None)
        mock_columns.return_value = [mock_col1, mock_col2]
        
        mock_button.return_value = False
        
        # Mock data_editor to return modified DataFrame
        mock_df = pd.DataFrame(self.sample_line_items)
        mock_data_editor.return_value = mock_df
        
        field_config = {
            "items": {
                "properties": self.line_item_properties
            }
        }
        
        result = render_object_array_editor("line_items", field_config, self.sample_line_items)
        
        # Should return the data (cleaned)
        self.assertEqual(len(result), 2)
        
        # data_editor should be called
        mock_data_editor.assert_called_once()

    @patch('streamlit.data_editor')
    @patch('streamlit.button')
    @patch('streamlit.columns')
    @patch('streamlit.container')
    def test_render_object_array_editor_add_row(self, mock_container, mock_columns, mock_button, mock_data_editor):
        """Test adding row to object array editor"""
        # Mock Streamlit components with proper context manager support
        mock_container.return_value.__enter__ = Mock(return_value=None)
        mock_container.return_value.__exit__ = Mock(return_value=None)
        
        # Mock columns to return context manager objects
        mock_col1 = Mock()
        mock_col1.__enter__ = Mock(return_value=None)
        mock_col1.__exit__ = Mock(return_value=None)
        mock_col2 = Mock()
        mock_col2.__enter__ = Mock(return_value=None)
        mock_col2.__exit__ = Mock(return_value=None)
        mock_columns.return_value = [mock_col1, mock_col2]
        
        mock_button.return_value = True  # Simulate button click
        
        # Mock data_editor
        extended_data = self.sample_line_items + [create_default_object(self.line_item_properties)]
        mock_df = pd.DataFrame(extended_data)
        mock_data_editor.return_value = mock_df
        
        field_config = {
            "items": {
                "properties": self.line_item_properties
            }
        }
        
        result = render_object_array_editor("line_items", field_config, self.sample_line_items)
        
        # Should return array with new item added
        self.assertEqual(len(result), 3)


class TestObjectArrayEditorIntegration(unittest.TestCase):
    """Integration tests for object array editor components"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.purchase_order_properties = {
            "item_code": {
                "type": "string",
                "required": True,
                "min_length": 3,
                "max_length": 10
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
                "min_value": 0,
                "max_value": 10000
            }
        }

    def test_full_validation_workflow(self):
        """Test complete validation workflow with realistic data"""
        # Valid purchase order line items
        valid_items = [
            {
                "item_code": "ITM001",
                "quantity": 5,
                "unit_price": 150.00
            },
            {
                "item_code": "ITM002",
                "quantity": 10,
                "unit_price": 45.00
            }
        ]
        
        errors = validate_object_array("line_items", valid_items, {"properties": self.purchase_order_properties})
        self.assertEqual(errors, [])
        
        # Invalid purchase order line items
        invalid_items = [
            {
                "item_code": "IT",  # Too short
                "quantity": 0,  # Below minimum
                "unit_price": 150.00
            },
            {
                "item_code": "ITM002",
                "quantity": 1001,  # Above maximum
                "unit_price": -10.00  # Below minimum
            }
        ]
        
        errors = validate_object_array("line_items", invalid_items, {"properties": self.purchase_order_properties})
        self.assertEqual(len(errors), 4)  # 4 constraint violations
        
        # Check error messages contain array indices and property names
        error_text = " ".join(errors)
        self.assertIn("line_items[0].item_code", error_text)
        self.assertIn("line_items[0].quantity", error_text)
        self.assertIn("line_items[1].quantity", error_text)
        self.assertIn("line_items[1].unit_price", error_text)

    def test_mixed_property_types_validation(self):
        """Test validation with mixed property types"""
        mixed_properties = {
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
        
        errors = validate_object_array("items", valid_object, {"properties": mixed_properties})
        self.assertEqual(errors, [])
        
        # Invalid mixed object
        invalid_object = [
            {
                "name": "",  # Empty required string
                "count": -1,  # Below minimum
                "price": -10,  # Below minimum
                "active": "not_boolean",  # Wrong type
                "date": "invalid-date"  # Invalid date format
            }
        ]
        
        errors = validate_object_array("items", invalid_object, {"properties": mixed_properties})
        self.assertGreater(len(errors), 0)  # Should have multiple validation errors

    def test_default_object_creation_comprehensive(self):
        """Test default object creation with all property types"""
        comprehensive_properties = {
            "text_field": {"type": "string"},
            "number_field": {"type": "number"},
            "integer_field": {"type": "integer"},
            "boolean_field": {"type": "boolean"},
            "date_field": {"type": "date"},
            "unknown_field": {"type": "unknown_type"}
        }
        
        default_obj = create_default_object(comprehensive_properties)
        
        # Verify all fields are present with appropriate defaults
        self.assertEqual(default_obj["text_field"], "")
        self.assertEqual(default_obj["number_field"], 0.0)
        self.assertEqual(default_obj["integer_field"], 0)
        self.assertEqual(default_obj["boolean_field"], False)
        self.assertIsInstance(default_obj["date_field"], str)
        self.assertEqual(default_obj["unknown_field"], "")  # Fallback to string default


if __name__ == "__main__":
    # Run the tests
    unittest.main(verbosity=2)