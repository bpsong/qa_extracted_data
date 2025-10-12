"""
Integration tests for JSON QA webapp.
Tests end-to-end workflows and component interactions.
"""

import json
import tempfile
import shutil
from pathlib import Path
from datetime import datetime
from unittest.mock import patch, MagicMock
import pytest
import os
from typing import Dict, Any

# Import modules to test
from utils.file_utils import (
    list_unverified_files, claim_file, release_file, 
    load_json_file, save_corrected_json, append_audit_log
)
from utils.schema_loader import get_schema_for_file, load_schema
from utils.model_builder import create_model_from_schema, validate_model_data
from utils.diff_utils import calculate_diff, has_changes, create_audit_diff_entry
from utils.submission_handler import SubmissionHandler


class TestEndToEndWorkflow:
    """Test complete end-to-end workflows."""
    
    def setup_method(self) -> None:
        """Set up test environment before each test."""
        # Create temporary directory for testing
        self.test_dir = tempfile.mkdtemp()
        self.original_cwd = os.getcwd()
        os.chdir(self.test_dir)
        
        # Create test directories
        for dir_name in ['json_docs', 'corrected', 'audits', 'pdf_docs', 'locks', 'schemas']:
            Path(dir_name).mkdir(exist_ok=True)
        
        # Create test schema
        self.test_schema = {
            "title": "Test Schema",
            "fields": {
                "supplier_name": {
                    "type": "string",
                    "label": "Supplier Name",
                    "required": True,
                    "min_length": 2
                },
                "invoice_amount": {
                    "type": "number",
                    "label": "Invoice Amount",
                    "required": True,
                    "min_value": 0
                },
                "invoice_date": {
                    "type": "date",
                    "label": "Invoice Date",
                    "required": True
                }
            }
        }
        
        with open("schemas/test_schema.yaml", 'w') as f:
            import yaml
            yaml.dump(self.test_schema, f)
        
        # Create test JSON data
        self.test_json_data: Dict[str, Any] = {
            "supplier_name": "Test Supplier",
            "invoice_amount": 1000.0,
            "invoice_date": "2025-01-13"
        }
        
        with open("json_docs/test_invoice.json", 'w') as f:
            json.dump(self.test_json_data, f)
        
        # Create corresponding PDF
        with open("pdf_docs/test_invoice.pdf", 'w') as f:
            f.write("fake pdf content")
    
    def teardown_method(self) -> None:
        """Clean up after each test."""
        os.chdir(self.original_cwd)
        shutil.rmtree(self.test_dir)
    
    def test_complete_file_processing_workflow(self) -> None:
        """Test complete workflow from file listing to submission."""
        # Step 1: List unverified files
        files = list_unverified_files()
        assert len(files) == 1
        assert files[0]['filename'] == 'test_invoice.json'
        assert not files[0]['is_locked']
        
        # Step 2: Claim file
        filename = files[0]['filename']
        user = "test_user"
        
        success = claim_file(filename, user)
        assert success == True
        
        # Verify file is now locked
        files = list_unverified_files()
        assert files[0]['is_locked'] == True
        assert files[0]['locked_by'] == user
        
        # Step 3: Load JSON data
        original_data_optional = load_json_file(filename)
        assert original_data_optional is not None
        original_data: Dict[str, Any] = original_data_optional
        
        # Step 4: Load schema
        schema = get_schema_for_file(filename)
        assert schema is not None
        assert 'fields' in schema
        
        # Step 5: Create model and validate
        model_class = create_model_from_schema(schema, "TestModel")
        assert model_class is not None
        
        validation_errors = validate_model_data(original_data, model_class)
        assert len(validation_errors) == 0
        
        # Step 6: Modify data
        modified_data = original_data.copy()
        modified_data['supplier_name'] = 'Modified Supplier'
        modified_data['invoice_amount'] = 1500.0
        
        # Step 7: Calculate diff
        diff = calculate_diff(original_data, modified_data)
        assert has_changes(diff) == True
        
        # Step 8: Submit changes
        success, errors = SubmissionHandler.validate_and_submit(
            filename, modified_data, original_data, schema, model_class, user
        )
        assert success == True
        assert len(errors) == 0
        
        # Step 9: Verify corrected file was saved
        corrected_file = Path("corrected") / filename
        assert corrected_file.exists()
        
        with open(corrected_file, 'r') as f:
            saved_data = json.load(f)
        assert saved_data == modified_data
        
        # Step 10: Verify audit log was created
        audit_file = Path("audits/audit.jsonl")
        assert audit_file.exists()
        
        with open(audit_file, 'r') as f:
            audit_entry = json.loads(f.readline())
        
        assert audit_entry['filename'] == filename
        assert audit_entry['user'] == user
        assert audit_entry['action'] == 'corrected'
        assert audit_entry['has_changes'] == True
        
        # Step 11: Verify file is no longer in unverified list
        files = list_unverified_files()
        assert len(files) == 0
        
        # Step 12: Verify lock was released
        lock_file = Path("locks") / f"{filename}.lock"
        assert not lock_file.exists()
    
    def test_concurrent_file_access(self) -> None:
        """Test concurrent file access scenarios."""
        filename = "test_invoice.json"
        user1 = "user1"
        user2 = "user2"
        
        # User 1 claims file
        success1 = claim_file(filename, user1)
        assert success1 == True
        
        # User 2 tries to claim same file
        success2 = claim_file(filename, user2)
        assert success2 == False
        
        # Verify only user 1 has the lock
        files = list_unverified_files()
        assert files[0]['is_locked'] == True
        assert files[0]['locked_by'] == user1
        
        # User 1 releases file
        release_success = release_file(filename)
        assert release_success == True
        
        # Now user 2 can claim it
        success2 = claim_file(filename, user2)
        assert success2 == True
        
        files = list_unverified_files()
        assert files[0]['locked_by'] == user2
    
    def test_schema_validation_integration(self) -> None:
        """Test schema loading and validation integration."""
        # Create a test schema with validation constraints
        test_schema = {
            "title": "Test Invoice Schema",
            "fields": {
                "supplier_name": {
                    "type": "string",
                    "label": "Supplier Name",
                    "required": True,
                    "min_length": 1,
                    "max_length": 200
                },
                "invoice_amount": {
                    "type": "number",
                    "label": "Invoice Amount",
                    "required": True,
                    "min_value": 0.01
                },
                "invoice_date": {
                    "type": "date",
                    "label": "Invoice Date",
                    "required": False
                }
            }
        }
        
        # Create model from test schema
        model_class = create_model_from_schema(test_schema, "TestModel")
        
        # Test valid data
        valid_data = {
            "supplier_name": "Valid Supplier",
            "invoice_amount": 500.0,
            "invoice_date": "2025-01-13"
        }
        
        errors = validate_model_data(valid_data, model_class)
        assert len(errors) == 0
        
        # Test invalid data
        invalid_data = {
            "supplier_name": "",  # Too short
            "invoice_amount": -100.0,  # Negative
            "invoice_date": "invalid-date"  # Invalid format
        }
        
        errors = validate_model_data(invalid_data, model_class)
        assert len(errors) > 0
    
    def test_diff_and_audit_integration(self) -> None:
        """Test diff calculation and audit logging integration."""
        original_data = {
            "supplier_name": "Original Supplier",
            "invoice_amount": 1000.0,
            "invoice_date": "2025-01-13"
        }
        
        modified_data = {
            "supplier_name": "Modified Supplier",
            "invoice_amount": 1500.0,
            "invoice_date": "2025-01-14"
        }
        
        # Calculate diff
        diff = calculate_diff(original_data, modified_data)
        assert has_changes(diff) == True
        
        # Create audit entry
        audit_entry = create_audit_diff_entry(original_data, modified_data)
        
        assert audit_entry['has_changes'] == True
        assert 'change_summary' in audit_entry
        assert audit_entry['change_summary']['total'] > 0
        assert 'detailed_diff' in audit_entry
        
        # Log audit entry
        audit_entry.update({
            'filename': 'test.json',
            'timestamp': datetime.now().isoformat(),
            'user': 'test_user',
            'action': 'corrected'
        })
        
        success = append_audit_log(audit_entry)
        assert success == True
        
        # Verify audit file
        audit_file = Path("audits/audit.jsonl")
        assert audit_file.exists()
    
    def test_error_handling_integration(self) -> None:
        """Test error handling across components."""
        # Test with non-existent file
        result = load_json_file("nonexistent.json")
        assert result is None
        
        # Test with invalid schema
        invalid_schema = {"invalid": "schema"}
        
        try:
            model_class = create_model_from_schema(invalid_schema, "InvalidModel")
            assert False, "Should have raised an exception"
        except (ValueError, KeyError):
            pass  # Expected
        
        # Test submission with invalid data (empty schema should cause validation issues)
        success, errors = SubmissionHandler.validate_and_submit(
            "test_file.json", {"required_field": "value"}, {}, {"fields": {"required_field": {"type": "string", "required": True}}}, user="test_user"
        )
        # This should succeed since we're providing valid data
        # Let's test with invalid data instead
        success, errors = SubmissionHandler.validate_and_submit(
            "test_file.json", {}, {}, {"fields": {"required_field": {"type": "string", "required": True}}}, user="test_user"
        )
        assert success == False
        assert len(errors) > 0
    
    def test_performance_with_large_data(self) -> None:
        """Test performance with larger datasets."""
        # Create larger test data
        large_data = {
            "supplier_name": "Large Data Supplier",
            "invoice_amount": 10000.0,
            "invoice_date": "2025-01-13",
            "line_items": []
        }
        
        # Add many line items
        for i in range(100):
            large_data["line_items"].append({
                "item_description": f"Item {i}",
                "quantity": i + 1,
                "unit_price": 10.0 + i,
                "total_price": (10.0 + i) * (i + 1)
            })
        
        # Save large file
        large_filename = "large_invoice.json"
        with open(f"json_docs/{large_filename}", 'w') as f:
            json.dump(large_data, f)
        
        # Test workflow with large data
        import time
        start_time = time.time()
        
        # Load and process
        loaded_data_optional = load_json_file(large_filename)
        assert loaded_data_optional is not None
        loaded_data = loaded_data_optional
        
        # Calculate diff with modified data
        modified_large_data = loaded_data.copy()
        modified_large_data['supplier_name'] = 'Modified Large Supplier'
        
        diff = calculate_diff(loaded_data, modified_large_data)
        assert has_changes(diff) == True
        
        end_time = time.time()
        processing_time = end_time - start_time
        
        # Should complete within reasonable time (adjust threshold as needed)
        assert processing_time < 5.0, f"Processing took too long: {processing_time}s"
    
    def test_multi_user_workflow_simulation(self) -> None:
        """Test simulation of multiple users working simultaneously."""
        # Create multiple test files
        test_files = []
        for i in range(3):
            filename = f"test_invoice_{i}.json"
            test_data = {
                "supplier_name": f"Supplier {i}",
                "invoice_amount": 1000.0 + i * 100,
                "invoice_date": "2025-01-13"
            }
            
            with open(f"json_docs/{filename}", 'w') as f:
                json.dump(test_data, f)
            
            test_files.append((filename, test_data))
        
        # Simulate multiple users claiming different files
        users = ["user1", "user2", "user3"]
        claimed_files = {}
        
        for i, (filename, data) in enumerate(test_files):
            user = users[i]
            success = claim_file(filename, user)
            assert success == True
            claimed_files[user] = (filename, data)
        
        # Verify all test files are locked by different users
        files = list_unverified_files()
        test_file_names = [f"test_invoice_{i}.json" for i in range(3)]
        test_files_info = [f for f in files if f['filename'] in test_file_names]
        assert len(test_files_info) == 3
        
        for file_info in test_files_info:
            assert file_info['is_locked'] == True
            assert file_info['locked_by'] in users
        
        # Simulate users processing their files
        for user, (filename, original_data) in claimed_files.items():
            # Modify data
            modified_data = original_data.copy()
            modified_data['supplier_name'] = f"Modified by {user}"
            
            # Submit changes
            schema = get_schema_for_file(filename)
            success, errors = SubmissionHandler.validate_and_submit(
                filename, modified_data, original_data, schema, user=user
            )
            assert success == True
            assert len(errors) == 0
        
        # Verify all test files are processed (filter out any existing files)
        files = list_unverified_files()
        test_file_names = [f"test_invoice_{i}.json" for i in range(3)]
        remaining_test_files = [f for f in files if f['filename'] in test_file_names]
        assert len(remaining_test_files) == 0
        
        # Verify all corrected files exist
        for filename, _ in test_files:
            corrected_file = Path("corrected") / filename
            assert corrected_file.exists()
        
        # Verify audit entries for all users
        audit_file = Path("audits/audit.jsonl")
        assert audit_file.exists()
        
        with open(audit_file, 'r') as f:
            audit_entries = [json.loads(line) for line in f]
        
        assert len(audit_entries) == 3
        audit_users = [entry['user'] for entry in audit_entries]
        assert set(audit_users) == set(users)


