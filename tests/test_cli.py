"""
test_cli.py - Integration tests for CLI pipeline.
"""
import pytest
from pathlib import Path
from unittest.mock import patch
import sys
import os

from oubliette.cli import _read_and_redact, main
from oubliette.gate import SecurityError

def test_read_and_redact_blocks_env(tmp_path):
    """Verify .env file is blocked at CLI level."""
    env_file = tmp_path / ".env"
    env_file.write_text("SECRET=sk-1234567890abcdef")
    with pytest.raises(SecurityError):
        _read_and_redact(str(env_file))

def test_read_and_redact_strips_aws_key(tmp_path):
    """Verify AWS key is redacted in file content."""
    code_file = tmp_path / "config.py"
    code_file.write_text('KEY = "AKIAIOSFODNN7EXAMPLE"')
    result = _read_and_redact(str(code_file))
    assert "AKIAIOSFODNN7EXAMPLE" not in result
    assert "[REDACTED]" in result

def test_read_and_redact_logs_action(tmp_path):
    """Verify read action is logged with redaction count."""
    code_file = tmp_path / "test.py"
    code_file.write_text('token = "ghp_' + "a" * 36 + '"')
    log_file = tmp_path / ".paranoid" / "audit.log"
    
    original_cwd = os.getcwd()
    os.chdir(tmp_path)
    try:
        _read_and_redact(str(code_file))
        assert log_file.exists()
        log_content = log_file.read_text()
        assert "read_file" in log_content
        assert "redactions_count" in log_content
    finally:
        os.chdir(original_cwd)

def test_cli_full_pipeline_with_mock_llm(tmp_path):
    """Verify full pipeline: read -> redact -> LLM -> print."""
    code_file = tmp_path / "main.py"
    code_file.write_text('print("hello")')
    
    test_args = ["oubliette", "--file", str(code_file), "--prompt", "Review this code."]
    
    with patch("sys.argv", test_args):
        with patch("oubliette.cli.send_to_llm", return_value="Code looks good."):
            with patch("builtins.print") as mock_print:
                main()
    
    printed_text = " ".join(str(call) for call in mock_print.call_args_list)
    assert "Code looks good." in printed_text

def test_cli_blocks_secret_file(tmp_path):
    """Verify CLI exits with error when blocked file is requested."""
    env_file = tmp_path / ".env"
    env_file.write_text("SECRET=123")
    test_args = ["oubliette", "--file", str(env_file), "--prompt", "Read this."]
    
    with patch("sys.argv", test_args):
        with pytest.raises(SystemExit) as exc_info:
            main()
        assert exc_info.value.code == 1

def test_cli_write_output_atomic(tmp_path):
    """Verify --write flag triggers atomic file write."""
    code_file = tmp_path / "input.py"
    code_file.write_text("x = 1")
    output_file = tmp_path / "output.txt"
    
    test_args = ["oubliette", "--file", str(code_file), "--prompt", "Increment x.", "--write", str(output_file)]
    
    with patch("sys.argv", test_args):
        with patch("oubliette.cli.send_to_llm", return_value="x = 2"):
            with patch("builtins.input", return_value="y"):
                main()
    
    assert output_file.exists()
    assert output_file.read_text() == "x = 2"

def test_cli_write_blocked_env(tmp_path):
    """Verify --write to .env is blocked."""
    code_file = tmp_path / "input.py"
    code_file.write_text("x = 1")
    output_file = tmp_path / ".env"
    
    test_args = ["oubliette", "--file", str(code_file), "--prompt", "Generate a secret.", "--write", str(output_file)]
    
    with patch("sys.argv", test_args):
        with patch("oubliette.cli.send_to_llm", return_value="SECRET=123"):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 1
