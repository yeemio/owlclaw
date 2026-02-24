# OwlHub Troubleshooting

## Common API Errors

- `401 missing credentials`:
  - Verify `Authorization: Bearer <token>` or `X-API-Key`.
- `403 admin role required`:
  - Use admin identity for blacklist/export/audit endpoints.
- `422 manifest validation failed`:
  - Check required fields and format in publish payload.
- `422 checksum does not match package content`:
  - Regenerate checksum from package and retry.

## Deployment Checks

1. Confirm rollout:

```bash
kubectl rollout status deployment/owlhub-api -n <namespace>
```

2. Validate runtime:

```bash
curl <base-url>/health
curl <base-url>/metrics
```

3. Verify migrations:

```bash
poetry run alembic -c alembic.ini heads
```
