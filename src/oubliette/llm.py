"""
llm.py - Local llama.cpp server router with auto-start capability.
"""
import os
import time
import socket
import subprocess
import requests

ENDPOINT = os.environ.get("OUBLIETTE_LLM_ENDPOINT", "http://127.0.0.1:8080/v1/chat/completions")
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
    
    port = 8080
    cmd = [
        LLAMA_BIN,
        "-m", MODEL_PATH,
        "--host", "127.0.0.1",
        "--port", str(port),
        "--ctx-size", "8192",
        "--n-gpu-layers", "99"  # Offload to GPU if available
    ]
    
    # Start detached process (survives if CLI exits)
    subprocess.Popen(
        cmd,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True
    )
    
    # Poll for port to open (max 120 seconds for model load)
    print("[oubliette] Waiting for model to load (up to 120s)...")
    for _ in range(120):
        if _is_port_in_use(port):
            time.sleep(3)  # Give model 3 extra seconds to fully initialize
            print("[oubliette] Model loaded and ready.")
            return
        time.sleep(1)
        
    raise LLMError("Timeout waiting for llama-server to start. Verify OUBLIETTE_LLAMA_BIN and OUBLIETTE_MODEL_PATH.")

def send_to_llm(prompt: str, system: str = None) -> str:
    """Sends prompt to the running (or newly started) llama-server instance."""
    port = 8080
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
        # 120s timeout for first token generation
        response = requests.post(ENDPOINT, json=payload, timeout=120)
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"].strip()
        
    except requests.exceptions.ConnectionError:
        raise LLMError(f"Cannot reach llama-server at {ENDPOINT}.")
    except requests.exceptions.HTTPError as e:
        raise LLMError(f"llama-server returned error: {e}")
    except Exception as e:
        raise LLMError(f"LLM execution failed: {e}")
