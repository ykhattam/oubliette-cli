# Paranoid AI Coding Assistant — Implementation Plan

## 1. Project Overview

**Name**: `oubliette-cli`
**Goal**: A minimal, terminal-native AI coding assistant with hard-coded forensic security boundaries. Zero telemetry. Hard secret blocking. Audit-grade logging.
**License**: Apache 2.0
**Target runtime**: Python 3.10+
**Max size**: ~200 lines of Python per core module (no arbitrary phase limits).

### Core Philosophy
- Paranoia is the default.
- Every byte sent to the model is logged as metadata only.
- Every file write is atomic and previewed.
- No feature that weakens the security boundary will be merged.

---

## 2. Architecture

```text
+-------------------------------------------------------------------+
|  CLI (stdin/stdout)                                               |
|  +-> argparse: file path + prompt                                 |
+-------------------------------------------------------------------+
|  Gate Layer (hard-coded, non-bypassable)                          |
|  +-> Path resolution: Path(user_path).resolve()                   |
|  +-> Blocklist check (resolved path against patterns)             |
|  +-> Regex redaction (AWS, GitHub, generic tokens)                |
|  +-> NO blanket Shannon entropy (prevents Base64/UUID breakage)   |
+-------------------------------------------------------------------+
|  Audit Logger (JSON lines, append-only, max 10MB)                 |
|  +-> Logs ONLY post-redaction metadata (path, redaction count)    |
|  +-> Logs SHA-256 of prompt, NEVER raw text                       |
+-------------------------------------------------------------------+
|  Local LLM Router (Ollama only, no fallback)                      |
|  +-> http://localhost:11434/v1/chat/completions                   |
|  +-> stream=True with 30s per-token timeout (no global 60s limit) |
+-------------------------------------------------------------------+
|  Atomic Writer (temp file + os.replace)                           |
|  +-> tempfile in SAME directory as target (prevents EXDEV error)  |
|  +-> diff preview -> user approval -> write                       |
+-------------------------------------------------------------------+