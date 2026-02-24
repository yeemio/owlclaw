# OwlHub CLI Reference

## Getting Started

```bash
owlclaw skill search --query monitor --index-url ./index.json
owlclaw skill install entry-monitor --index-url ./index.json
owlclaw skill installed --lock-file ./skill-lock.json
```

## Skill Author Guide (Publish Flow)

1. Prepare a local skill directory with `SKILL.md`.
2. Validate locally:

```bash
owlclaw skill validate ./my-skill --strict
```

3. Publish to API mode:

```bash
owlclaw skill publish ./my-skill \
  --mode api \
  --api-base-url http://localhost:8000 \
  --api-token <token>
```

## Command Reference

- Search:

```bash
owlclaw skill search \
  --query monitor \
  --tags trading,alert \
  --tag-mode or \
  --include-draft \
  --verbose
```

- Install:

```bash
owlclaw skill install entry-monitor \
  --version 1.0.0 \
  --no-deps \
  --verbose
```

- Update:

```bash
owlclaw skill update
owlclaw skill update entry-monitor
```

- Cache:

```bash
owlclaw skill cache-clear
```

## API Mode Troubleshooting

- `401` on publish: verify `--api-token` and role mapping.
- `403` on publish: check publisher identity and blacklist status.
- `422` on publish: check `SKILL.md` required fields and checksum.
- Install checksum mismatch: verify artifact integrity or use `--force` only for emergency recovery.

## Shell Completion

Completion scripts are provided under `scripts/completions/`:

- `scripts/completions/owlclaw.bash`
- `scripts/completions/owlclaw.zsh`
- `scripts/completions/owlclaw.fish`
