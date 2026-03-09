# Pages 部署前检查清单

## 1) 数据文件完整性

- 运行数据构建脚本：
  - `python 50-publish/build_repo_data.py --source "20-normalized/repo_master_latest.csv"`
- `50-publish/site/repo-data.json` 存在且可被 JSON 解析
- `repo-data.json` 中关键字段完整：`repo` `url` `topic` `relevance` `risk` `adoption_priority`
- 数据来源映射已确认：`20-normalized/repo_master_latest.csv -> repo-data.json`

## 2) 页面资源可用性

- `50-publish/site/data-viewer.html` 存在
- `50-publish/site/data.js` 存在
- `data-viewer.html` 能正确加载 `data.js` 与 `repo-data.json`（浏览器无 404）

## 3) 功能校验（手工）

- 页面能展示仓库表格数据
- 四个筛选器可用：`topic` / `relevance` / `risk` / `adoption_priority`
- 切换筛选条件后，表格和数量统计会联动更新
- 仓库链接点击后可跳转到对应 GitHub 页面

## 4) 发布路径与配置

- GitHub Pages 发布目录指向 `50-publish/site/`（或等价输出目录）
- 若有 CI/CD，确认工作流包含站点文件同步步骤
- 若配置了缓存策略，确保 `repo-data.json` 更新后能及时生效

## 5) 回滚与应急

- 保留最近一次可用版本的 `repo-data.json`
- 发布失败时可回滚到上一个可访问 commit
- 若数据异常，优先回滚 `repo-data.json`，页面静态资源保持不变

