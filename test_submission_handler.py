"""
Unit tests for submission_handler module.
"""

import json
import tempfile
import shutil
from pathlib import Path
from datetime import datetime
from unittest.mock import patch, MagicMock
import pytest

# Import the module to test
from utils.submission_handler import (
    SubmissionHandler,
    validate_and_submit_data,
    handle_streamlit_submission,
    handle_cancel_submission
)


class TestSubmissionHandler:
    """Test class for submission handler."""
    
    def setup_method(self):
        """Set up test environment before each test."""
        # Create temporary directory for testing
        self.test_dir = tempfile.mkdtemp()
        self.original_cwd = os.getcwd()
        os.chdir(self.test_dir)
        
        # Create test directories
        for dir_name in ['corrected', 'audits', 'locks']:
            Path(dir_name).mkdir(exist_ok=True)
    
    def teardown_method(self):
        """Clean up after each test."""
        os.chdir(self.original_cwd)
        shutil.rmtree(self.test_dir)
    
    def test_validate_and_submit_success(self):
        """Test successful validation and submission."""
        filename = "test.json"
        form_data = {
            "name": "John Doe",
            "age": 30,
            "email": "john@example.com"
        }
        original_data = {
            "name": "Jane Doe",
            "age": 25,
            "email": "jane@example.com"
        }
        schema = {
            "fields": {
                "name": {"type": "string", "required": True},
                "age": {"type": "integer", "required": True, "min_value": 0},
                "email": {"type": "string", "required": True}
            }
        }
        
        success, errors = SubmissionHandler.validate_and_submit(
            filename, form_data, original_data, schema, user="test_user"
        )
        
        assert success == True
        assert len(errors) == 0
        
        # Check that corrected file was created
        corrected_file = Path("corrected/test.json")
        assert corrected_file.exists()
        
        # Check that audit log was created
        audit_file = Path("audits/audit.jsonl")
        assert audit_file.exists()
    
    def test_validate_and_submit_validation_errors(self):
        """Test submission with validation errors."""
        filename = "test.json"
        form_data = {
            "name": "",  # Required field empty
            "age": -5,   # Below minimum value
            "email": "invalid-email"  # Invalid format
        }
        original_data = {"name": "John", "age": 30, "email": "john@example.com"}
        schema = {
            "fields": {
                "name": {"type": "string", "required": True, "min_length": 1},
                "age": {"type": "integer", "required": True, "min_value": 0},
                "email": {"type": "string", "required": True, "pattern": "^[^@]+@[^@]+\\.[^@]+$"}
            }
        }
        
        success, errors = SubmissionHandler.validate_and_submit(
            filename, form_data, original_data, schema, user="test_user"
        )
        
        assert success == False
        assert len(errors) > 0
        assert any("required" in error.lower() for error in errors)
    
    def test_validate_string_field(self):
        """Test string field validation."""
        field_config = {
            "type": "string",
            "label": "Name",
            "required": True,
            "min_length": 2,
            "max_length": 50,
            "pattern": "^[A-Za-z\\s]+$"
        }
        
        # Valid string
        errors = SubmissionHandler._validate_string_field("name", "John Doe", field_config)
        assert len(errors) == 0
        
        # Too short
        errors = SubmissionHandler._validate_string_field("name", "J", field_config)
        assert len(errors) == 1
        assert "at least 2 characters" in errors[0]
        
        # Too long
        long_name = "A" * 60
        errors = SubmissionHandler._validate_string_field("name", long_name, field_config)
        assert len(errors) == 1
        assert "at most 50 characters" in errors[0]
        
        # Invalid pattern
        errors = SubmissionHandler._validate_string_field("name", "John123", field_config)
        assert len(errors) == 1
        assert "format is invalid" in errors[0]
    
    def test_validate_numeric_field(self):
        """Test numeric field validation."""
        field_config = {
            "type": "number",
            "label": "Age",
            "min_value": 0,
            "max_value": 150
        }
        
        # Valid number
        errors = SubmissionHandler._validate_numeric_field("age", 25, field_config)
        assert len(errors) == 0
        
        # Below minimum
        errors = SubmissionHandler._validate_numeric_field("age", -5, field_config)
        assert len(errors) == 1
        assert "at least 0" in errors[0]
        
        # Above maximum
        errors = SubmissionHandler._validate_numeric_field("age", 200, field_config)
        assert len(errors) == 1
        assert "at most 150" in errors[0]
        
        # Invalid type
        errors = SubmissionHandler._validate_numeric_field("age", "not a number", field_config)
        assert len(errors) == 1
        assert "must be a number" in errors[0]
    
    def test_validate_enum_field(self):
        """Test enum field validation."""
        field_config = {
            "type": "enum",
            "label": "Status",
            "choices": ["active", "inactive", "pending"]
        }
        
        # Valid choice
        errors = SubmissionHandler._validate_enum_field("status", "active", field_config)
        assert len(errors) == 0
        
        # Invalid choice
        errors = SubmissionHandler._validate_enum_field("status", "invalid", field_config)
        assert len(errors) == 1
        assert "must be one of" in errors[0]
    
    def test_validate_array_field(self):
        """Test array field validation."""
        field_config = {
            "type": "array",
            "label": "Tags",
            "items": {
                "type": "string",
                "min_length": 1
            }
        }
        
        # Valid array
        errors = SubmissionHandler._validate_array_field("tags", ["tag1", "tag2"], field_config)
        assert len(errors) == 0
        
        # Invalid array type
        errors = SubmissionHandler._validate_array_field("tags", "not an array", field_config)
        assert len(errors) == 1
        assert "must be a list" in errors[0]
        
        # Invalid array items
        errors = SubmissionHandler._validate_array_field("tags", ["valid", ""], field_config)
        assert len(errors) == 1
        assert "tags[1]" in errors[0]
    
    def test_validate_object_field(self):
        """Test object field validation."""
        field_config = {
            "type": "object",
            "label": "Address",
            "properties": {
                "street": {"type": "string", "required": True},
                "city": {"type": "string", "required": True}
            }
        }
        
        # Valid object
        address = {"street": "123 Main St", "city": "Anytown"}
        errors = SubmissionHandler._validate_object_field("address", address, field_config)
        assert len(errors) == 0
        
        # Invalid object type
        errors = SubmissionHandler._validate_object_field("address", "not an object", field_config)
        assert len(errors) == 1
        assert "must be an object" in errors[0]
        
        # Missing required property
        incomplete_address = {"street": "123 Main St"}
        errors = SubmissionHandler._validate_object_field("address", incomplete_address, field_config)
        assert len(errors) == 1
        assert "address.city" in errors[0]
    
    def test_validate_business_rules(self):
        """Test business rule validation."""
        # Test invoice amount vs subtotal
        form_data = {
            "invoice_amount": 100.0,
            "subtotal": 150.0  # Invoice amount less than subtotal
        }
        schema = {"fields": {}}
        
        errors = SubmissionHandler._validate_business_rules(form_data, schema)
        assert len(errors) > 0
        assert any("cannot be less than subtotal" in error for error in errors)
        
        # Test date consistency
        form_data = {
            "invoice_date": "2025-01-15",
            "due_date": "2025-01-10"  # Due date before invoice date
        }
        
        errors = SubmissionHandler._validate_business_rules(form_data, schema)
        assert len(errors) > 0
        assert any("cannot be before invoice date" in error for error in errors)
        
        # Test tax calculation
        form_data = {
            "subtotal": 100.0,
            "tax_amount": 8.0,
            "invoice_amount": 120.0  # Should be 108.0
        }
        
        errors = SubmissionHandler._validate_business_rules(form_data, schema)
        assert len(errors) > 0
        assert any("should equal subtotal + tax" in error for error in errors)
    
    def test_create_audit_entry(self):
        """Test audit entry creation."""
        filename = "test.json"
        original_data = {"name": "John", "age": 30}
        form_data = {"name": "Jane", "age": 25}
        user = "test_user"
        
        from utils.diff_utils import calculate_diff
        diff = calculate_diff(original_data, form_data)
        
        success = SubmissionHandler._create_audit_entry(
            filename, original_data, form_data, user, diff
        )
        
        assert success == True
        
        # Check audit file was created
        audit_file = Path("audits/audit.jsonl")
        assert audit_file.exists()
        
        # Check audit entry content
        with open(audit_file, 'r') as f:
            audit_entry = json.loads(f.readline())
        
        assert audit_entry['filename'] == filename
        assert audit_entry['user'] == user
        assert audit_entry['action'] == 'corrected'
        assert 'timestamp' in audit_entry
    
    @patch('utils.submission_handler.SessionManager')
    @patch('utils.submission_handler.st.session_state', {})
    def test_handle_streamlit_submission_success(self, mock_session_manager):
        """Test successful Streamlit submission handling."""
        # Mock session manager
        mock_session_manager.get_current_file.return_value = "test.json"
        mock_session_manager.get_form_data.return_value = {"name": "John"}
        mock_session_manager.get_original_data.return_value = {"name": "Jane"}
        mock_session_manager.get_schema.return_value = {"fields": {"name": {"type": "string"}}}
        mock_session_manager.get_model_class.return_value = None
        mock_session_manager.get_current_user.return_value = "test_user"
        mock_session_manager.has_unsaved_changes.return_value = False
        mock_session_manager._clear_file_state.return_value = None
        mock_session_manager.set_current_page.return_value = None
        mock_session_manager.clear_validation_errors.return_value = None
        mock_session_manager.set_form_data.return_value = None
        
        # Mock Streamlit functions and Notify
        with patch('utils.submission_handler.Notify.success') as mock_notify_success, \
             patch('streamlit.balloons') as mock_balloons, \
             patch('utils.submission_handler.SubmissionHandler.validate_and_submit') as mock_validate_submit:
            
            # Mock successful validation and submission
            mock_validate_submit.return_value = (True, [])
            
            result = SubmissionHandler.handle_streamlit_submission()
            
            assert result == True
            mock_notify_success.assert_called()
            mock_balloons.assert_called_once()
    
    @patch('utils.submission_handler.SessionManager')
    def test_handle_streamlit_submission_missing_data(self, mock_session_manager):
        """Test Streamlit submission with missing data."""
        # Mock missing data
        mock_session_manager.get_current_file.return_value = None
        
        with patch('streamlit.error') as mock_error:
            result = SubmissionHandler.handle_streamlit_submission()
            
            assert result == False
            mock_error.assert_called_once()
    
    @patch('utils.submission_handler.SessionManager')
    def test_handle_cancel_submission(self, mock_session_manager):
        """Test cancellation handling."""
        mock_session_manager.get_current_file.return_value = "test.json"
        mock_session_manager.has_unsaved_changes.return_value = False
        
        with patch('streamlit.info') as mock_info:
            result = SubmissionHandler.handle_cancel_submission()
            
            assert result == True
            mock_info.assert_called_once()
    
    def test_convenience_functions(self):
        """Test convenience functions."""
        filename = "test.json"
        form_data = {"name": "John"}
        original_data = {"name": "Jane"}
        schema = {"fields": {"name": {"type": "string"}}}
        
        # Test validate_and_submit_data
        success, errors = validate_and_submit_data(
            filename, form_data, original_data, schema, user="test_user"
        )
        
        assert isinstance(success, bool)
        assert isinstance(errors, list)


if __name__ == "__main__":
    # Run tests if script is executed directly
    pytest.main([__file__])

# Import os for the test setup
import os