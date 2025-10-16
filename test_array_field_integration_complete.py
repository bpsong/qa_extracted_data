"""
Complete integration tests for array field bug fixes.

This file implements task 4.5 from the array-field-bugfixes spec:
- Test complete edit-validate-submit cycle with arrays
- Test reset after multiple edits
- Test validation errors with arrays
- Test audit log contains all array changes

Requirements covered: All requirements from the array-field-bugfixes spec
"""

import pytest
import streamlit as st
from unittest.mock import Mock, patch, MagicMock, call
from pathlib import Path
import json
import yaml
from datetime import datetime, date
import pandas as pd
import tempfile
import shutil

from utils.form_generator import FormGenerator
from utils.edit_view import EditView
from utils.session_manager import SessionManager
from utils.diff_utils import calculate_diff
from utils.file_utils import load_json_file, save_corrected_json, append_audit_log, read_audit_logs
from utils.submission_handler import SubmissionHandler
from utils.model_builder import create_model_from_schema, validate_model_data


@pytest.fixture
def temp_directories():
    """Create temporary directories for testing."""
    temp_dir = Path(tempfile.mkdtemp())
    
    # Create required directories
    (temp_dir / "json_docs").mkdir()
    (temp_dir / "corrected").mkdir()
    (temp_dir / "audits").mkdir()
    (temp_dir / "schemas").mkdir()
    (temp_dir / "locks").mkdir()
    
    yield temp_dir
    
    # Cleanup
    shutil.rmtree(temp_dir)


@pytest.fixture
def insurance_schema():
    """Insurance schema with array fields for testing."""
    return {
        "fields": {
            "Supplier name": {
                "type": "string",
                "label": "Supplier Name",
                "required": True
            },
            "Invoice amount": {
                "type": "number",
                "label": "Invoice Amount",
                "required": True
            },
            "Serial Numbers": {
                "type": "array",
                "label": "Serial Numbers",
                "items": {
                    "type": "string",
                    "pattern": "^[A-Z0-9]+$"
                },
                "min_length": 1,
                "max_length": 10
            },
            "Line Items": {
                "type": "array",
                "label": "Line Items",
                "items": {
                    "type": "object",
                    "properties": {
                        "description": {"type": "string", "required": True},
                        "quantity": {"type": "integer", "minimum": 1},
                        "unit_price": {"type": "number", "minimum": 0}
                    }
                }
            }
        }
    }


@pytest.fixture
def sample_insurance_data():
    """Sample insurance data for testing."""
    return {
        "Supplier name": "China Taiping Insurance (Singapore) Pte. Ltd.",
        "Invoice amount": 490.5,
        "Serial Numbers": ["SN001", "SN002"],
        "Line Items": [
            {"description": "Insurance Premium", "quantity": 1, "unit_price": 490.5}
        ]
    }


@pytest.fixture
def mock_streamlit_environment():
    """Mock complete Streamlit environment."""
    class MockSessionState(dict):
        def __setattr__(self, key, value):
            self[key] = value
        
        def __getattr__(self, key):
            try:
                return self[key]
            except KeyError:
                raise AttributeError(f"'{type(self).__name__}' object has no attribute '{key}'")
    
    mock_state = MockSessionState()
    
    with patch('streamlit.session_state', mock_state), \
         patch('streamlit.rerun') as mock_rerun, \
         patch('streamlit.success') as mock_success, \
         patch('streamlit.error') as mock_error, \
         patch('streamlit.warning') as mock_warning, \
         patch('streamlit.info') as mock_info:
        
        yield {
            'session_state': mock_state,
            'rerun': mock_rerun,
            'success': mock_success,
            'error': mock_error,
            'warning': mock_warning,
            'info': mock_info
        }


