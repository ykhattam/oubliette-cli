"""
llm.py - Local llama.cpp server router with lazy-start capability.
"""
import os
import time
import socket
import subprocess
import requests

ENDPOINT = os.environ.get("OUBLIETTE_LLM_ENDPOINT", "http://localhost:8080/v1/chat/completions")
MODEL = os.environ.get("OUBLIETTE_MODEL", "default")
LLAMA_BIN = os.environ.get("OUBLIETTE_LLAMA_BIN", "llama-server")
MODEL_PATH = os.environ.get("OUBLIETTE_MODEL_PATH", "models/qwen2.5-7b-instruct-q4_k_m.gguf")

class LLMError(Exception):
    """Raised when LLM communication fails."""
    pass

def _is_port_in_use(port: int) -> bool:
    """Check if a local port is currently listening."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('127.0.0.1', port)) == 0

def _start_llama_server():
    """Spawn llama-server in the background detached from the terminal."""
    print("[oubliette] Server not detected. Starting llama-server in background...")
    cmd = [
        LLAMA_BIN,
        "-m", MODEL_PATH,
        "--host", "127.0.0.1",
        "--port", "8080",
        "--ctx-size", "8192",
        "--n-gpu-layers", "99" # Adjust based on your hardware
    ]
    subprocess.Popen(
        cmd,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True # Detaches process so it survives if CLI exits
    )
    
    # Poll for port to open (max 30 seconds)
    for _ in range(30):
        if _is_port_in_use(8080):
            time.sleep(3) # Give model 3 extra seconds to load into VRAM
            return
        time.sleep(1)
    raise LLMError("Timeout waiting for llama-server to start on port 8080.")

def send_to_llm(prompt: str, system: str = None) -> str:
    """Sends prompt to the running (or newly started) llama-server instance."""
    # Lazy start: if port 8080 is closed, start the server
    if not _is_port_in_use(8080):
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
        response = requests.post(ENDPOINT, json=payload, timeout=120) # 120s for first token
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"].strip()
        
    except requests.exceptions.ConnectionError:
        raise LLMError(f"Cannot reach llama-server at {ENDPOINT}.")
    except requests.exceptions.HTTPError as e:
        raise LLMError(f"llama-server returned error: {e}")
    except Exception as e:
        raise LLMError(f"LLM execution failed: {e}")
