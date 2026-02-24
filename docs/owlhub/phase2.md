# OwlHub Phase 2 静态站点模式说明

## 1. Phase 2 新增能力

Phase 2 在 Phase 1 的基础上，增加了静态站点发现能力：
- 站点生成：`index/search/detail/dashboard/tag` 页面
- 搜索元数据：`search-index.json`
- 订阅与发现：`rss.xml`、`sitemap.xml`
- 标签分类：tag cloud + `tags/<tag>.html`
- 统计展示：下载总量、近 30 天下载量
- 审核体系（自动化）：Review System（提交、校验、状态流转）

## 2. 架构图（Phase 2）

```
Repositories(SKILL.md)
      |
      v
IndexBuilder + StatisticsTracker
      |
      v
index.json (+search_index +statistics)
      |
      v
SiteGenerator (Jinja2)
      |
      v
Static Pages (index/search/detail/dashboard/tag/rss/sitemap)
      |
      v
CLI Client (search/install/update, backward compatible)
```

## 3. 核心文件

- 索引构建：`owlclaw/owlhub/indexer/builder.py`
- 统计跟踪：`owlclaw/owlhub/statistics/tracker.py`
- 站点生成：`owlclaw/owlhub/site/generator.py`
- 审核系统：`owlclaw/owlhub/review/system.py`
- 发布工作流：`.github/workflows/owlhub-build-index.yml`

## 4. 工作流（Phase 2）

GitHub Actions 流程：
1. 构建 index（含 GitHub release 统计）
2. 生成静态站点产物
3. 上传 artifact（index + pages）
4. 部署到 GitHub Pages

可选参数：
- `vars.OWLHUB_BASE_URL`
- `vars.OWLHUB_CNAME`

## 5. 标签与检索行为

- CLI：`--tags` + `--tag-mode and|or`
- CLI 默认隐藏 `draft`，可用 `--include-draft` 查看
- 站点支持 tag cloud 浏览和 tag 详情页
- 站点搜索支持关键词 + tag 下拉筛选

## 6. 审核流程（自动化）

Review System 使用 JSON 文件存储记录，状态机：
- `pending` -> `approved`
- `pending` -> `rejected`

提交时先执行结构校验，失败直接落 `rejected`。
