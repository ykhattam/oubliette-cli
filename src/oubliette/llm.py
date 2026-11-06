"""
llm.py - Local llama.cpp server router with auto-start capability.
"""
import os
import time
import socket
import subprocess
import requests
from urllib.parse import urlparse

ENDPOINT = os.environ.get("OUBLIETTE_LLM_ENDPOINT", "http://127.0.0.1:8081/v1/chat/completions")
MODEL = os.environ.get("OUBLIETTE_MODEL", "default")
LLAMA_BIN = os.environ.get("OUBLIETTE_LLAMA_BIN", "llama-server")
MODEL_PATH = os.environ.get("OUBLIETTE_MODEL_PATH", "models/qwen2.5-7b-instruct-q4_k_m.gguf")
READY_TIMEOUT_SECONDS = int(os.environ.get("OUBLIETTE_READY_TIMEOUT", "120"))

class LLMError(Exception):
    """Raised when LLM communication fails."""
    pass

def _get_port_from_endpoint() -> int:
    parsed = urlparse(ENDPOINT)
    return parsed.port or 8080

def _base_url() -> str:
    """Scheme://host:port of the server, with the API path stripped.

    ``ENDPOINT`` points at /v1/chat/completions, but llama.cpp serves /health at
    the server root, so the path must not be reused.
    """
    parsed = urlparse(ENDPOINT)
    scheme = parsed.scheme or "http"
    netloc = parsed.netloc or f"127.0.0.1:{_get_port_from_endpoint()}"
    return f"{scheme}://{netloc}"

def _is_port_in_use(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('127.0.0.1', port)) == 0

def _wait_for_server_ready(timeout: int = READY_TIMEOUT_SECONDS, interval: float = 1.0) -> bool:
    """Poll llama.cpp's /health until the model is actually loaded.

    An open port does not mean a usable server: llama-server binds the port
    before the weights are in memory and answers 503 while it loads. Polling
    only the socket (as this used to) returns 3s after the bind, so the first
    completion request hits a half-initialised server.
    """
    url = f"{_base_url()}/health"
    attempts = max(1, min(int(timeout / interval) if interval > 0 else 1, 60))
    for _ in range(attempts):
        try:
            response = requests.get(url, timeout=2)
            if response.status_code == 200 and (response.json() or {}).get("status") == "ok":
                return True
        except (requests.RequestException, ValueError):
            pass
        time.sleep(interval)
    return False

def _start_llama_server():
    port = _get_port_from_endpoint()
    print(f"[oubliette] Server not detected on port {port}. Starting llama-server in background...")
    
    cmd = [LLAMA_BIN, "-m", MODEL_PATH, "--host", "127.0.0.1", "--port", str(port), "--ctx-size", "8192"]
    
    subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
    
    print(f"[oubliette] Waiting for llama-server to listen on port {port} (up to 120s)...")
    for _ in range(120):
        if _is_port_in_use(port):
            break
        time.sleep(1)
    else:
        raise LLMError(f"Timeout waiting for llama-server to start on port {port}.")
    
    print(f"[oubliette] Port {port} is open; waiting for the model to finish loading...")
    if _wait_for_server_ready():
        print("[oubliette] Model loaded and ready.")
    else:
        # Older llama.cpp builds and OpenAI-compatible stand-ins do not expose
        # /health, so this is a warning rather than a hard failure.
        print("[oubliette] /health did not report ready; attempting the request anyway.")

def send_to_llm(prompt: str, system: str = None) -> str:
    port = _get_port_from_endpoint()
    if not _is_port_in_use(port):
        _start_llama_server()

    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})
    
    payload = {
        "model": MODEL,
        "messages": messages,
        "stream": False,
        "temperature": 0.2,
        "n_predict": 1024
    }
    
    try:
        # Increased timeout to 300s (5 minutes) for CPU inference
        response = requests.post(ENDPOINT, json=payload, timeout=300)
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"].strip()
        
    except requests.exceptions.ConnectionError:
        raise LLMError(f"Cannot reach llama-server at {ENDPOINT}.")
    except requests.exceptions.Timeout:
        raise LLMError("Model generation timed out after 300s. The model may be too large for your CPU, or the prompt is too long.")
    except requests.exceptions.HTTPError as e:
        raise LLMError(f"llama-server returned error: {e}")
    except Exception as e:
        raise LLMError(f"LLM execution failed: {e}")
