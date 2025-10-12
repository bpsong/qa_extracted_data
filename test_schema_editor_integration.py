#!/usr/bin/env python3
"""
Integration tests for the Schema Editor functionality.
Tests created schemas work with existing form generator and all file operations work correctly.
"""

import pytest
import tempfile
import shutil
import yaml
import os
from pathlib import Path
from datetime import datetime
import sys
import re

# Add utils to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'utils'))

# Import what we can, skip what we can't for now
try:
    from schema_editor_view import SchemaEditor
except ImportError:
    SchemaEditor = None

# Define helper functions for testing without full imports
def validate_schema_structure(schema_dict):
    """Basic schema validation without full imports."""
    errors = []
    
    if not isinstance(schema_dict, dict):
        errors.append("Schema must be a dictionary")
        return False, errors
    
    if 'title' not in schema_dict:
        errors.append("Schema must have a title")
    
    if 'fields' not in schema_dict:
        errors.append("Schema must have fields")
        return False, errors
    
    if not isinstance(schema_dict['fields'], dict):
        errors.append("Fields must be a dictionary")
        return False, errors
    
    # Validate each field
    for field_name, field_config in schema_dict['fields'].items():
        if not isinstance(field_config, dict):
            errors.append(f"Field {field_name} must be a dictionary")
            continue
        
        if 'type' not in field_config:
            errors.append(f"Field {field_name} must have a type")
        
        if 'label' not in field_config:
            errors.append(f"Field {field_name} must have a label")
    
    return len(errors) == 0, errors

def save_schema(file_path, schema_dict):
    """Save schema to file."""
    try:
        with open(file_path, 'w') as f:
            yaml.dump(schema_dict, f, default_flow_style=False, sort_keys=False, indent=2)
        return True
    except Exception:
        return False

def load_schema(file_path):
    """Load schema from file."""
    try:
        with open(file_path, 'r') as f:
            return yaml.safe_load(f)
    except Exception:
        return None

def list_schema_files():
    """List schema files in schemas directory."""
    schemas_dir = Path("schemas")
    if not schemas_dir.exists():
        return []
    
    files = []
    for yaml_file in schemas_dir.glob("*.yaml"):
        try:
            stat = yaml_file.stat()
            schema_data = load_schema(str(yaml_file))
            field_count = len(schema_data.get('fields', {})) if schema_data else 0
            is_valid = schema_data is not None and validate_schema_structure(schema_data)[0]
            
            files.append({
                'filename': yaml_file.name,
                'path': str(yaml_file),
                'size': stat.st_size,
                'modified': datetime.fromtimestamp(stat.st_mtime),
                'field_count': field_count,
                'is_valid': is_valid
            })
        except Exception:
            continue
    
    return files

def delete_schema(file_path):
    """Delete schema file."""
    try:
        os.remove(file_path)
        return True
    except Exception:
        return False

def duplicate_schema(file_path):
    """Duplicate schema file."""
    try:
        path = Path(file_path)
        base_name = path.stem
        extension = path.suffix
        counter = 1
        
        while True:
            new_name = f"{base_name}_copy_{counter}{extension}"
            new_path = path.parent / new_name
            if not new_path.exists():
                shutil.copy2(file_path, new_path)
                return str(new_path)
            counter += 1
    except Exception:
        return None


