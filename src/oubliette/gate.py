"""
gate.py - Security boundary for file access and content redaction.
"""
import re
from pathlib import Path

class SecurityError(Exception):
    """Raised when a file access or content check violates policy."""
    pass

# Hard-coded blocklist. No config override permitted.
# Checks resolved filename and suffix.
BLOCKED_NAMES = {".env", ".git/config"}
BLOCKED_SUFFIXES = {".pem", ".key"}
BLOCKED_PREFIXES = ("id_rsa", "id_ed25519")
BLOCKED_SUBSTRINGS = ("credentials", "service_account")

def check_path_access(path_str: str) -> Path:
    """
    Resolve path and verify against blocklist.
    Returns resolved Path if safe. Raises SecurityError if blocked.
    """
    # Resolve to absolute path to defeat traversal (e.g., ../)
    resolved = Path(path_str).resolve()
    
    name = resolved.name
    
    # 1. Check exact filenames
    if name in BLOCKED_NAMES:
        raise SecurityError(f"Access denied: {name} is blocked.")
        
    # 2. Check suffixes (.pem, .key)
    if resolved.suffix in BLOCKED_SUFFIXES:
        raise SecurityError(f"Access denied: suffix {resolved.suffix} is blocked.")
        
    # 3. Check prefixes (id_rsa, id_ed25519)
    if name.startswith(BLOCKED_PREFIXES):
        raise SecurityError(f"Access denied: prefix match on {name}.")
        
    # 4. Check substrings (credentials, service_account) in JSON files
    if resolved.suffix == ".json":
        for sub in BLOCKED_SUBSTRINGS:
            if sub in name:
                raise SecurityError(f"Access denied: substring '{sub}' in {name}.")
                
    # 5. Check specific patterns (secrets.*)
    if name.startswith("secrets."):
        raise SecurityError(f"Access denied: {name} matches secrets pattern.")

    return resolved

# Regex patterns for known secret formats.
# Strict matching to avoid false positives on UUIDs/Hashes.
REDACTION_PATTERNS = [
    re.compile(r"AKIA[0-9A-Z]{16}"),             # AWS Access Key
    re.compile(r"ghp_[a-zA-Z0-9]{36}"),          # GitHub Personal Access Token
    re.compile(r"sk-[a-zA-Z0-9]{20,}"),          # Generic Secret Key (OpenAI/Stripe style)
    re.compile(r"gho_[a-zA-Z0-9]{36}"),          # GitHub OAuth Token
    re.compile(r"ghu_[a-zA-Z0-9]{36}"),          # GitHub User-to-Server Token
    re.compile(r"ghs_[a-zA-Z0-9]{36}"),          # GitHub Server-to-Server Token
    re.compile(r"ghr_[a-zA-Z0-9]{36}"),          # GitHub Refresh Token
]

REDACTED_MARKER = "[REDACTED]"

def redact_content(content: str) -> str:
    """
    Scan content for known secret patterns and replace with marker.
    Does NOT use entropy scanning to preserve valid Base64/UUIDs.
    """
    sanitized = content
    for pattern in REDACTION_PATTERNS:
        sanitized = pattern.sub(REDACTED_MARKER, sanitized)
    return sanitized
