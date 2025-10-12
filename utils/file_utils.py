"""
File utilities for JSON QA webapp.
Handles file operations, locking, and concurrency control.
"""

import json
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional, Any
import logging

from .config_loader import load_config, get_directory_config
from .directory_config import DirectoryConfig
from .directory_validator import DirectoryValidator
from .directory_creator import DirectoryCreator
from .directory_exceptions import DirectoryConfigError, handle_directory_error
from .graceful_degradation import apply_graceful_degradation

logger = logging.getLogger(__name__)

# Global directory configuration
_directory_config: Optional[DirectoryConfig] = None

# Lock timeout in minutes
DEFAULT_LOCK_TIMEOUT = 60

# Legacy constants for backward compatibility (deprecated)
SAMPLE_JSON_DIR = Path("json_docs")
CORRECTED_DIR = Path("corrected")
AUDITS_DIR = Path("audits")
PDF_DOCS_DIR = Path("pdf_docs")
LOCKS_DIR = Path("locks")


def initialize_directories(config: Optional[Dict[str, Any]] = None) -> bool:
    """
    Initialize directory configuration and ensure directories exist with graceful degradation.
    
    Args:
        config: Optional configuration dictionary. If None, loads from config.yaml
        
    Returns:
        True if initialization successful, False otherwise
    """
    global _directory_config
    
    try:
        # Apply graceful degradation for robust initialization
        if config is None:
            _directory_config = apply_graceful_degradation()
        else:
            try:
                _directory_config = DirectoryConfig.from_config(config)
                
                # Validate and create directories
                validator = DirectoryValidator()
                validation_results = validator.validate_all_paths(_directory_config)
                
                creator = DirectoryCreator()
                creation_results = creator.create_all_directories(_directory_config)
                
                # Check if any critical failures occurred
                critical_failures = [r for r in creation_results if not r.is_successful]
                if critical_failures:
                    logger.warning("Some directory creation failed, applying graceful degradation")
                    _directory_config = apply_graceful_degradation()
                
            except Exception as config_error:
                logger.warning(f"Configuration error, applying graceful degradation: {config_error}")
                _directory_config = apply_graceful_degradation(config_error)
        
        # Final validation
        validator = DirectoryValidator()
        final_validation = validator.validate_all_paths(_directory_config)
        all_ready = all(result.is_ready for result in final_validation)
        
        if all_ready:
            logger.info("Directory configuration initialized successfully")
            return True
        else:
            # Try one more time with complete defaults
            logger.warning("Final validation failed, using complete defaults")
            from .config_loader import get_default_config
            _directory_config = DirectoryConfig.from_config(get_default_config())
            
            # Ensure default directories exist
            creator = DirectoryCreator()
            creator.create_all_directories(_directory_config)
            
            return True  # Continue with defaults
        
    except Exception as e:
        if not handle_directory_error(e, "initialization"):
            logger.error(f"Critical failure in directory initialization: {e}")
            return False
        
        # Use defaults as last resort
        logger.info("Using hardcoded defaults as last resort")
        from .config_loader import get_default_config
        _directory_config = DirectoryConfig.from_config(get_default_config())
        return True


def get_directories() -> DirectoryConfig:
    """
    Get current directory configuration with lazy loading.
    
    Returns:
        DirectoryConfig instance
    """
    global _directory_config
    
    if _directory_config is None:
        logger.info("Directory configuration not initialized, loading defaults")
        if not initialize_directories():
            logger.warning("Failed to initialize directories, using hardcoded defaults")
            # Fallback to hardcoded paths
            from .config_loader import get_default_config
            _directory_config = get_directory_config(get_default_config())
    
    assert _directory_config is not None
    return _directory_config


def ensure_directories_exist() -> None:
    """Ensure all required directories exist using configured paths."""
    dirs = get_directories()
    directory_dict = dirs.to_dict()
    
    for name, directory in directory_dict.items():
        try:
            directory.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            logger.error(f"Failed to create directory {name} ({directory}): {e}")


