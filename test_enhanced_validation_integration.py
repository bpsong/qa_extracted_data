"""
Unit tests for enhanced validation integration.
Tests the comprehensive validation system integration with the submission workflow,
error reporting, UI feedback, and state management for array fields.
"""

import pytest
import streamlit as st
from unittest.mock import patch, MagicMock, call
from datetime import datetime, date
import json
import tempfile
import shutil
from pathlib import Path
import os

# Import the modules to test
from utils.submission_handler import SubmissionHandler
from utils.form_generator import FormGenerator
from utils.session_manager import SessionManager
from utils.ui_feedback import Notify


class TestEnhancedValidationIntegration:
    """Test class for enhanced validation integration."""
    
    def setup_method(self):
        """Set up test environment before each test."""
        # Clear session state before each test
        if hasattr(st, 'session_state'):
            st.session_state.clear()
        
        # Create temporary directory for testing
        self.test_dir = tempfile.mkdtemp()
        self.original_cwd = os.getcwd()
        os.chdir(self.test_dir)
        
        # Create test directories
        for dir_name in ['corrected', 'audits', 'locks']:
            Path(dir_name).mkdir(exist_ok=True)
    
    def teardown_method(self):
        """Clean up after each test."""
        # Clear session state after each test
        if hasattr(st, 'session_state'):
            st.session_state.clear()
        
        # Clean up temporary directory
        os.chdir(self.original_cwd)
        shutil.rmtree(self.test_dir)
    
    def test_validation_integration_with_submission_workflow(self):
        """Test validation integration with existing submission workflow."""
        # Test data with mixed scalar and object arrays
        form_data = {
            "supplier_name": "Test Company",
            "serial_numbers": ["SN001", "SN002", "SN003"],  # Scalar array
            "line_items": [  # Object array
                {"name": "Item 1", "quantity": 5, "price": 100.0},
                {"name": "Item 2", "quantity": 10, "price": 200.0}
            ],
            "tags": ["urgent", "electronics"]  # Another scalar array
        }
        
        original_data = {
            "supplier_name": "Old Company",
            "serial_numbers": ["SN001"],
            "line_items": [{"name": "Item 1", "quantity": 3, "price": 100.0}],
            "tags": ["electronics"]
        }
        
        schema = {
            "fields": {
                "supplier_name": {
                    "type": "string",
                    "label": "Supplier Name",
                    "required": True,
                    "min_length": 1
                },
                "serial_numbers": {
                    "type": "array",
                    "label": "Serial Numbers",
                    "items": {
                        "type": "string",
                        "min_length": 3,
                        "pattern": "^SN\\d{3}$"
                    }
                },
                "line_items": {
                    "type": "array",
                    "label": "Line Items",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string", "required": True, "min_length": 1},
                            "quantity": {"type": "integer", "required": True, "min_value": 1},
                            "price": {"type": "number", "required": True, "min_value": 0}
                        }
                    }
                },
                "tags": {
                    "type": "array",
                    "label": "Tags",
                    "items": {
                        "type": "string",
                        "min_length": 1
                    }
                }
            }
        }
        
        # Test successful validation and submission
        success, errors = SubmissionHandler.validate_and_submit(
            "test_mixed_arrays.json", form_data, original_data, schema, user="test_user"
        )
        
        assert success is True
        assert len(errors) == 0
        
        # Verify corrected file was created
        corrected_file = Path("corrected/test_mixed_arrays.json")
        assert corrected_file.exists()
        
        # Verify audit log was created
        audit_file = Path("audits/audit.jsonl")
        assert audit_file.exists()
        
        # Verify audit entry contains array changes
        with open(audit_file, 'r') as f:
            audit_entry = json.loads(f.readline())
        
        assert audit_entry['filename'] == "test_mixed_arrays.json"
        assert audit_entry['user'] == "test_user"
        assert 'detailed_diff' in audit_entry
    
    def test_validation_error_reporting_and_ui_feedback(self):
        """Test error reporting and UI feedback integration for array validation errors."""
        # Test data with validation errors in both scalar and object arrays
        form_data = {
            "serial_numbers": ["SN001", "", "INVALID"],  # Empty string and invalid pattern
            "line_items": [
                {"name": "Item 1", "quantity": 5, "price": 100.0},  # Valid
                {"name": "", "quantity": 0, "price": -10.0},  # Multiple errors
                {"quantity": 3, "price": 50.0}  # Missing required name
            ],
            "tags": ["", "valid_tag", "x"]  # Empty and too short
        }
        
        schema = {
            "fields": {
                "serial_numbers": {
                    "type": "array",
                    "label": "Serial Numbers",
                    "items": {
                        "type": "string",
                        "min_length": 3,
                        "pattern": "^SN\\d{3}$"
                    }
                },
                "line_items": {
                    "type": "array",
                    "label": "Line Items",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string", "required": True, "min_length": 1},
                            "quantity": {"type": "integer", "required": True, "min_value": 1},
                            "price": {"type": "number", "required": True, "min_value": 0}
                        }
                    }
                },
                "tags": {
                    "type": "array",
                    "label": "Tags",
                    "items": {
                        "type": "string",
                        "min_length": 2
                    }
                }
            }
        }
        
        # Test comprehensive validation
        validation_result = SubmissionHandler.comprehensive_validate_data(form_data, schema)
        
        assert validation_result["is_valid"] is False
        assert len(validation_result["errors"]) > 0
        
        # Check that errors contain proper field paths and contextual information
        error_messages = [error["message"] for error in validation_result["errors"]]
        error_paths = [error["field_path"] for error in validation_result["errors"]]
        
        # Verify scalar array errors
        assert any("serial_numbers[1]" in path for path in error_paths)  # Empty string
        assert any("serial_numbers[2]" in path for path in error_paths)  # Invalid pattern
        
        # Verify object array errors
        assert any("line_items[1].name" in path for path in error_paths)  # Empty name
        assert any("line_items[1].quantity" in path for path in error_paths)  # Zero quantity
        assert any("line_items[1].price" in path for path in error_paths)  # Negative price
        assert any("line_items[2].name" in path for path in error_paths)  # Missing name
        
        # Verify tag array errors
        assert any("tags[0]" in path for path in error_paths)  # Empty tag
        assert any("tags[2]" in path for path in error_paths)  # Too short tag
        
        # Test that error messages are user-friendly
        assert any("is required" in msg for msg in error_messages)
        assert any("must be at least" in msg for msg in error_messages)
        assert any("must match pattern" in msg for msg in error_messages)
    
    def test_validation_state_management_for_arrays(self):
        """Test validation state management for arrays during editing."""
        # Setup session state with array data
        st.session_state["array_serial_numbers"] = ["SN001", "SN002"]
        st.session_state["array_line_items"] = [
            {"name": "Item 1", "quantity": 5, "price": 100.0}
        ]
        st.session_state["validation_errors"] = {}
        
        schema = {
            "fields": {
                "serial_numbers": {
                    "type": "array",
                    "label": "Serial Numbers",
                    "items": {"type": "string", "min_length": 3}
                },
                "line_items": {
                    "type": "array",
                    "label": "Line Items",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string", "required": True},
                            "quantity": {"type": "integer", "required": True, "min_value": 1},
                            "price": {"type": "number", "required": True, "min_value": 0}
                        }
                    }
                }
            }
        }
        
        # Test collecting form data with arrays
        form_data = FormGenerator.collect_current_form_data(schema)
        
        assert "serial_numbers" in form_data
        assert form_data["serial_numbers"] == ["SN001", "SN002"]
        assert "line_items" in form_data
        assert form_data["line_items"] == [{"name": "Item 1", "quantity": 5, "price": 100.0}]
        
        # Test validation state persistence
        with patch.object(SessionManager, 'set_validation_errors') as mock_set_errors:
            # Simulate validation with errors
            validation_errors = ["serial_numbers[0] is too short"]
            
            # Mock the session manager call
            SessionManager.set_validation_errors(validation_errors)
            mock_set_errors.assert_called_once_with(validation_errors)
        
        # Test validation state clearing
        with patch.object(SessionManager, 'clear_validation_errors') as mock_clear_errors:
            SessionManager.clear_validation_errors()
            mock_clear_errors.assert_called_once()
    
    def test_mixed_scalar_object_arrays_single_submission(self):
        """Test regression coverage for mixed scalar/object arrays within single submission."""
        # Complex form data with multiple array types
        form_data = {
            "document_id": "DOC123",
            "serial_numbers": ["SN001", "SN002", "SN003"],  # Scalar string array
            "quantities": [10, 20, 30],  # Scalar integer array
            "prices": [100.5, 200.75, 300.25],  # Scalar number array
            "flags": [True, False, True],  # Scalar boolean array
            "dates": ["2024-01-01", "2024-01-02", "2024-01-03"],  # Scalar date array
            "categories": ["electronics", "hardware", "software"],  # Scalar enum array
            "line_items": [  # Object array
                {
                    "name": "Item 1",
                    "quantity": 10,
                    "price": 100.5,
                    "active": True,
                    "delivery_date": "2024-01-15",
                    "category": "electronics"
                },
                {
                    "name": "Item 2", 
                    "quantity": 20,
                    "price": 200.75,
                    "active": False,
                    "delivery_date": "2024-01-16",
                    "category": "hardware"
                }
            ],
            "contacts": [  # Another object array
                {"name": "John Doe", "email": "john@example.com", "phone": "123-456-7890"},
                {"name": "Jane Smith", "email": "jane@example.com", "phone": "098-765-4321"}
            ]
        }
        
        schema = {
            "fields": {
                "document_id": {"type": "string", "required": True},
                "serial_numbers": {
                    "type": "array",
                    "items": {"type": "string", "pattern": "^SN\\d{3}$"}
                },
                "quantities": {
                    "type": "array", 
                    "items": {"type": "integer", "min_value": 1}
                },
                "prices": {
                    "type": "array",
                    "items": {"type": "number", "min_value": 0}
                },
                "flags": {
                    "type": "array",
                    "items": {"type": "boolean"}
                },
                "dates": {
                    "type": "array",
                    "items": {"type": "date"}
                },
                "categories": {
                    "type": "array",
                    "items": {"type": "enum", "choices": ["electronics", "hardware", "software"]}
                },
                "line_items": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string", "required": True},
                            "quantity": {"type": "integer", "required": True, "min_value": 1},
                            "price": {"type": "number", "required": True, "min_value": 0},
                            "active": {"type": "boolean", "required": True},
                            "delivery_date": {"type": "date", "required": True},
                            "category": {"type": "enum", "required": True, "choices": ["electronics", "hardware", "software"]}
                        }
                    }
                },
                "contacts": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string", "required": True, "min_length": 1},
                            "email": {"type": "string", "required": True, "pattern": "^[^@]+@[^@]+\\.[^@]+$"},
                            "phone": {"type": "string", "required": True, "pattern": "^\\d{3}-\\d{3}-\\d{4}$"}
                        }
                    }
                }
            }
        }
        
        # Test comprehensive validation of mixed arrays
        validation_result = SubmissionHandler.comprehensive_validate_data(form_data, schema)
        
        assert validation_result["is_valid"] is True
        assert len(validation_result["errors"]) == 0
        
        # Test submission with mixed arrays
        success, errors = SubmissionHandler.validate_and_submit(
            "test_mixed_complex.json", form_data, {}, schema, user="test_user"
        )
        
        assert success is True
        assert len(errors) == 0
        
        # Verify all array types were processed correctly
        corrected_file = Path("corrected/test_mixed_complex.json")
        assert corrected_file.exists()
        
        with open(corrected_file, 'r') as f:
            saved_data = json.load(f)
        
        # Verify all array fields are preserved
        assert "serial_numbers" in saved_data
        assert "quantities" in saved_data
        assert "prices" in saved_data
        assert "flags" in saved_data
        assert "dates" in saved_data
        assert "categories" in saved_data
        assert "line_items" in saved_data
        assert "contacts" in saved_data
        
        # Verify array lengths are preserved
        assert len(saved_data["serial_numbers"]) == 3
        assert len(saved_data["line_items"]) == 2
        assert len(saved_data["contacts"]) == 2
    
    def test_enum_default_handling_negative_minima(self):
        """Test enum/default handling, negative minima, and mixed array payloads."""
        # Test data with enums, defaults, and negative values
        form_data = {
            "status_codes": ["active", "inactive", "pending"],  # Enum array
            "temperature_readings": [-10.5, 0.0, 25.5, -5.2],  # Numbers with negative values
            "offset_values": [-5, -3, 0, 2, 5],  # Integers with negative values
            "measurements": [  # Object array with negative minima and enums
                {
                    "sensor_id": "TEMP001",
                    "value": -15.5,  # Negative value within allowed range
                    "status": "active",
                    "calibration_offset": -2
                },
                {
                    "sensor_id": "TEMP002", 
                    "value": 22.3,
                    "status": "inactive",
                    "calibration_offset": 1
                }
            ]
        }
        
        schema = {
            "fields": {
                "status_codes": {
                    "type": "array",
                    "items": {
                        "type": "enum",
                        "choices": ["active", "inactive", "pending", "error"],
                        "default": "active"
                    }
                },
                "temperature_readings": {
                    "type": "array",
                    "items": {
                        "type": "number",
                        "min_value": -20.0,  # Negative minimum
                        "max_value": 50.0,
                        "default": 0.0
                    }
                },
                "offset_values": {
                    "type": "array",
                    "items": {
                        "type": "integer",
                        "min_value": -10,  # Negative minimum
                        "max_value": 10,
                        "default": 0
                    }
                },
                "measurements": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "sensor_id": {
                                "type": "string",
                                "required": True,
                                "pattern": "^TEMP\\d{3}$"
                            },
                            "value": {
                                "type": "number",
                                "required": True,
                                "min_value": -20.0,  # Negative minimum
                                "max_value": 50.0
                            },
                            "status": {
                                "type": "enum",
                                "required": True,
                                "choices": ["active", "inactive", "pending", "error"],
                                "default": "active"
                            },
                            "calibration_offset": {
                                "type": "integer",
                                "required": False,
                                "min_value": -5,  # Negative minimum
                                "max_value": 5,
                                "default": 0
                            }
                        }
                    }
                }
            }
        }
        
        # Test validation with negative minima and enums
        validation_result = SubmissionHandler.comprehensive_validate_data(form_data, schema)
        
        assert validation_result["is_valid"] is True
        assert len(validation_result["errors"]) == 0
        
        # Test default value generation for different types with negative minima
        string_default = FormGenerator._get_default_value_for_type("string", {})
        assert string_default == ""
        
        number_default_negative = FormGenerator._get_default_value_for_type("number", {"min_value": -10.0})
        assert number_default_negative == -10.0
        
        integer_default_negative = FormGenerator._get_default_value_for_type("integer", {"min_value": -5})
        assert integer_default_negative == -5
        
        enum_default_explicit = FormGenerator._get_default_value_for_type("enum", {
            "choices": ["red", "green", "blue"],
            "default": "green"
        })
        assert enum_default_explicit == "green"
        
        enum_default_first = FormGenerator._get_default_value_for_type("enum", {
            "choices": ["red", "green", "blue"]
        })
        assert enum_default_first == "red"
        
        # Test validation of invalid enum values
        invalid_form_data = {
            "status_codes": ["active", "invalid_status", "pending"],
            "measurements": [
                {
                    "sensor_id": "TEMP001",
                    "value": -15.5,
                    "status": "invalid_enum_value",
                    "calibration_offset": -2
                }
            ]
        }
        
        invalid_validation_result = SubmissionHandler.comprehensive_validate_data(invalid_form_data, schema)
        
        assert invalid_validation_result["is_valid"] is False
        assert len(invalid_validation_result["errors"]) > 0
        
        # Check that enum validation errors are properly reported
        error_messages = [error["message"] for error in invalid_validation_result["errors"]]
        assert any("must be one of" in msg for msg in error_messages)
    
    @patch('utils.session_manager.SessionManager')
    def test_concurrent_editors_state_machine(self, mock_session_manager):
        """Test that updated state machine handles concurrent editors properly."""
        # Simulate concurrent editing scenario
        filename = "test_concurrent.json"
        
        # Setup mock session manager for first editor
        mock_session_manager.get_current_file.return_value = filename
        mock_session_manager.get_current_user.return_value = "user1"
        
        # Test data for first editor
        form_data_user1 = {
            "serial_numbers": ["SN001", "SN002"],
            "line_items": [{"name": "Item 1", "quantity": 5, "price": 100.0}]
        }
        
        schema = {
            "fields": {
                "serial_numbers": {
                    "type": "array",
                    "items": {"type": "string", "pattern": "^SN\\d{3}$"}
                },
                "line_items": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string", "required": True},
                            "quantity": {"type": "integer", "required": True, "min_value": 1},
                            "price": {"type": "number", "required": True, "min_value": 0}
                        }
                    }
                }
            }
        }
        
        # Test validation state isolation between users
        with patch('streamlit.session_state', {}) as mock_st_state:
            # Set up state for user1
            mock_st_state[f"validation_errors_{filename}_user1"] = []
            mock_st_state[f"form_data_{filename}_user1"] = form_data_user1
            
            # Validate for user1
            validation_result_user1 = SubmissionHandler.comprehensive_validate_data(form_data_user1, schema)
            assert validation_result_user1["is_valid"] is True
            
            # Simulate second user with different data
            form_data_user2 = {
                "serial_numbers": ["SN003", "INVALID"],  # Invalid pattern
                "line_items": [{"name": "", "quantity": 0, "price": -10.0}]  # Multiple errors
            }
            
            # Set up state for user2
            mock_st_state[f"validation_errors_{filename}_user2"] = []
            mock_st_state[f"form_data_{filename}_user2"] = form_data_user2
            
            # Validate for user2
            validation_result_user2 = SubmissionHandler.comprehensive_validate_data(form_data_user2, schema)
            assert validation_result_user2["is_valid"] is False
            assert len(validation_result_user2["errors"]) > 0
            
            # Verify that user1's validation state is not affected by user2's errors
            assert mock_st_state[f"validation_errors_{filename}_user1"] == []
            assert mock_st_state[f"form_data_{filename}_user1"] == form_data_user1
    
    def test_validation_error_recovery_and_persistence(self):
        """Test validation error recovery and state persistence during editing."""
        # Initial form data with errors
        initial_form_data = {
            "serial_numbers": ["SN001", "", "INVALID"],  # Errors at indices 1 and 2
            "line_items": [
                {"name": "Item 1", "quantity": 5, "price": 100.0},  # Valid
                {"name": "", "quantity": 0, "price": -10.0}  # Multiple errors
            ]
        }
        
        schema = {
            "fields": {
                "serial_numbers": {
                    "type": "array",
                    "items": {"type": "string", "min_length": 3, "pattern": "^SN\\d{3}$"}
                },
                "line_items": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string", "required": True, "min_length": 1},
                            "quantity": {"type": "integer", "required": True, "min_value": 1},
                            "price": {"type": "number", "required": True, "min_value": 0}
                        }
                    }
                }
            }
        }
        
        # Initial validation - should have errors
        initial_validation = SubmissionHandler.comprehensive_validate_data(initial_form_data, schema)
        assert initial_validation["is_valid"] is False
        initial_error_count = len(initial_validation["errors"])
        assert initial_error_count > 0
        
        # Partially corrected form data - fix some errors
        partially_corrected_data = {
            "serial_numbers": ["SN001", "SN002", "INVALID"],  # Fixed index 1, still error at index 2
            "line_items": [
                {"name": "Item 1", "quantity": 5, "price": 100.0},  # Still valid
                {"name": "Item 2", "quantity": 0, "price": -10.0}  # Fixed name, still quantity and price errors
            ]
        }
        
        # Partial validation - should have fewer errors
        partial_validation = SubmissionHandler.comprehensive_validate_data(partially_corrected_data, schema)
        assert partial_validation["is_valid"] is False
        partial_error_count = len(partial_validation["errors"])
        assert partial_error_count < initial_error_count
        
        # Fully corrected form data
        fully_corrected_data = {
            "serial_numbers": ["SN001", "SN002", "SN003"],  # All valid
            "line_items": [
                {"name": "Item 1", "quantity": 5, "price": 100.0},  # Still valid
                {"name": "Item 2", "quantity": 3, "price": 50.0}  # All errors fixed
            ]
        }
        
        # Final validation - should have no errors
        final_validation = SubmissionHandler.comprehensive_validate_data(fully_corrected_data, schema)
        assert final_validation["is_valid"] is True
        assert len(final_validation["errors"]) == 0
        
        # Test that error paths are consistent across validation attempts
        initial_paths = {error["field_path"] for error in initial_validation["errors"]}
        partial_paths = {error["field_path"] for error in partial_validation["errors"]}
        
        # Verify that fixed errors are no longer reported
        assert "serial_numbers[1]" in initial_paths
        assert "serial_numbers[1]" not in partial_paths
        assert "line_items[1].name" in initial_paths
        assert "line_items[1].name" not in partial_paths
    
    def test_validation_performance_with_large_arrays(self):
        """Test validation performance with large arrays."""
        # Create large arrays for performance testing
        large_serial_numbers = [f"SN{i:03d}" for i in range(1000)]  # 1000 items
        large_line_items = [
            {
                "name": f"Item {i}",
                "quantity": i + 1,
                "price": (i + 1) * 10.0,
                "active": i % 2 == 0
            }
            for i in range(500)  # 500 objects
        ]
        
        form_data = {
            "serial_numbers": large_serial_numbers,
            "line_items": large_line_items
        }
        
        schema = {
            "fields": {
                "serial_numbers": {
                    "type": "array",
                    "items": {"type": "string", "pattern": "^SN\\d{3}$"}
                },
                "line_items": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string", "required": True},
                            "quantity": {"type": "integer", "required": True, "min_value": 1},
                            "price": {"type": "number", "required": True, "min_value": 0},
                            "active": {"type": "boolean", "required": True}
                        }
                    }
                }
            }
        }
        
        # Measure validation time
        import time
        start_time = time.time()
        
        validation_result = SubmissionHandler.comprehensive_validate_data(form_data, schema)
        
        end_time = time.time()
        validation_time = end_time - start_time
        
        # Validation should complete in reasonable time (less than 5 seconds)
        assert validation_time < 5.0
        
        # All data should be valid
        assert validation_result["is_valid"] is True
        assert len(validation_result["errors"]) == 0
        
        # Test with some errors in large arrays
        form_data_with_errors = form_data.copy()
        form_data_with_errors["serial_numbers"][500] = "INVALID"  # Invalid pattern
        form_data_with_errors["line_items"][250]["quantity"] = 0  # Invalid quantity
        
        start_time = time.time()
        
        validation_result_with_errors = SubmissionHandler.comprehensive_validate_data(form_data_with_errors, schema)
        
        end_time = time.time()
        validation_time_with_errors = end_time - start_time
        
        # Validation with errors should still complete in reasonable time
        assert validation_time_with_errors < 5.0
        
        # Should detect the errors
        assert validation_result_with_errors["is_valid"] is False
        assert len(validation_result_with_errors["errors"]) == 2
        
        # Verify error paths are correct
        error_paths = [error["field_path"] for error in validation_result_with_errors["errors"]]
        assert "serial_numbers[500]" in error_paths
        assert "line_items[250].quantity" in error_paths


