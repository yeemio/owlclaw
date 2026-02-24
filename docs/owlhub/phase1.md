# OwlHub Phase 1 使用与结构说明

## 1. 架构边界（GitHub Index Mode）

```
Publisher Repos (SKILL.md + files)
            |
            v
IndexBuilder (crawl + validate + checksum)
            |
            v
index.json (static artifact / GitHub Pages / CDN)
            |
            v
owlclaw skill search/install/installed
```

Phase 1 只依赖静态 `index.json`，不引入服务端 API 和数据库。

## 2. 配置文件

默认配置文件：`.owlhub/config.yaml`

```yaml
index_url: "./index.json"
repositories:
  - "templates/skills"
update_interval: "1h"
install_dir: "./.owlhub/skills"
lock_file: "./skill-lock.json"
```

字段说明：
- `index_url`: 本地路径或 HTTP(S) 地址
- `repositories`: 构建索引时扫描的仓库路径列表
- `update_interval`: 索引构建周期（用于 workflow/scheduler）
- `install_dir`: 技能安装根目录
- `lock_file`: 已安装技能锁文件

## 3. Skill 包结构要求

最小结构：

```
<publisher>/<skill-name>/
  SKILL.md
```

`SKILL.md` frontmatter 最小字段：
- `name`
- `description`
- `metadata.version`

安装包校验规则（Phase 1）：
- 必须包含 `SKILL.md`
- 包校验和必须匹配 `index.json` 的 `checksum`

## 4. index.json Schema（Phase 1）

顶层结构：

```json
{
  "version": "1.0",
  "generated_at": "2026-02-24T00:00:00+00:00",
  "total_skills": 1,
  "skills": []
}
```

`skills[]` 单项：

```json
{
  "manifest": {
    "name": "entry-monitor",
    "publisher": "acme",
    "version": "1.0.0",
    "description": "Skill description",
    "license": "MIT",
    "tags": ["demo"],
    "dependencies": {}
  },
  "download_url": "https://example.com/entry-monitor-1.0.0.tar.gz",
  "checksum": "sha256:<hex>",
  "published_at": "2026-02-24T00:00:00+00:00",
  "updated_at": "2026-02-24T00:00:00+00:00",
  "version_state": "released"
}
```

## 5. CLI 命令（Phase 1）

- `owlclaw skill search --query <text> [--tags tag1,tag2] [--index-url <path|url>]`
- `owlclaw skill install <name> [--version <semver>] [--index-url <path|url>]`
- `owlclaw skill installed [--lock-file <path>]`

安装成功后会更新 `skill-lock.json`，记录解析后的版本、下载 URL、checksum 和安装路径。
