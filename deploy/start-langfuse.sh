#!/usr/bin/env bash
# Start Langfuse locally via official Docker Compose (for integration tests / dev).
# Usage: from repo root, run: ./deploy/start-langfuse.sh
# Then open http://localhost:3000 and create project + API keys; set LANGFUSE_* in .env.

set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
LANGFUSE_DIR="${LANGFUSE_DIR:-$REPO_ROOT/.langfuse}"

if [ ! -d "$LANGFUSE_DIR" ]; then
  echo "Cloning Langfuse into $LANGFUSE_DIR ..."
  git clone --depth 1 https://github.com/langfuse/langfuse.git "$LANGFUSE_DIR"
fi

cd "$LANGFUSE_DIR"
echo "Starting Langfuse (docker compose up -d) ..."
docker compose up -d
echo "Wait 2-3 minutes for langfuse-web to be Ready. Then open http://localhost:3000"
echo "Create a project and add LANGFUSE_PUBLIC_KEY / LANGFUSE_SECRET_KEY to $REPO_ROOT/.env"