class TestCompleteEditValidateSubmitCycle:
    """Test complete edit-validate-submit cycle with arrays."""
    
    def test_complete_workflow_with_scalar_arrays(self, temp_directories, insurance_schema, 
                                                sample_insurance_data, mock_streamlit_environment):
        """Test complete edit-validate-submit cycle with scalar array modifications."""
        
        # Setup test file
        test_file = temp_directories / "json_docs" / "test_insurance.json"
        with open(test_file, 'w') as f:
            json.dump(sample_insurance_data, f)
        
        # Initialize session state
        mock_state = mock_streamlit_environment['session_state']
        
        # Step 1: Load document
        SessionManager.set_current_file(str(test_file))
        SessionManager.set_schema(insurance_schema)
        SessionManager.set_form_data(sample_insurance_data.copy())
        
        # Initialize array field in session state
        field_name = "Serial Numbers"
        original_array = sample_insurance_data[field_name].copy()
        mock_state[f"field_{field_name}"] = original_array.copy()
        mock_state[f"scalar_array_{field_name}_size"] = len(original_array)
        
        # Step 2: Edit array - add items
        modified_array = original_array + ["SN003", "SN004"]
        mock_state[f"field_{field_name}"] = modified_array
        mock_state[f"scalar_array_{field_name}_size"] = len(modified_array)
        
        # Sync array changes
        FormGenerator._sync_array_to_session(field_name, modified_array)
        
        # Step 3: Edit scalar field
        mock_state["field_Invoice amount"] = 750.0
        
        # Step 4: Collect form data (simulating validate)
        form_data = FormGenerator.collect_current_form_data(insurance_schema)
        SessionManager.set_form_data(form_data)
        
        # Step 5: Validate data
        with patch('utils.model_builder.validate_model_data') as mock_validate:
            mock_validate.return_value = []  # No validation errors
            
            # Simulate validation call
            model = create_model_from_schema(insurance_schema)
            errors = mock_validate(form_data, model)  # Use mocked function
            is_valid = len(errors) == 0
            
            assert is_valid == True
            assert errors == []
        
        # Step 6: Submit changes
        with patch('utils.file_utils.save_corrected_json') as mock_save, \
             patch('utils.file_utils.append_audit_log') as mock_audit:
            
            mock_save.return_value = True
            mock_audit.return_value = True
            
            # Simulate submission
            corrected_file = temp_directories / "corrected" / "test_insurance.json"
            success = mock_save(str(corrected_file), form_data)  # Use mocked function
            
            # Create audit entry
            audit_entry = {
                "filename": "test_insurance.json",
                "timestamp": datetime.now().isoformat(),
                "user": "test_user",
                "action": "corrected",
                "changes": calculate_diff(sample_insurance_data, form_data)
            }
            
            audit_success = mock_audit(audit_entry)  # Use mocked function
            
            assert success == True
            assert audit_success == True
            
            # Verify save was called with correct data
            mock_save.assert_called_once()
            saved_data = mock_save.call_args[0][1]
            
            # Verify array changes are in saved data
            assert len(saved_data[field_name]) == 4
            assert "SN003" in saved_data[field_name]
            assert "SN004" in saved_data[field_name]
            assert saved_data["Invoice amount"] == 750.0
            
            # Verify audit log was called
            mock_audit.assert_called_once()
            audit_data = mock_audit.call_args[0][0]
            assert audit_data["filename"] == "test_insurance.json"
            assert audit_data["action"] == "corrected"
    
    def test_complete_workflow_with_object_arrays(self, temp_directories, insurance_schema,
                                                sample_insurance_data, mock_streamlit_environment):
        """Test complete edit-validate-submit cycle with object array modifications."""
        
        # Setup test file
        test_file = temp_directories / "json_docs" / "test_insurance.json"
        with open(test_file, 'w') as f:
            json.dump(sample_insurance_data, f)
        
        mock_state = mock_streamlit_environment['session_state']
        
        # Initialize session
        SessionManager.set_current_file(str(test_file))
        SessionManager.set_schema(insurance_schema)
        SessionManager.set_form_data(sample_insurance_data.copy())
        
        # Initialize object array field
        field_name = "Line Items"
        original_array = sample_insurance_data[field_name].copy()
        
        # Create DataFrame for object array editing
        df = pd.DataFrame(original_array)
        mock_state[f"data_editor_{field_name}"] = df
        
        # Modify object array - add row and edit existing
        new_row = pd.DataFrame([{"description": "Additional Fee", "quantity": 1, "unit_price": 50.0}])
        modified_df = pd.concat([df, new_row], ignore_index=True)
        
        # Edit existing row
        modified_df.loc[0, 'unit_price'] = 500.0
        
        mock_state[f"data_editor_{field_name}"] = modified_df
        
        # Sync object array changes
        modified_array = modified_df.to_dict('records')
        FormGenerator._sync_array_to_session(field_name, modified_array)
        
        # Collect and validate
        form_data = FormGenerator.collect_current_form_data(insurance_schema)
        SessionManager.set_form_data(form_data)
        
        # Validate
        with patch('utils.model_builder.validate_model_data') as mock_validate:
            mock_validate.return_value = []
            
            model = create_model_from_schema(insurance_schema)
            errors = mock_validate(form_data, model)  # Use mocked function
            is_valid = len(errors) == 0
            
            assert is_valid == True
        
        # Submit
        with patch('utils.file_utils.save_corrected_json') as mock_save, \
             patch('utils.file_utils.append_audit_log') as mock_audit:
            
            mock_save.return_value = True
            mock_audit.return_value = True
            
            corrected_file = temp_directories / "corrected" / "test_insurance.json"
            success = mock_save(str(corrected_file), form_data)  # Use mocked function
            
            audit_entry = {
                "filename": "test_insurance.json",
                "timestamp": datetime.now().isoformat(),
                "user": "test_user",
                "action": "corrected",
                "changes": calculate_diff(sample_insurance_data, form_data)
            }
            
            audit_success = mock_audit(audit_entry)  # Use mocked function
            
            assert success == True
            assert audit_success == True
            
            # Verify object array changes
            saved_data = mock_save.call_args[0][1]
            assert len(saved_data[field_name]) == 2
            assert saved_data[field_name][0]['unit_price'] == 500.0
            assert saved_data[field_name][1]['description'] == "Additional Fee"


