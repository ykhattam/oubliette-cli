"""
cli.py - Main CLI entry point and orchestration.
"""
import argparse
import sys
from oubliette.gate import check_path_access, redact_content, SecurityError
from oubliette.audit import log_event
from oubliette.llm import send_to_llm, LLMError
from oubliette.writer import write_file_atomic, WriteError

def _read_and_redact(file_path: str) -> str:
    """Read file, verify access, redact secrets, log action."""
    resolved = check_path_access(file_path)
    
    with open(resolved, "r") as f:
        raw = f.read()
    
    # Unpack the tuple returned by redact_content
    redacted_content, redaction_count = redact_content(raw)
    
    if redaction_count > 0:
        log_event("read_file", file_path=str(resolved), redactions_count=redaction_count)
    else:
        log_event("read_file", file_path=str(resolved))
    
    return redacted_content

def main():
    parser = argparse.ArgumentParser(description="Paranoid local AI coding assistant.")
    parser.add_argument("--file", required=True, help="Path to the file to analyze")
    parser.add_argument("--prompt", required=True, help="Prompt to send to the LLM")
    parser.add_argument("--write", help="Path to write the LLM response (triggers atomic write)")
    parser.add_argument("--no-approval", action="store_true", help="Skip interactive approval for --write")
    
    args = parser.parse_args()
    
    try:
        # 1. Read and redact the file
        file_content = _read_and_redact(args.file)

        print("[oubliette] Sending to local LLM server...")

        # 2. Send to LLM
        system_prompt = "You are a security-focused code reviewer. Be concise and direct."
        full_prompt = f"File content:\n\n{file_content}\n\nUser request: {args.prompt}"
        
        log_event("send_to_llm", prompt=full_prompt)
        response = send_to_llm(full_prompt, system=system_prompt)
        log_event("receive_from_llm", prompt=full_prompt)
        
        print("\n" + "="*60)
        print("LLM RESPONSE:")
        print("="*60)
        print(response)
        print("="*60 + "\n")
        
        # 3. Optional: Write to file
        if args.write:
            require_approval = not args.no_approval
            success = write_file_atomic(args.write, response, require_approval=require_approval)
            if success:
                print(f"[oubliette] Successfully wrote to {args.write}")
            else:
                print("[oubliette] Write cancelled by user.")
                
    except SecurityError as e:
        print(f"[oubliette] SECURITY ERROR: {e}", file=sys.stderr)
        sys.exit(1)
    except LLMError as e:
        print(f"[oubliette] LLM ERROR: {e}", file=sys.stderr)
        sys.exit(1)
    except WriteError as e:
        print(f"[oubliette] WRITE ERROR: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"[oubliette] UNEXPECTED ERROR: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
