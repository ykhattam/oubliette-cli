"""
test_llm.py - Verification of local llama.cpp runner.
"""
import pytest
import subprocess
from unittest.mock import patch, MagicMock
from oubliette.llm import send_to_llm, LLMError

def test_send_to_llm_subprocess_success():
    """Verify successful subprocess execution."""
    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_result.stdout = "def hello():\n    pass"
    mock_result.stderr = ""
    
    with patch("oubliette.llm.subprocess.run", return_value=mock_result) as mock_run:
        result = send_to_llm("write a function")
        
    assert result == "def hello():\n    pass"
    mock_run.assert_called_once()
    call_args = mock_run.call_args[0][0]
    assert "llama-cli" in call_args[0]
    assert "-p" in call_args

def test_send_to_llm_with_system_prompt():
    """Verify system prompt is prepended correctly."""
    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_result.stdout = "ok"
    
    with patch("oubliette.llm.subprocess.run", return_value=mock_result) as mock_run:
        send_to_llm("user prompt", system="system prompt")
        
    call_args = mock_run.call_args[0][0]
    prompt_idx = call_args.index("-p") + 1
    assert "System: system prompt" in call_args[prompt_idx]
    assert "User: user prompt" in call_args[prompt_idx]

def test_send_to_llm_subprocess_failure():
    """Verify subprocess failure raises LLMError."""
    mock_result = MagicMock()
    mock_result.returncode = 1
    mock_result.stderr = "error: model not found"
    
    with patch("oubliette.llm.subprocess.run", return_value=mock_result):
        with pytest.raises(LLMError) as exc_info:
            send_to_llm("test")
    assert "llama.cpp failed" in str(exc_info.value)

def test_send_to_llm_file_not_found():
    """Verify missing binary raises LLMError."""
    with patch("oubliette.llm.subprocess.run", side_effect=FileNotFoundError):
        with pytest.raises(LLMError) as exc_info:
            send_to_llm("test")
    assert "not found" in str(exc_info.value)

def test_send_to_llm_timeout():
    """Verify timeout raises LLMError."""
    with patch("oubliette.llm.subprocess.run", side_effect=subprocess.TimeoutExpired(cmd="llama-cli", timeout=60)):
        with pytest.raises(LLMError) as exc_info:
            send_to_llm("test")
    assert "timed out" in str(exc_info.value)
