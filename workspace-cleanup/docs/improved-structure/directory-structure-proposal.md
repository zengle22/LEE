---
title: 文档目录结构优化方案
author: LEE Team
date: 2026-02-19
version: 1.0
last_updated: 2026-02-19
---

# 文档目录结构优化方案

## 现状分析

### 当前目录结构

```
lee/
├── README.md                    # 项目主页 ✓
├── CHANGELOG.md                 # 变更日志 ✓
├── docs/                        # 主文档目录
│   ├── README.md               # 文档索引 ✓
│   ├── architecture/           # 架构文档 (21 个)
│   ├── features/               # 功能文档 (18 个)
│   ├── guides/                 # 指南 (19 个)
│   ├── technical/              # 技术文档 (19 个)
│   ├── operations/             # 运维文档 (1 个)
│   └── archive/                # 归档文档 (15 个)
├── spec-global/                # 全局规范 (64 个)
├── examples/                   # 示例 (15 个)
├── changelogs/                 # 变更日志 (3 个)
├── tech-debt/                  # 技术债务 (1 个)
├── mcp-server/                 # MCP 服务器
├── tests/                      # 测试文档
└── output/                     # 输出文件
```

### 问题识别

1. **技术债务文档位置不当**
   - 当前在根目录的 `tech-debt/`
   - 应该归档到技术文档下

2. **输出文件混用**
   - `output/` 包含临时和永久输出
   - 缺乏清晰的分类

3. **示例文档分散**
   - 部分在 `examples/`
   - 部分在 `demos/`
   - 部分在 `demo_l3_orchestration/`

## 优化方案

### 方案 1: 最小调整（推荐）

仅调整明显不合理的文档位置，保持整体结构稳定。

#### 需要移动的文档

```bash
# 1. 技术债务文档
tech-debt/ → docs/technical/tech-debt/

# 2. 合并演示目录
demo_l3_orchestration/ → examples/l3-orchestration-demo/
demos/ → examples/ (合并内容)
```

#### 需要创建的索引

```bash
# 创建文档索引
docs/INDEX.md                   # 主索引
docs/technical/INDEX.md         # 技术文档索引
docs/features/INDEX.md          # 功能文档索引
```

### 方案 2: 全面重组

对整个文档结构进行全面重组，按用户角色和文档类型分类。

```
docs/
├── overview/                   # 概览文档
│   ├── README.md
│   ├── getting-started.md
│   └── architecture-overview.md
│
├── user-guide/                # 用户指南
│   ├── installation/
│   ├── quick-start/
│   ├── tutorials/
│   └── reference/
│
├── developer-guide/           # 开发者指南
│   ├── architecture/
│   ├── api-reference/
│   ├── contributing/
│   └── internals/
│
├── operator-guide/            # 运维指南
│   ├── deployment/
│   ├── monitoring/
│   └── troubleshooting/
│
├── specifications/            # 规范文档
│   ├── adr/                   # 架构决策
│   ├── rfc/                   # 征求意见
│   └── requirements/          # 需求文档
│
└── reports/                   # 报告文档
    ├── project-reports/
    ├── bug-reports/
    └── tech-debt/
```

### 方案 3: 混合方案

结合方案 1 和方案 2 的优点，逐步优化。

#### 第一阶段（立即执行）

1. 移动技术债务文档
2. 创建文档索引
3. 补充缺失的元数据

#### 第二阶段（后续优化）

1. 重组用户指南
2. 创建开发者指南
3. 优化导航结构

## 推荐执行方案

**采用方案 1**，原因如下：

1. **最小化影响**
   - 不破坏现有的文档链接
   - 保持用户熟悉的结构
   - 降低迁移风险

2. **立即可行**
   - 移动文档数量少
   - 执行时间短
   - 易于验证

3. **渐进改进**
   - 为后续优化留出空间
   - 可以根据反馈调整
   - 风险可控

## 具体执行步骤

### Step 1: 移动技术债务文档

