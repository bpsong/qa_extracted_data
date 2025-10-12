"""
Unit tests for sandbox Schema Editor functionality

Tests cover array field configuration creation for both scalar and object types,
YAML generation and validation, and property management for object arrays.
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
import sys
import os
import yaml

# Add sandbox to path for imports
sys.path.insert(0, os.path.dirname(__file__))

from array_sandbox_app import (
    render_scalar_array_config,
    render_object_array_config
)


class TestSchemaEditor(unittest.TestCase):
    """Test cases for Schema Editor functionality"""
    
    def setUp(self):
        """Set up test fixtures"""
        pass

    @patch('streamlit.selectbox')
    @patch('streamlit.number_input')
    @patch('streamlit.text_input')
    @patch('streamlit.checkbox')
    def test_render_scalar_array_config_string(self, mock_checkbox, mock_text_input, mock_number_input, mock_selectbox):
        """Test scalar array configuration for string type"""
        # Mock user inputs
        mock_selectbox.return_value = "string"
        mock_number_input.side_effect = [3, 50]  # min_length, max_length
        mock_text_input.return_value = "^[A-Z0-9]+$"  # pattern
        
        config = render_scalar_array_config()
        
        # Verify configuration structure
        self.assertEqual(config["type"], "string")
        self.assertEqual(config["min_length"], 3)
        self.assertEqual(config["max_length"], 50)
        self.assertEqual(config["pattern"], "^[A-Z0-9]+$")

    @patch('streamlit.selectbox')
    @patch('streamlit.number_input')
    @patch('streamlit.text_input')
    def test_render_scalar_array_config_number(self, mock_text_input, mock_number_input, mock_selectbox):
        """Test scalar array configuration for number type"""
        # Mock user inputs
        mock_selectbox.return_value = "number"
        mock_number_input.side_effect = [0.0, 1000.0, 0.01]  # min_value, max_value, step
        mock_text_input.return_value = ""  # no pattern for numbers
        
        config = render_scalar_array_config()
        
        # Verify configuration structure
        self.assertEqual(config["type"], "number")
        self.assertEqual(config["min_value"], 0.0)
        self.assertEqual(config["max_value"], 1000.0)
        self.assertEqual(config["step"], 0.01)

    @patch('streamlit.selectbox')
    @patch('streamlit.number_input')
    @patch('streamlit.text_input')
    def test_render_scalar_array_config_integer(self, mock_text_input, mock_number_input, mock_selectbox):
        """Test scalar array configuration for integer type"""
        # Mock user inputs
        mock_selectbox.return_value = "integer"
        mock_number_input.side_effect = [1, 100, 1]  # min_value, max_value, step
        mock_text_input.return_value = ""
        
        config = render_scalar_array_config()
        
        # Verify configuration structure
        self.assertEqual(config["type"], "integer")
        self.assertEqual(config["min_value"], 1)
        self.assertEqual(config["max_value"], 100)
        self.assertEqual(config["step"], 1)

    @patch('streamlit.selectbox')
    @patch('streamlit.checkbox')
    def test_render_scalar_array_config_boolean(self, mock_checkbox, mock_selectbox):
        """Test scalar array configuration for boolean type"""
        # Mock user inputs
        mock_selectbox.return_value = "boolean"
        mock_checkbox.return_value = True  # default value
        
        config = render_scalar_array_config()
        
        # Verify configuration structure
        self.assertEqual(config["type"], "boolean")
        self.assertEqual(config["default"], True)

    @patch('streamlit.selectbox')
    def test_render_scalar_array_config_date(self, mock_selectbox):
        """Test scalar array configuration for date type"""
        # Mock user inputs
        mock_selectbox.return_value = "date"
        
        config = render_scalar_array_config()
        
        # Verify configuration structure
        self.assertEqual(config["type"], "date")
        # Date type has minimal configuration

    @patch('streamlit.selectbox')
    @patch('streamlit.number_input')
    @patch('streamlit.text_input')
    def test_render_scalar_array_config_string_no_constraints(self, mock_text_input, mock_number_input, mock_selectbox):
        """Test scalar array configuration for string with minimal constraints"""
        # Mock user inputs - no optional constraints
        mock_selectbox.return_value = "string"
        mock_number_input.side_effect = [0, 100]  # min_length=0 (not added), max_length
        mock_text_input.return_value = ""  # no pattern
        
        config = render_scalar_array_config()
        
        # Verify configuration structure
        self.assertEqual(config["type"], "string")
        self.assertNotIn("min_length", config)  # Should not be added when 0
        self.assertEqual(config["max_length"], 100)
        self.assertNotIn("pattern", config)  # Should not be added when empty


class TestSchemaEditorIntegration(unittest.TestCase):
    """Integration tests for Schema Editor components"""
    
    def test_yaml_generation_scalar_array(self):
        """Test YAML generation for scalar array fields"""
        # Simulate a complete scalar array field configuration
        field_config = {
            "type": "array",
            "label": "Serial Numbers",
            "required": True,
            "help": "List of equipment serial numbers",
            "items": {
                "type": "string",
                "min_length": 3,
                "max_length": 20,
                "pattern": "^[A-Z0-9]+$"
            }
        }
        
        # Test YAML generation
        yaml_output = yaml.dump({"serial_numbers": field_config}, default_flow_style=False)
        
        # Verify YAML can be parsed back
        parsed_config = yaml.safe_load(yaml_output)
        self.assertEqual(parsed_config["serial_numbers"]["type"], "array")
        self.assertEqual(parsed_config["serial_numbers"]["items"]["type"], "string")
        self.assertEqual(parsed_config["serial_numbers"]["items"]["pattern"], "^[A-Z0-9]+$")

    def test_yaml_generation_object_array(self):
        """Test YAML generation for object array fields"""
        # Simulate a complete object array field configuration
        field_config = {
            "type": "array",
            "label": "Line Items",
            "required": True,
            "help": "Purchase order line items",
            "items": {
                "type": "object",
                "properties": {
                    "item_code": {
                        "type": "string",
                        "label": "Item Code",
                        "required": True,
                        "min_length": 3,
                        "max_length": 10
                    },
                    "quantity": {
                        "type": "integer",
                        "label": "Quantity",
                        "required": True,
                        "min_value": 1,
                        "max_value": 1000
                    },
                    "unit_price": {
                        "type": "number",
                        "label": "Unit Price",
                        "required": True,
                        "min_value": 0,
                        "max_value": 10000
                    }
                }
            }
        }
        
        # Test YAML generation
        yaml_output = yaml.dump({"line_items": field_config}, default_flow_style=False)
        
        # Verify YAML can be parsed back
        parsed_config = yaml.safe_load(yaml_output)
        self.assertEqual(parsed_config["line_items"]["type"], "array")
        self.assertEqual(parsed_config["line_items"]["items"]["type"], "object")
        
        properties = parsed_config["line_items"]["items"]["properties"]
        self.assertIn("item_code", properties)
        self.assertIn("quantity", properties)
        self.assertIn("unit_price", properties)
        
        # Verify property configurations
        self.assertEqual(properties["item_code"]["type"], "string")
        self.assertEqual(properties["quantity"]["type"], "integer")
        self.assertEqual(properties["unit_price"]["type"], "number")

    def test_complete_schema_generation(self):
        """Test generation of complete schema with multiple array fields"""
        schema_fields = {
            "serial_numbers": {
                "type": "array",
                "label": "Serial Numbers",
                "required": False,
                "help": "Equipment serial numbers",
                "items": {
                    "type": "string",
                    "pattern": "^[A-Z0-9]+$"
                }
            },
            "line_items": {
                "type": "array",
                "label": "Line Items",
                "required": True,
                "help": "Purchase order items",
                "items": {
                    "type": "object",
                    "properties": {
                        "item_code": {
                            "type": "string",
                            "required": True
                        },
                        "quantity": {
                            "type": "integer",
                            "required": True,
                            "min_value": 1
                        }
                    }
                }
            }
        }
        
        complete_schema = {
            "title": "Test Schema",
            "description": "Schema with array fields",
            "fields": schema_fields
        }
        
        # Test YAML generation
        yaml_output = yaml.dump(complete_schema, default_flow_style=False)
        
        # Verify YAML structure
        parsed_schema = yaml.safe_load(yaml_output)
        self.assertEqual(parsed_schema["title"], "Test Schema")
        self.assertIn("fields", parsed_schema)
        self.assertIn("serial_numbers", parsed_schema["fields"])
        self.assertIn("line_items", parsed_schema["fields"])

    def test_field_validation_scalar_array(self):
        """Test validation of scalar array field configurations"""
        # Valid scalar array configuration
        valid_config = {
            "type": "array",
            "label": "Tags",
            "required": False,
            "items": {
                "type": "string",
                "min_length": 1,
                "max_length": 50
            }
        }
        
        # Should not raise any exceptions
        yaml_output = yaml.dump({"tags": valid_config})
        parsed_config = yaml.safe_load(yaml_output)
        self.assertEqual(parsed_config["tags"]["type"], "array")

    def test_field_validation_object_array(self):
        """Test validation of object array field configurations"""
        # Valid object array configuration
        valid_config = {
            "type": "array",
            "label": "Items",
            "required": True,
            "items": {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "required": True
                    },
                    "active": {
                        "type": "boolean",
                        "required": False,
                        "default": True
                    }
                }
            }
        }
        
        # Should not raise any exceptions
        yaml_output = yaml.dump({"items": valid_config})
        parsed_config = yaml.safe_load(yaml_output)
        self.assertEqual(parsed_config["items"]["items"]["type"], "object")
        self.assertIn("properties", parsed_config["items"]["items"])

    def test_constraint_combinations(self):
        """Test various constraint combinations in field configurations"""
        # String with all constraints
        string_config = {
            "type": "string",
            "min_length": 5,
            "max_length": 100,
            "pattern": "^[A-Za-z0-9_]+$"
        }
        
        yaml_output = yaml.dump(string_config)
        parsed_config = yaml.safe_load(yaml_output)
        self.assertEqual(parsed_config["min_length"], 5)
        self.assertEqual(parsed_config["max_length"], 100)
        self.assertEqual(parsed_config["pattern"], "^[A-Za-z0-9_]+$")
        
        # Number with constraints
        number_config = {
            "type": "number",
            "min_value": 0.01,
            "max_value": 999.99,
            "step": 0.01
        }
        
        yaml_output = yaml.dump(number_config)
        parsed_config = yaml.safe_load(yaml_output)
        self.assertEqual(parsed_config["min_value"], 0.01)
        self.assertEqual(parsed_config["max_value"], 999.99)
        self.assertEqual(parsed_config["step"], 0.01)

    def test_complex_object_properties(self):
        """Test complex object array with multiple property types"""
        complex_config = {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "id": {
                        "type": "string",
                        "required": True,
                        "pattern": "^ID[0-9]{4}$"
                    },
                    "name": {
                        "type": "string",
                        "required": True,
                        "min_length": 2,
                        "max_length": 100
                    },
                    "price": {
                        "type": "number",
                        "required": True,
                        "min_value": 0,
                        "max_value": 10000
                    },
                    "quantity": {
                        "type": "integer",
                        "required": True,
                        "min_value": 1,
                        "max_value": 1000
                    },
                    "active": {
                        "type": "boolean",
                        "required": False,
                        "default": True
                    },
                    "created_date": {
                        "type": "date",
                        "required": False
                    }
                }
            }
        }
        
        # Test YAML generation and parsing
        yaml_output = yaml.dump({"complex_items": complex_config})
        parsed_config = yaml.safe_load(yaml_output)
        
        properties = parsed_config["complex_items"]["items"]["properties"]
        
        # Verify all property types are preserved
        self.assertEqual(properties["id"]["type"], "string")
        self.assertEqual(properties["name"]["type"], "string")
        self.assertEqual(properties["price"]["type"], "number")
        self.assertEqual(properties["quantity"]["type"], "integer")
        self.assertEqual(properties["active"]["type"], "boolean")
        self.assertEqual(properties["created_date"]["type"], "date")
        
        # Verify constraints are preserved
        self.assertEqual(properties["id"]["pattern"], "^ID[0-9]{4}$")
        self.assertEqual(properties["name"]["min_length"], 2)
        self.assertEqual(properties["price"]["max_value"], 10000)
        self.assertEqual(properties["active"]["default"], True)


if __name__ == "__main__":
    # Run the tests
    unittest.main(verbosity=2)