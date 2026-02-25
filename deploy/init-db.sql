-- OwlClaw 数据库初始化脚本
-- 详见 docs/DATABASE_ARCHITECTURE.md
-- 仅当 PostgreSQL 数据目录为空时由 docker-entrypoint 执行。
-- 创建 hatchet（Hatchet 独占）与 owlclaw（OwlClaw 业务）两个 database。

-- 1. Hatchet 独占数据库
CREATE DATABASE hatchet;
CREATE ROLE hatchet WITH LOGIN PASSWORD 'hatchet';
ALTER DATABASE hatchet OWNER TO hatchet;

-- 2. OwlClaw 业务数据库
CREATE DATABASE owlclaw;
CREATE ROLE owlclaw WITH LOGIN PASSWORD 'owlclaw';
ALTER DATABASE owlclaw OWNER TO owlclaw;

-- 2.5 Langfuse 观测数据库（可选组件，dev compose 复用同一 PostgreSQL 实例）
CREATE DATABASE langfuse;
CREATE ROLE langfuse WITH LOGIN PASSWORD 'langfuse';
ALTER DATABASE langfuse OWNER TO langfuse;

-- 3. OwlClaw 库启用 pgvector（Agent 记忆向量搜索）
\c owlclaw
CREATE EXTENSION IF NOT EXISTS vector;