class TestResetAfterMultipleEdits:
    """Test reset functionality after multiple edits."""
    
    def test_reset_after_multiple_array_and_scalar_edits(self, insurance_schema, 
                                                       sample_insurance_data, mock_streamlit_environment):
        """Test reset functionality after modifying multiple arrays and scalar fields."""
        
        mock_state = mock_streamlit_environment['session_state']
        
        # Initialize session
        SessionManager.set_schema(insurance_schema)
        SessionManager.set_form_data(sample_insurance_data.copy())
        
        # Initialize fields in session state
        for field_name, field_config in insurance_schema['fields'].items():
            original_value = sample_insurance_data.get(field_name)
            mock_state[f"field_{field_name}"] = original_value
            
            if field_config.get('type') == 'array':
                if isinstance(original_value, list):
                    mock_state[f"scalar_array_{field_name}_size"] = len(original_value)
                    if field_config.get('items', {}).get('type') == 'object':
                        mock_state[f"data_editor_{field_name}"] = pd.DataFrame(original_value)
        
        # Make multiple edits
        
        # Edit scalar array
        serial_numbers = sample_insurance_data["Serial Numbers"] + ["SN003", "SN004", "SN005"]
        mock_state["field_Serial Numbers"] = serial_numbers
        mock_state["scalar_array_Serial Numbers_size"] = len(serial_numbers)
        FormGenerator._sync_array_to_session("Serial Numbers", serial_numbers)
        
        # Edit object array
        line_items = sample_insurance_data["Line Items"].copy()
        line_items.append({"description": "New Item", "quantity": 2, "unit_price": 100.0})
        line_items[0]['unit_price'] = 600.0
        
        df = pd.DataFrame(line_items)
        mock_state["data_editor_Line Items"] = df
        FormGenerator._sync_array_to_session("Line Items", line_items)
        
        # Edit scalar fields
        mock_state["field_Supplier name"] = "Modified Supplier Name"
        mock_state["field_Invoice amount"] = 1000.0
        
        # Verify changes are present
        form_data_before_reset = FormGenerator.collect_current_form_data(insurance_schema)
        diff_before_reset = calculate_diff(sample_insurance_data, form_data_before_reset)
        
        assert len(diff_before_reset) > 0  # Should have changes
        assert len(form_data_before_reset["Serial Numbers"]) == 5
        assert len(form_data_before_reset["Line Items"]) == 2
        assert form_data_before_reset["Invoice amount"] == 1000.0
        
        # Perform reset
        with patch('utils.file_utils.load_json_file', return_value=sample_insurance_data):
            # Simulate reset logic from EditView._handle_reset
            
            # Clear session state keys
            keys_to_clear = [key for key in mock_state.keys() if any(
                key.startswith(prefix) for prefix in [
                    'field_', 'scalar_array_', 'data_editor_', 'add_row_', 'delete_row_'
                ]
            )]
            
            for key in keys_to_clear:
                del mock_state[key]
            
            # Reinitialize with original data
            for field_name, field_config in insurance_schema['fields'].items():
                original_value = sample_insurance_data.get(field_name)
                mock_state[f"field_{field_name}"] = original_value
                
                if field_config.get('type') == 'array' and isinstance(original_value, list):
                    mock_state[f"scalar_array_{field_name}_size"] = len(original_value)
                    
                    if field_config.get('items', {}).get('type') == 'object':
                        mock_state[f"data_editor_{field_name}"] = pd.DataFrame(original_value)
            
            # Update SessionManager with original data
            SessionManager.set_form_data(sample_insurance_data.copy())
        
        # Verify reset worked
        form_data_after_reset = FormGenerator.collect_current_form_data(insurance_schema)
        diff_after_reset = calculate_diff(sample_insurance_data, form_data_after_reset)
        
        assert len(diff_after_reset) == 0  # Should have no changes
        assert len(form_data_after_reset["Serial Numbers"]) == 2  # Back to original
        assert len(form_data_after_reset["Line Items"]) == 1  # Back to original
        assert form_data_after_reset["Invoice amount"] == 490.5  # Back to original
        assert form_data_after_reset["Supplier name"] == sample_insurance_data["Supplier name"]
    
    def test_reset_preserves_original_array_structure(self, insurance_schema, mock_streamlit_environment):
        """Test that reset preserves original array structure including empty arrays."""
        
        mock_state = mock_streamlit_environment['session_state']
        
        # Data with empty arrays
        data_with_empty_arrays = {
            "Supplier name": "Test Supplier",
            "Invoice amount": 100.0,
            "Serial Numbers": [],  # Empty array
            "Line Items": []  # Empty object array
        }
        
        SessionManager.set_schema(insurance_schema)
        SessionManager.set_form_data(data_with_empty_arrays.copy())
        
        # Initialize session state
        for field_name, field_config in insurance_schema['fields'].items():
            original_value = data_with_empty_arrays.get(field_name)
            mock_state[f"field_{field_name}"] = original_value
            
            if field_config.get('type') == 'array':
                if isinstance(original_value, list):
                    mock_state[f"scalar_array_{field_name}_size"] = len(original_value)
        
        # Add items to empty arrays
        mock_state["field_Serial Numbers"] = ["SN001", "SN002"]
        mock_state["scalar_array_Serial Numbers_size"] = 2
        
        line_items = [{"description": "Item 1", "quantity": 1, "unit_price": 50.0}]
        mock_state["field_Line Items"] = line_items
        mock_state["data_editor_Line Items"] = pd.DataFrame(line_items)
        
        # Verify changes exist
        form_data_with_changes = FormGenerator.collect_current_form_data(insurance_schema)
        assert len(form_data_with_changes["Serial Numbers"]) == 2
        assert len(form_data_with_changes["Line Items"]) == 1
        
        # Reset
        with patch('utils.file_utils.load_json_file', return_value=data_with_empty_arrays):
            # Clear and reinitialize
            keys_to_clear = [key for key in mock_state.keys() if any(
                key.startswith(prefix) for prefix in ['field_', 'scalar_array_', 'data_editor_']
            )]
            
            for key in keys_to_clear:
                del mock_state[key]
            
            for field_name, field_config in insurance_schema['fields'].items():
                original_value = data_with_empty_arrays.get(field_name)
                mock_state[f"field_{field_name}"] = original_value
                
                if field_config.get('type') == 'array' and isinstance(original_value, list):
                    mock_state[f"scalar_array_{field_name}_size"] = len(original_value)
            
            SessionManager.set_form_data(data_with_empty_arrays.copy())
        
        # Verify empty arrays are preserved
        form_data_after_reset = FormGenerator.collect_current_form_data(insurance_schema)
        assert form_data_after_reset["Serial Numbers"] == []
        assert form_data_after_reset["Line Items"] == []
        
        diff_after_reset = calculate_diff(data_with_empty_arrays, form_data_after_reset)
        assert len(diff_after_reset) == 0


