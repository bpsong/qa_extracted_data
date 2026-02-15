"""
Unit tests for file_utils module.
"""

import json
import os
import tempfile
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
import pytest
from unittest.mock import patch, mock_open
from typing import Optional, Dict, Any

# Import the module to test
import utils.file_utils as file_utils
from utils.file_utils import (
    list_unverified_files,
    initialize_directories,
    get_directories,
    ensure_directories_exist,
    claim_file,
    release_file,
    is_file_locked,
    get_lock_owner,
    get_lock_expiry,
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


def _result(is_ready: bool = True, is_successful: bool = True):
    return SimpleNamespace(is_ready=is_ready, is_successful=is_successful)


def test_initialize_directories_with_config_creation_failure_uses_graceful_degradation(monkeypatch):
    cfg_primary = object()
    cfg_fallback = object()
    monkeypatch.setattr(file_utils, "_directory_config", None)

    validator = SimpleNamespace(validate_all_paths=lambda _cfg: [_result(is_ready=True)])
    creator = SimpleNamespace(create_all_directories=lambda _cfg: [_result(is_successful=False)])

    with patch.object(file_utils.DirectoryConfig, "from_config", return_value=cfg_primary), patch.object(
        file_utils, "DirectoryValidator", return_value=validator
    ), patch.object(file_utils, "DirectoryCreator", return_value=creator), patch.object(
        file_utils, "apply_graceful_degradation", return_value=cfg_fallback
    ) as mock_degrade:
        assert initialize_directories({"directories": {}}) is True

    assert mock_degrade.called


def test_initialize_directories_outer_exception_uses_defaults_when_handled(monkeypatch):
    cfg_default = object()
    monkeypatch.setattr(file_utils, "_directory_config", None)

    with patch.object(file_utils, "apply_graceful_degradation", side_effect=RuntimeError("boom")), patch.object(
        file_utils, "handle_directory_error", return_value=True
    ), patch("utils.config_loader.get_default_config", return_value={"directories": {}}), patch.object(
        file_utils.DirectoryConfig, "from_config", return_value=cfg_default
    ):
        assert initialize_directories() is True

    assert file_utils._directory_config is cfg_default


def test_initialize_directories_outer_exception_returns_false_when_unhandled(monkeypatch):
    monkeypatch.setattr(file_utils, "_directory_config", None)

    with patch.object(file_utils, "apply_graceful_degradation", side_effect=RuntimeError("boom")), patch.object(
        file_utils, "handle_directory_error", return_value=False
    ):
        assert initialize_directories() is False


def test_get_directories_falls_back_when_initialize_fails(monkeypatch):
    fallback_config = object()
    monkeypatch.setattr(file_utils, "_directory_config", None)

    with patch.object(file_utils, "initialize_directories", return_value=False), patch(
        "utils.config_loader.get_default_config", return_value={"directories": {}}
    ), patch.object(file_utils, "get_directory_config", return_value=fallback_config):
        result = get_directories()

    assert result is fallback_config


def test_ensure_directories_exist_logs_mkdir_error(monkeypatch):
    class BadDir:
        def mkdir(self, parents=True, exist_ok=True):
            raise OSError("cannot create")

    fake_dirs = SimpleNamespace(to_dict=lambda: {"bad": BadDir()})
    with patch.object(file_utils, "get_directories", return_value=fake_dirs), patch.object(
        file_utils, "logger"
    ) as mock_logger:
        ensure_directories_exist()

    mock_logger.error.assert_called_once()


def test_claim_file_returns_false_when_lock_write_fails(monkeypatch, tmp_path):
    locks = tmp_path / "locks"
    locks.mkdir()
    fake_dirs = SimpleNamespace(locks=locks)

    with patch.object(file_utils, "ensure_directories_exist"), patch.object(
        file_utils, "get_directories", return_value=fake_dirs
    ), patch.object(file_utils, "is_file_locked", return_value=False), patch(
        "builtins.open", side_effect=OSError("no write")
    ):
        assert claim_file("doc.json", "user") is False


def test_release_file_returns_false_when_unlink_fails(tmp_path):
    locks = tmp_path / "locks"
    locks.mkdir()
    lock_file = locks / "doc.json.lock"
    lock_file.write_text("x", encoding="utf-8")
    fake_dirs = SimpleNamespace(locks=locks)

    with patch.object(file_utils, "get_directories", return_value=fake_dirs), patch.object(
        Path, "unlink", side_effect=OSError("cannot unlink")
    ):
        assert release_file("doc.json") is False


def test_is_file_locked_invalid_lock_data_removes_lock_and_returns_false(tmp_path):
    locks = tmp_path / "locks"
    locks.mkdir()
    lock_file = locks / "doc.json.lock"
    lock_file.write_text("not-json", encoding="utf-8")
    fake_dirs = SimpleNamespace(locks=locks)

    with patch.object(file_utils, "get_directories", return_value=fake_dirs):
        assert is_file_locked("doc.json") is False

    assert not lock_file.exists()


def test_get_lock_owner_invalid_json_returns_none(tmp_path):
    locks = tmp_path / "locks"
    locks.mkdir()
    lock_file = locks / "doc.json.lock"
    lock_file.write_text("not-json", encoding="utf-8")
    fake_dirs = SimpleNamespace(locks=locks)

    with patch.object(file_utils, "get_directories", return_value=fake_dirs):
        assert get_lock_owner("doc.json") is None


def test_get_lock_expiry_invalid_json_returns_none(tmp_path):
    locks = tmp_path / "locks"
    locks.mkdir()
    lock_file = locks / "doc.json.lock"
    lock_file.write_text("not-json", encoding="utf-8")
    fake_dirs = SimpleNamespace(locks=locks)

    with patch.object(file_utils, "get_directories", return_value=fake_dirs):
        assert get_lock_expiry("doc.json") is None


def test_cleanup_stale_locks_removes_corrupted_files(tmp_path):
    locks = tmp_path / "locks"
    locks.mkdir()
    corrupted = locks / "broken.lock"
    corrupted.write_text("not-json", encoding="utf-8")
    fake_dirs = SimpleNamespace(locks=locks)

    with patch.object(file_utils, "ensure_directories_exist"), patch.object(
        file_utils, "get_directories", return_value=fake_dirs
    ):
        removed = cleanup_stale_locks()

    assert removed == 1
    assert not corrupted.exists()


def test_load_json_file_returns_none_on_parse_error(tmp_path):
    json_docs = tmp_path / "json_docs"
    json_docs.mkdir()
    bad_json = json_docs / "bad.json"
    bad_json.write_text("{bad json}", encoding="utf-8")
    fake_dirs = SimpleNamespace(json_docs=json_docs)

    with patch.object(file_utils, "get_directories", return_value=fake_dirs):
        assert load_json_file("bad.json") is None


def test_save_corrected_json_returns_false_on_write_error(tmp_path):
    corrected = tmp_path / "corrected"
    corrected.mkdir()
    fake_dirs = SimpleNamespace(corrected=corrected)

    with patch.object(file_utils, "ensure_directories_exist"), patch.object(
        file_utils, "get_directories", return_value=fake_dirs
    ), patch("builtins.open", side_effect=OSError("no write")):
        assert save_corrected_json("x.json", {"a": 1}) is False


def test_append_audit_log_sanitizes_deepdiff_root_paths(tmp_path):
    audits = tmp_path / "audits"
    audits.mkdir()
    fake_dirs = SimpleNamespace(audits=audits)
    entry = {
        "filename": "sample.json",
        "detailed_diff": {
            "values_changed": "SetOrdered([<root['Supplier name'] t1:'A', t2:'B'>, <root['Invoice Amount'] t1:1, t2:2>])",
            "single": "root['Tax Amount']",
        },
    }

    with patch.object(file_utils, "ensure_directories_exist"), patch.object(
        file_utils, "get_directories", return_value=fake_dirs
    ):
        assert append_audit_log(entry) is True

    saved_line = (audits / "audit.jsonl").read_text(encoding="utf-8").strip()
    saved = json.loads(saved_line)
    assert saved["detailed_diff"]["values_changed"] == ["Supplier name", "Invoice Amount"]
    assert saved["detailed_diff"]["single"] == ["Tax Amount"]


def test_append_audit_log_returns_false_on_write_error(tmp_path):
    audits = tmp_path / "audits"
    audits.mkdir()
    fake_dirs = SimpleNamespace(audits=audits)

    with patch.object(file_utils, "ensure_directories_exist"), patch.object(
        file_utils, "get_directories", return_value=fake_dirs
    ), patch("builtins.open", side_effect=OSError("no write")):
        assert append_audit_log({"filename": "x.json"}) is False


def test_read_audit_logs_returns_empty_on_invalid_line(tmp_path):
    audits = tmp_path / "audits"
    audits.mkdir()
    audit_file = audits / "audit.jsonl"
    audit_file.write_text("{invalid json}\n", encoding="utf-8")
    fake_dirs = SimpleNamespace(audits=audits)

    with patch.object(file_utils, "get_directories", return_value=fake_dirs):
        assert read_audit_logs() == []
