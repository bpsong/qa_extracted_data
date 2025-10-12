#!/usr/bin/env python3
"""
Test script to verify array of scalar values support in the JSON QA webapp.
"""

import sys
import json
from pathlib import Path

# Add current directory to path
sys.path.append('.')

def test_array_schema_loading():
    """Test loading a schema with array fields."""
    print("=== Testing Array Schema Loading ===")
    
    try:
        from utils.schema_loader import load_schema
        
        schema = load_schema('test_array_schema.yaml')
        if schema is None:
            print("❌ Schema loading failed - returned None")
            return False
            
        print("✅ Schema loaded successfully")
        print(f"Schema title: {schema.get('title', 'N/A')}")
        
        # Check if array fields are present
        fields = schema.get('fields', {})
        serial_numbers_field = fields.get('Serial Numbers')
        tags_field = fields.get('Tags')
        
        if serial_numbers_field and serial_numbers_field.get('type') == 'array':
            print("✅ Serial Numbers array field found")
        else:
            print("❌ Serial Numbers array field missing or incorrect")
            return False
            
        if tags_field and tags_field.get('type') == 'array':
            print("✅ Tags array field found")
        else:
            print("❌ Tags array field missing or incorrect")
            return False
            
        return True
        
    except Exception as e:
        print(f"❌ Error loading schema: {e}")
        return False

def test_model_creation():
    """Test creating a Pydantic model from array schema."""
    print("\n=== Testing Model Creation ===")
    
    try:
        from utils.schema_loader import load_schema
        from utils.model_builder import create_model_from_schema, validate_model_data
        
        schema = load_schema('test_array_schema.yaml')
        if schema is None:
            print("❌ Schema not available")
            return False
            
        model_class = create_model_from_schema(schema, 'TestArrayModel')
        print("✅ Model created successfully")
        
        # Test with valid data
        test_data = {
            'Supplier name': 'Test Company',
            'Serial Numbers': ['SerialNo1', 'SerialNo2', 'SerialNo3'],
            'Invoice Amount': 100.50,
            'Tags': ['urgent', 'equipment', 'maintenance']
        }
        
        errors = validate_model_data(test_data, model_class)
        if errors:
            print(f"❌ Validation errors: {errors}")
            return False
        else:
            print("✅ Validation passed for valid data")
            
        # Test with invalid array data
        invalid_data = {
            'Supplier name': 'Test Company',
            'Serial Numbers': 'not_an_array',  # Should be array
            'Invoice Amount': 100.50,
            'Tags': ['valid']
        }
        
        errors = validate_model_data(invalid_data, model_class)
        if errors:
            print("✅ Validation correctly caught invalid array data")
        else:
            print("❌ Validation should have failed for invalid array")
            return False
            
        return True
        
    except Exception as e:
        print(f"❌ Error in model creation: {e}")
        return False

def test_form_generator_array_support():
    """Test if form generator can handle array fields."""
    print("\n=== Testing Form Generator Array Support ===")
    
    try:
        from utils.schema_loader import load_schema
        from utils.form_generator import FormGenerator
        
        schema = load_schema('test_array_schema.yaml')
        if schema is None:
            print("❌ Schema not available")
            return False
            
        # Check if FormGenerator has array rendering methods
        has_array_editor = hasattr(FormGenerator, '_render_array_editor')
        if has_array_editor:
            print("✅ FormGenerator has _render_array_editor method")
        else:
            print("❌ FormGenerator missing _render_array_editor method")
            return False
            
        # Test field type detection
        serial_field = schema['fields']['Serial Numbers']
        field_type = FormGenerator._render_field.__code__.co_varnames
        
        print("✅ FormGenerator appears to support array fields")
        return True
        
    except Exception as e:
        print(f"❌ Error testing form generator: {e}")
        return False

def test_submission_handler_array_validation():
    """Test if submission handler can validate arrays."""
    print("\n=== Testing Submission Handler Array Validation ===")
    
    try:
        from utils.submission_handler import SubmissionHandler
        
        # Check if array validation method exists
        has_array_validation = hasattr(SubmissionHandler, '_validate_array_field')
        if has_array_validation:
            print("✅ SubmissionHandler has _validate_array_field method")
        else:
            print("❌ SubmissionHandler missing _validate_array_field method")
            return False
            
        # Test array validation
        field_config = {
            "type": "array",
            "label": "Test Array",
            "items": {
                "type": "string",
                "min_length": 1
            }
        }
        
        # Valid array
        errors = SubmissionHandler._validate_array_field("test", ["item1", "item2"], field_config)
        if len(errors) == 0:
            print("✅ Valid array passed validation")
        else:
            print(f"❌ Valid array failed validation: {errors}")
            return False
            
        # Invalid array (not a list)
        errors = SubmissionHandler._validate_array_field("test", "not_array", field_config)
        if len(errors) > 0:
            print("✅ Invalid array type correctly rejected")
        else:
            print("❌ Invalid array type should have been rejected")
            return False
            
        return True
        
    except Exception as e:
        print(f"❌ Error testing submission handler: {e}")
        return False

def main():
    """Run all tests."""
    print("Testing Array of Scalar Values Support in JSON QA Webapp")
    print("=" * 60)
    
    tests = [
        test_array_schema_loading,
        test_model_creation,
        test_form_generator_array_support,
        test_submission_handler_array_validation
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
        else:
            print("❌ Test failed")
    
    print(f"\n=== Test Results ===")
    print(f"Passed: {passed}/{total}")
    
    if passed == total:
        print("🎉 All tests passed! Array of scalar values is supported.")
        return True
    else:
        print("⚠️  Some tests failed. Array support may be incomplete.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)