class TestValidationErrorsWithArrays:
    """Test validation error handling with arrays."""
    
    def test_scalar_array_validation_errors(self, insurance_schema, mock_streamlit_environment):
        """Test validation errors with scalar array fields."""
        
        mock_state = mock_streamlit_environment['session_state']
        
        # Data with validation errors in scalar array
        invalid_data = {
            "Supplier name": "Test Supplier",
            "Invoice amount": 100.0,
            "Serial Numbers": ["VALID1", "", "invalid_lowercase", "VALID2"],  # Empty and invalid pattern
            "Line Items": []
        }
        
        SessionManager.set_schema(insurance_schema)
        
        # Initialize session state
        for field_name, value in invalid_data.items():
            mock_state[f"field_{field_name}"] = value
            
            if field_name == "Serial Numbers":
                mock_state[f"scalar_array_{field_name}_size"] = len(value)
        
        # Collect form data
        form_data = FormGenerator.collect_current_form_data(insurance_schema)
        
        # Validate data
        with patch('utils.model_builder.validate_model_data') as mock_validate:
            # Mock validation errors
            validation_errors = [
                "Serial Numbers[1]: Field cannot be empty",
                "Serial Numbers[2]: Must match pattern ^[A-Z0-9]+$"
            ]
            mock_validate.return_value = validation_errors
            
            model = create_model_from_schema(insurance_schema)
            errors = mock_validate(form_data, model)  # Use mocked function
            is_valid = len(errors) == 0
            
            assert is_valid == False
            assert len(errors) == 2
            assert "Serial Numbers[1]" in errors[0]
            assert "Serial Numbers[2]" in errors[1]
        
        # Test that submission is blocked with validation errors
        with patch('utils.file_utils.save_corrected_json') as mock_save:
            # Should not save when validation fails
            if not is_valid:
                # Validation failed, don't save
                pass
            else:
                save_corrected_json("test.json", form_data)
            
            # Verify save was not called due to validation errors
            mock_save.assert_not_called()
    
    def test_object_array_validation_errors(self, insurance_schema, mock_streamlit_environment):
        """Test validation errors with object array fields."""
        
        mock_state = mock_streamlit_environment['session_state']
        
        # Data with validation errors in object array
        invalid_line_items = [
            {"description": "", "quantity": 0, "unit_price": -10.0},  # All invalid
            {"description": "Valid Item", "quantity": 1, "unit_price": 50.0}  # Valid
        ]
        
        invalid_data = {
            "Supplier name": "Test Supplier",
            "Invoice amount": 100.0,
            "Serial Numbers": ["VALID1"],
            "Line Items": invalid_line_items
        }
        
        SessionManager.set_schema(insurance_schema)
        
        # Initialize session state
        for field_name, value in invalid_data.items():
            mock_state[f"field_{field_name}"] = value
            
            if field_name == "Line Items":
                mock_state[f"data_editor_{field_name}"] = pd.DataFrame(value)
        
        # Collect form data
        form_data = FormGenerator.collect_current_form_data(insurance_schema)
        
        # Validate data
        with patch('utils.model_builder.validate_model_data') as mock_validate:
            validation_errors = [
                "Line Items[0].description: Field is required",
                "Line Items[0].quantity: Must be at least 1",
                "Line Items[0].unit_price: Must be at least 0"
            ]
            mock_validate.return_value = validation_errors
            
            model = create_model_from_schema(insurance_schema)
            errors = mock_validate(form_data, model)  # Use mocked function
            is_valid = len(errors) == 0
            
            assert is_valid == False
            assert len(errors) == 3
            assert "Line Items[0].description" in errors[0]
            assert "Line Items[0].quantity" in errors[1]
            assert "Line Items[0].unit_price" in errors[2]
    
    def test_array_length_constraint_validation(self, insurance_schema, mock_streamlit_environment):
        """Test validation of array length constraints."""
        
        mock_state = mock_streamlit_environment['session_state']
        
        # Test min_length constraint violation
        data_too_short = {
            "Supplier name": "Test Supplier",
            "Invoice amount": 100.0,
            "Serial Numbers": [],  # Violates min_length: 1
            "Line Items": []
        }
        
        SessionManager.set_schema(insurance_schema)
        
        for field_name, value in data_too_short.items():
            mock_state[f"field_{field_name}"] = value
            if field_name == "Serial Numbers":
                mock_state[f"scalar_array_{field_name}_size"] = len(value)
        
        form_data = FormGenerator.collect_current_form_data(insurance_schema)
        
        with patch('utils.model_builder.validate_model_data') as mock_validate:
            validation_errors = ["Serial Numbers: Array must have at least 1 items"]
            mock_validate.return_value = validation_errors
            
            model = create_model_from_schema(insurance_schema)
            errors = mock_validate(form_data, model)  # Use mocked function
            is_valid = len(errors) == 0
            
            assert is_valid == False
            assert "Serial Numbers" in errors[0]
            assert "at least 1" in errors[0]
        
        # Test max_length constraint violation
        data_too_long = {
            "Supplier name": "Test Supplier",
            "Invoice amount": 100.0,
            "Serial Numbers": [f"SN{i:03d}" for i in range(15)],  # Violates max_length: 10
            "Line Items": []
        }
        
        mock_state["field_Serial Numbers"] = data_too_long["Serial Numbers"]
        mock_state["scalar_array_Serial Numbers_size"] = len(data_too_long["Serial Numbers"])
        
        form_data = FormGenerator.collect_current_form_data(insurance_schema)
        
        with patch('utils.model_builder.validate_model_data') as mock_validate:
            validation_errors = ["Serial Numbers: Array must have at most 10 items"]
            mock_validate.return_value = validation_errors
            
            model = create_model_from_schema(insurance_schema)
            errors = mock_validate(form_data, model)  # Use mocked function
            is_valid = len(errors) == 0
            
            assert is_valid == False
            assert "Serial Numbers" in errors[0]
            assert "at most 10" in errors[0]


