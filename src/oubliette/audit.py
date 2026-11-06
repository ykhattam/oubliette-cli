"""
audit.py - Metadata-only audit logger.
"""
import json
import hashlib
import os
from pathlib import Path
from datetime import datetime, timezone

# Resolution order: OUBLIETTE_AUDIT_DIR, else ./.paranoid in the current directory.
# The env override exists so a launcher can pin one stable audit trail instead of
# scattering a .paranoid/ folder into every project you happen to run from.
LOG_DIR = Path(os.environ.get("OUBLIETTE_AUDIT_DIR", ".paranoid"))
LOG_FILE = LOG_DIR / "audit.log"
MAX_LOG_SIZE_BYTES = 10 * 1024 * 1024

def _ensure_log_dir():
    LOG_DIR.mkdir(mode=0o700, exist_ok=True)
    if not LOG_FILE.exists():
        LOG_FILE.touch(mode=0o600)

def _hash_content(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()

def _rotate_log_if_needed():
    if not LOG_FILE.exists():
        return
    size = LOG_FILE.stat().st_size
    if size <= MAX_LOG_SIZE_BYTES:
        return
    with open(LOG_FILE, "r") as f:
        lines = f.readlines()
    keep_count = len(lines) // 2
    with open(LOG_FILE, "w") as f:
        f.writelines(lines[-keep_count:])

def log_event(action: str, file_path: str = None, redactions_count: int = 0, prompt: str = None):
    _ensure_log_dir()
    _rotate_log_if_needed()
    
    event = {
        "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "action": action,
    }
    if file_path:
        event["file_path"] = file_path
    if redactions_count > 0:
        event["redactions_count"] = redactions_count
    if prompt:
        event["prompt_hash"] = _hash_content(prompt)
    
    with open(LOG_FILE, "a") as f:
        f.write(json.dumps(event) + "\n")