def list_unverified_files() -> List[Dict[str, Any]]:
    """
    Get list of JSON files that need validation.
    Returns files from json_docs that don't have corresponding files in corrected.
    """
    ensure_directories_exist()
    
    dirs = get_directories()
    unverified_files: List[Dict[str, Any]] = []
    
    if not dirs.json_docs.exists():
        return unverified_files
    
    for json_file in dirs.json_docs.glob("*.json"):
        corrected_file = dirs.corrected / json_file.name
        
        # Skip if already corrected
        if corrected_file.exists():
            continue
            
        # Get file metadata
        stat = json_file.stat()
        file_info: Dict[str, Any] = {
            "filename": json_file.name,
            "filepath": str(json_file),
            "size": stat.st_size,
            "created_at": datetime.fromtimestamp(stat.st_ctime),
            "modified_at": datetime.fromtimestamp(stat.st_mtime),
            "is_locked": is_file_locked(json_file.name),
            "locked_by": get_lock_owner(json_file.name),
            "lock_expires": get_lock_expiry(json_file.name)
        }
        
        unverified_files.append(file_info)
    
    # Sort by creation time (oldest first)
    unverified_files.sort(key=lambda x: x["created_at"])
    
    return unverified_files


def claim_file(filename: str, user: str, timeout_minutes: int = DEFAULT_LOCK_TIMEOUT) -> bool:
    """
    Claim a file by creating a lock.
    Returns True if successfully claimed, False if already locked.
    """
    ensure_directories_exist()
    
    dirs = get_directories()
    lock_file = dirs.locks / f"{filename}.lock"
    
    # Check if already locked
    if is_file_locked(filename):
        return False
    
    # Create lock
    lock_data: Dict[str, Any] = {
        "filename": filename,
        "user": user,
        "timestamp": datetime.now().isoformat(),
        "expires": (datetime.now() + timedelta(minutes=timeout_minutes)).isoformat()
    }
    
    try:
        with open(lock_file, 'w') as f:
            json.dump(lock_data, f, indent=2)
        
        logger.info(f"File {filename} claimed by {user}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to claim file {filename}: {e}")
        return False


def release_file(filename: str) -> bool:
    """
    Release a file by removing its lock.
    Returns True if successfully released, False otherwise.
    """
    dirs = get_directories()
    lock_file = dirs.locks / f"{filename}.lock"
    
    try:
        if lock_file.exists():
            lock_file.unlink()
            logger.info(f"File {filename} released")
        return True
        
    except Exception as e:
        logger.error(f"Failed to release file {filename}: {e}")
        return False


def is_file_locked(filename: str) -> bool:
    """
    Check if a file is currently locked.
    Returns True if locked and not stale, False otherwise.
    """
    dirs = get_directories()
    lock_file = dirs.locks / f"{filename}.lock"
    
    if not lock_file.exists():
        return False
    
    try:
        with open(lock_file, 'r') as f:
            lock_data = json.load(f)
        
        # Check if lock is stale
        expires = datetime.fromisoformat(lock_data["expires"])
        if datetime.now() > expires:
            # Remove stale lock
            lock_file.unlink()
            logger.info(f"Removed stale lock for {filename}")
            return False
        
        return True
        
    except Exception as e:
        logger.error(f"Error checking lock for {filename}: {e}")
        # Remove corrupted lock file
        try:
            lock_file.unlink()
        except Exception:
            pass
        return False


def get_lock_owner(filename: str) -> Optional[str]:
    """Get the owner of a file lock."""
    dirs = get_directories()
    lock_file = dirs.locks / f"{filename}.lock"
    
    if not lock_file.exists():
        return None
    
    try:
        with open(lock_file, 'r') as f:
            lock_data = json.load(f)
        return lock_data.get("user")
        
    except Exception:
        return None


def get_lock_expiry(filename: str) -> Optional[datetime]:
    """Get the expiry time of a file lock."""
    dirs = get_directories()
    lock_file = dirs.locks / f"{filename}.lock"
    
    if not lock_file.exists():
        return None
    
    try:
        with open(lock_file, 'r') as f:
            lock_data = json.load(f)
        return datetime.fromisoformat(lock_data["expires"])
        
    except Exception:
        return None


def cleanup_stale_locks(timeout_minutes: int = DEFAULT_LOCK_TIMEOUT) -> int:
    """
    Remove all stale locks.
    Returns number of locks removed.
    """
    ensure_directories_exist()
    
    dirs = get_directories()
    removed_count = 0
    cutoff_time = datetime.now() - timedelta(minutes=timeout_minutes)
    
    for lock_file in dirs.locks.glob("*.lock"):
        try:
            with open(lock_file, 'r') as f:
                lock_data = json.load(f)
            
            expires = datetime.fromisoformat(lock_data["expires"])
            if datetime.now() > expires:
                lock_file.unlink()
                removed_count += 1
                logger.info(f"Removed stale lock: {lock_file.name}")
                
        except Exception as e:
            # Remove corrupted lock files
            try:
                lock_file.unlink()
                removed_count += 1
                logger.info(f"Removed corrupted lock: {lock_file.name}")
            except Exception:
                pass
    
    return removed_count


