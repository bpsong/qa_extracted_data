"""
Unit tests for file_utils module.
"""

import json
import os
import tempfile
import shutil
from datetime import datetime, timedelta
from pathlib import Path
import pytest
from unittest.mock import patch, mock_open
from typing import Optional, Dict, Any

# Import the module to test
from utils.file_utils import (
    list_unverified_files,
    claim_file,
    release_file,
    is_file_locked,
    cleanup_stale_locks,
    load_json_file,
    save_corrected_json,
    append_audit_log,
    get_pdf_path,
    read_audit_logs
)


class TestFileUtils:
    """Test class for file utilities."""
    
    def setup_method(self) -> None:
        """Set up test environment before each test."""
        # Create temporary directory for testing
        self.test_dir = tempfile.mkdtemp()
        self.original_cwd = os.getcwd()
        os.chdir(self.test_dir)
        
        # Create test directories
        for dir_name in ['json_docs', 'corrected', 'audits', 'pdf_docs', 'locks']:
            Path(dir_name).mkdir(exist_ok=True)
    
    def teardown_method(self) -> None:
        """Clean up after each test."""
        os.chdir(self.original_cwd)
        shutil.rmtree(self.test_dir)
    
    def test_list_unverified_files_empty_directory(self) -> None:
        """Test listing files when json_docs is empty."""
        files = list_unverified_files()
        assert files == []
    
    def test_list_unverified_files_with_files(self) -> None:
        """Test listing files with sample JSON files."""
        # Create test JSON files
        test_data = {"test": "data"}
        
        sample_file = Path("json_docs/test1.json")
        with open(sample_file, 'w') as f:
            json.dump(test_data, f)
        
        files = list_unverified_files()
        assert len(files) == 1
        assert files[0]["filename"] == "test1.json"
        assert files[0]["size"] > 0
        assert "created_at" in files[0]
        assert files[0]["is_locked"] == False
    
    def test_list_unverified_files_excludes_corrected(self) -> None:
        """Test that corrected files are excluded from listing."""
        test_data = {"test": "data"}
        
        # Create sample file
        sample_file = Path("json_docs/test1.json")
        with open(sample_file, 'w') as f:
            json.dump(test_data, f)
        
        # Create corresponding corrected file
        corrected_file = Path("corrected/test1.json")
        with open(corrected_file, 'w') as f:
            json.dump(test_data, f)
        
        files = list_unverified_files()
        assert len(files) == 0
    
    def test_claim_file_success(self) -> None:
        """Test successfully claiming a file."""
        result = claim_file("test.json", "user1")
        assert result == True
        
        # Check lock file was created
        lock_file = Path("locks/test.json.lock")
        assert lock_file.exists()
        
        # Check lock content
        with open(lock_file, 'r') as f:
            lock_data = json.load(f)
        
        assert lock_data["filename"] == "test.json"
        assert lock_data["user"] == "user1"
        assert "timestamp" in lock_data
        assert "expires" in lock_data
    
    def test_claim_file_already_locked(self) -> None:
        """Test claiming a file that's already locked."""
        # First claim
        claim_file("test.json", "user1")
        
        # Second claim should fail
        result = claim_file("test.json", "user2")
        assert result == False
    
    def test_release_file_success(self) -> None:
        """Test successfully releasing a file."""
        # First claim the file
        claim_file("test.json", "user1")
        
        # Then release it
        result = release_file("test.json")
        assert result == True
        
        # Check lock file was removed
        lock_file = Path("locks/test.json.lock")
        assert not lock_file.exists()
    
    def test_is_file_locked_true(self) -> None:
        """Test checking if a file is locked (true case)."""
        claim_file("test.json", "user1")
        assert is_file_locked("test.json") == True
    
    def test_is_file_locked_false(self) -> None:
        """Test checking if a file is locked (false case)."""
        assert is_file_locked("test.json") == False
    
    def test_is_file_locked_stale_lock(self) -> None:
        """Test that stale locks are automatically removed."""
        # Create a stale lock (expired)
        lock_data = {
            "filename": "test.json",
            "user": "user1",
            "timestamp": (datetime.now() - timedelta(hours=2)).isoformat(),
            "expires": (datetime.now() - timedelta(hours=1)).isoformat()
        }
        
        lock_file = Path("locks/test.json.lock")
        with open(lock_file, 'w') as f:
            json.dump(lock_data, f)
        
        # Check should return False and remove the stale lock
        assert is_file_locked("test.json") == False
        assert not lock_file.exists()
    
    def test_cleanup_stale_locks(self) -> None:
        """Test cleaning up stale locks."""
        # Create a fresh lock
        claim_file("fresh.json", "user1")
        
        # Create a stale lock
        stale_lock_data = {
            "filename": "stale.json",
            "user": "user2",
            "timestamp": (datetime.now() - timedelta(hours=2)).isoformat(),
            "expires": (datetime.now() - timedelta(hours=1)).isoformat()
        }
        
        stale_lock_file = Path("locks/stale.json.lock")
        with open(stale_lock_file, 'w') as f:
            json.dump(stale_lock_data, f)
        
        # Cleanup should remove only the stale lock
        removed_count = cleanup_stale_locks()
        assert removed_count == 1
        
        # Fresh lock should still exist
        assert Path("locks/fresh.json.lock").exists()
        # Stale lock should be removed
        assert not stale_lock_file.exists()
    
    def test_load_json_file_success(self) -> None:
        """Test successfully loading a JSON file."""
        test_data = {"key": "value", "number": 42}
        
        json_file = Path("json_docs/test.json")
        with open(json_file, 'w') as f:
            json.dump(test_data, f)
        
        loaded_data = load_json_file("test.json")
        assert loaded_data == test_data
    
    def test_load_json_file_not_found(self) -> None:
        """Test loading a non-existent JSON file."""
        result = load_json_file("nonexistent.json")
        assert result is None
    
    def test_save_corrected_json(self) -> None:
        """Test saving corrected JSON data."""
        test_data = {"corrected": True, "value": 123}
        
        result = save_corrected_json("test.json", test_data)
        assert result == True
        
        # Check file was created
        corrected_file = Path("corrected/test.json")
        assert corrected_file.exists()
        
        # Check content
        with open(corrected_file, 'r') as f:
            saved_data = json.load(f)
        
        assert saved_data == test_data
    
    def test_append_audit_log(self) -> None:
        """Test appending to audit log."""
        entry1 = {
            "filename": "test1.json",
            "timestamp": datetime.now().isoformat(),
            "user": "user1",
            "action": "corrected"
        }
        
        entry2 = {
            "filename": "test2.json",
            "timestamp": datetime.now().isoformat(),
            "user": "user2",
            "action": "corrected"
        }
        
        # Append entries
        assert append_audit_log(entry1) == True
        assert append_audit_log(entry2) == True
        
        # Check audit file exists
        audit_file = Path("audits/audit.jsonl")
        assert audit_file.exists()
        
        # Check content
        with open(audit_file, 'r') as f:
            lines = f.readlines()
        
        assert len(lines) == 2
        assert json.loads(lines[0])["filename"] == "test1.json"
        assert json.loads(lines[1])["filename"] == "test2.json"
    
    def test_get_pdf_path_exists(self) -> None:
        """Test getting PDF path when PDF exists."""
        # Create test PDF file
        pdf_file = Path("pdf_docs/test.pdf")
        pdf_file.write_text("fake pdf content")
        
        pdf_path: Optional[Path] = get_pdf_path("test.json")
        assert pdf_path is not None
        actual_pdf_path: Path = pdf_path
        assert actual_pdf_path == pdf_file
        assert actual_pdf_path.exists()
    
    def test_get_pdf_path_not_exists(self) -> None:
        """Test getting PDF path when PDF doesn't exist."""
        pdf_path = get_pdf_path("nonexistent.json")
        assert pdf_path is None
    
    def test_read_audit_logs(self) -> None:
        """Test reading audit logs."""
        # Create test audit entries
        entries = [
            {
                "filename": "test1.json",
                "timestamp": "2025-01-13T10:00:00",
                "user": "user1"
            },
            {
                "filename": "test2.json",
                "timestamp": "2025-01-13T11:00:00",
                "user": "user2"
            }
        ]
        
        # Write to audit file
        audit_file = Path("audits/audit.jsonl")
        with open(audit_file, 'w') as f:
            for entry in entries:
                json.dump(entry, f)
                f.write('\n')
        
        # Read back
        read_entries = read_audit_logs()
        assert len(read_entries) == 2
        
        # Should be sorted by timestamp (newest first)
        assert read_entries[0]["timestamp"] == "2025-01-13T11:00:00"
        assert read_entries[1]["timestamp"] == "2025-01-13T10:00:00"
    
    def test_read_audit_logs_empty(self) -> None:
        """Test reading audit logs when file doesn't exist."""
        entries = read_audit_logs()
        assert entries == []


if __name__ == "__main__":
    # Run tests if script is executed directly
    pytest.main([__file__])