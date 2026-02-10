# OwlClaw Spec 文档目录

> **规范文档**: `.kiro/SPEC_DOCUMENTATION_STANDARD.md`

---

## 目录结构

```
.kiro/
├── SPEC_DOCUMENTATION_STANDARD.md  # 文档规范标准（必读）
└── specs/                           # 功能文档
    ├── {feature-name}/
    │   ├── requirements.md          # 需求文档（WHAT）
    │   ├── design.md                # 设计文档（HOW）
    │   └── tasks.md                 # 任务文档（WHO/WHEN）
    └── ...
```

---

## 快速开始

### 创建新功能文档

```bash
# 1. 创建目录
mkdir -p .kiro/specs/{feature-name}

# 2. 按 SPEC_DOCUMENTATION_STANDARD.md 第二、三、四章的模板编写
#    - requirements.md（需求）
#    - design.md（设计）
#    - tasks.md（任务）
```

### 查看规范

阅读 `.kiro/SPEC_DOCUMENTATION_STANDARD.md` 了解完整的文档规范。

---

## 功能总览

**SPEC_TASKS_SCAN**（Spec 循环的单一真源）：`.kiro/specs/SPEC_TASKS_SCAN.md`

## 现有文档

| 功能 | 状态 | 路径 |
|------|------|------|
| **功能清单总览** | ✅ 已创建 | `.kiro/specs/SPEC_TASKS_SCAN.md` |
| （各 spec 待创建） | | |

---

## 规范要点

### 三层文档结构

1. **requirements.md** — 需求文档（WHAT）
2. **design.md** — 设计文档（HOW）
3. **tasks.md** — 任务文档（WHO/WHEN）

### 适用范围

- ✅ **必须**：新功能和重大重构
- 🟡 **建议**：小功能（至少 requirements + tasks）
- 🟢 **可选**：Bug 修复

---

**维护者**: yeemio
**最后更新**: 2026-02-10
