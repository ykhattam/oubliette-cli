"""
cli.py - Entry point for oubliette.
"""
import argparse
import sys
from pathlib import Path

from oubliette.gate import check_path_access, redact_content, SecurityError
from oubliette.audit import log_event
from oubliette.llm import send_to_llm, LLMError
from oubliette.writer import write_file_atomic, WriteError

SYSTEM_PROMPT = (
    "You are a code assistant. "
    "Respond in plain ASCII. "
    "Use concise comments. "
    "Do not include secrets or credentials."
)

def _read_and_redact(file_path: str) -> str:
    """Read file, verify access, redact secrets, log action."""
    resolved = check_path_access(file_path)
    
    with open(resolved, "r") as f:
        raw = f.read()
    
    redacted = redact_content(raw)
    redaction_count = raw.count(redacted) - redacted.count("[REDACTED]")
    # Accurate count: compare length difference via pattern matches
    import re
    from oubliette.gate import REDACTION_PATTERNS
    total_redactions = 0
    for pattern in REDACTION_PATTERNS:
        total_redactions += len(pattern.findall(raw))
    
    log_event(
        "read_file",
        file_path=str(resolved),
        redactions_count=total_redactions,
    )
    
    if total_redactions > 0:
        print(f"[oubliette] Redacted {total_redactions} secret pattern(s).")
    
    return redacted

def main():
    parser = argparse.ArgumentParser(
        description="Paranoid AI coding assistant. Zero telemetry.",
    )
    parser.add_argument(
        "--file",
        type=str,
        help="File to read and analyze.",
    )
    parser.add_argument(
        "--prompt",
        type=str,
        required=True,
        help="Prompt to send to local LLM.",
    )
    parser.add_argument(
        "--write",
        type=str,
        help="Optional: write LLM response to this file (atomic, with diff preview).",
    )
    parser.add_argument(
        "--no-approval",
        action="store_true",
        help="Skip write approval prompt (use with caution).",
    )
    
    args = parser.parse_args()
    
    # Build prompt content
    prompt_parts = [args.prompt]
    
    if args.file:
        try:
            file_content = _read_and_redact(args.file)
            prompt_parts.append(f"\n--- File: {args.file} ---\n{file_content}")
        except SecurityError as e:
            print(f"[oubliette] BLOCKED: {e}", file=sys.stderr)
            sys.exit(1)
        except FileNotFoundError:
            print(f"[oubliette] File not found: {args.file}", file=sys.stderr)
            sys.exit(1)
    
    full_prompt = "\n".join(prompt_parts)
    
    log_event("send_to_llm", prompt=full_prompt)
    
    try:
        print("[oubliette] Sending to local Ollama...")
        response = send_to_llm(full_prompt, system=SYSTEM_PROMPT)
    except LLMError as e:
        print(f"[oubliette] LLM ERROR: {e}", file=sys.stderr)
        sys.exit(1)
    
    log_event("receive_from_llm", prompt=response)
    
    print("\n" + "=" * 60)
    print("LLM RESPONSE:")
    print("=" * 60)
    print(response)
    print("=" * 60)
    
    if args.write:
        try:
            write_file_atomic(
                args.write,
                response,
                require_approval=not args.no_approval,
            )
        except WriteError as e:
            print(f"[oubliette] WRITE ERROR: {e}", file=sys.stderr)
            sys.exit(1)

if __name__ == "__main__":
    main()
