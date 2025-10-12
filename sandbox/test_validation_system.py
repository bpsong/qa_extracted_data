"""
Unit tests for sandbox validation system

Tests cover validation of scalar arrays with various constraints,
validation of object arrays with required properties, and error message
formatting and contextual information.
"""

import unittest
import sys
import os
from datetime import datetime, date

# Add sandbox to path for imports
sys.path.insert(0, os.path.dirname(__file__))

from array_sandbox_app import (
    comprehensive_validate_data,
    validate_field_comprehensive,
    validate_array_field_comprehensive,
    validate_scalar_item_comprehensive,
    get_validation_scenarios
)


class TestValidationSystem(unittest.TestCase):
    """Test cases for comprehensive validation system"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.insurance_schema = {
            "fields": {
                "supplier_name": {
                    "type": "string",
                    "required": True,
                    "min_length": 3,
                    "max_length": 100
                },
                "policy_number": {
                    "type": "string",
                    "required": True,
                    "pattern": "^[A-Z0-9]+$"
                },
                "serial_numbers": {
                    "type": "array",
                    "required": False,
                    "items": {
                        "type": "string",
                        "min_length": 3,
                        "max_length": 20,
                        "pattern": "^[A-Z0-9]+$"
                    }
                },
                "invoice_amount": {
                    "type": "number",
                    "required": True,
                    "min_value": 0
                },
                "tags": {
                    "type": "array",
                    "required": False,
                    "items": {
                        "type": "string",
                        "min_length": 1,
                        "max_length": 50
                    }
                }
            }
        }
        
        self.purchase_order_schema = {
            "fields": {
                "po_number": {
                    "type": "string",
                    "required": True
                },
                "line_items": {
                    "type": "array",
                    "required": True,
                    "items": {
                        "type": "object",
                        "properties": {
                            "item_code": {
                                "type": "string",
                                "required": True,
                                "min_length": 3
                            },
                            "quantity": {
                                "type": "integer",
                                "required": True,
                                "min_value": 1
                            },
                            "unit_price": {
                                "type": "number",
                                "required": True,
                                "min_value": 0
                            },
                            "description": {
                                "type": "string",
                                "required": False
                            }
                        }
                    }
                }
            }
        }

    def test_comprehensive_validate_data_valid(self):
        """Test comprehensive validation with valid data"""
        valid_data = {
            "supplier_name": "Test Insurance Co.",
            "policy_number": "POL123456",
            "serial_numbers": ["SN001", "SN002"],
            "invoice_amount": 500.00,
            "tags": ["insurance", "equipment"]
        }
        
        result = comprehensive_validate_data(valid_data, self.insurance_schema)
        
        self.assertTrue(result["is_valid"])
        self.assertEqual(len(result["errors"]), 0)

    def test_comprehensive_validate_data_missing_required(self):
        """Test comprehensive validation with missing required fields"""
        invalid_data = {
            "policy_number": "POL123456",
            "serial_numbers": ["SN001"],
            "invoice_amount": 500.00
            # Missing required supplier_name
        }
        
        result = comprehensive_validate_data(invalid_data, self.insurance_schema)
        
        self.assertFalse(result["is_valid"])
        self.assertGreater(len(result["errors"]), 0)
        
        # Check that error mentions the missing field
        error_messages = [error["message"] for error in result["errors"]]
        self.assertTrue(any("supplier_name" in msg for msg in error_messages))

    def test_validate_scalar_array_valid(self):
        """Test validation of valid scalar arrays"""
        field_config = {
            "type": "array",
            "items": {
                "type": "string",
                "min_length": 3,
                "pattern": "^[A-Z0-9]+$"
            }
        }
        
        valid_array = ["ABC123", "DEF456", "GHI789"]
        errors = validate_array_field_comprehensive("serial_numbers", valid_array, field_config)
        
        self.assertEqual(len(errors), 0)

    def test_validate_scalar_array_invalid_items(self):
        """Test validation of scalar arrays with invalid items"""
        field_config = {
            "type": "array",
            "items": {
                "type": "string",
                "min_length": 3,
                "pattern": "^[A-Z0-9]+$"
            }
        }
        
        invalid_array = ["AB", "abc123", "XYZ999"]  # Too short, wrong pattern, valid
        errors = validate_array_field_comprehensive("serial_numbers", invalid_array, field_config)
        
        self.assertEqual(len(errors), 2)  # Two invalid items
        
        # Check error paths
        error_paths = [error["field_path"] for error in errors]
        self.assertIn("serial_numbers[0]", error_paths)
        self.assertIn("serial_numbers[1]", error_paths)

    def test_validate_object_array_valid(self):
        """Test validation of valid object arrays"""
        field_config = {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "item_code": {
                        "type": "string",
                        "required": True,
                        "min_length": 3
                    },
                    "quantity": {
                        "type": "integer",
                        "required": True,
                        "min_value": 1
                    }
                }
            }
        }
        
        valid_array = [
            {"item_code": "ITM001", "quantity": 5},
            {"item_code": "ITM002", "quantity": 10}
        ]
        
        errors = validate_array_field_comprehensive("line_items", valid_array, field_config)
        
        self.assertEqual(len(errors), 0)

    def test_validate_object_array_missing_required_properties(self):
        """Test validation of object arrays with missing required properties"""
        field_config = {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "item_code": {
                        "type": "string",
                        "required": True,
                        "min_length": 3
                    },
                    "quantity": {
                        "type": "integer",
                        "required": True,
                        "min_value": 1
                    }
                }
            }
        }
        
        invalid_array = [
            {"item_code": "ITM001"},  # Missing quantity
            {"quantity": 5}  # Missing item_code
        ]
        
        errors = validate_array_field_comprehensive("line_items", invalid_array, field_config)
        
        self.assertEqual(len(errors), 2)  # Two missing required properties
        
        # Check error paths
        error_paths = [error["field_path"] for error in errors]
        self.assertIn("line_items[0].quantity", error_paths)
        self.assertIn("line_items[1].item_code", error_paths)

    def test_validate_object_array_constraint_violations(self):
        """Test validation of object arrays with constraint violations"""
        field_config = {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "item_code": {
                        "type": "string",
                        "required": True,
                        "min_length": 3
                    },
                    "quantity": {
                        "type": "integer",
                        "required": True,
                        "min_value": 1
                    },
                    "unit_price": {
                        "type": "number",
                        "required": True,
                        "min_value": 0
                    }
                }
            }
        }
        
        invalid_array = [
            {
                "item_code": "IT",  # Too short
                "quantity": 0,  # Below minimum
                "unit_price": -10.0  # Below minimum
            }
        ]
        
        errors = validate_array_field_comprehensive("line_items", invalid_array, field_config)
        
        self.assertEqual(len(errors), 3)  # Three constraint violations
        
        # Check error types
        error_types = [error["error_type"] for error in errors]
        self.assertIn("Length Constraint", error_types)
        self.assertIn("Range Constraint", error_types)

    def test_validate_scalar_item_string_constraints(self):
        """Test validation of string scalar items with various constraints"""
        # Test min_length constraint
        errors = validate_scalar_item_comprehensive(
            "test[0]", "ab", {"type": "string", "min_length": 3}
        )
        self.assertEqual(len(errors), 1)
        self.assertEqual(errors[0]["error_type"], "Length Constraint")
        
        # Test max_length constraint
        errors = validate_scalar_item_comprehensive(
            "test[0]", "a" * 101, {"type": "string", "max_length": 100}
        )
        self.assertEqual(len(errors), 1)
        self.assertEqual(errors[0]["error_type"], "Length Constraint")
        
        # Test pattern constraint
        errors = validate_scalar_item_comprehensive(
            "test[0]", "abc123", {"type": "string", "pattern": "^[A-Z0-9]+$"}
        )
        self.assertEqual(len(errors), 1)
        self.assertEqual(errors[0]["error_type"], "Pattern Constraint")

    def test_validate_scalar_item_number_constraints(self):
        """Test validation of number scalar items with range constraints"""
        # Test min_value constraint
        errors = validate_scalar_item_comprehensive(
            "test[0]", -5.0, {"type": "number", "min_value": 0}
        )
        self.assertEqual(len(errors), 1)
        self.assertEqual(errors[0]["error_type"], "Range Constraint")
        
        # Test max_value constraint
        errors = validate_scalar_item_comprehensive(
            "test[0]", 1500.0, {"type": "number", "max_value": 1000}
        )
        self.assertEqual(len(errors), 1)
        self.assertEqual(errors[0]["error_type"], "Range Constraint")

    def test_validate_scalar_item_integer_constraints(self):
        """Test validation of integer scalar items with range constraints"""
        # Test min_value constraint
        errors = validate_scalar_item_comprehensive(
            "test[0]", 0, {"type": "integer", "min_value": 1}
        )
        self.assertEqual(len(errors), 1)
        self.assertEqual(errors[0]["error_type"], "Range Constraint")
        
        # Test max_value constraint
        errors = validate_scalar_item_comprehensive(
            "test[0]", 1001, {"type": "integer", "max_value": 1000}
        )
        self.assertEqual(len(errors), 1)
        self.assertEqual(errors[0]["error_type"], "Range Constraint")

    def test_validate_scalar_item_type_errors(self):
        """Test validation of scalar items with type errors"""
        # String type error
        errors = validate_scalar_item_comprehensive(
            "test[0]", 123, {"type": "string"}
        )
        self.assertEqual(len(errors), 1)
        self.assertEqual(errors[0]["error_type"], "Type Error")
        
        # Number type error
        errors = validate_scalar_item_comprehensive(
            "test[0]", "not_a_number", {"type": "number"}
        )
        self.assertEqual(len(errors), 1)
        self.assertEqual(errors[0]["error_type"], "Type Error")
        
        # Boolean type error
        errors = validate_scalar_item_comprehensive(
            "test[0]", "true", {"type": "boolean"}
        )
        self.assertEqual(len(errors), 1)
        self.assertEqual(errors[0]["error_type"], "Type Error")

    def test_validate_scalar_item_date_validation(self):
        """Test validation of date scalar items"""
        # Valid date string
        errors = validate_scalar_item_comprehensive(
            "test[0]", "2024-01-15", {"type": "date"}
        )
        self.assertEqual(len(errors), 0)
        
        # Invalid date format
        errors = validate_scalar_item_comprehensive(
            "test[0]", "2024/01/15", {"type": "date"}
        )
        self.assertEqual(len(errors), 1)
        self.assertEqual(errors[0]["error_type"], "Format Error")
        
        # Invalid date string
        errors = validate_scalar_item_comprehensive(
            "test[0]", "not-a-date", {"type": "date"}
        )
        self.assertEqual(len(errors), 1)
        self.assertEqual(errors[0]["error_type"], "Format Error")

    def test_error_message_formatting(self):
        """Test that error messages contain proper contextual information"""
        field_config = {
            "type": "array",
            "items": {
                "type": "string",
                "min_length": 5,
                "pattern": "^[A-Z]+$"
            }
        }
        
        invalid_array = ["abc", "DEFG"]  # Too short and wrong pattern, too short
        errors = validate_array_field_comprehensive("test_field", invalid_array, field_config)
        
        # Should have 3 errors (abc: length + pattern, DEFG: length)
        self.assertEqual(len(errors), 3)
        
        # Check that error messages contain array indices
        error_messages = [error["message"] for error in errors]
        self.assertTrue(any("test_field[0]" in msg for msg in error_messages))
        self.assertTrue(any("test_field[1]" in msg for msg in error_messages))
        
        # Check that suggestions are provided
        suggestions = [error.get("suggestion", "") for error in errors]
        self.assertTrue(all(suggestion for suggestion in suggestions))

    def test_validation_scenarios_insurance_document(self):
        """Test predefined validation scenarios for insurance document"""
        scenarios = get_validation_scenarios("insurance_document")
        
        # Test valid scenario
        valid_scenario = scenarios["Valid Data"]
        result = comprehensive_validate_data(valid_scenario["data"], self.insurance_schema)
        self.assertTrue(result["is_valid"])
        
        # Test invalid scenarios
        invalid_scenario = scenarios["Missing Required Fields"]
        result = comprehensive_validate_data(invalid_scenario["data"], self.insurance_schema)
        self.assertFalse(result["is_valid"])
        
        serial_scenario = scenarios["Invalid Serial Numbers"]
        result = comprehensive_validate_data(serial_scenario["data"], self.insurance_schema)
        self.assertFalse(result["is_valid"])

    def test_validation_scenarios_purchase_order(self):
        """Test predefined validation scenarios for purchase order"""
        scenarios = get_validation_scenarios("purchase_order")
        
        # Test valid scenario
        valid_scenario = scenarios["Valid Purchase Order"]
        result = comprehensive_validate_data(valid_scenario["data"], self.purchase_order_schema)
        self.assertTrue(result["is_valid"])
        
        # Test invalid scenarios
        empty_items_scenario = scenarios["Empty Line Items"]
        result = comprehensive_validate_data(empty_items_scenario["data"], self.purchase_order_schema)
        self.assertFalse(result["is_valid"])
        
        invalid_props_scenario = scenarios["Invalid Line Item Properties"]
        result = comprehensive_validate_data(invalid_props_scenario["data"], self.purchase_order_schema)
        self.assertFalse(result["is_valid"])

    def test_array_type_validation(self):
        """Test validation when array field contains non-array value"""
        field_config = {
            "type": "array",
            "items": {"type": "string"}
        }
        
        # Test with non-array value
        errors = validate_array_field_comprehensive("test_field", "not_an_array", field_config)
        
        self.assertEqual(len(errors), 1)
        self.assertEqual(errors[0]["error_type"], "Type Error")
        self.assertIn("must be an array", errors[0]["message"])

    def test_object_array_non_object_items(self):
        """Test validation when object array contains non-object items"""
        field_config = {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "required": True}
                }
            }
        }
        
        # Test with non-object items
        invalid_array = ["not_an_object", 123, True]
        errors = validate_array_field_comprehensive("test_field", invalid_array, field_config)
        
        self.assertEqual(len(errors), 3)  # All three items are invalid
        
        # All errors should be type errors
        error_types = [error["error_type"] for error in errors]
        self.assertTrue(all(error_type == "Type Error" for error_type in error_types))

    def test_optional_fields_validation(self):
        """Test that optional fields are not validated when missing"""
        data = {
            "supplier_name": "Test Company",
            "policy_number": "POL123",
            "invoice_amount": 100.0
            # Missing optional fields: serial_numbers, tags
        }
        
        result = comprehensive_validate_data(data, self.insurance_schema)
        
        # Should be valid even with missing optional fields
        self.assertTrue(result["is_valid"])
        self.assertEqual(len(result["errors"]), 0)

    def test_empty_array_validation(self):
        """Test validation of empty arrays"""
        # Empty optional array should be valid
        field_config = {
            "type": "array",
            "required": False,
            "items": {"type": "string"}
        }
        
        errors = validate_field_comprehensive("optional_array", [], field_config)
        self.assertEqual(len(errors), 0)
        
        # Empty required array should be invalid
        field_config["required"] = True
        errors = validate_field_comprehensive("required_array", [], field_config)
        self.assertEqual(len(errors), 1)
        self.assertEqual(errors[0]["error_type"], "Required Field")


class TestValidationSystemIntegration(unittest.TestCase):
    """Integration tests for validation system"""
    
    def test_complex_validation_scenario(self):
        """Test complex validation scenario with multiple error types"""
        schema = {
            "fields": {
                "name": {
                    "type": "string",
                    "required": True,
                    "min_length": 2
                },
                "items": {
                    "type": "array",
                    "required": True,
                    "items": {
                        "type": "object",
                        "properties": {
                            "id": {
                                "type": "string",
                                "required": True,
                                "pattern": "^ID[0-9]{3}$"
                            },
                            "count": {
                                "type": "integer",
                                "required": True,
                                "min_value": 1,
                                "max_value": 100
                            },
                            "price": {
                                "type": "number",
                                "required": False,
                                "min_value": 0
                            }
                        }
                    }
                }
            }
        }
        
        # Data with multiple validation errors
        invalid_data = {
            "name": "A",  # Too short
            "items": [
                {
                    "id": "ID12",  # Wrong pattern (needs 3 digits)
                    "count": 0,  # Below minimum
                    "price": -5.0  # Below minimum
                },
                {
                    # Missing required id
                    "count": 150,  # Above maximum
                    "price": 10.0
                },
                "not_an_object"  # Wrong type
            ]
        }
        
        result = comprehensive_validate_data(invalid_data, schema)
        
        # Should have multiple errors
        self.assertFalse(result["is_valid"])
        self.assertGreater(len(result["errors"]), 5)
        
        # Check that different error types are present
        error_types = [error["error_type"] for error in result["errors"]]
        self.assertIn("Length Constraint", error_types)
        self.assertIn("Pattern Constraint", error_types)
        self.assertIn("Range Constraint", error_types)
        self.assertIn("Required Field", error_types)
        self.assertIn("Type Error", error_types)


if __name__ == "__main__":
    # Run the tests
    unittest.main(verbosity=2)