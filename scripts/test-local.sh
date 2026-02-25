#!/usr/bin/env bash
set -euo pipefail

UNIT_ONLY=0
KEEP_UP=0

for arg in "$@"; do
  case "$arg" in
    --unit-only)
      UNIT_ONLY=1
      ;;
    --keep-up)
      KEEP_UP=1
      ;;
    *)
      echo "Unknown argument: $arg" >&2
      exit 1
      ;;
  esac
done

cleanup() {
  if [ "$KEEP_UP" -eq 0 ]; then
    docker compose -f docker-compose.test.yml down >/dev/null 2>&1 || true
  fi
}

if [ "$KEEP_UP" -eq 0 ]; then
  trap cleanup EXIT
fi

docker compose -f docker-compose.test.yml up -d

echo "Waiting for postgres healthcheck..."
for _ in $(seq 1 30); do
  status=$(docker inspect --format '{{json .State.Health.Status}}' "$(docker compose -f docker-compose.test.yml ps -q postgres)" 2>/dev/null || echo '"starting"')
  if [ "$status" = '"healthy"' ]; then
    break
  fi
  sleep 2
done

if [ "$UNIT_ONLY" -eq 1 ]; then
  poetry run pytest tests/unit/ -q
else
  poetry run pytest tests/unit/ tests/integration/ -m "not e2e" -q
fi
