# oubliette-cli

Paranoid AI coding assistant. Zero telemetry. Hard secret boundaries. Audit-grade logging.

> An oubliette is a secret dungeon with access only through a trapdoor.
> Secrets go in. Nothing leaks out.

## Install

pipx install git+https://github.com/ykhattam/oubliette-cli.git

## Usage

Requires a local llama-server on port 8080.

    oubliette --file src/main.py --prompt "Review this code."
    oubliette --file src/main.py --prompt "Add type hints." --write src/main_typed.py

## Security Invariants

1. No cloud endpoints — localhost only
2. No telemetry — zero phone-home
3. Hard secret blocking — .env, .key, credentials.json
4. Regex-only redaction — preserves UUIDs/Base64
5. Metadata-only audit log — SHA-256 hashes, never raw text
6. Strict permissions — dir 0o700, log 0o600

## License

Apache 2.0
