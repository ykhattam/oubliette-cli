"""
llm.py - Direct llama.cpp CLI runner (No HTTP/TCP overhead)
"""
import os
import subprocess

class LLMError(Exception):
    """Raised when LLM communication fails."""
    pass

def send_to_llm(prompt: str, system: str = None) -> str:
    """
    Executes local llama.cpp binary directly via subprocess.
    Bypasses local HTTP sockets entirely. Zero network stack.
    """
    # External control for speed/model swapping
    model_path = os.environ.get("OUBLIETTE_MODEL_PATH", "models/qwen2.5-coder.gguf")
    llama_bin = os.environ.get("OUBLIETTE_LLAMA_BIN", "llama-cli")
    
    full_prompt = prompt
    if system:
        full_prompt = f"System: {system}\n\nUser: {prompt}"
        
    # llama.cpp CLI arguments for fast, clean code generation
    cmd = [
        llama_bin,
        "-m", model_path,
        "-p", full_prompt,
        "-n", "512",          # Max tokens
        "--temp", "0.2",      # Low temperature for deterministic code
        "--no-display-prompt" # Prevent echoing input in output
    ]
    
    try:
        # subprocess.run is safer and cleaner than Popen for single-turn
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=60  # Hard 60s timeout prevents hangs
        )
        
        if result.returncode != 0:
            raise LLMError(f"llama.cpp failed: {result.stderr.strip()}")
            
        return result.stdout.strip()
        
    except FileNotFoundError:
        raise LLMError(f"Binary '{llama_bin}' not found. Install llama.cpp or set OUBLIETTE_LLAMA_BIN.")
    except subprocess.TimeoutExpired:
        raise LLMError("Local model execution timed out after 60s.")
    except Exception as e:
        raise LLMError(f"Failed executing local model: {e}")
