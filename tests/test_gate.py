"""
test_gate.py - Verification of security boundaries.
"""
import pytest
from pathlib import Path
from oubliette.gate import check_path_access, redact_content, SecurityError

def test_block_env_file(tmp_path):
    """Verify .env files are blocked."""
    env_file = tmp_path / ".env"
    env_file.write_text("SECRET=123")
    
    with pytest.raises(SecurityError):
        check_path_access(str(env_file))

def test_block_traversal(tmp_path):
    """Verify path traversal (../) is resolved and blocked."""
    # Create a blocked file in parent
    parent = tmp_path.parent
    secret_file = parent / "secret.key"
    secret_file.write_text("KEY=123")
    
    # Attempt to access via traversal from tmp_path
    target = tmp_path / ".." / "secret.key"
    
    with pytest.raises(SecurityError):
        check_path_access(str(target))

def test_block_credentials_json(tmp_path):
    """Verify *credentials*.json files are blocked."""
    cred_file = tmp_path / "aws_credentials.json"
    cred_file.write_text("{}")
    
    with pytest.raises(SecurityError):
        check_path_access(str(cred_file))

def test_allow_safe_python_file(tmp_path):
    """Verify safe files are allowed."""
    safe_file = tmp_path / "main.py"
    safe_file.write_text("print('hello')")
    
    resolved = check_path_access(str(safe_file))
    assert resolved == safe_file.resolve()

def test_redact_aws_key():
    """Verify AWS keys are redacted."""
    text = "my key is AKIAIOSFODNN7EXAMPLE and more text"
    result = redact_content(text)
    assert "AKIA" not in result
    assert "[REDACTED]" in result

def test_redact_github_token():
    """Verify GitHub tokens are redacted."""
    token = "ghp_" + "a" * 36
    text = f"token={token}"
    result = redact_content(text)
    assert token not in result
    assert "[REDACTED]" in result

def test_preserve_uuids():
    """Verify UUIDs are NOT redacted (entropy trap prevention)."""
    uuid = "123e4567-e89b-12d3-a456-426614174000"
    text = f"id={uuid}"
    result = redact_content(text)
    assert uuid in result
    assert "[REDACTED]" not in result

def test_preserve_base64():
    """Verify standard Base64 strings are NOT redacted."""
    # A standard base64 string that is NOT a secret key format
    b64 = "SGVsbG8gV29ybGQ=" 
    text = f"data={b64}"
    result = redact_content(text)
    assert b64 in result
