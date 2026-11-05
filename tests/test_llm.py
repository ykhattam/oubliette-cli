"""
test_llm.py - Verification of local LLM router.
"""
import pytest
import json
from unittest.mock import patch, MagicMock
import requests
from oubliette.llm import (
    send_to_llm,
    _parse_sse_line,
    LLMError,
    LLMTimeoutError,
    OLLAMA_URL,
)

def test_parse_sse_content_line():
    """Verify SSE content line is parsed."""
    line = 'data: {"choices":[{"delta":{"content":"Hello"}}]}'
    result = _parse_sse_line(line)
    assert result == "Hello"

def test_parse_sse_done_signal():
    """Verify [DONE] returns empty string."""
    result = _parse_sse_line("data: [DONE]")
    assert result == ""

def test_parse_sse_empty_line():
    """Verify empty line returns None."""
    result = _parse_sse_line("")
    assert result is None

def test_parse_sse_malformed_json():
    """Verify malformed JSON returns None."""
    result = _parse_sse_line("data: not-json")
    assert result is None

def test_send_to_llm_streams_response():
    """Verify streaming response is concatenated."""
    mock_lines = [
        'data: {"choices":[{"delta":{"content":"Hello"}}]}',
        '',
        'data: {"choices":[{"delta":{"content":" world"}}]}',
        '',
        'data: [DONE]',
    ]
    
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.iter_lines.return_value = mock_lines
    mock_response.raise_for_status.return_value = None
    
    with patch("oubliette.llm.requests.post", return_value=mock_response):
        result = send_to_llm("test prompt")
    
    assert result == "Hello world"

def test_send_to_llm_connection_refused():
    """Verify connection error raises LLMError."""
    with patch(
        "oubliette.llm.requests.post",
        side_effect=requests.exceptions.ConnectionError(),
    ):
        with pytest.raises(LLMError) as exc_info:
            send_to_llm("test")
        assert "Cannot reach Ollama" in str(exc_info.value)

def test_send_to_llm_initial_timeout():
    """Verify initial timeout raises LLMError."""
    with patch(
        "oubliette.llm.requests.post",
        side_effect=requests.exceptions.Timeout(),
    ):
        with pytest.raises(LLMError) as exc_info:
            send_to_llm("test")
        assert "timed out" in str(exc_info.value)

def test_send_to_llm_http_error():
    """Verify HTTP error raises LLMError."""
    mock_response = MagicMock()
    mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError("500")
    
    with patch("oubliette.llm.requests.post", return_value=mock_response):
        with pytest.raises(LLMError) as exc_info:
            send_to_llm("test")
        assert "Ollama returned error" in str(exc_info.value)

def test_send_to_llm_uses_hardcoded_url():
    """Verify router uses hard-coded localhost URL only."""
    mock_response = MagicMock()
    mock_response.iter_lines.return_value = ['data: [DONE]']
    mock_response.raise_for_status.return_value = None
    
    with patch("oubliette.llm.requests.post", return_value=mock_response) as mock_post:
        send_to_llm("test")
        
        call_args = mock_post.call_args
        assert call_args[0][0] == OLLAMA_URL
        assert "localhost" in OLLAMA_URL
        assert "api.openai" not in OLLAMA_URL
        assert "api.anthropic" not in OLLAMA_URL

def test_send_to_llm_includes_system_prompt():
    """Verify system prompt is included when provided."""
    mock_response = MagicMock()
    mock_response.iter_lines.return_value = ['data: [DONE]']
    mock_response.raise_for_status.return_value = None
    
    with patch("oubliette.llm.requests.post", return_value=mock_response) as mock_post:
        send_to_llm("user prompt", system="system prompt")
        
        call_args = mock_post.call_args
        payload = call_args[1]["json"]
        messages = payload["messages"]
        
        assert len(messages) == 2
        assert messages[0]["role"] == "system"
        assert messages[0]["content"] == "system prompt"
        assert messages[1]["role"] == "user"
        assert messages[1]["content"] == "user prompt"