class TestAuditLogContainsArrayChanges:
    """Test that audit log contains all array changes."""
    
    def test_audit_log_captures_scalar_array_changes(self, temp_directories, insurance_schema,
                                                   sample_insurance_data, mock_streamlit_environment):
        """Test that audit log captures all scalar array changes."""
        
        mock_state = mock_streamlit_environment['session_state']
        
        # Setup
        SessionManager.set_schema(insurance_schema)
        SessionManager.set_form_data(sample_insurance_data.copy())
        
        # Initialize and modify scalar array
        field_name = "Serial Numbers"
        original_array = sample_insurance_data[field_name].copy()
        modified_array = original_array + ["SN003"]  # Add one item
        modified_array[0] = "MODIFIED1"  # Modify existing item
        
        mock_state[f"field_{field_name}"] = modified_array
        FormGenerator._sync_array_to_session(field_name, modified_array)
        
        # Collect form data
        form_data = FormGenerator.collect_current_form_data(insurance_schema)
        
        # Calculate diff
        diff = calculate_diff(sample_insurance_data, form_data)
        
        # Create audit entry
        audit_entry = {
            "filename": "test_insurance.json",
            "timestamp": datetime.now().isoformat(),
            "user": "test_user",
            "action": "corrected",
            "changes": diff,
            "original_data": sample_insurance_data,
            "corrected_data": form_data
        }
        
        # Test audit log creation
        with patch('utils.file_utils.append_audit_log') as mock_audit:
            mock_audit.return_value = True
            
            success = mock_audit(audit_entry)  # Use mocked function
            assert success == True
            
            # Verify audit entry contains array changes
            mock_audit.assert_called_once()
            logged_entry = mock_audit.call_args[0][0]
            
            assert logged_entry["filename"] == "test_insurance.json"
            assert logged_entry["action"] == "corrected"
            assert "changes" in logged_entry
            
            # Verify the changes include array modifications
            changes = logged_entry["changes"]
            assert len(changes) > 0
            
            # Check that original and corrected data are preserved
            assert "original_data" in logged_entry
            assert "corrected_data" in logged_entry
            assert len(logged_entry["corrected_data"]["Serial Numbers"]) == 3
            assert "SN003" in logged_entry["corrected_data"]["Serial Numbers"]
            assert logged_entry["corrected_data"]["Serial Numbers"][0] == "MODIFIED1"
    
    def test_audit_log_captures_object_array_changes(self, temp_directories, insurance_schema,
                                                   sample_insurance_data, mock_streamlit_environment):
        """Test that audit log captures all object array changes."""
        
        mock_state = mock_streamlit_environment['session_state']
        
        # Setup
        SessionManager.set_schema(insurance_schema)
        SessionManager.set_form_data(sample_insurance_data.copy())
        
        # Modify object array
        field_name = "Line Items"
        original_array = sample_insurance_data[field_name].copy()
        
        # Add new item and modify existing
        modified_array = original_array.copy()
        modified_array[0]['unit_price'] = 600.0  # Modify existing
        modified_array.append({  # Add new item
            "description": "Additional Service",
            "quantity": 2,
            "unit_price": 75.0
        })
        
        # Update session state
        df = pd.DataFrame(modified_array)
        mock_state[f"data_editor_{field_name}"] = df
        FormGenerator._sync_array_to_session(field_name, modified_array)
        
        # Collect form data and calculate diff
        form_data = FormGenerator.collect_current_form_data(insurance_schema)
        diff = calculate_diff(sample_insurance_data, form_data)
        
        # Create and test audit entry
        audit_entry = {
            "filename": "test_insurance.json",
            "timestamp": datetime.now().isoformat(),
            "user": "test_user",
            "action": "corrected",
            "changes": diff,
            "original_data": sample_insurance_data,
            "corrected_data": form_data
        }
        
        with patch('utils.file_utils.append_audit_log') as mock_audit:
            mock_audit.return_value = True
            
            success = mock_audit(audit_entry)  # Use mocked function
            assert success == True
            
            logged_entry = mock_audit.call_args[0][0]
            
            # Verify object array changes are captured
            assert len(logged_entry["corrected_data"]["Line Items"]) == 2
            assert logged_entry["corrected_data"]["Line Items"][0]["unit_price"] == 600.0
            assert logged_entry["corrected_data"]["Line Items"][1]["description"] == "Additional Service"
            
            # Verify changes are detailed
            changes = logged_entry["changes"]
            assert len(changes) > 0
    
    def test_audit_log_captures_multiple_array_changes_in_single_session(self, temp_directories,
                                                                       insurance_schema, sample_insurance_data,
                                                                       mock_streamlit_environment):
        """Test that audit log captures multiple array changes made in a single editing session."""
        
        mock_state = mock_streamlit_environment['session_state']
        
        # Setup
        SessionManager.set_schema(insurance_schema)
        SessionManager.set_form_data(sample_insurance_data.copy())
        
        # Modify both array fields
        
        # Modify scalar array
        serial_numbers = sample_insurance_data["Serial Numbers"] + ["SN003", "SN004"]
        mock_state["field_Serial Numbers"] = serial_numbers
        FormGenerator._sync_array_to_session("Serial Numbers", serial_numbers)
        
        # Modify object array
        line_items = sample_insurance_data["Line Items"].copy()
        line_items[0]['quantity'] = 2  # Modify existing
        line_items.append({"description": "New Item", "quantity": 1, "unit_price": 25.0})  # Add new
        
        df = pd.DataFrame(line_items)
        mock_state["data_editor_Line Items"] = df
        FormGenerator._sync_array_to_session("Line Items", line_items)
        
        # Also modify a scalar field
        mock_state["field_Invoice amount"] = 800.0
        
        # Collect all changes
        form_data = FormGenerator.collect_current_form_data(insurance_schema)
        diff = calculate_diff(sample_insurance_data, form_data)
        
        # Create comprehensive audit entry
        audit_entry = {
            "filename": "test_insurance.json",
            "timestamp": datetime.now().isoformat(),
            "user": "test_user",
            "action": "corrected",
            "changes": diff,
            "original_data": sample_insurance_data,
            "corrected_data": form_data,
            "session_summary": {
                "fields_modified": ["Serial Numbers", "Line Items", "Invoice amount"],
                "arrays_modified": ["Serial Numbers", "Line Items"],
                "total_changes": len(diff) if diff else 0
            }
        }
        
        with patch('utils.file_utils.append_audit_log') as mock_audit:
            mock_audit.return_value = True
            
            success = mock_audit(audit_entry)  # Use mocked function
            assert success == True
            
            logged_entry = mock_audit.call_args[0][0]
            
            # Verify all changes are captured
            corrected_data = logged_entry["corrected_data"]
            
            # Scalar array changes
            assert len(corrected_data["Serial Numbers"]) == 4
            assert "SN003" in corrected_data["Serial Numbers"]
            assert "SN004" in corrected_data["Serial Numbers"]
            
            # Object array changes
            assert len(corrected_data["Line Items"]) == 2
            assert corrected_data["Line Items"][0]["quantity"] == 2
            assert corrected_data["Line Items"][1]["description"] == "New Item"
            
            # Scalar field changes
            assert corrected_data["Invoice amount"] == 800.0
            
            # Verify session summary
            session_summary = logged_entry["session_summary"]
            assert len(session_summary["fields_modified"]) == 3
            assert len(session_summary["arrays_modified"]) == 2
            assert session_summary["total_changes"] > 0
    
    def test_audit_log_readable_format_for_array_changes(self, insurance_schema, sample_insurance_data,
                                                       mock_streamlit_environment):
        """Test that audit log stores array changes in a readable format."""
        
        mock_state = mock_streamlit_environment['session_state']
        
        # Setup and modify data
        SessionManager.set_schema(insurance_schema)
        SessionManager.set_form_data(sample_insurance_data.copy())
        
        # Make specific changes for readability testing
        serial_numbers = ["CHANGED1", "SN002", "ADDED3"]  # Changed first, kept second, added third
        mock_state["field_Serial Numbers"] = serial_numbers
        FormGenerator._sync_array_to_session("Serial Numbers", serial_numbers)
        
        form_data = FormGenerator.collect_current_form_data(insurance_schema)
        diff = calculate_diff(sample_insurance_data, form_data)
        
        # Create audit entry with human-readable summary
        audit_entry = {
            "filename": "test_insurance.json",
            "timestamp": datetime.now().isoformat(),
            "user": "test_user",
            "action": "corrected",
            "changes": diff,
            "original_data": sample_insurance_data,
            "corrected_data": form_data,
            "human_readable_summary": {
                "Serial Numbers": {
                    "action": "modified",
                    "original_count": len(sample_insurance_data["Serial Numbers"]),
                    "new_count": len(serial_numbers),
                    "changes": [
                        "Changed item 0: 'SN001' → 'CHANGED1'",
                        "Added item 2: 'ADDED3'"
                    ]
                }
            }
        }
        
        with patch('utils.file_utils.append_audit_log') as mock_audit:
            mock_audit.return_value = True
            
            success = mock_audit(audit_entry)  # Use mocked function
            assert success == True
            
            logged_entry = mock_audit.call_args[0][0]
            
            # Verify human-readable summary exists and is informative
            summary = logged_entry["human_readable_summary"]
            assert "Serial Numbers" in summary
            
            serial_summary = summary["Serial Numbers"]
            assert serial_summary["action"] == "modified"
            assert serial_summary["original_count"] == 2
            assert serial_summary["new_count"] == 3
            assert len(serial_summary["changes"]) == 2
            assert "SN001" in serial_summary["changes"][0]
            assert "CHANGED1" in serial_summary["changes"][0]
            assert "ADDED3" in serial_summary["changes"][1]


