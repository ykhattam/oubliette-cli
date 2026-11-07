"""
writer.py - Atomic file writer with diff preview.
"""
import os
import sys
import tempfile
import difflib
from pathlib import Path
from oubliette.gate import check_path_access, SecurityError
from oubliette.audit import log_event

class WriteError(Exception):
    """Raised when file write fails or is blocked."""
    pass

def _strip_code_fences(content: str) -> str:
    """Drop a single wrapping markdown fence the model likes to add.

    Models answer code requests inside ```lang ... ``` blocks. Writing that
    verbatim puts fence lines into a .py/.js file and breaks it, so the outer
    fence (and its language tag) is removed when it wraps the whole response.
    """
    stripped = content.strip()
    if not stripped.startswith("```"):
        return content
    lines = stripped.splitlines()
    if len(lines) < 2 or not lines[-1].strip().startswith("```"):
        return content
    inner = lines[1:-1]
    return "\n".join(inner) + "\n"


def _generate_diff(original: str, new: str, path: str) -> str:
    """Generate unified diff between original and new content."""
    original_lines = original.splitlines(keepends=True)
    new_lines = new.splitlines(keepends=True)
    
    diff = difflib.unified_diff(
        original_lines,
        new_lines,
        fromfile=f"a/{path}",
        tofile=f"b/{path}",
    )
    return "".join(diff)

def write_file_atomic(target_path: str, content: str, require_approval: bool = True) -> bool:
    """
    Write content to file atomically with diff preview.
    
    1. Verify path is not blocked
    2. Read existing content (if file exists)
    3. Generate and display diff
    4. Require user approval (unless require_approval=False)
    5. Write to temp file in same directory
    6. Atomic replace via os.replace()
    
    Returns True if write succeeded, False if user declined.
    Raises WriteError if path is blocked or write fails.
    """
    # 1. Verify path is safe (raises SecurityError if blocked)
    try:
        resolved = check_path_access(target_path)
    except SecurityError as e:
        raise WriteError(f"Write blocked: {e}")
    
    # 2. Read existing content
    original = ""
    if resolved.exists():
        with open(resolved, "r") as f:
            original = f.read()

    # Models wrap code answers in ``` fences; strip the outer pair before diffing.
    content = _strip_code_fences(content)

    # Redaction markers must not silently land on disk as the real value's
    # replacement — writing back a file whose key now reads [REDACTED] is data
    # loss, so say so loudly rather than discovering it later.
    if "[REDACTED]" in content:
        print(
            "[oubliette] WARNING: proposed content contains [REDACTED] markers. "
            "Writing it will overwrite the original secret with this placeholder.",
            file=sys.stderr,
        )
    
    # 3. Generate diff
    diff = _generate_diff(original, content, str(resolved))
    
    if not diff:
        print("No changes detected. File already matches target content.")
        log_event("write_skipped", file_path=str(resolved))
        return True
    
    # 4. Display diff and require approval
    print("\n" + "=" * 60)
    print("PROPOSED CHANGES:")
    print("=" * 60)
    print(diff)
    print("=" * 60)
    
    if require_approval:
        response = input("Apply these changes? [y/N]: ").strip().lower()
        if response != "y":
            print("Write cancelled by user.")
            log_event("write_declined", file_path=str(resolved))
            return False
    
    # 5. Write to temp file in SAME directory (prevents EXDEV)
    target_dir = resolved.parent
    tmp_path = None
    try:
        target_dir.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(
            mode="w",
            dir=target_dir,
            delete=False,
            suffix=".tmp",
        ) as tmp:
            tmp.write(content)
            tmp_path = Path(tmp.name)
    except OSError as e:
        if tmp_path is not None and tmp_path.exists():
            tmp_path.unlink()
        raise WriteError(f"Failed to create temp file: {e}")
    
    # 6. Atomic replace
    try:
        os.replace(tmp_path, resolved)
    except OSError as e:
        # Clean up temp file on failure
        if tmp_path is not None and tmp_path.exists():
            tmp_path.unlink()
        raise WriteError(f"Atomic replace failed: {e}")
    
    print(f"Successfully wrote to {resolved}")
    log_event("write_success", file_path=str(resolved))
    return True
