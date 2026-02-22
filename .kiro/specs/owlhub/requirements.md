# 需求文档：Skills 注册中心（OwlHub）

## 简介

OwlHub 是 OwlClaw Skills 的注册、发现与分发中心，负责维护技能索引、版本、发布流程与审核策略，并为 CLI 提供搜索、安装、更新与统计能力。OwlHub 采用渐进式架构：GitHub 索引 → 静态站点 → 服务化数据库。

## 术语表

- **Skill**: 符合 Agent Skills 规范的技能包
- **Skill_Package**: 技能包标识（name + publisher）
- **Skill_Version**: 版本实体
- **Manifest**: 技能元数据清单
- **Index**: 技能索引（可搜索）
- **Publisher**: 技能发布者
- **Verification**: 自动校验与审查

## 需求

### 需求 1：技能发布与版本管理

**用户故事：** 作为技能作者，我希望能够发布和管理版本，以便持续迭代。

#### 验收标准

1. THE OwlHub SHALL 支持发布新 Skill_Version
2. THE OwlHub SHALL 支持语义化版本号
3. THE OwlHub SHALL 保留历史版本并可回滚
4. THE OwlHub SHALL 提供版本状态（draft/released/deprecated）
5. WHEN 版本信息缺失时，THE OwlHub SHALL 拒绝发布

### 需求 2：技能索引与搜索

**用户故事：** 作为开发者，我希望能够搜索技能并查看详情，以便快速集成。

#### 验收标准

1. THE OwlHub SHALL 提供按 name/keyword/tag 搜索
2. THE OwlHub SHALL 提供排序（下载量、更新时间、评分）
3. THE OwlHub SHALL 显示 Skill_Version 详情与依赖
4. THE OwlHub SHALL 提供分页与过滤
5. THE OwlHub SHALL 提供 CLI 搜索接口

### 需求 3：技能安装与更新

**用户故事：** 作为业务开发者，我希望通过 CLI 安装和更新技能。

#### 验收标准

1. THE CLI SHALL 支持按 name 安装 Skill
2. THE CLI SHALL 支持指定版本安装
3. THE CLI SHALL 支持检查并更新到最新版本
4. THE CLI SHALL 支持锁定版本并生成 lock 信息
5. WHEN 校验失败时，THE CLI SHALL 拒绝安装

### 需求 4：元数据与规范校验

**用户故事：** 作为维护者，我希望自动校验技能包规范性。

#### 验收标准

1. THE OwlHub SHALL 校验 SKILL.md frontmatter
2. THE OwlHub SHALL 校验目录结构与必要文件
3. THE OwlHub SHALL 提供校验报告
4. THE OwlHub SHALL 在发布前阻止不合规包
5. THE OwlHub SHALL 支持本地预检命令

### 需求 5：安全与信任

**用户故事：** 作为平台维护者，我希望控制技能来源并保障安全。

#### 验收标准

1. THE OwlHub SHALL 支持发布者身份验证
2. THE OwlHub SHALL 记录发布者与变更记录
3. THE OwlHub SHALL 支持签名或校验哈希
4. THE OwlHub SHALL 支持黑名单与撤销
5. THE OwlHub SHALL 提供漏洞或违规反馈渠道

### 需求 6：可观测与统计

**用户故事：** 作为运营人员，我希望了解技能使用与分发情况。

#### 验收标准

1. THE OwlHub SHALL 记录下载量与安装量
2. THE OwlHub SHALL 记录最近更新时间与活跃度
3. THE OwlHub SHALL 提供基础统计 API
4. THE OwlHub SHALL 支持导出统计数据
5. THE OwlHub SHALL 在 CLI 中展示关键指标

### 需求 7：生态治理与审核

**用户故事：** 作为平台管理员，我希望对技能进行审核与治理。

#### 验收标准

1. THE OwlHub SHALL 支持审核流程（自动 + 人工）
2. THE OwlHub SHALL 支持内容分类与标签
3. THE OwlHub SHALL 支持下架与冻结
4. THE OwlHub SHALL 记录审核结果与原因
5. THE OwlHub SHALL 支持申诉流程记录

### 需求 8：渐进式架构演进

**用户故事：** 作为架构负责人，我希望系统能从轻量形态逐步演进。

#### 验收标准

1. THE OwlHub SHALL 支持 GitHub 索引模式
2. THE OwlHub SHALL 支持静态站点索引发布
3. THE OwlHub SHALL 提供服务化 API 的迁移路径
4. THE OwlHub SHALL 在阶段切换时保持兼容
5. THE OwlHub SHALL 文档化演进阶段与边界

---

## 非功能需求

### NFR-1：可用性

- 索引查询可用性 ≥ 99%
- 关键路径支持缓存与降级

### NFR-2：性能

- 搜索响应 P95 < 500ms（静态/缓存前提）

---

## 约束与假设

### 约束

- 早期阶段避免引入复杂服务依赖
- 必须遵循 Agent Skills 规范

### 假设

- 发布者使用 GitHub 或类似托管平台

---

## 依赖

### 内部依赖

- cli-skill
- capabilities-skills

### 外部依赖

- GitHub API
- 静态站点托管

---

## 风险与缓解

### 风险：生态质量不稳定

- **影响**：劣质技能影响用户体验
- **缓解**：校验 + 审核 + 黑名单机制

---

## Definition of Done

- [ ] 需求 1-8 验收通过
- [ ] NFR-1/2 通过
- [ ] CLI 可完成搜索与安装
- [ ] 索引可公开访问

---

## 参考文档

- docs/ARCHITECTURE_ANALYSIS.md
- .kiro/specs/capabilities-skills/requirements.md

---

**维护者**：平台研发
**最后更新**：2026-02-22
