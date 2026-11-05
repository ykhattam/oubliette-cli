"""
test_writer.py - Verification of atomic file writer.
"""
import pytest
from pathlib import Path
from unittest.mock import patch
from oubliette.writer import write_file_atomic, WriteError, _generate_diff

def test_generate_diff_shows_changes():
    """Verify diff is generated for changed content."""
    original = "line1\nline2\n"
    new = "line1\nline3\n"
    diff = _generate_diff(original, new, "test.txt")
    assert "-line2" in diff
    assert "+line3" in diff

def test_generate_diff_empty_for_identical():
    """Verify diff is empty for identical content."""
    content = "same\ncontent\n"
    diff = _generate_diff(content, content, "test.txt")
    assert diff == ""

def test_write_new_file(tmp_path):
    """Verify writing to new file works."""
    target = tmp_path / "new.txt"
    content = "hello world"
    
    # Mock user approval
    with patch("builtins.input", return_value="y"):
        result = write_file_atomic(str(target), content)
    
    assert result is True
    assert target.exists()
    assert target.read_text() == content

def test_write_existing_file(tmp_path):
    """Verify overwriting existing file works."""
    target = tmp_path / "existing.txt"
    target.write_text("old content")
    
    new_content = "new content"
    
    with patch("builtins.input", return_value="y"):
        result = write_file_atomic(str(target), new_content)
    
    assert result is True
    assert target.read_text() == new_content

def test_write_blocked_env_file(tmp_path):
    """Verify writing to .env is blocked."""
    target = tmp_path / ".env"
    
    with pytest.raises(WriteError) as exc_info:
        write_file_atomic(str(target), "SECRET=123")
    
    assert "blocked" in str(exc_info.value).lower()

def test_write_blocked_key_file(tmp_path):
    """Verify writing to .key is blocked."""
    target = tmp_path / "secret.key"
    
    with pytest.raises(WriteError) as exc_info:
        write_file_atomic(str(target), "KEY=123")
    
    assert "blocked" in str(exc_info.value).lower()

def test_write_user_declines(tmp_path):
    """Verify write is cancelled when user declines."""
    target = tmp_path / "test.txt"
    
    with patch("builtins.input", return_value="n"):
        result = write_file_atomic(str(target), "content")
    
    assert result is False
    assert not target.exists()

def test_write_no_changes(tmp_path):
    """Verify no write when content is identical."""
    target = tmp_path / "test.txt"
    content = "same content"
    target.write_text(content)
    
    with patch("builtins.input", return_value="y") as mock_input:
        result = write_file_atomic(str(target), content)
    
    assert result is True
    # Should not prompt user if no changes
    mock_input.assert_not_called()

def test_write_skip_approval(tmp_path):
    """Verify require_approval=False bypasses prompt."""
    target = tmp_path / "test.txt"
    
    with patch("builtins.input") as mock_input:
        result = write_file_atomic(str(target), "content", require_approval=False)
    
    assert result is True
    mock_input.assert_not_called()

def test_write_creates_audit_log(tmp_path):
    """Verify write action is logged."""
    target = tmp_path / "test.txt"
    log_file = tmp_path / ".paranoid" / "audit.log"
    
    # Change to tmp_path so .paranoid/ is created there
    import os
    original_cwd = os.getcwd()
    os.chdir(tmp_path)
    
    try:
        with patch("builtins.input", return_value="y"):
            write_file_atomic(str(target), "content")
        
        assert log_file.exists()
        log_content = log_file.read_text()
        assert "write_success" in log_content
    finally:
        os.chdir(original_cwd)

def test_write_atomic_on_failure(tmp_path):
    """Verify temp file is cleaned up if replace fails."""
    target = tmp_path / "test.txt"
    
    # Mock os.replace to fail
    with patch("builtins.input", return_value="y"):
        with patch("oubliette.writer.os.replace", side_effect=OSError("mock error")):
            with pytest.raises(WriteError) as exc_info:
                write_file_atomic(str(target), "content")
            
            assert "Atomic replace failed" in str(exc_info.value)
    
    # Verify no temp files left behind
    temp_files = list(tmp_path.glob("*.tmp"))
    assert len(temp_files) == 0