```bash
# 创建目标目录
mkdir -p docs/technical/tech-debt

# 移动文档
mv tech-debt/tech-debt-2025-02-19.md docs/technical/tech-debt/

# 更新元数据中的引用
```

### Step 2: 合并演示目录

```bash
# 移动 L3 编排演示
mv demo_l3_orchestration/* examples/l3-orchestration-demo/

# 移动通用演示
mv demos/* examples/demos/

# 删除空目录
rmdir demo_l3_orchestration demos
```

### Step 3: 创建文档索引

创建以下索引文件：

1. **主索引** (`docs/INDEX.md`)
   - 按角色分类的文档导航
   - 快速链接到常用文档

2. **技术文档索引** (`docs/technical/INDEX.md`)
   - 按主题分类的技术文档
   - 相关文档链接

3. **功能文档索引** (`docs/features/INDEX.md`)
   - 功能特性列表
   - 实现状态和文档链接

### Step 4: 更新交叉引用

检查并更新以下位置的文档引用：

- README.md
- docs/README.md
- 各目录的 README.md

## 文档元数据标准化

### 统一元数据格式

所有文档应包含以下元数据：

```yaml
---
title: 文档标题
author: LEE Team
date: YYYY-MM-DD
version: X.Y
last_updated: YYYY-MM-DD
tags: [tag1, tag2, tag3]
category: category-name
---
```

### 新增字段

- **tags**: 文档标签，便于搜索和分类
- **category**: 文档类别，用于索引

### 标签体系

定义以下标签类别：

**按角色**:
- `user` - 最终用户
- `developer` - 开发者
- `operator` - 运维人员
- `architect` - 架构师

**按主题**:
- `workflow` - 工作流
- `orchestrator` - 编排器
- `gates` - 人工门禁
- `testing` - 测试
- `deployment` - 部署

**按状态**:
- `stable` - 稳定
- `experimental` - 实验性
- `deprecated` - 已弃用
- `archived` - 已归档

## 验证和测试

### 移动验证清单

- [ ] 所有文档成功移动
- [ ] 元数据已更新
- [ ] 交叉引用已更新
- [ ] 文档可正常访问
- [ ] 链接有效性检查

### 质量检查

- [ ] 所有文档有元数据
- [ ] 文档命名符合规范
- [ ] 目录结构清晰
- [ ] 索引文件完整

## 后续改进建议

### 短期（1-2 周）

1. 完成所有文档的元数据补充
2. 创建完整的文档索引
3. 建立文档更新流程

### 中期（1-2 个月）

1. 实施文档搜索功能
2. 创建文档贡献指南
3. 建立文档审核流程

### 长期（3-6 个月）

1. 考虑迁移到静态网站生成器
2. 建立文档版本控制系统
3. 实现自动化文档测试

## 风险评估

### 低风险

- 移动技术债务文档
- 创建索引文件
- 补充元数据

### 中风险

- 合并演示目录
- 更新交叉引用
- 重组子目录

### 高风险

- 全面重组目录结构
- 修改文档命名规范
- 改变文档格式

## 时间估算

| 任务 | 工作量 | 优先级 |
|------|--------|--------|
| 移动技术债务文档 | 5 分钟 | 高 |
| 合并演示目录 | 15 分钟 | 中 |
| 创建文档索引 | 30 分钟 | 高 |
| 补充元数据 | 2 小时 | 高 |
| 更新交叉引用 | 30 分钟 | 中 |
| 验证和测试 | 30 分钟 | 高 |

**总计**: 约 4 小时

## 成功标准

1. **所有文档有完整元数据**
   - 覆盖率: 100%
   - 格式统一: ✓

2. **目录结构清晰**
   - 分类合理: ✓
   - 命名一致: ✓

3. **文档易于发现**
   - 有索引文件: ✓
   - 交叉引用正确: ✓

4. **无破坏性变更**
   - 现有链接有效: ✓
   - 向后兼容: ✓

---

**文档版本**: 1.0
**创建日期**: 2026-02-19
**审核状态**: 待审核
**实施状态**: 待实施
