-- OwlClaw database bootstrap for local/dev/prod compose.
-- Executed by postgres entrypoint only when PGDATA is empty.
-- Creates isolated databases for hatchet, owlclaw, and langfuse.

-- 1) Hatchet database and role (Hatchet only)
CREATE DATABASE hatchet;
CREATE ROLE hatchet WITH LOGIN PASSWORD 'hatchet';
ALTER DATABASE hatchet OWNER TO hatchet;

-- 2) OwlClaw business database and role
CREATE DATABASE owlclaw;
CREATE ROLE owlclaw WITH LOGIN PASSWORD 'owlclaw';
ALTER DATABASE owlclaw OWNER TO owlclaw;

-- 3) Langfuse database and role
CREATE DATABASE langfuse;
CREATE ROLE langfuse WITH LOGIN PASSWORD 'langfuse';
ALTER DATABASE langfuse OWNER TO langfuse;

-- 4) Enable pgvector for owlclaw database
\c owlclaw
CREATE EXTENSION IF NOT EXISTS vector;
