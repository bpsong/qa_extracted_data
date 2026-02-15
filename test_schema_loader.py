"""
Unit tests for schema_loader module.
"""

import json
import yaml
import tempfile
import shutil
import os
from pathlib import Path
import pytest
from unittest.mock import patch

# Import the module to test
import utils.schema_loader as schema_loader
from utils.schema_loader import (
    load_schema,
    get_schema_for_file,
    validate_schema,
    validate_field_config,
    create_fallback_schema,
    list_available_schemas,
    get_schema_info,
    validate_data_against_schema,
    validate_field_value,
    load_config,
    get_configured_schema,
    reload_config,
    get_config_value,
    extract_field_names,
    load_active_schema,
    _load_schema_with_mtime,
)


class TestSchemaLoader:
    """Test class for schema loader."""
    
    def setup_method(self):
        """Set up test environment before each test."""
        # Create temporary directory for testing
        self.test_dir = tempfile.mkdtemp()
        self.original_cwd = os.getcwd()
        os.chdir(self.test_dir)
        
        # Create schemas directory
        Path("schemas").mkdir(exist_ok=True)
    
    def teardown_method(self):
        """Clean up after each test."""
        os.chdir(self.original_cwd)
        shutil.rmtree(self.test_dir)
    
    def create_test_schema(self, filename: str, schema_data: dict):
        """Helper to create test schema files."""
        schema_path = Path("schemas") / filename
        
        if filename.endswith('.yaml') or filename.endswith('.yml'):
            with open(schema_path, 'w') as f:
                yaml.dump(schema_data, f)
        else:
            with open(schema_path, 'w') as f:
                json.dump(schema_data, f, indent=2)
    
    def test_load_schema_yaml_success(self):
        """Test successfully loading a YAML schema."""
        schema_data = {
            "title": "Test Schema",
            "fields": {
                "name": {
                    "type": "string",
                    "label": "Name",
                    "required": True
                }
            }
        }
        
        self.create_test_schema("test.yaml", schema_data)
        
        loaded_schema = load_schema("test.yaml")
        assert loaded_schema == schema_data
    
    def test_load_schema_json_success(self):
        """Test successfully loading a JSON schema."""
        schema_data = {
            "title": "Test Schema",
            "fields": {
                "age": {
                    "type": "number",
                    "label": "Age",
                    "min_value": 0
                }
            }
        }
        
        self.create_test_schema("test.json", schema_data)
        
        loaded_schema = load_schema("test.json")
        assert loaded_schema == schema_data
    
    def test_load_schema_file_not_found(self):
        """Test loading a non-existent schema file."""
        result = load_schema("nonexistent.yaml")
        assert result is None
    
    def test_load_schema_invalid_yaml(self):
        """Test loading invalid YAML."""
        schema_path = Path("schemas/invalid.yaml")
        with open(schema_path, 'w') as f:
            f.write("invalid: yaml: content: [")
        
        result = load_schema("invalid.yaml")
        assert result is None
    
    def test_load_schema_invalid_json(self):
        """Test loading invalid JSON."""
        schema_path = Path("schemas/invalid.json")
        with open(schema_path, 'w') as f:
            f.write('{"invalid": json content}')
        
        result = load_schema("invalid.json")
        assert result is None

    def test_load_schema_unsupported_extension(self):
        schema_path = Path("schemas/unsupported.txt")
        with open(schema_path, "w", encoding="utf-8") as f:
            f.write("fields: {}")

        assert load_schema("unsupported.txt") is None

    def test_load_schema_invalid_structure_returns_none(self):
        self.create_test_schema("invalid_structure.yaml", {"title": "Missing fields"})
        assert load_schema("invalid_structure.yaml") is None

    def test_load_schema_generic_exception_returns_none(self):
        self.create_test_schema("broken.yaml", {"fields": {"a": {"type": "string"}}})

        with patch("utils.schema_loader.validate_schema", side_effect=RuntimeError("boom")):
            assert load_schema("broken.yaml") is None
    
    def test_validate_schema_valid(self):
        """Test validating a valid schema."""
        schema = {
            "fields": {
                "name": {
                    "type": "string",
                    "required": True
                },
                "age": {
                    "type": "number",
                    "min_value": 0,
                    "max_value": 150
                },
                "status": {
                    "type": "enum",
                    "choices": ["active", "inactive"]
                }
            }
        }
        
        assert validate_schema(schema) == True
    
    def test_validate_schema_missing_fields(self):
        """Test validating schema without fields key."""
        schema = {"title": "Test"}
        assert validate_schema(schema) == False

    def test_validate_schema_non_dict_and_non_dict_fields(self):
        assert validate_schema("not-a-dict") is False
        assert validate_schema({"fields": []}) is False
    
    def test_validate_schema_invalid_field_type(self):
        """Test validating schema with invalid field type."""
        schema = {
            "fields": {
                "name": {
                    "type": "invalid_type"
                }
            }
        }
        
        assert validate_schema(schema) == False
    
    def test_validate_field_config_string(self):
        """Test validating string field configuration."""
        field_config = {
            "type": "string",
            "min_length": 1,
            "max_length": 100,
            "pattern": "^[A-Za-z]+$"
        }
        
        assert validate_field_config("test_field", field_config) == True
    
    def test_validate_field_config_enum_missing_choices(self):
        """Test validating enum field without choices."""
        field_config = {
            "type": "enum"
        }
        
        assert validate_field_config("test_field", field_config) == False

    def test_validate_field_config_additional_invalid_cases(self):
        assert validate_field_config("x", "not-a-dict") is False
        assert validate_field_config("x", {}) is False
        assert validate_field_config("x", {"type": "enum", "choices": []}) is False
        assert validate_field_config("x", {"type": "array"}) is False
        assert validate_field_config("x", {"type": "array", "items": {"type": "unknown"}}) is False
        assert validate_field_config("x", {"type": "object"}) is False
        assert validate_field_config("x", {"type": "object", "properties": []}) is False
        assert validate_field_config("x", {"type": "object", "properties": {"a": {"type": "bad"}}}) is False
        assert validate_field_config("x", {"type": "number", "min_value": "bad"}) is False
        assert validate_field_config("x", {"type": "string", "min_length": -1}) is False
        assert validate_field_config("x", {"type": "string", "pattern": "["}) is False
    
    def test_validate_field_config_array_with_items(self):
        """Test validating array field with items definition."""
        field_config = {
            "type": "array",
            "items": {
                "type": "string"
            }
        }
        
        assert validate_field_config("test_field", field_config) == True
    
    def test_validate_field_config_object_with_properties(self):
        """Test validating object field with properties."""
        field_config = {
            "type": "object",
            "properties": {
                "nested_field": {
                    "type": "string"
                }
            }
        }
        
        assert validate_field_config("test_field", field_config) == True
    
    def test_get_schema_for_file_exact_match(self):
        """Test that get_schema_for_file now uses configuration instead of filename matching."""
        # Create a schema that would match by filename in old system
        filename_schema = {
            "fields": {
                "invoice_number": {"type": "string"}
            }
        }
        
        # Create a different schema that's configured as primary
        configured_schema = {
            "title": "Configured Schema",
            "fields": {
                "configured_field": {"type": "string"}
            }
        }
        
        self.create_test_schema("invoice_001_schema.yaml", filename_schema)
        self.create_test_schema("configured_schema.yaml", configured_schema)
        
        # Create config pointing to configured schema (not filename-based)
        config_data = {
            "schema": {
                "primary_schema": "configured_schema.yaml"
            }
        }
        
        with open("config.yaml", 'w') as f:
            yaml.dump(config_data, f)
        
        # Force reload to clear cache
        reload_config()
        
        # Should return configured schema, not filename-based schema
        schema = get_schema_for_file("invoice_001.json")
        assert schema == configured_schema
        assert schema != filename_schema
    
    def test_get_schema_for_file_prefix_match(self):
        """Test that get_schema_for_file ignores filename prefixes and uses configuration."""
        # Create a schema that would match by prefix in old system
        prefix_schema = {
            "fields": {
                "invoice_field": {"type": "string"}
            }
        }
        
        # Create a different schema that's configured as primary
        configured_schema = {
            "title": "Primary Schema",
            "fields": {
                "primary_field": {"type": "number"}
            }
        }
        
        self.create_test_schema("invoice_schema.yaml", prefix_schema)
        self.create_test_schema("primary_schema.yaml", configured_schema)
        
        # Create config pointing to primary schema (ignoring prefix matching)
        config_data = {
            "schema": {
                "primary_schema": "primary_schema.yaml"
            }
        }
        
        with open("config.yaml", 'w') as f:
            yaml.dump(config_data, f)
        
        # Force reload to clear cache
        reload_config()
        
        # Should return configured schema, not prefix-based schema
        schema = get_schema_for_file("invoice_123.json")
        assert schema == configured_schema
        assert schema != prefix_schema
    
    def test_get_schema_for_file_default_fallback(self):
        """Test falling back to default schema."""
        default_schema = {
            "fields": {
                "default_field": {"type": "string"}
            }
        }
        
        self.create_test_schema("default_schema.yaml", default_schema)
        
        schema = get_schema_for_file("unknown_file.json")
        assert schema == default_schema
    
    def test_get_schema_for_file_minimal_fallback(self):
        """Test creating minimal fallback when no schemas exist."""
        schema = get_schema_for_file("unknown_file.json")
        
        # Should return the minimal fallback schema
        assert "fields" in schema
        assert "document_type" in schema["fields"]
        assert "content" in schema["fields"]
    
    def test_create_fallback_schema(self):
        """Test creating fallback schema."""
        schema = create_fallback_schema()
        
        assert "fields" in schema
        assert "document_type" in schema["fields"]
        assert "content" in schema["fields"]
        assert schema["fields"]["document_type"]["type"] == "string"
        assert schema["fields"]["content"]["type"] == "object"
    
    def test_list_available_schemas(self):
        """Test listing available schema files."""
        # Create test schema files
        self.create_test_schema("schema1.yaml", {"fields": {}})
        self.create_test_schema("schema2.yml", {"fields": {}})
        self.create_test_schema("schema3.json", {"fields": {}})
        
        schemas = list_available_schemas()
        
        assert "schema1.yaml" in schemas
        assert "schema2.yml" in schemas
        assert "schema3.json" in schemas
        assert len(schemas) == 3
    
    def test_get_schema_info(self):
        """Test getting schema metadata information."""
        schema_data = {
            "title": "Test Schema",
            "description": "A test schema",
            "fields": {
                "required_field": {
                    "type": "string",
                    "required": True
                },
                "optional_field": {
                    "type": "number",
                    "required": False
                }
            }
        }
        
        self.create_test_schema("test.yaml", schema_data)
        
        info = get_schema_info("test.yaml")
        
        assert info["title"] == "Test Schema"
        assert info["description"] == "A test schema"
        assert info["field_count"] == 2
        assert "required_field" in info["required_fields"]
        assert "optional_field" not in info["required_fields"]
        assert info["field_types"]["required_field"] == "string"
        assert info["field_types"]["optional_field"] == "number"

    def test_get_schema_info_missing_returns_none(self):
        assert get_schema_info("does_not_exist.yaml") is None
    
    def test_validate_data_against_schema_valid(self):
        """Test validating valid data against schema."""
        schema = {
            "fields": {
                "name": {
                    "type": "string",
                    "required": True
                },
                "age": {
                    "type": "number",
                    "min_value": 0
                }
            }
        }
        
        data = {
            "name": "John Doe",
            "age": 30
        }
        
        errors = validate_data_against_schema(data, schema)
        assert len(errors) == 0
    
    def test_validate_data_against_schema_missing_required(self):
        """Test validating data with missing required field."""
        schema = {
            "fields": {
                "name": {
                    "type": "string",
                    "required": True
                }
            }
        }
        
        data = {}
        
        errors = validate_data_against_schema(data, schema)
        assert len(errors) == 1
        assert "Required field 'name' is missing" in errors[0]

    def test_validate_data_against_schema_ignores_unknown_fields(self):
        schema = {"fields": {"name": {"type": "string"}}}
        data = {"name": "ok", "unknown": "value"}
        errors = validate_data_against_schema(data, schema)
        assert errors == []
    
    def test_validate_field_value_string_valid(self):
        """Test validating valid string field."""
        field_config = {
            "type": "string",
            "min_length": 2,
            "max_length": 10
        }
        
        errors = validate_field_value("test_field", "hello", field_config)
        assert len(errors) == 0
    
    def test_validate_field_value_string_too_short(self):
        """Test validating string that's too short."""
        field_config = {
            "type": "string",
            "min_length": 5
        }
        
        errors = validate_field_value("test_field", "hi", field_config)
        assert len(errors) == 1
        assert "must be at least 5 characters" in errors[0]
    
    def test_validate_field_value_number_out_of_range(self):
        """Test validating number out of range."""
        field_config = {
            "type": "number",
            "min_value": 0,
            "max_value": 100
        }
        
        errors = validate_field_value("test_field", 150, field_config)
        assert len(errors) == 1
        assert "must be at most 100" in errors[0]
    
    def test_validate_field_value_enum_invalid_choice(self):
        """Test validating enum with invalid choice."""
        field_config = {
            "type": "enum",
            "choices": ["red", "green", "blue"]
        }
        
        errors = validate_field_value("test_field", "yellow", field_config)
        assert len(errors) == 1
        assert "must be one of: ['red', 'green', 'blue']" in errors[0]
    
    def test_validate_field_value_array_with_items(self):
        """Test validating array with item validation."""
        field_config = {
            "type": "array",
            "items": {
                "type": "string",
                "min_length": 2
            }
        }
        
        # Valid array
        errors = validate_field_value("test_field", ["hello", "world"], field_config)
        assert len(errors) == 0
        
        # Invalid array (item too short)
        errors = validate_field_value("test_field", ["hello", "x"], field_config)
        assert len(errors) == 1
        assert "test_field[1]" in errors[0]

    def test_validate_field_value_additional_types_and_constraints(self):
        assert validate_field_value("f", None, {"type": "string", "required": False}) == []
        assert validate_field_value("f", 1, {"type": "string"}) == ["Field 'f' must be a string"]
        assert validate_field_value("f", "toolong", {"type": "string", "max_length": 3}) == [
            "Field 'f' must be at most 3 characters"
        ]
        assert validate_field_value("f", "abc", {"type": "string", "pattern": "^\\d+$"}) == [
            "Field 'f' does not match required pattern"
        ]
        assert validate_field_value("f", "x", {"type": "number"}) == ["Field 'f' must be a number"]
        assert validate_field_value("f", -1, {"type": "number", "min_value": 0}) == [
            "Field 'f' must be at least 0"
        ]
        assert validate_field_value("f", "x", {"type": "boolean"}) == ["Field 'f' must be a boolean"]
        assert validate_field_value("f", "x", {"type": "array"}) == ["Field 'f' must be an array"]
        assert validate_field_value("f", "x", {"type": "object"}) == ["Field 'f' must be an object"]
        object_errors = validate_field_value(
            "obj",
            {},
            {"type": "object", "properties": {"name": {"type": "string", "required": True}}},
        )
        assert any("obj.name" in err for err in object_errors)

    def test_load_config_default(self):
        """Test loading default configuration when no config file exists."""
        # Ensure no config file exists
        config_path = Path("config.yaml")
        if config_path.exists():
            config_path.unlink()
        
        # Force reload to clear cache
        reload_config()
        
        config = load_config()
        
        # Check default values
        assert config["app"]["name"] == "JSON QA Webapp"
        assert config["schema"]["primary_schema"] == "default_schema.yaml"
        assert config["schema"]["fallback_schema"] == "default_schema.yaml"

    def test_load_config_from_file(self):
        """Test loading configuration from config.yaml file."""
        # Create test config file
        config_data = {
            "app": {
                "name": "Test QA App",
                "version": "2.0.0"
            },
            "schema": {
                "primary_schema": "invoice_schema.yaml",
                "fallback_schema": "default_schema.yaml"
            },
            "ui": {
                "page_title": "Test Page"
            }
        }
        
        with open("config.yaml", 'w') as f:
            yaml.dump(config_data, f)
        
        # Force reload to clear cache
        reload_config()
        
        config = load_config()
        
        # Check loaded values
        assert config["app"]["name"] == "Test QA App"
        assert config["app"]["version"] == "2.0.0"
        assert config["schema"]["primary_schema"] == "invoice_schema.yaml"
        assert config["ui"]["page_title"] == "Test Page"

    def test_load_config_invalid_yaml(self):
        """Test loading configuration with invalid YAML."""
        # Create invalid YAML file
        with open("config.yaml", 'w') as f:
            f.write("invalid: yaml: content: [")
        
        # Force reload to clear cache
        reload_config()
        
        config = load_config()
        
        # Should fall back to defaults
        assert config["app"]["name"] == "JSON QA Webapp"
        assert config["schema"]["primary_schema"] == "default_schema.yaml"

    def test_get_config_value(self):
        """Test getting specific configuration values."""
        # Create test config
        config_data = {
            "schema": {
                "primary_schema": "test_schema.yaml"
            },
            "ui": {
                "page_title": "Custom Title"
            }
        }
        
        with open("config.yaml", 'w') as f:
            yaml.dump(config_data, f)
        
        # Force reload to clear cache
        reload_config()
        
        # Test getting existing values
        assert get_config_value("schema", "primary_schema") == "test_schema.yaml"
        assert get_config_value("ui", "page_title") == "Custom Title"
        
        # Test getting non-existent values with defaults
        assert get_config_value("nonexistent", "key", "default") == "default"
        assert get_config_value("schema", "nonexistent", "fallback") == "fallback"

    def test_get_configured_schema_primary(self):
        """Test getting configured schema when primary exists."""
        # Create test schemas
        primary_schema = {
            "title": "Primary Schema",
            "fields": {
                "name": {"type": "string", "required": True}
            }
        }
        
        fallback_schema = {
            "title": "Fallback Schema", 
            "fields": {
                "content": {"type": "string"}
            }
        }
        
        self.create_test_schema("primary_schema.yaml", primary_schema)
        self.create_test_schema("fallback_schema.yaml", fallback_schema)
        
        # Create config pointing to primary
        config_data = {
            "schema": {
                "primary_schema": "primary_schema.yaml",
                "fallback_schema": "fallback_schema.yaml"
            }
        }
        
        with open("config.yaml", 'w') as f:
            yaml.dump(config_data, f)
        
        # Force reload to clear cache
        reload_config()
        
        schema = get_configured_schema()
        
        # Should get primary schema
        assert schema["title"] == "Primary Schema"
        assert "name" in schema["fields"]

    def test_get_configured_schema_fallback(self):
        """Test getting configured schema when primary doesn't exist."""
        # Create only fallback schema
        fallback_schema = {
            "title": "Fallback Schema",
            "fields": {
                "content": {"type": "string"}
            }
        }
        
        self.create_test_schema("fallback_schema.yaml", fallback_schema)
        
        # Create config pointing to non-existent primary
        config_data = {
            "schema": {
                "primary_schema": "nonexistent_schema.yaml",
                "fallback_schema": "fallback_schema.yaml"
            }
        }
        
        with open("config.yaml", 'w') as f:
            yaml.dump(config_data, f)
        
        # Force reload to clear cache
        reload_config()
        
        schema = get_configured_schema()
        
        # Should get fallback schema
        assert schema["title"] == "Fallback Schema"
        assert "content" in schema["fields"]

    def test_get_configured_schema_minimal_fallback(self):
        """Test getting minimal fallback when no schemas exist."""
        # Create config pointing to non-existent schemas
        config_data = {
            "schema": {
                "primary_schema": "nonexistent_primary.yaml",
                "fallback_schema": "nonexistent_fallback.yaml"
            }
        }
        
        with open("config.yaml", 'w') as f:
            yaml.dump(config_data, f)
        
        # Force reload to clear cache
        reload_config()
        
        schema = get_configured_schema()
        
        # Should get minimal fallback
        assert "fields" in schema
        assert "document_type" in schema["fields"]
        assert "content" in schema["fields"]

    def test_get_schema_for_file_uses_configuration(self):
        """Test that get_schema_for_file now uses configuration instead of filename."""
        # Create test schema
        test_schema = {
            "title": "Configured Schema",
            "fields": {
                "configured_field": {"type": "string"}
            }
        }
        
        self.create_test_schema("configured_schema.yaml", test_schema)
        
        # Create config
        config_data = {
            "schema": {
                "primary_schema": "configured_schema.yaml"
            }
        }
        
        with open("config.yaml", 'w') as f:
            yaml.dump(config_data, f)
        
        # Force reload to clear cache
        reload_config()
        
        # Test with different filenames - should all return same configured schema
        schema1 = get_schema_for_file("invoice_001.json")
        schema2 = get_schema_for_file("completely_different_name.json")
        schema3 = get_schema_for_file("1781037_ITL HARDWARE & ENGINEERING SUPPLIES PTE LTD_862.33.json")
        
        # All should return the same configured schema
        assert schema1["title"] == "Configured Schema"
        assert schema2["title"] == "Configured Schema"
        assert schema3["title"] == "Configured Schema"
        assert schema1 == schema2 == schema3

    def test_extract_field_names_handles_invalid_schema(self):
        assert extract_field_names({"fields": {"a": {}}}) == {"a"}
        assert extract_field_names({"bad": {}}) == set()
        assert extract_field_names("bad") == set()

    def test_load_schema_with_mtime_delegates_to_load_schema(self):
        with patch("utils.schema_loader.load_schema", return_value={"fields": {}}) as mock_load:
            result = _load_schema_with_mtime("a.yaml", 123.0)
        assert result == {"fields": {}}
        mock_load.assert_called_once_with("a.yaml")

    def test_load_active_schema_not_found(self):
        assert load_active_schema("missing.yaml") is None

    def test_load_active_schema_updates_session_state(self):
        schema = {"fields": {"name": {"type": "string"}}, "schema_version": "v3"}
        schema_path = Path("schemas/active.yaml")
        schema_path.write_text("fields: {name: {type: string}}\n", encoding="utf-8")
        fake_st = type("FakeSt", (), {"session_state": {}})()
        with patch("utils.schema_loader._load_schema_with_mtime", return_value=schema), patch(
            "utils.schema_loader.os.path.getmtime", return_value=42.0
        ), patch("utils.schema_loader.st", fake_st):
            result = load_active_schema("active.yaml")

        assert result == schema
        assert fake_st.session_state["active_schema"] == schema
        assert fake_st.session_state["active_schema_mtime"] == 42.0
        assert fake_st.session_state["schema_fields"] == {"name"}
        assert fake_st.session_state["schema_version"] == "v3"

    def test_load_config_generic_exception_uses_defaults(self):
        with open("config.yaml", "w", encoding="utf-8") as f:
            f.write("schema:\n  primary_schema: default_schema.yaml\n")

        reload_config()
        with patch("utils.schema_loader.yaml.safe_load", side_effect=RuntimeError("boom")):
            config = load_config()

        assert config["app"]["name"] == "JSON QA Webapp"


if __name__ == "__main__":
    # Run tests if script is executed directly
    pytest.main([__file__])
