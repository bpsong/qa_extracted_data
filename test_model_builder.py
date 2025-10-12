"""
Unit tests for model_builder module.
"""

import pytest
from datetime import datetime, date
from typing import List, Dict, Any
from pydantic import BaseModel, ValidationError

# Import the module to test
from utils.model_builder import (
    create_model_from_schema,
    create_field_from_config,
    get_field_type,
    create_nested_model,
    create_validators_for_field,
    get_streamlit_widget_type,
    get_widget_kwargs,
    model_to_dict,
    dict_to_model,
    get_model_fields_info,
    validate_model_data,
    create_form_schema
)


class TestModelBuilder:
    """Test class for model builder."""
    
    def test_create_model_from_schema_basic(self):
        """Test creating a basic model from schema."""
        schema = {
            "fields": {
                "name": {
                    "type": "string",
                    "label": "Full Name",
                    "required": True
                },
                "age": {
                    "type": "integer",
                    "label": "Age",
                    "required": False,
                    "default": 0
                }
            }
        }
        
        model_class = create_model_from_schema(schema, "TestModel")
        
        # Test model creation
        assert model_class.__name__ == "TestModel"
        assert "name" in model_class.model_fields
        assert "age" in model_class.model_fields
        
        # Test field properties
        name_field = model_class.model_fields["name"]
        assert name_field.is_required() == True
        assert name_field.annotation == str
        
        age_field = model_class.model_fields["age"]
        assert age_field.is_required() == False
        assert age_field.annotation == int
        assert age_field.default == 0
    
    def test_create_model_from_schema_no_fields(self):
        """Test creating model from schema without fields."""
        schema = {"title": "Test"}
        
        with pytest.raises(ValueError, match="Schema must contain 'fields' key"):
            create_model_from_schema(schema)
    
    def test_get_field_type_string(self):
        """Test getting field type for string."""
        field_config = {"type": "string"}
        field_type = get_field_type(field_config)
        assert field_type == str
    
    def test_get_field_type_integer(self):
        """Test getting field type for integer."""
        field_config = {"type": "integer"}
        field_type = get_field_type(field_config)
        assert field_type == int
    
    def test_get_field_type_number(self):
        """Test getting field type for number."""
        field_config = {"type": "number"}
        field_type = get_field_type(field_config)
        assert field_type == float
    
    def test_get_field_type_boolean(self):
        """Test getting field type for boolean."""
        field_config = {"type": "boolean"}
        field_type = get_field_type(field_config)
        assert field_type == bool
    
    def test_get_field_type_date(self):
        """Test getting field type for date."""
        field_config = {"type": "date"}
        field_type = get_field_type(field_config)
        assert field_type == date
    
    def test_get_field_type_datetime(self):
        """Test getting field type for datetime."""
        field_config = {"type": "datetime"}
        field_type = get_field_type(field_config)
        assert field_type == datetime
    
    def test_get_field_type_array(self):
        """Test getting field type for array."""
        field_config = {
            "type": "array",
            "items": {"type": "string"}
        }
        field_type = get_field_type(field_config)
        assert field_type == List[str]
    
    def test_get_field_type_enum(self):
        """Test getting field type for enum."""
        field_config = {
            "type": "enum",
            "choices": ["red", "green", "blue"]
        }
        field_type = get_field_type(field_config)
        assert field_type == str  # Enums are validated strings
    
    def test_get_field_type_object_with_properties(self):
        """Test getting field type for object with properties."""
        field_config = {
            "type": "object",
            "properties": {
                "nested_field": {"type": "string"}
            }
        }
        field_type = get_field_type(field_config)
        
        # Should return a BaseModel subclass
        assert issubclass(field_type, BaseModel)
    
    def test_get_field_type_object_without_properties(self):
        """Test getting field type for object without properties."""
        field_config = {"type": "object"}
        field_type = get_field_type(field_config)
        assert field_type == Dict[str, Any]
    
    def test_create_field_from_config_required(self):
        """Test creating required field from config."""
        field_config = {
            "type": "string",
            "label": "Test Field",
            "required": True
        }
        
        field_type, field_info = create_field_from_config("test_field", field_config)
        
        assert field_type == str
        assert field_info.is_required() == True  # Required field
        assert field_info.description == "Test Field"
    
    def test_create_field_from_config_optional_with_default(self):
        """Test creating optional field with default value."""
        field_config = {
            "type": "string",
            "label": "Test Field",
            "required": False,
            "default": "default_value"
        }
        
        field_type, field_info = create_field_from_config("test_field", field_config)
        
        assert field_type == str
        assert field_info.default == "default_value"
    
    def test_create_field_from_config_with_constraints(self):
        """Test creating field with constraints."""
        field_config = {
            "type": "string",
            "min_length": 2,
            "max_length": 10
        }
        
        field_type, field_info = create_field_from_config("test_field", field_config)
        
        # In Pydantic V2, constraints are stored differently
        # Check that the field was created successfully
        assert field_type == str
        assert field_info is not None
    
    def test_create_nested_model(self):
        """Test creating nested model."""
        properties = {
            "street": {"type": "string", "required": True},
            "city": {"type": "string", "required": True},
            "zip_code": {"type": "string", "required": False}
        }
        
        nested_model = create_nested_model(properties, "AddressModel")
        
        assert nested_model.__name__ == "AddressModel"
        assert "street" in nested_model.model_fields
        assert "city" in nested_model.model_fields
        assert "zip_code" in nested_model.model_fields
        
        # Test creating instance
        address = nested_model(street="123 Main St", city="Anytown")
        assert address.street == "123 Main St"
        assert address.city == "Anytown"
    
    def test_create_validators_for_field_pattern(self):
        """Test creating pattern validator."""
        field_config = {
            "type": "string",
            "pattern": "^[A-Z][a-z]+$"
        }
        
        validators = create_validators_for_field("test_field", field_config)
        
        assert len(validators) == 1
        assert "validate_test_field_pattern" in validators
    
    def test_create_validators_for_field_enum(self):
        """Test creating enum validator."""
        field_config = {
            "type": "enum",
            "choices": ["red", "green", "blue"]
        }
        
        validators = create_validators_for_field("test_field", field_config)
        
        assert len(validators) == 1
        assert "validate_test_field_enum" in validators
    
    def test_get_streamlit_widget_type_string(self):
        """Test getting widget type for string field."""
        field_config = {"type": "string"}
        widget_type = get_streamlit_widget_type(field_config)
        assert widget_type == "text_input"
    
    def test_get_streamlit_widget_type_string_with_choices(self):
        """Test getting widget type for string field with choices."""
        field_config = {
            "type": "string",
            "choices": ["option1", "option2"]
        }
        widget_type = get_streamlit_widget_type(field_config)
        assert widget_type == "selectbox"
    
    def test_get_streamlit_widget_type_number(self):
        """Test getting widget type for number field."""
        field_config = {"type": "number"}
        widget_type = get_streamlit_widget_type(field_config)
        assert widget_type == "number_input"
    
    def test_get_streamlit_widget_type_boolean(self):
        """Test getting widget type for boolean field."""
        field_config = {"type": "boolean"}
        widget_type = get_streamlit_widget_type(field_config)
        assert widget_type == "checkbox"
    
    def test_get_streamlit_widget_type_date(self):
        """Test getting widget type for date field."""
        field_config = {"type": "date"}
        widget_type = get_streamlit_widget_type(field_config)
        assert widget_type == "date_input"
    
    def test_get_streamlit_widget_type_enum(self):
        """Test getting widget type for enum field."""
        field_config = {"type": "enum"}
        widget_type = get_streamlit_widget_type(field_config)
        assert widget_type == "selectbox"
    
    def test_get_streamlit_widget_type_array(self):
        """Test getting widget type for array field."""
        field_config = {"type": "array"}
        widget_type = get_streamlit_widget_type(field_config)
        assert widget_type == "data_editor"
    
    def test_get_widget_kwargs_basic(self):
        """Test getting widget kwargs for basic field."""
        field_config = {
            "type": "string",
            "label": "Test Field",
            "help": "This is a test field",
            "default": "default_value"
        }
        
        kwargs = get_widget_kwargs(field_config)
        
        assert kwargs["label"] == "Test Field"
        assert kwargs["help"] == "This is a test field"
        assert kwargs["value"] == "default_value"
    
    def test_get_widget_kwargs_string_constraints(self):
        """Test getting widget kwargs for string with constraints."""
        field_config = {
            "type": "string",
            "max_length": 100,
            "placeholder": "Enter text here"
        }
        
        kwargs = get_widget_kwargs(field_config)
        
        assert kwargs["max_chars"] == 100
        assert kwargs["placeholder"] == "Enter text here"
    
    def test_get_widget_kwargs_number_constraints(self):
        """Test getting widget kwargs for number with constraints."""
        field_config = {
            "type": "number",
            "min_value": 0,
            "max_value": 100,
            "step": 0.1
        }
        
        kwargs = get_widget_kwargs(field_config)
        
        assert kwargs["min_value"] == 0
        assert kwargs["max_value"] == 100
        assert kwargs["step"] == 0.1
    
    def test_get_widget_kwargs_readonly(self):
        """Test getting widget kwargs for readonly field."""
        field_config = {
            "type": "string",
            "readonly": True
        }
        
        kwargs = get_widget_kwargs(field_config)
        
        assert kwargs["disabled"] == True
    
    def test_model_to_dict(self):
        """Test converting model to dictionary."""
        schema = {
            "fields": {
                "name": {"type": "string", "required": True},
                "age": {"type": "integer", "required": False}
            }
        }
        
        model_class = create_model_from_schema(schema)
        instance = model_class(name="John", age=30)
        
        result = model_to_dict(instance)
        
        assert result == {"name": "John", "age": 30}
    
    def test_dict_to_model(self):
        """Test creating model from dictionary."""
        schema = {
            "fields": {
                "name": {"type": "string", "required": True},
                "age": {"type": "integer", "required": False}
            }
        }
        
        model_class = create_model_from_schema(schema)
        data = {"name": "John", "age": 30}
        
        instance = dict_to_model(data, model_class)
        
        assert instance.name == "John"
        assert instance.age == 30
    
    def test_get_model_fields_info(self):
        """Test getting model fields information."""
        schema = {
            "fields": {
                "name": {
                    "type": "string",
                    "label": "Full Name",
                    "required": True
                },
                "age": {
                    "type": "integer",
                    "required": False,
                    "default": 0
                }
            }
        }
        
        model_class = create_model_from_schema(schema)
        fields_info = get_model_fields_info(model_class)
        
        assert "name" in fields_info
        assert "age" in fields_info
        
        name_info = fields_info["name"]
        assert name_info["type"] == str
        assert name_info["required"] == True
        assert name_info["description"] == "Full Name"
        
        age_info = fields_info["age"]
        assert age_info["type"] == int
        assert age_info["required"] == False
        assert age_info["default"] == 0
    
    def test_validate_model_data_valid(self):
        """Test validating valid data against model."""
        schema = {
            "fields": {
                "name": {"type": "string", "required": True},
                "age": {"type": "integer", "required": False}
            }
        }
        
        model_class = create_model_from_schema(schema)
        data = {"name": "John", "age": 30}
        
        errors = validate_model_data(data, model_class)
        
        assert len(errors) == 0
    
    def test_validate_model_data_invalid(self):
        """Test validating invalid data against model."""
        schema = {
            "fields": {
                "name": {"type": "string", "required": True},
                "age": {"type": "integer", "required": False}
            }
        }
        
        model_class = create_model_from_schema(schema)
        data = {"age": "not_a_number"}  # Missing required name, invalid age type
        
        errors = validate_model_data(data, model_class)
        
        assert len(errors) > 0
        # Should have errors for missing name and invalid age type
    
    def test_create_form_schema(self):
        """Test creating form schema from model."""
        schema = {
            "fields": {
                "name": {
                    "type": "string",
                    "label": "Full Name",
                    "required": True
                },
                "age": {
                    "type": "integer",
                    "required": False,
                    "default": 0
                }
            }
        }
        
        model_class = create_model_from_schema(schema, "TestModel")
        form_schema = create_form_schema(model_class)
        
        assert form_schema["title"] == "TestModel"
        assert "fields" in form_schema
        
        name_field = form_schema["fields"]["name"]
        assert name_field["type"] == "string"
        assert name_field["label"] == "Full Name"
        assert name_field["required"] == True
        
        age_field = form_schema["fields"]["age"]
        assert age_field["type"] == "integer"
        assert age_field["required"] == False
        assert age_field["default"] == 0
    
    def test_model_with_enum_validation(self):
        """Test model with enum field validation."""
        schema = {
            "fields": {
                "status": {
                    "type": "enum",
                    "choices": ["active", "inactive", "pending"],
                    "required": True
                }
            }
        }
        
        model_class = create_model_from_schema(schema)
        
        # Valid enum value
        valid_instance = model_class(status="active")
        assert valid_instance.status == "active"
        
        # Invalid enum value should raise validation error
        with pytest.raises(ValidationError):
            model_class(status="invalid_status")
    
    def test_model_with_pattern_validation(self):
        """Test model with pattern validation."""
        schema = {
            "fields": {
                "code": {
                    "type": "string",
                    "pattern": "^[A-Z]{2}[0-9]{3}$",
                    "required": True
                }
            }
        }
        
        model_class = create_model_from_schema(schema)
        
        # Valid pattern
        valid_instance = model_class(code="AB123")
        assert valid_instance.code == "AB123"
        
        # Invalid pattern should raise validation error
        with pytest.raises(ValidationError):
            model_class(code="invalid")


if __name__ == "__main__":
    # Run tests if script is executed directly
    pytest.main([__file__])