class TestComponentIntegration:
    """Test integration between specific components."""
    
    def setup_method(self) -> None:
        """Set up test environment."""
        self.test_dir = tempfile.mkdtemp()
        self.original_cwd = os.getcwd()
        os.chdir(self.test_dir)
        
        for dir_name in ['schemas', 'json_docs', 'corrected', 'audits', 'locks']:
            Path(dir_name).mkdir(exist_ok=True)
    
    def teardown_method(self) -> None:
        """Clean up after each test."""
        os.chdir(self.original_cwd)
        shutil.rmtree(self.test_dir)
    
    def test_schema_to_model_integration(self) -> None:
        """Test schema loading to model creation integration."""
        # Create test schema
        schema_data = {
            "fields": {
                "name": {"type": "string", "required": True},
                "age": {"type": "integer", "min_value": 0, "max_value": 150},
                "email": {"type": "string", "pattern": "^[^@]+@[^@]+\\.[^@]+$"}
            }
        }
        
        with open("schemas/person_schema.yaml", 'w') as f:
            import yaml
            yaml.dump(schema_data, f)
        
        # Load schema
        schema_optional = load_schema("person_schema.yaml")
        assert schema_optional is not None
        schema = schema_optional
        assert schema == schema_data
        
        # Create model
        model_class = create_model_from_schema(schema, "PersonModel")
        assert model_class is not None
        
        # Test model validation
        valid_data = {
            "name": "John Doe",
            "age": 30,
            "email": "john@example.com"
        }
        
        errors = validate_model_data(valid_data, model_class)
        assert len(errors) == 0
        
        # Test with invalid data
        invalid_data = {
            "name": "",  # Required but empty
            "age": 200,  # Above max
            "email": "invalid-email"  # Invalid format
        }
        
        errors = validate_model_data(invalid_data, model_class)
        assert len(errors) > 0
    
    def test_file_operations_integration(self) -> None:
        """Test file operations integration."""
        filename = "test.json"
        test_data = {"key": "value"}
        user = "test_user"
        
        # Create test file
        with open(f"json_docs/{filename}", 'w') as f:
            json.dump(test_data, f)
        
        # Test file listing
        files = list_unverified_files()
        assert len(files) == 1
        assert files[0]['filename'] == filename
        
        # Test file claiming
        success = claim_file(filename, user)
        assert success == True
        
        # Test file loading
        loaded_data_optional = load_json_file(filename)
        assert loaded_data_optional is not None
        loaded_data = loaded_data_optional
        
        # Test file saving
        modified_data = {"key": "modified_value"}
        success = save_corrected_json(filename, modified_data)
        assert success == True
        
        # Verify saved file
        corrected_file = Path("corrected") / filename
        assert corrected_file.exists()
        
        with open(corrected_file, 'r') as f:
            saved_data = json.load(f)
        assert saved_data == modified_data
        
        # Test file release
        success = release_file(filename)
        assert success == True
        
        # Verify lock is removed
        lock_file = Path("locks") / f"{filename}.lock"
        assert not lock_file.exists()


if __name__ == "__main__":
    # Run tests if script is executed directly
    pytest.main([__file__])