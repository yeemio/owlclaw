-- CI-aligned test database initialization for local docker-compose.test.yml
-- Mirrors .github/workflows/test.yml behavior for owlclaw_test.

\c owlclaw_test
CREATE EXTENSION IF NOT EXISTS vector;
