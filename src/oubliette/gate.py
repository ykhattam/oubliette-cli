"""
gate.py - Security gate for file access and content redaction.
"""
import re
from pathlib import Path

class SecurityError(Exception):
    """Raised when a security boundary is violated."""
    pass

# Hard-coded blocklist (non-configurable by design)
BLOCKED_NAMES = {
    ".env", ".env.local", ".env.production", ".env.development",
    "git/config", "config", "credentials", "service_account.json"
}
BLOCKED_SUFFIXES = {".pem", ".key", ".p12", ".pfx", ".jks", ".keystore"}
BLOCKED_PREFIXES = ("id_rsa", "id_ed25519", "id_ecdsa", "id_dsa")
BLOCKED_SUBSTRINGS = ("credentials", "service_account", "private_key", "secret_key")

# Regex patterns for secret redaction
REDACTION_PATTERNS = [
re.compile(r"AKIA[0-9A-Z]{16}"),             # AWS Access Key ID
re.compile(r"(?<![A-Za-z0-9/+=])[A-Za-z0-9/+=]{40}(?![A-Za-z0-9/+=])"), # AWS Secret Access Key
re.compile(r"ghp_[a-zA-Z0-9]{36}"),          # GitHub Personal Access Token
re.compile(r"gho_[a-zA-Z0-9]{36}"),          # GitHub OAuth Token
re.compile(r"ghu_[a-zA-Z0-9]{36}"),          # GitHub User-to-Server Token
re.compile(r"ghs_[a-zA-Z0-9]{36}"),          # GitHub Server-to-Server Token
re.compile(r"ghr_[a-zA-Z0-9]{36}"),          # GitHub Refresh Token
re.compile(r"sk-[A-Za-z0-9][A-Za-z0-9_-]{15,}"),  # Generic Secret Key (OpenAI/Stripe style, incl. sk-live-…)
re.compile(r"sk_live_[a-zA-Z0-9]{24,}"),     # Stripe Live Key
re.compile(r"sk_test_[a-zA-Z0-9]{24,}"),     # Stripe Test Key
re.compile(r"xoxb-[0-9]{11,13}-[a-zA-Z0-9-]*"), # Slack Token
re.compile(r"-----BEGIN (RSA |EC |DSA )?PRIVATE KEY-----"),  # Private keys
]

def check_path_access(path_str: str) -> Path:
    """
    Validates path access against security boundaries.
    Returns resolved Path if allowed, raises SecurityError if blocked.
    """
    # 1. Explicitly block path traversal attempts
    if ".." in Path(path_str).parts:
        raise SecurityError("Path traversal detected: '..' is not allowed")
    
    try:
        # 2. Resolve the path (without strict=True to allow checking new files)
        resolved = Path(path_str).resolve()
    except OSError as e:
        raise SecurityError(f"Path is inaccessible: {path_str}")
    
    name = resolved.name.lower()
    
    # 3. Check against hard-coded blocklist
    if name in BLOCKED_NAMES:
        raise SecurityError(f"Access denied: {name} is in the blocklist")
    
    if any(name.endswith(suffix) for suffix in BLOCKED_SUFFIXES):
        raise SecurityError(f"Access denied: {name} has a blocked suffix")
    
    if any(name.startswith(prefix) for prefix in BLOCKED_PREFIXES):
        raise SecurityError(f"Access denied: {name} has a blocked prefix")
    
    if any(substring in name for substring in BLOCKED_SUBSTRINGS):
        raise SecurityError(f"Access denied: {name} contains a blocked substring")
    
    return resolved

def redact_content(content: str) -> tuple[str, int]:
    """
    Redacts secrets from content using regex patterns.
    Returns (redacted_content, redaction_count).
    """
    redaction_count = 0
    
    for pattern in REDACTION_PATTERNS:
        matches = pattern.findall(content)
        redaction_count += len(matches)
        content = pattern.sub("[REDACTED]", content)
    
    return content, redaction_count
