"""
llm.py - Local Ollama router with streaming.
"""
import time
import json
import requests

# Hard-coded local endpoint. No env var override. No cloud fallback.
OLLAMA_URL = "http://localhost:11434/v1/chat/completions"
PER_TOKEN_TIMEOUT_SECONDS = 30
REQUEST_TIMEOUT_SECONDS = 60

class LLMError(Exception):
    """Raised when LLM communication fails."""
    pass

class LLMTimeoutError(LLMError):
    """Raised when per-token timeout is exceeded."""
    pass

def _parse_sse_line(line: str) -> str | None:
    """
    Parse one SSE line. Return content delta or None.
    Returns empty string on [DONE] signal.
    """
    line = line.strip()
    if not line or not line.startswith("data:"):
        return None
    
    payload = line[len("data:"):].strip()
    
    if payload == "[DONE]":
        return ""
    
    try:
        data = json.loads(payload)
    except json.JSONDecodeError:
        return None
    
    choices = data.get("choices", [])
    if not choices:
        return None
    
    delta = choices[0].get("delta", {})
    return delta.get("content", "")

def send_to_llm(prompt: str, system: str = None) -> str:
    """
    Send prompt to local Ollama, stream response.
    Returns concatenated content. Raises LLMError on failure.
    """
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})
    
    payload = {
        "model": "qwen2.5-coder:latest",
        "messages": messages,
        "stream": True,
    }
    
    try:
        response = requests.post(
            OLLAMA_URL,
            json=payload,
            stream=True,
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
    except requests.exceptions.ConnectionError:
        raise LLMError(
            f"Cannot reach Ollama at {OLLAMA_URL}. "
            "Verify Ollama is running locally."
        )
    except requests.exceptions.Timeout:
        raise LLMError("Initial connection to Ollama timed out.")
    except requests.exceptions.HTTPError as e:
        raise LLMError(f"Ollama returned error: {e}")
    
    content_parts = []
    last_token_time = time.time()
    
    for line in response.iter_lines(decode_unicode=True):
        now = time.time()
        if (now - last_token_time) > PER_TOKEN_TIMEOUT_SECONDS:
            raise LLMTimeoutError(
                f"No token received for {PER_TOKEN_TIMEOUT_SECONDS}s. "
                "Local model may be stalled."
            )
        
        if line is None:
            continue
        
        parsed = _parse_sse_line(line)
        
        if parsed is None:
            continue
        
        if parsed == "":
            break
        
        content_parts.append(parsed)
        last_token_time = now
    
    return "".join(content_parts)