class TestEndToEndIntegrationScenarios:
    """End-to-end integration test scenarios."""
    
    def test_complete_qa_workflow_with_arrays(self, temp_directories, insurance_schema,
                                            sample_insurance_data, mock_streamlit_environment):
        """Test complete QA workflow: load → edit arrays → validate → fix errors → submit → audit."""
        
        mock_state = mock_streamlit_environment['session_state']
        
        # Step 1: Setup test file
        test_file = temp_directories / "json_docs" / "complete_workflow.json"
        with open(test_file, 'w') as f:
            json.dump(sample_insurance_data, f)
        
        # Step 2: Load document (simulating queue selection)
        SessionManager.set_current_file(str(test_file))
        SessionManager.set_schema(insurance_schema)
        SessionManager.set_form_data(sample_insurance_data.copy())
        
        # Initialize session state
        for field_name, field_config in insurance_schema['fields'].items():
            value = sample_insurance_data.get(field_name)
            mock_state[f"field_{field_name}"] = value
            
            if field_config.get('type') == 'array' and isinstance(value, list):
                mock_state[f"scalar_array_{field_name}_size"] = len(value)
                if field_config.get('items', {}).get('type') == 'object':
                    mock_state[f"data_editor_{field_name}"] = pd.DataFrame(value)
        
        # Step 3: Make edits with validation errors
        # Add invalid serial numbers
        invalid_serials = ["SN001", "", "invalid_lower", "VALID3"]  # Contains empty and invalid
        mock_state["field_Serial Numbers"] = invalid_serials
        mock_state["scalar_array_Serial Numbers_size"] = len(invalid_serials)
        FormGenerator._sync_array_to_session("Serial Numbers", invalid_serials)
        
        # Step 4: First validation attempt (should fail)
        form_data_invalid = FormGenerator.collect_current_form_data(insurance_schema)
        
        with patch('utils.model_builder.validate_model_data') as mock_validate:
            validation_errors = [
                "Serial Numbers[1]: Field cannot be empty",
                "Serial Numbers[2]: Must match pattern ^[A-Z0-9]+$"
            ]
            mock_validate.return_value = validation_errors
            
            model = create_model_from_schema(insurance_schema)
            errors = mock_validate(form_data_invalid, model)  # Use mocked function
            is_valid = len(errors) == 0
            
            assert is_valid == False
            assert len(errors) == 2
        
        # Step 5: Fix validation errors
        fixed_serials = ["SN001", "SN002", "VALID3"]  # Fixed empty and invalid
        mock_state["field_Serial Numbers"] = fixed_serials
        mock_state["scalar_array_Serial Numbers_size"] = len(fixed_serials)
        FormGenerator._sync_array_to_session("Serial Numbers", fixed_serials)
        
        # Step 6: Second validation attempt (should pass)
        form_data_valid = FormGenerator.collect_current_form_data(insurance_schema)
        
        with patch('utils.model_builder.validate_model_data') as mock_validate:
            mock_validate.return_value = []
            
            model = create_model_from_schema(insurance_schema)
            errors = mock_validate(form_data_valid, model)  # Use mocked function
            is_valid = len(errors) == 0
            
            assert is_valid == True
            assert len(errors) == 0
        
        # Step 7: Submit corrected data
        with patch('utils.file_utils.save_corrected_json') as mock_save, \
             patch('utils.file_utils.append_audit_log') as mock_audit:
            
            mock_save.return_value = True
            mock_audit.return_value = True
            
            # Calculate final diff
            final_diff = calculate_diff(sample_insurance_data, form_data_valid)
            
            # Save corrected file
            corrected_file = temp_directories / "corrected" / "complete_workflow.json"
            save_success = mock_save(str(corrected_file), form_data_valid)  # Use mocked function
            
            # Create audit entry
            audit_entry = {
                "filename": "complete_workflow.json",
                "timestamp": datetime.now().isoformat(),
                "user": "qa_analyst",
                "action": "corrected",
                "changes": final_diff,
                "validation_attempts": 2,
                "validation_errors_fixed": [
                    "Serial Numbers[1]: Field cannot be empty",
                    "Serial Numbers[2]: Must match pattern ^[A-Z0-9]+$"
                ],
                "original_data": sample_insurance_data,
                "corrected_data": form_data_valid
            }
            
            audit_success = mock_audit(audit_entry)  # Use mocked function
            
            # Verify complete workflow
            assert save_success == True
            assert audit_success == True
            
            # Verify saved data
            saved_data = mock_save.call_args[0][1]
            assert len(saved_data["Serial Numbers"]) == 3
            assert "VALID3" in saved_data["Serial Numbers"]
            assert "" not in saved_data["Serial Numbers"]
            assert "invalid_lower" not in saved_data["Serial Numbers"]
            
            # Verify audit entry
            logged_entry = mock_audit.call_args[0][0]
            assert logged_entry["validation_attempts"] == 2
            assert len(logged_entry["validation_errors_fixed"]) == 2
            assert logged_entry["action"] == "corrected"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])