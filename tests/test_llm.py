"""
test_llm.py - Verification of local llama.cpp server router.
"""
import pytest
import requests
from unittest.mock import patch, MagicMock
from oubliette.llm import send_to_llm, LLMError

@patch("oubliette.llm._is_port_in_use", return_value=True)
def test_send_to_llm_success(mock_port):
    """Verify successful response from server."""
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "choices": [{"message": {"content": "Code looks good."}}]
    }
    mock_response.raise_for_status.return_value = None
    
    with patch("oubliette.llm.requests.post", return_value=mock_response):
        result = send_to_llm("test prompt")
        
    assert result == "Code looks good."

@patch("oubliette.llm._is_port_in_use", return_value=True)
def test_send_to_llm_connection_refused(mock_port):
    """Verify connection error raises LLMError."""
    with patch(
        "oubliette.llm.requests.post",
        side_effect=requests.exceptions.ConnectionError(),
    ):
        with pytest.raises(LLMError) as exc_info:
            send_to_llm("test")
    assert "Cannot reach llama-server" in str(exc_info.value)

@patch("oubliette.llm._is_port_in_use", return_value=False)
@patch("oubliette.llm.subprocess.Popen")
@patch("oubliette.llm.time.sleep")
def test_send_to_llm_lazy_starts_server(mock_sleep, mock_popen, mock_port):
    """Verify server is started if port is closed."""
    # Simulate port opening after start
    mock_port.side_effect = [False, True] 
    
    mock_response = MagicMock()
    mock_response.json.return_value = {"choices": [{"message": {"content": "ok"}}]}
    mock_response.raise_for_status.return_value = None
    
    with patch("oubliette.llm.requests.post", return_value=mock_response):
        result = send_to_llm("test")
        
    assert result == "ok"
    mock_popen.assert_called_once() # Verify server was spawned
