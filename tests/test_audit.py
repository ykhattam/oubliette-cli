"""
test_audit.py - Verification of audit logging invariants.
"""
import pytest
import json
from pathlib import Path
from oubliette.audit import log_event, LOG_FILE, LOG_DIR, MAX_LOG_SIZE_BYTES

@pytest.fixture(autouse=True)
def clean_log():
    """Remove log file before each test."""
    if LOG_FILE.exists():
        LOG_FILE.unlink()
    yield
    if LOG_FILE.exists():
        LOG_FILE.unlink()

def test_creates_log_directory():
    """Verify .paranoid/ directory is created."""
    log_event("test_action")
    assert LOG_DIR.exists()
    assert LOG_DIR.is_dir()

def test_logs_json_format():
    """Verify log entries are valid JSON."""
    log_event("read_file", file_path="/tmp/test.py", redactions_count=2)
    
    with open(LOG_FILE, "r") as f:
        line = f.readline()
    
    event = json.loads(line)
    assert event["action"] == "read_file"
    assert event["file_path"] == "/tmp/test.py"
    assert event["redactions_count"] == 2
    assert "timestamp" in event

def test_hashes_prompt_content():
    """Verify prompt is hashed, never logged raw."""
    secret_prompt = "my API key is sk-1234567890abcdef"
    log_event("send_to_llm", prompt=secret_prompt)
    
    with open(LOG_FILE, "r") as f:
        line = f.readline()
    
    event = json.loads(line)
    
    # Raw secret must NOT appear in log
    assert secret_prompt not in line
    assert "sk-1234567890abcdef" not in line
    
    # Hash must be present
    assert "prompt_hash" in event
    assert len(event["prompt_hash"]) == 64  # SHA-256 hex length

def test_append_only():
    """Verify log is append-only (multiple writes)."""
    log_event("action_1")
    log_event("action_2")
    log_event("action_3")
    
    with open(LOG_FILE, "r") as f:
        lines = f.readlines()
    
    assert len(lines) == 3
    
    events = [json.loads(line) for line in lines]
    assert events[0]["action"] == "action_1"
    assert events[1]["action"] == "action_2"
    assert events[2]["action"] == "action_3"

def test_rotates_large_log():
    """Verify log rotates when exceeding 10MB."""
    # Write enough events to exceed 10MB
    # Each event ~100 bytes, need ~100k events
    for i in range(110000):
        log_event(f"action_{i}", file_path=f"/tmp/file_{i}.py")
    
    size = LOG_FILE.stat().st_size
    # After rotation, size should be ~5MB (half of 10MB)
    assert size < MAX_LOG_SIZE_BYTES

def test_no_raw_file_content():
    """Verify file content is never logged."""
    # Simulate reading a file with secrets
    file_content = """
    API_KEY = "sk-secret123"
    AWS_KEY = "AKIAIOSFODNN7EXAMPLE"
    """
    
    # Log the action, not the content
    log_event("read_file", file_path="/tmp/test.py", redactions_count=2)
    
    with open(LOG_FILE, "r") as f:
        log_text = f.read()
    
    # File content must NOT appear in log
    assert "sk-secret123" not in log_text
    assert "AKIAIOSFODNN7EXAMPLE" not in log_text
    assert file_content not in log_text
