# Design: Skills 注册中心（OwlHub）

> **目标**：建立 Skills 注册、发布与发现机制，支持 OwlHub 生态
> **状态**：设计中
> **最后更新**：2026-02-22

---

## 1. 架构设计

### 1.1 整体架构

```
Publisher Repo
   │
   ▼
Index Builder ──▶ Static Index (phase 1)
   │
   └────────────▶ OwlHub API (phase 2/3)

CLI ───────────▶ Search/Install
```

### 1.2 核心组件

#### 组件 1：Index Builder

**职责**：抓取技能仓库，生成标准索引与校验报告。

#### 组件 2：Registry API

**职责**：提供搜索、详情、下载统计、版本管理接口。

#### 组件 3：CLI 客户端

**职责**：搜索、安装、更新技能。

---

## 2. 实现细节

### 2.1 文件结构（示意）

```
owlhub/
├── indexer/
├── api/
└── schema/
```

### 2.2 索引格式

**Manifest 示例**：
```json
{
  "name": "entry-monitor",
  "version": "1.2.0",
  "publisher": "acme",
  "tags": ["trading", "monitor"],
  "files": ["SKILL.md", "scripts/check.py"]
}
```

---

## 3. 数据流

### 3.1 发布流程

```
Publisher Repo
   │
   ▼
Index Builder
   │
   ▼
Index Publish
   │
   ▼
CLI Search/Install
```

---

## 4. 错误处理

### 4.1 校验失败

- 记录失败原因
- 拒绝发布

---

## 5. 配置

### 5.1 配置文件

```yaml
owlhub:
  index_url: https://example.com/index.json
```

### 5.2 环境变量

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `OWLHUB_INDEX_URL` | 索引地址 | 无 |

---

## 6. 测试策略

### 6.1 单元测试

- 索引生成与校验

### 6.2 集成测试

- CLI 搜索与安装

---

## 7. 迁移计划

### Phase 1：GitHub 索引（2-3 天）

- [ ] 基础索引生成
- [ ] 静态站点发布

### Phase 2：服务化 API（3-5 天）

- [ ] API 服务与数据库
- [ ] 权限与统计

---

## 8. 风险与缓解

### 风险：索引不一致

**缓解**：每次发布生成新版本并校验

---

## 9. 契约与 Mock

### 9.1 API 契约

- `/skills` 搜索
- `/skills/{name}` 详情
- `/skills/{name}/versions` 版本

### 9.2 Mock 策略

- 使用本地索引文件模拟 API

---

## 10. 参考文档

- docs/ARCHITECTURE_ANALYSIS.md

---

**维护者**：平台研发
**最后更新**：2026-02-22
