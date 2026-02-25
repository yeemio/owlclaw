# Release Security Scan Report

- Date: 2026-02-25
- Scope: repository working tree (excluding `.git/`, `.venv/`, `dist/`, `build/`)
- Scanner: `rg` pattern scan for common credential signatures

## Commands

```bash
rg -n --hidden -S "(AKIA[0-9A-Z]{16}|ghp_[A-Za-z0-9]{36}|xox[baprs]-|-----BEGIN (RSA|EC|OPENSSH) PRIVATE KEY-----|sk-[A-Za-z0-9]{20,})" -g "!.git/**" -g "!.venv/**" -g "!dist/**" -g "!build/**"
```

```bash
rg -n "^\\.env$|^dist/$|^build/$|__pycache__|\\.pyc" .gitignore -S
```

## Findings

1. One hit found:
   - `tests/unit/test_cli_skill.py:183`
   - value shape: `sk-...` (test fixture token string)
2. Classification:
   - Non-production test fixture only.
   - Not loaded from runtime secrets and not used as real credential.

## Result

- No production secrets detected in tracked runtime/config files.
- `.gitignore` covers `.env`, `dist/`, `build/`, caches and bytecode artifacts.

