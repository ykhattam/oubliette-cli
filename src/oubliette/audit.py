"""
audit.py - Metadata-only audit logger.
"""
import json
import hashlib
from pathlib import Path
from datetime import datetime

# Hard-coded log path. No config override.
LOG_DIR = Path(".paranoid")
LOG_FILE = LOG_DIR / "audit.log"
MAX_LOG_SIZE_BYTES = 10 * 1024 * 1024  # 10MB

def _ensure_log_dir():
    """Create .paranoid/ directory if missing."""
    LOG_DIR.mkdir(exist_ok=True)

def _hash_content(content: str) -> str:
    """SHA-256 hash of content. Never log raw text."""
    return hashlib.sha256(content.encode("utf-8")).hexdigest()

def _rotate_log_if_needed():
    """Truncate oldest entries if log exceeds 10MB."""
    if not LOG_FILE.exists():
        return
    
    size = LOG_FILE.stat().st_size
    if size <= MAX_LOG_SIZE_BYTES:
        return
    
    # Read all lines, keep newest half
    with open(LOG_FILE, "r") as f:
        lines = f.readlines()
    
    keep_count = len(lines) // 2
    rotated_lines = lines[-keep_count:]
    
    with open(LOG_FILE, "w") as f:
        f.writelines(rotated_lines)

def log_event(action: str, file_path: str = None, redactions_count: int = 0, prompt: str = None):
    """
    Append one JSON-line event to audit log.
    Only logs metadata. Never logs raw content.
    """
    _ensure_log_dir()
    _rotate_log_if_needed()
    
    event = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "action": action,
    }
    
    if file_path:
        event["file_path"] = file_path
    
    if redactions_count > 0:
        event["redactions_count"] = redactions_count
    
    if prompt:
        # Hash prompt, never log raw text
        event["prompt_hash"] = _hash_content(prompt)
    
    with open(LOG_FILE, "a") as f:
        f.write(json.dumps(event) + "\n")
