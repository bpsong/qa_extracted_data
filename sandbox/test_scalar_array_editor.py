"""
Unit tests for sandbox scalar array editor functionality

Tests cover add/remove functionality, validation with constraints,
and edge cases for various data types.
"""

import unittest
from unittest.mock import Mock, patch
import sys
import os
from datetime import datetime, date

# Add sandbox to path for imports
sys.path.insert(0, os.path.dirname(__file__))

from array_sandbox_app import (
    get_default_value_for_type,
    validate_scalar_array,
    validate_scalar_item,
    render_scalar_input
)


class TestScalarArrayEditor(unittest.TestCase):
    """Test cases for scalar array editor functionality"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.string_config = {
            "type": "string",
            "min_length": 3,
            "max_length": 20,
            "pattern": "^[A-Z0-9]+$"
        }
        
        self.number_config = {
            "type": "number",
            "min_value": 0,
            "max_value": 1000,
            "step": 0.01
        }
        
        self.integer_config = {
            "type": "integer", 
            "min_value": 1,
            "max_value": 100,
            "step": 1
        }
        
        self.boolean_config = {
            "type": "boolean"
        }
        
        self.date_config = {
            "type": "date"
        }

    def test_get_default_value_for_type(self):
        """Test default value generation for different types"""
        # String default
        self.assertEqual(get_default_value_for_type("string", {}), "")
        
        # Number default
        self.assertEqual(get_default_value_for_type("number", {}), 0.0)
        
        # Integer default
        self.assertEqual(get_default_value_for_type("integer", {}), 0)
        
        # Boolean default
        self.assertEqual(get_default_value_for_type("boolean", {}), False)
        
        # Date default (should be today's date string)
        date_default = get_default_value_for_type("date", {})
        self.assertIsInstance(date_default, str)
        self.assertEqual(len(date_default), 10)  # YYYY-MM-DD format
        
        # Unknown type default
        self.assertEqual(get_default_value_for_type("unknown", {}), "")

    def test_validate_scalar_item_string_valid(self):
        """Test string validation with valid values"""
        # Valid string
        errors = validate_scalar_item("test[0]", "ABC123", "string", self.string_config)
        self.assertEqual(errors, [])
        
        # Minimum length boundary
        errors = validate_scalar_item("test[0]", "ABC", "string", self.string_config)
        self.assertEqual(errors, [])
        
        # Maximum length boundary
        errors = validate_scalar_item("test[0]", "A" * 20, "string", self.string_config)
        self.assertEqual(errors, [])

    def test_validate_scalar_item_string_invalid(self):
        """Test string validation with invalid values"""
        # Too short
        errors = validate_scalar_item("test[0]", "AB", "string", self.string_config)
        self.assertEqual(len(errors), 1)
        self.assertIn("must be at least 3 characters", errors[0])
        
        # Too long
        errors = validate_scalar_item("test[0]", "A" * 21, "string", self.string_config)
        self.assertEqual(len(errors), 1)
        self.assertIn("must be no more than 20 characters", errors[0])
        
        # Pattern mismatch
        errors = validate_scalar_item("test[0]", "abc123", "string", self.string_config)
        self.assertEqual(len(errors), 1)
        self.assertIn("must match pattern", errors[0])
        
        # Wrong type
        errors = validate_scalar_item("test[0]", 123, "string", self.string_config)
        self.assertEqual(len(errors), 1)
        self.assertIn("must be a string", errors[0])

    def test_validate_scalar_item_number_valid(self):
        """Test number validation with valid values"""
        # Valid number
        errors = validate_scalar_item("test[0]", 50.5, "number", self.number_config)
        self.assertEqual(errors, [])
        
        # Minimum boundary
        errors = validate_scalar_item("test[0]", 0, "number", self.number_config)
        self.assertEqual(errors, [])
        
        # Maximum boundary
        errors = validate_scalar_item("test[0]", 1000, "number", self.number_config)
        self.assertEqual(errors, [])

    def test_validate_scalar_item_number_invalid(self):
        """Test number validation with invalid values"""
        # Below minimum
        errors = validate_scalar_item("test[0]", -1, "number", self.number_config)
        self.assertEqual(len(errors), 1)
        self.assertIn("must be at least 0", errors[0])
        
        # Above maximum
        errors = validate_scalar_item("test[0]", 1001, "number", self.number_config)
        self.assertEqual(len(errors), 1)
        self.assertIn("must be no more than 1000", errors[0])
        
        # Invalid type
        errors = validate_scalar_item("test[0]", "not_a_number", "number", self.number_config)
        self.assertEqual(len(errors), 1)
        self.assertIn("must be a valid number", errors[0])

    def test_validate_scalar_item_integer_valid(self):
        """Test integer validation with valid values"""
        # Valid integer
        errors = validate_scalar_item("test[0]", 50, "integer", self.integer_config)
        self.assertEqual(errors, [])
        
        # Minimum boundary
        errors = validate_scalar_item("test[0]", 1, "integer", self.integer_config)
        self.assertEqual(errors, [])
        
        # Maximum boundary
        errors = validate_scalar_item("test[0]", 100, "integer", self.integer_config)
        self.assertEqual(errors, [])

    def test_validate_scalar_item_integer_invalid(self):
        """Test integer validation with invalid values"""
        # Below minimum
        errors = validate_scalar_item("test[0]", 0, "integer", self.integer_config)
        self.assertEqual(len(errors), 1)
        self.assertIn("must be at least 1", errors[0])
        
        # Above maximum
        errors = validate_scalar_item("test[0]", 101, "integer", self.integer_config)
        self.assertEqual(len(errors), 1)
        self.assertIn("must be no more than 100", errors[0])
        
        # Invalid type
        errors = validate_scalar_item("test[0]", "not_an_integer", "integer", self.integer_config)
        self.assertEqual(len(errors), 1)
        self.assertIn("must be a valid integer", errors[0])

    def test_validate_scalar_item_boolean_valid(self):
        """Test boolean validation with valid values"""
        # Valid boolean values
        errors = validate_scalar_item("test[0]", True, "boolean", self.boolean_config)
        self.assertEqual(errors, [])
        
        errors = validate_scalar_item("test[0]", False, "boolean", self.boolean_config)
        self.assertEqual(errors, [])

    def test_validate_scalar_item_boolean_invalid(self):
        """Test boolean validation with invalid values"""
        # Invalid type
        errors = validate_scalar_item("test[0]", "true", "boolean", self.boolean_config)
        self.assertEqual(len(errors), 1)
        self.assertIn("must be a boolean", errors[0])
        
        errors = validate_scalar_item("test[0]", 1, "boolean", self.boolean_config)
        self.assertEqual(len(errors), 1)
        self.assertIn("must be a boolean", errors[0])

    def test_validate_scalar_item_date_valid(self):
        """Test date validation with valid values"""
        # Valid date string
        errors = validate_scalar_item("test[0]", "2024-01-15", "date", self.date_config)
        self.assertEqual(errors, [])
        
        # Valid date object
        errors = validate_scalar_item("test[0]", date(2024, 1, 15), "date", self.date_config)
        self.assertEqual(errors, [])

    def test_validate_scalar_item_date_invalid(self):
        """Test date validation with invalid values"""
        # Invalid date format
        errors = validate_scalar_item("test[0]", "2024/01/15", "date", self.date_config)
        self.assertEqual(len(errors), 1)
        self.assertIn("must be a valid date in YYYY-MM-DD format", errors[0])
        
        # Invalid date string
        errors = validate_scalar_item("test[0]", "not-a-date", "date", self.date_config)
        self.assertEqual(len(errors), 1)
        self.assertIn("must be a valid date in YYYY-MM-DD format", errors[0])
        
        # Invalid type
        errors = validate_scalar_item("test[0]", 20240115, "date", self.date_config)
        self.assertEqual(len(errors), 1)
        self.assertIn("must be a valid date", errors[0])

    def test_validate_scalar_array_multiple_items(self):
        """Test validation of entire scalar arrays"""
        # Valid array
        valid_array = ["ABC123", "DEF456", "GHI789"]
        errors = validate_scalar_array("serial_numbers", valid_array, self.string_config)
        self.assertEqual(errors, [])
        
        # Mixed valid/invalid array
        mixed_array = ["ABC123", "ab", "XYZ999"]  # Second item too short and wrong pattern
        errors = validate_scalar_array("serial_numbers", mixed_array, self.string_config)
        self.assertEqual(len(errors), 2)  # Both min_length and pattern violations
        error_text = " ".join(errors)
        self.assertIn("serial_numbers[1]", error_text)
        
        # Multiple errors
        invalid_array = ["AB", "xyz", ""]  # All invalid
        errors = validate_scalar_array("serial_numbers", invalid_array, self.string_config)
        self.assertEqual(len(errors), 3)

    def test_validate_scalar_array_empty(self):
        """Test validation of empty arrays"""
        errors = validate_scalar_array("test_field", [], self.string_config)
        self.assertEqual(errors, [])

    def test_validate_scalar_array_edge_cases(self):
        """Test edge cases for array validation"""
        # Array with None values
        array_with_none = ["ABC123", None, "DEF456"]
        errors = validate_scalar_array("test_field", array_with_none, self.string_config)
        self.assertGreater(len(errors), 0)  # Should have validation errors
        
        # Array with mixed types
        mixed_type_array = ["ABC123", 456, True]
        errors = validate_scalar_array("test_field", mixed_type_array, self.string_config)
        self.assertGreater(len(errors), 0)  # Should have type validation errors

    @patch('streamlit.text_input')
    def test_render_scalar_input_string(self, mock_text_input):
        """Test rendering string input widget"""
        mock_text_input.return_value = "TEST123"
        
        result = render_scalar_input("test_field[0]", "string", "initial", {}, "test_key")
        
        mock_text_input.assert_called_once()
        self.assertEqual(result, "TEST123")

    @patch('streamlit.number_input')
    def test_render_scalar_input_number(self, mock_number_input):
        """Test rendering number input widget"""
        mock_number_input.return_value = 42.5
        
        result = render_scalar_input("test_field[0]", "number", 10.0, self.number_config, "test_key")
        
        mock_number_input.assert_called_once()
        self.assertEqual(result, 42.5)

    @patch('streamlit.number_input')
    def test_render_scalar_input_integer(self, mock_number_input):
        """Test rendering integer input widget"""
        mock_number_input.return_value = 42.0
        
        result = render_scalar_input("test_field[0]", "integer", 10, self.integer_config, "test_key")
        
        mock_number_input.assert_called_once()
        self.assertEqual(result, 42)  # Should be converted to int

    @patch('streamlit.checkbox')
    def test_render_scalar_input_boolean(self, mock_checkbox):
        """Test rendering boolean input widget"""
        mock_checkbox.return_value = True
        
        result = render_scalar_input("test_field[0]", "boolean", False, {}, "test_key")
        
        mock_checkbox.assert_called_once()
        self.assertEqual(result, True)

    @patch('streamlit.date_input')
    def test_render_scalar_input_date(self, mock_date_input):
        """Test rendering date input widget"""
        test_date = date(2024, 1, 15)
        mock_date_input.return_value = test_date
        
        result = render_scalar_input("test_field[0]", "date", "2024-01-15", {}, "test_key")
        
        mock_date_input.assert_called_once()
        self.assertEqual(result, "2024-01-15")

    def test_constraint_combinations(self):
        """Test various constraint combinations"""
        # String with only min_length
        config = {"type": "string", "min_length": 5}
        errors = validate_scalar_item("test[0]", "hello", "string", config)
        self.assertEqual(errors, [])
        
        errors = validate_scalar_item("test[0]", "hi", "string", config)
        self.assertEqual(len(errors), 1)
        
        # Number with only max_value
        config = {"type": "number", "max_value": 100}
        errors = validate_scalar_item("test[0]", 50, "number", config)
        self.assertEqual(errors, [])
        
        errors = validate_scalar_item("test[0]", 150, "number", config)
        self.assertEqual(len(errors), 1)
        
        # String with pattern only
        config = {"type": "string", "pattern": "^[0-9]+$"}
        errors = validate_scalar_item("test[0]", "12345", "string", config)
        self.assertEqual(errors, [])
        
        errors = validate_scalar_item("test[0]", "abc123", "string", config)
        self.assertEqual(len(errors), 1)


class TestScalarArrayEditorIntegration(unittest.TestCase):
    """Integration tests for scalar array editor components"""
    
    def test_full_validation_workflow(self):
        """Test complete validation workflow with realistic data"""
        # Insurance document serial numbers
        serial_config = {
            "type": "string",
            "min_length": 3,
            "max_length": 20,
            "pattern": "^[A-Z0-9]+$"
        }
        
        # Valid serial numbers
        valid_serials = ["SN001", "SN002", "ABC123XYZ"]
        errors = validate_scalar_array("serial_numbers", valid_serials, serial_config)
        self.assertEqual(errors, [])
        
        # Invalid serial numbers
        invalid_serials = ["SN001", "sn002", ""]  # lowercase and empty
        errors = validate_scalar_array("serial_numbers", invalid_serials, serial_config)
        self.assertEqual(len(errors), 2)
        
        # Check error messages contain array indices
        error_text = " ".join(errors)
        self.assertIn("serial_numbers[1]", error_text)
        self.assertIn("serial_numbers[2]", error_text)

    def test_tags_validation_workflow(self):
        """Test tag validation with different constraints"""
        tag_config = {
            "type": "string",
            "min_length": 1,
            "max_length": 50
        }
        
        # Valid tags
        valid_tags = ["insurance", "equipment", "annual-policy"]
        errors = validate_scalar_array("tags", valid_tags, tag_config)
        self.assertEqual(errors, [])
        
        # Invalid tags
        invalid_tags = ["", "a" * 51, "valid-tag"]  # empty and too long
        errors = validate_scalar_array("tags", invalid_tags, tag_config)
        self.assertEqual(len(errors), 2)

    def test_numeric_array_validation(self):
        """Test numeric array validation scenarios"""
        price_config = {
            "type": "number",
            "min_value": 0,
            "max_value": 10000
        }
        
        # Valid prices
        valid_prices = [100.50, 250.00, 999.99]
        errors = validate_scalar_array("prices", valid_prices, price_config)
        self.assertEqual(errors, [])
        
        # Invalid prices
        invalid_prices = [-10, 15000, "not_a_number"]
        errors = validate_scalar_array("prices", invalid_prices, price_config)
        self.assertEqual(len(errors), 3)


if __name__ == "__main__":
    # Run the tests
    unittest.main(verbosity=2)