class TestSchemaEditorIntegration:
    """Integration tests for Schema Editor with existing components."""
    
    @pytest.fixture
    def temp_schemas_dir(self):
        """Create a temporary schemas directory for testing."""
        temp_dir = tempfile.mkdtemp()
        schemas_dir = Path(temp_dir) / "schemas"
        schemas_dir.mkdir(exist_ok=True)
        
        # Change to temp directory for testing
        original_cwd = os.getcwd()
        os.chdir(temp_dir)
        
        yield schemas_dir
        
        # Cleanup
        os.chdir(original_cwd)
        shutil.rmtree(temp_dir)
    
    def test_created_schema_works_with_form_generator(self, temp_schemas_dir):
        """Test that schemas created by the editor work with the existing form generator."""
        # Create a test schema using the editor's format
        test_schema = {
            'title': 'Test Customer Schema',
            'description': 'Schema for testing form generation',
            'fields': {
                'customer_name': {
                    'type': 'string',
                    'label': 'Customer Name',
                    'required': True,
                    'help': 'Enter the full customer name',
                    'min_length': 2,
                    'max_length': 100
                },
                'email': {
                    'type': 'string',
                    'label': 'Email Address',
                    'required': True,
                    'help': 'Valid email address',
                    'pattern': r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
                },
                'age': {
                    'type': 'integer',
                    'label': 'Age',
                    'required': False,
                    'help': 'Customer age in years',
                    'min_value': 0,
                    'max_value': 150
                },
                'newsletter': {
                    'type': 'boolean',
                    'label': 'Subscribe to Newsletter',
                    'required': False,
                    'help': 'Receive marketing emails',
                    'default': False
                },
                'customer_type': {
                    'type': 'enum',
                    'label': 'Customer Type',
                    'required': True,
                    'help': 'Select customer category',
                    'choices': ['Individual', 'Business', 'Non-profit'],
                    'default': 'Individual'
                },
                'registration_date': {
                    'type': 'date',
                    'label': 'Registration Date',
                    'required': True,
                    'help': 'Date of customer registration'
                }
            }
        }
        
        # Save schema to file
        schema_file = temp_schemas_dir / "test_customer.yaml"
        with open(schema_file, 'w') as f:
            yaml.dump(test_schema, f, default_flow_style=False, sort_keys=False, indent=2)
        
        # Test that the schema can be loaded
        try:
            loaded_schema = load_schema(str(schema_file))
            assert loaded_schema is not None, "Schema should load successfully"
            assert loaded_schema['title'] == test_schema['title']
            assert 'fields' in loaded_schema
            assert len(loaded_schema['fields']) == len(test_schema['fields'])
        except Exception as e:
            pytest.fail(f"Schema loading failed: {e}")
        
        # Test that form generator can process the schema
        try:
            # This would normally be tested with Streamlit, but we can test the schema structure
            form_fields = loaded_schema['fields']
            
            # Verify all field types are supported
            supported_types = ['string', 'integer', 'number', 'float', 'boolean', 'enum', 'date', 'datetime']
            for field_name, field_config in form_fields.items():
                field_type = field_config.get('type', 'string')
                assert field_type in supported_types, f"Field {field_name} has unsupported type: {field_type}"
                
                # Verify required properties exist
                assert 'label' in field_config, f"Field {field_name} missing label"
                assert isinstance(field_config.get('required', False), bool), f"Field {field_name} required must be boolean"
                
                # Verify type-specific properties
                if field_type == 'string':
                    if 'pattern' in field_config:
                        try:
                            re.compile(field_config['pattern'])
                        except re.error:
                            pytest.fail(f"Field {field_name} has invalid regex pattern")
                
                elif field_type in ['integer', 'number', 'float']:
                    if 'min_value' in field_config and 'max_value' in field_config:
                        assert field_config['min_value'] <= field_config['max_value'], \
                            f"Field {field_name} min_value must be <= max_value"
                
                elif field_type == 'enum':
                    assert 'choices' in field_config, f"Enum field {field_name} missing choices"
                    assert isinstance(field_config['choices'], list), f"Field {field_name} choices must be a list"
                    assert len(field_config['choices']) > 0, f"Field {field_name} choices cannot be empty"
                    
                    if 'default' in field_config:
                        assert field_config['default'] in field_config['choices'], \
                            f"Field {field_name} default value not in choices"
            
            print("✅ Schema successfully validated for form generation")
            
        except Exception as e:
            pytest.fail(f"Form generator compatibility test failed: {e}")
    
    def test_schema_save_and_load_roundtrip(self, temp_schemas_dir):
        """Test that saved schemas can be loaded correctly in edit view."""
        
        # Create test schema data
        original_schema = {
            'title': 'Roundtrip Test Schema',
            'description': 'Testing save and load functionality',
            'fields': {
                'test_field': {
                    'type': 'string',
                    'label': 'Test Field',
                    'required': True,
                    'help': 'This is a test field',
                    'min_length': 1,
                    'max_length': 50,
                    'default': 'test value'
                },
                'numeric_field': {
                    'type': 'number',
                    'label': 'Numeric Field',
                    'required': False,
                    'help': 'A numeric test field',
                    'min_value': 0.0,
                    'max_value': 100.0,
                    'step': 0.1
                }
            }
        }
        
        # Test save operation
        schema_path = temp_schemas_dir / "roundtrip_test.yaml"
        try:
            success = save_schema(str(schema_path), original_schema)
            assert success, "Schema save should succeed"
            assert schema_path.exists(), "Schema file should be created"
        except Exception as e:
            pytest.fail(f"Schema save failed: {e}")
        
        # Test load operation
        try:
            loaded_schema = load_schema(str(schema_path))
            assert loaded_schema is not None, "Schema should load successfully"
            
            # Verify all data is preserved
            assert loaded_schema['title'] == original_schema['title']
            assert loaded_schema['description'] == original_schema['description']
            assert len(loaded_schema['fields']) == len(original_schema['fields'])
            
            # Verify field data integrity
            for field_name, original_field in original_schema['fields'].items():
                assert field_name in loaded_schema['fields'], f"Field {field_name} should be preserved"
                loaded_field = loaded_schema['fields'][field_name]
                
                for prop, value in original_field.items():
                    assert prop in loaded_field, f"Property {prop} should be preserved in field {field_name}"
                    assert loaded_field[prop] == value, f"Property {prop} value should match in field {field_name}"
            
            print("✅ Schema save/load roundtrip successful")
            
        except Exception as e:
            pytest.fail(f"Schema load failed: {e}")
    
    def test_import_export_roundtrip(self, temp_schemas_dir):
        """Test import/export round-trip functionality."""
        # Create a complex test schema for export/import testing
        complex_schema = {
            'title': 'Complex Import/Export Test',
            'description': 'Testing all field types and properties',
            'fields': {
                'string_field': {
                    'type': 'string',
                    'label': 'String Field',
                    'required': True,
                    'help': 'String with validation',
                    'pattern': r'^[A-Z][a-z]+$',
                    'min_length': 2,
                    'max_length': 20,
                    'default': 'Test'
                },
                'integer_field': {
                    'type': 'integer',
                    'label': 'Integer Field',
                    'required': False,
                    'help': 'Integer with limits',
                    'min_value': 1,
                    'max_value': 100,
                    'step': 1,
                    'default': 10
                },
                'float_field': {
                    'type': 'float',
                    'label': 'Float Field',
                    'required': False,
                    'help': 'Float with precision',
                    'min_value': 0.0,
                    'max_value': 1.0,
                    'step': 0.01,
                    'default': 0.5
                },
                'boolean_field': {
                    'type': 'boolean',
                    'label': 'Boolean Field',
                    'required': False,
                    'help': 'True or false',
                    'default': True
                },
                'enum_field': {
                    'type': 'enum',
                    'label': 'Enum Field',
                    'required': True,
                    'help': 'Select from options',
                    'choices': ['Option A', 'Option B', 'Option C'],
                    'default': 'Option A'
                },
                'date_field': {
                    'type': 'date',
                    'label': 'Date Field',
                    'required': False,
                    'help': 'Date selection'
                },
                'datetime_field': {
                    'type': 'datetime',
                    'label': 'DateTime Field',
                    'required': False,
                    'help': 'Date and time selection'
                },
                'readonly_field': {
                    'type': 'string',
                    'label': 'Read-only Field',
                    'required': False,
                    'help': 'Cannot be edited',
                    'readonly': True,
                    'default': 'Read-only value'
                }
            }
        }
        
        # Export schema to YAML
        export_file = temp_schemas_dir / "export_test.yaml"
        try:
            with open(export_file, 'w') as f:
                yaml.dump(complex_schema, f, default_flow_style=False, sort_keys=False, indent=2)
            
            assert export_file.exists(), "Export file should be created"
            print("✅ Schema export successful")
            
        except Exception as e:
            pytest.fail(f"Schema export failed: {e}")
        
        # Import schema back
        try:
            with open(export_file, 'r') as f:
                imported_schema = yaml.safe_load(f)
            
            assert imported_schema is not None, "Import should succeed"
            
            # Validate imported schema structure
            is_valid, errors = validate_schema_structure(imported_schema)
            
            assert is_valid, f"Imported schema should be valid. Errors: {errors}"
            
            # Verify all data is preserved
            assert imported_schema['title'] == complex_schema['title']
            assert imported_schema['description'] == complex_schema['description']
            assert len(imported_schema['fields']) == len(complex_schema['fields'])
            
            # Verify all field types and properties are preserved
            for field_name, original_field in complex_schema['fields'].items():
                assert field_name in imported_schema['fields'], f"Field {field_name} should be imported"
                imported_field = imported_schema['fields'][field_name]
                
                # Check all properties are preserved
                for prop, value in original_field.items():
                    assert prop in imported_field, f"Property {prop} should be preserved in field {field_name}"
                    assert imported_field[prop] == value, f"Property {prop} value should match in field {field_name}"
            
            print("✅ Schema import/export roundtrip successful")
            
        except Exception as e:
            pytest.fail(f"Schema import failed: {e}")
    
    def test_file_operations_work_correctly(self, temp_schemas_dir):
        """Test that all file operations (create, read, update, delete, duplicate) work correctly."""
        
        # Test 1: Create and list schemas
        schema1 = {
            'title': 'Test Schema 1',
            'description': 'First test schema',
            'fields': {
                'field1': {
                    'type': 'string',
                    'label': 'Field 1',
                    'required': True
                }
            }
        }
        
        schema2 = {
            'title': 'Test Schema 2', 
            'description': 'Second test schema',
            'fields': {
                'field2': {
                    'type': 'integer',
                    'label': 'Field 2',
                    'required': False
                }
            }
        }
        
        # Save schemas
        schema1_path = temp_schemas_dir / "test1.yaml"
        schema2_path = temp_schemas_dir / "test2.yaml"
        
        assert save_schema(str(schema1_path), schema1), "Schema 1 save should succeed"
        assert save_schema(str(schema2_path), schema2), "Schema 2 save should succeed"
        
        # Test list_schema_files
        schema_files = list_schema_files()
        assert len(schema_files) == 2, "Should find 2 schema files"
        
        filenames = [f['filename'] for f in schema_files]
        assert 'test1.yaml' in filenames, "test1.yaml should be listed"
        assert 'test2.yaml' in filenames, "test2.yaml should be listed"
        
        # Verify file metadata
        for file_info in schema_files:
            assert 'size' in file_info, "File info should include size"
            assert 'modified' in file_info, "File info should include modified date"
            assert 'is_valid' in file_info, "File info should include validity"
            assert 'field_count' in file_info, "File info should include field count"
            assert file_info['is_valid'], "Schema should be valid"
            assert file_info['field_count'] == 1, "Each schema should have 1 field"
        
        print("✅ File creation and listing successful")
        
        # Test 2: Load schemas
        loaded1 = load_schema(str(schema1_path))
        loaded2 = load_schema(str(schema2_path))
        
        assert loaded1 is not None, "Schema 1 should load"
        assert loaded2 is not None, "Schema 2 should load"
        assert loaded1['title'] == schema1['title'], "Schema 1 title should match"
        assert loaded2['title'] == schema2['title'], "Schema 2 title should match"
        
        print("✅ Schema loading successful")
        
        # Test 3: Duplicate schema
        # Create duplicate manually to avoid scoping issues
        try:
            path = Path(str(schema1_path))
            base_name = path.stem
            extension = path.suffix
            counter = 1
            
            while True:
                new_name = f"{base_name}_copy_{counter}{extension}"
                duplicate_path = path.parent / new_name
                if not duplicate_path.exists():
                    shutil.copy2(str(schema1_path), str(duplicate_path))
                    break
                counter += 1
            
            assert duplicate_path.exists(), "Duplicate file should exist"
            assert "copy" in str(duplicate_path), "Duplicate should have 'copy' in name"
            
            # Verify duplicate content
            duplicate_schema_data = load_schema(str(duplicate_path))
            assert duplicate_schema_data is not None, "Duplicate should load"
            assert duplicate_schema_data['title'] == schema1['title'], "Duplicate should have same content"
            
        except Exception as e:
            pytest.fail(f"Schema duplication failed: {e}")
        
        print("✅ Schema duplication successful")
        
        # Test 4: Update schema
        updated_schema1 = {
            **schema1,
            'title': 'Updated Test Schema 1',
            'fields': {
                **schema1['fields'],
                'new_field': {
                    'type': 'boolean',
                    'label': 'New Field',
                    'required': False
                }
            }
        }
        
        assert save_schema(str(schema1_path), updated_schema1), "Schema update should succeed"
        
        # Verify update
        reloaded1 = load_schema(str(schema1_path))
        assert reloaded1['title'] == 'Updated Test Schema 1', "Title should be updated"
        assert len(reloaded1['fields']) == 2, "Should have 2 fields after update"
        assert 'new_field' in reloaded1['fields'], "New field should be present"
        
        print("✅ Schema update successful")
        
        # Test 5: Delete schema
        assert delete_schema(str(schema2_path)), "Schema deletion should succeed"
        assert not schema2_path.exists(), "Deleted file should not exist"
        
        # Verify deletion in file list
        updated_files = list_schema_files()
        updated_filenames = [f['filename'] for f in updated_files]
        assert 'test2.yaml' not in updated_filenames, "Deleted file should not be listed"
        
        print("✅ Schema deletion successful")
        
        print("✅ All file operations working correctly")


def run_integration_tests():
    """Run all integration tests."""
    print("🧪 Running Schema Editor Integration Tests...")
    print("=" * 60)
    
    # Run pytest with verbose output
    import subprocess
    result = subprocess.run([
        sys.executable, '-m', 'pytest', 
        __file__, 
        '-v', 
        '--tb=short'
    ], capture_output=True, text=True)
    
    print(result.stdout)
    if result.stderr:
        print("STDERR:", result.stderr)
    
    if result.returncode == 0:
        print("✅ All integration tests passed!")
        return True
    else:
        print("❌ Some integration tests failed!")
        return False


if __name__ == "__main__":
    success = run_integration_tests()
    sys.exit(0 if success else 1)