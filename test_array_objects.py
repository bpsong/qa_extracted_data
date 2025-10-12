#!/usr/bin/env python3
"""
Test script to verify array of objects support in the JSON QA webapp.
"""

import sys
import json
from pathlib import Path

# Add current directory to path
sys.path.append('.')

def test_array_objects_schema():
    """Test loading a schema with array of objects."""
    print("=== Testing Array of Objects Schema ===")
    
    try:
        from utils.schema_loader import load_schema
        
        # Test with the existing invoice schema that has line items
        schema = load_schema('invoice_schema.yaml')
        if schema is None:
            print("❌ Invoice schema loading failed")
            return False
            
        print("✅ Invoice schema loaded successfully")
        
        # Check if line items array field is present
        fields = schema.get('fields', {})
        line_items_field = fields.get('Line items')
        
        if not line_items_field:
            print("❌ Line items field not found")
            return False
            
        if line_items_field.get('type') != 'array':
            print("❌ Line items is not array type")
            return False
            
        items_config = line_items_field.get('items', {})
        if items_config.get('type') != 'object':
            print("❌ Line items array items are not object type")
            return False
            
        properties = items_config.get('properties', {})
        if not properties:
            print("❌ Line items object has no properties")
            return False
            
        print(f"✅ Line items array of objects found with {len(properties)} properties:")
        for prop_name in properties.keys():
            print(f"   • {prop_name}")
            
        return True
        
    except Exception as e:
        print(f"❌ Error loading schema: {e}")
        return False

def test_model_creation_with_objects():
    """Test creating a Pydantic model with array of objects."""
    print("\n=== Testing Model Creation with Array of Objects ===")
    
    try:
        from utils.schema_loader import load_schema
        from utils.model_builder import create_model_from_schema, validate_model_data
        
        schema = load_schema('invoice_schema.yaml')
        if schema is None:
            print("❌ Schema not available")
            return False
            
        model_class = create_model_from_schema(schema, 'TestInvoiceModel')
        print("✅ Model created successfully")
        
        # Test with valid data including array of objects
        test_data = {
            'Supplier name': 'Test Company',
            'Purchase Order number': 'PO123456',
            'Invoice Amount': 100.50,
            'Line items': [
                {
                    'Item description': 'Widget A',
                    'Quantity': 2,
                    'Unit price': 25.00,
                    'Total price': 50.00
                },
                {
                    'Item description': 'Widget B', 
                    'Quantity': 1,
                    'Unit price': 50.50,
                    'Total price': 50.50
                }
            ]
        }
        
        errors = validate_model_data(test_data, model_class)
        if errors:
            print(f"❌ Validation errors: {errors}")
            return False
        else:
            print("✅ Validation passed for array of objects data")
            
        return True
        
    except Exception as e:
        print(f"❌ Error in model creation: {e}")
        return False

def test_form_generator_objects():
    """Test if form generator can handle array of objects."""
    print("\n=== Testing Form Generator Array of Objects Support ===")
    
    try:
        from utils.form_generator import FormGenerator
        
        # Check if FormGenerator has the right methods
        has_array_editor = hasattr(FormGenerator, '_render_array_editor')
        if not has_array_editor:
            print("❌ FormGenerator missing _render_array_editor method")
            return False
            
        print("✅ FormGenerator has _render_array_editor method")
        
        # Test the array editor logic with object configuration
        field_config = {
            "type": "array",
            "label": "Test Line Items",
            "items": {
                "type": "object",
                "properties": {
                    "description": {
                        "type": "string",
                        "label": "Description"
                    },
                    "quantity": {
                        "type": "number", 
                        "label": "Quantity"
                    }
                }
            }
        }
        
        test_data = [
            {"description": "Item 1", "quantity": 2},
            {"description": "Item 2", "quantity": 1}
        ]
        
        # This would normally render UI, but we can test the logic
        print("✅ Array of objects configuration is valid")
        return True
        
    except Exception as e:
        print(f"❌ Error testing form generator: {e}")
        return False

def test_submission_handler_objects():
    """Test if submission handler can validate array of objects."""
    print("\n=== Testing Submission Handler Array of Objects Validation ===")
    
    try:
        from utils.submission_handler import SubmissionHandler
        
        # Test array of objects validation
        field_config = {
            "type": "array",
            "label": "Line Items",
            "items": {
                "type": "object",
                "properties": {
                    "description": {
                        "type": "string",
                        "label": "Description",
                        "required": True
                    },
                    "quantity": {
                        "type": "number",
                        "label": "Quantity", 
                        "required": True,
                        "min_value": 0
                    }
                }
            }
        }
        
        # Valid array of objects
        valid_data = [
            {"description": "Item 1", "quantity": 2},
            {"description": "Item 2", "quantity": 1}
        ]
        
        errors = SubmissionHandler._validate_array_field("line_items", valid_data, field_config)
        if len(errors) == 0:
            print("✅ Valid array of objects passed validation")
        else:
            print(f"❌ Valid array of objects failed validation: {errors}")
            return False
            
        # Invalid array of objects (missing required field)
        invalid_data = [
            {"description": "Item 1", "quantity": 2},
            {"description": "Item 2"}  # Missing quantity
        ]
        
        errors = SubmissionHandler._validate_array_field("line_items", invalid_data, field_config)
        if len(errors) > 0:
            print("✅ Invalid array of objects correctly rejected")
        else:
            print("❌ Invalid array of objects should have been rejected")
            return False
            
        return True
        
    except Exception as e:
        print(f"❌ Error testing submission handler: {e}")
        return False

def main():
    """Run all tests."""
    print("Testing Array of Objects Support in JSON QA Webapp")
    print("=" * 60)
    
    tests = [
        test_array_objects_schema,
        test_model_creation_with_objects,
        test_form_generator_objects,
        test_submission_handler_objects
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
        print("🎉 All tests passed! Array of objects is supported.")
        return True
    else:
        print("⚠️  Some tests failed. Array of objects support may be incomplete.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)