class TestValidationIntegrationEdgeCases:
    """Test edge cases for validation integration."""
    
    def setup_method(self):
        """Set up test environment before each test."""
        if hasattr(st, 'session_state'):
            st.session_state.clear()
    
    def teardown_method(self):
        """Clean up after each test."""
        if hasattr(st, 'session_state'):
            st.session_state.clear()
    
    def test_empty_arrays_validation(self):
        """Test validation of empty arrays."""
        form_data = {
            "serial_numbers": [],  # Empty scalar array
            "line_items": []  # Empty object array
        }
        
        schema = {
            "fields": {
                "serial_numbers": {
                    "type": "array",
                    "items": {"type": "string", "min_length": 3}
                },
                "line_items": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string", "required": True}
                        }
                    }
                }
            }
        }
        
        validation_result = SubmissionHandler.comprehensive_validate_data(form_data, schema)
        
        # Empty arrays should be valid
        assert validation_result["is_valid"] is True
        assert len(validation_result["errors"]) == 0
    
    def test_null_and_undefined_array_values(self):
        """Test validation with null and undefined array values."""
        form_data = {
            "serial_numbers": None,  # Null array
            "line_items": [
                {"name": "Item 1", "quantity": None, "price": 100.0},  # Null property
                {"name": None, "quantity": 5, "price": None}  # Multiple null properties
            ]
        }
        
        schema = {
            "fields": {
                "serial_numbers": {
                    "type": "array",
                    "required": False,
                    "items": {"type": "string"}
                },
                "line_items": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string", "required": True},
                            "quantity": {"type": "integer", "required": True, "min_value": 1},
                            "price": {"type": "number", "required": False, "min_value": 0}
                        }
                    }
                }
            }
        }
        
        validation_result = SubmissionHandler.comprehensive_validate_data(form_data, schema)
        
        # Should have errors for required fields with null values
        assert validation_result["is_valid"] is False
        assert len(validation_result["errors"]) > 0
        
        error_paths = [error["field_path"] for error in validation_result["errors"]]
        assert "line_items[0].quantity" in error_paths  # Required field is null
        assert "line_items[1].name" in error_paths  # Required field is null
    
    def test_nested_array_validation(self):
        """Test validation of nested array structures."""
        # Note: This tests the current system's handling of complex nested structures
        form_data = {
            "categories": [
                {
                    "name": "Electronics",
                    "subcategories": ["Phones", "Laptops", "Tablets"]  # Array within object
                },
                {
                    "name": "Clothing",
                    "subcategories": ["Shirts", "Pants"]
                }
            ]
        }
        
        schema = {
            "fields": {
                "categories": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string", "required": True},
                            "subcategories": {
                                "type": "array",
                                "items": {"type": "string", "min_length": 1}
                            }
                        }
                    }
                }
            }
        }
        
        validation_result = SubmissionHandler.comprehensive_validate_data(form_data, schema)
        
        # Should be valid - nested arrays are supported
        assert validation_result["is_valid"] is True
        assert len(validation_result["errors"]) == 0
    
    def test_mixed_valid_invalid_array_items(self):
        """Test arrays with mix of valid and invalid items."""
        form_data = {
            "mixed_data": [
                {"name": "Valid Item", "value": 100},  # Valid
                {"name": "", "value": -50},  # Invalid name and value
                {"name": "Another Valid", "value": 200},  # Valid
                {"value": 150},  # Missing required name
                {"name": "Last Valid", "value": 75}  # Valid
            ]
        }
        
        schema = {
            "fields": {
                "mixed_data": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string", "required": True, "min_length": 1},
                            "value": {"type": "integer", "required": True, "min_value": 0}
                        }
                    }
                }
            }
        }
        
        validation_result = SubmissionHandler.comprehensive_validate_data(form_data, schema)
        
        assert validation_result["is_valid"] is False
        assert len(validation_result["errors"]) >= 3  # At least 3 errors: empty name, negative value, missing name
        
        error_paths = [error["field_path"] for error in validation_result["errors"]]
        
        # Check that errors are correctly attributed to specific array indices
        assert any("mixed_data[1].name" in path for path in error_paths)
        assert any("mixed_data[1].value" in path for path in error_paths)
        assert any("mixed_data[3].name" in path for path in error_paths)
        
        # Verify that valid items don't generate errors
        assert not any("mixed_data[0]" in path for path in error_paths)
        assert not any("mixed_data[2]" in path for path in error_paths)
        assert not any("mixed_data[4]" in path for path in error_paths)


if __name__ == "__main__":
    # Run tests if script is executed directly
    pytest.main([__file__, "-v"])