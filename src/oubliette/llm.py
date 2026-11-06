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

class LLMError(Exception):
    """Raised when LLM communication fails."""
    pass

def _get_port_from_endpoint() -> int:
    parsed = urlparse(ENDPOINT)
    return parsed.port or 8080

def _is_port_in_use(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('127.0.0.1', port)) == 0

def _start_llama_server():
    port = _get_port_from_endpoint()
    print(f"[oubliette] Server not detected on port {port}. Starting llama-server in background...")
    
    cmd = [LLAMA_BIN, "-m", MODEL_PATH, "--host", "127.0.0.1", "--port", str(port), "--ctx-size", "8192"]
    
    subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
    
    print(f"[oubliette] Waiting for model to load on port {port} (up to 120s)...")
    for _ in range(120):
        if _is_port_in_use(port):
            time.sleep(3)
            print("[oubliette] Model loaded and ready.")
            return
        time.sleep(1)
    raise LLMError(f"Timeout waiting for llama-server to start on port {port}.")

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
