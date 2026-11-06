"""
test_gate.py - Verification of security gate boundaries.
"""
import pytest
from oubliette.gate import check_path_access, redact_content, SecurityError

def test_block_env_file(tmp_path):
    env_file = tmp_path / ".env"
    with pytest.raises(SecurityError):
        check_path_access(str(env_file))

def test_block_traversal(tmp_path):
    with pytest.raises(SecurityError):
        check_path_access("../etc/passwd")

def test_block_credentials_json(tmp_path):
    cred_file = tmp_path / "service_account.json"
    with pytest.raises(SecurityError):
        check_path_access(str(cred_file))

def test_allow_safe_python_file(tmp_path):
    safe_file = tmp_path / "safe_script.py"
    safe_file.write_text("print('hello')")
    # Should not raise
    resolved = check_path_access(str(safe_file))
    assert resolved.name == "safe_script.py"

def test_redact_aws_key():
    text = "my key is AKIAIOSFODNN7EXAMPLE and more text"
    result, count = redact_content(text)
    assert "AKIA" not in result
    assert "[REDACTED]" in result
    assert count == 1

def test_redact_github_token():
    token = "ghp_" + "a" * 36
    text = f"token={token}"
    result, count = redact_content(text)
    assert token not in result
    assert "[REDACTED]" in result
    assert count == 1

def test_preserve_uuids():
    uuid = "123e4567-e89b-12d3-a456-426614174000"
    text = f"id={uuid}"
    result, count = redact_content(text)
    assert uuid in result
    assert count == 0

def test_preserve_base64():
    b64 = "SGVsbG8gV29ybGQ="
    text = f"data={b64}"
    result, count = redact_content(text)
    assert b64 in result
    assert count == 0