def load_json_file(filename: str) -> Optional[Dict[str, Any]]:
    """Load JSON data from json_docs directory."""
    dirs = get_directories()
    json_file = dirs.json_docs / filename
    
    if not json_file.exists():
        return None
    
    try:
        with open(json_file, 'r', encoding='utf-8') as f:
            return json.load(f)
            
    except Exception as e:
        logger.error(f"Failed to load JSON file {filename}: {e}")
        return None


def save_corrected_json(filename: str, data: Dict[str, Any]) -> bool:
    """
    Save corrected JSON data to corrected directory.
    Returns True if successful, False otherwise.
    """
    ensure_directories_exist()
    
    dirs = get_directories()
    corrected_file = dirs.corrected / filename
    
    try:
        with open(corrected_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Saved corrected JSON: {filename}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to save corrected JSON {filename}: {e}")
        return False


def append_audit_log(entry: Dict[str, Any]) -> bool:
    """
    Append an audit log entry to the audit log file.
    Uses JSONL format (one JSON object per line).

    Sanitizes any DeepDiff string/SetOrdered fragments found in the
    `detailed_diff` section so we store structured, JSON-serializable data
    (avoids opaque string representations in audit.jsonl).
    """
    ensure_directories_exist()
    
    dirs = get_directories()
    audit_file = dirs.audits / "audit.jsonl"

    def _sanitize_deepdiff_section(val: Any) -> Any:
        """
        Convert DeepDiff SetOrdered/stringified sections into simple structured
        Python objects (lists or dicts) that serialize cleanly to JSON.

        Examples handled:
        - String starting with "SetOrdered([" -> extract paths into a list of strings
        - String path nodes -> return as list with single string
        - Dicts/lists are returned unchanged (recursively sanitized)
        """
        import re
        if isinstance(val, dict):
            return {k: _sanitize_deepdiff_section(v) for k, v in val.items()}
        if isinstance(val, list):
            return [_sanitize_deepdiff_section(i) for i in val]
        if isinstance(val, str):
            s = val.strip()
            # Handle DeepDiff SetOrdered string that contains root[...] nodes
            if s.startswith("SetOrdered([") and "root" in s:
                # extract root['Field name'] occurrences
                names = re.findall(r"root\['([^']+)'\]", s)
                # keep them as list of field path strings
                return names
            # Handle single path-like string containing root[...] or <root[...]>
            if "root" in s:
                names = re.findall(r"root\['([^']+)'\]", s)
                if names:
                    return names
            # Fallback: return original string
            return s
        return val

    try:
        # Make a shallow copy to avoid mutating caller's object
        safe_entry = dict(entry)
        dd = safe_entry.get('detailed_diff')
        if dd is not None:
            safe_entry['detailed_diff'] = _sanitize_deepdiff_section(dd)

        # Finally write sanitized entry
        with open(audit_file, 'a', encoding='utf-8') as f:
            json.dump(safe_entry, f, ensure_ascii=False, default=str)
            f.write('\n')
        
        logger.info(f"Added audit log entry for {entry.get('filename', 'unknown')}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to append audit log: {e}")
        return False


def get_pdf_path(json_filename: str) -> Optional[Path]:
    """
    Get the corresponding PDF path for a JSON file.
    Assumes PDF has same name but .pdf extension.
    """
    dirs = get_directories()
    pdf_name = json_filename.replace('.json', '.pdf')
    pdf_path = dirs.pdf_docs / pdf_name
    
    return pdf_path if pdf_path.exists() else None


def read_audit_logs() -> List[Dict[str, Any]]:
    """
    Read all audit log entries.
    Returns list of audit entries sorted by timestamp (newest first).
    """
    dirs = get_directories()
    audit_file = dirs.audits / "audit.jsonl"
    
    if not audit_file.exists():
        return []
    
    entries: List[Dict[str, Any]] = []
    
    try:
        with open(audit_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line:
                    entry = json.loads(line)
                    entries.append(entry)
        
        # Sort by timestamp (newest first)
        entries.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
        
    except Exception as e:
        logger.error(f"Failed to read audit logs: {e}")
    
    return entries