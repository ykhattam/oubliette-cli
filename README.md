# oubliette-cli

Paranoid AI coding assistant. Zero telemetry. Hard secret boundaries. Audit-grade logging.

> An oubliette is a secret dungeon with access only through a trapdoor.
> Secrets go in. Nothing leaks out.

## Installation

### From Source (Local / Development)
```bash
git clone https://github.com/ykhattam/oubliette-cli.git
cd oubliette-cli
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

### Direct Install via pipx
```bash
pipx install git+https://github.com/ykhattam/oubliette-cli.git
```

## Usage

Requires a local llama-server running (e.g., on port 8081 or 8080).

```bash
oubliette --file src/main.py --prompt "Review this code."
oubliette --file src/main.py --prompt "Add type hints." --write src/main_typed.py
```

### CLI Arguments
- `--file <path>`: Path to the file to analyze.
- `--prompt <text>`: Prompt/instructions for the local LLM.
- `--write <path>`: Path to write the LLM response (triggers atomic write with diff preview).
- `--no-approval`: Skip interactive confirmation when writing changes.

## Security Invariants

1. No cloud endpoints — localhost only
2. No telemetry — zero phone-home
3. Hard secret blocking — `.env`, `.key`, `credentials.json`
4. Regex-only redaction — preserves UUIDs/Base64
5. Metadata-only audit log — SHA-256 hashes, never raw text
6. Strict permissions — dir `0o700`, log `0o600`

## Running Tests
```bash
pip install pytest
pytest
```

## License

Apache 2.0
