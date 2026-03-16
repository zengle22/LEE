# 决策引用 - 交付主链建立与 RELEASE 起点治理

本文件整理了 TECH-FEAT-SRC-046-001 技术设计所依赖的架构决策引用 (ADR References)。

---

## ADR-001: SSOT 交付链硬治理设计

**版本**: v1
**状态**: frozen
**路径**: `spec/adr/ADR-001__ssot-delivery-chain-hard-governance.md`

### 关键章节引用

| 章节 | 引用目的 | 技术影响 |
|------|----------|----------|
| [10] ID Grammar Migration | ID 解析器扩展依据 | 需实现 `parse_parent()` 对新 grammar 的支持 |
| [11.7] Transition Authority Matrix | 状态转换权限定义 | CLI 命令必须执行校验而非只改字段 |
| [12.1] P0 Blocking Rules | 校验器规则来源 | SSOTValidator 必须实现全部 23 条 P0 规则 |
| [15.4] Typical L1 Workflow | 工作流编排参考 | 定义 release 级 DAG 节点 |
| [15.9] Slice Data Model | 切片数据模型 | DEVPLAN/TESTPLAN 的 `properties.slices[]` 结构 |
| [8.2.1] Front Matter Templates | 对象模板基线 | schema.json 字段定义的权威来源 |
| [19] 对现有代码的具体改造点 | 实施清单 | 6 个核心模块改造点 |

### 技术约束继承

从 ADR-001 继承的硬约束：

1. **RELEASE 是交付轴唯一根对象** - 不允许其他对象作为交付起点
2. **TASK.parent_id 必须是 DEVPLAN 或 TESTPLAN** - 禁止直接挂在 FEIC 下
3. **DEVPLAN/TESTPLAN.parent_id 必须是 RELEASE** - 确保同属一个版本范围
4. **derived_from_ids 必须是结构化 `{id, version}`** - 不允许裸字符串
5. **RELEASE 必须 pin 住 FEAT 版本** - 不允许引用"最新版本"
6. **recut 必须留下审计记录** - 不允许静默修改 scope

### Schema 改造引用

基于 ADR-001 [19.3] Schema 层改造要求：

```json
{
  "ssot_type": {
    "enum": ["src", "epic", "feat", "release", "ui", "tech",
             "devplan", "testplan", "task", "testset", "tc",
             "bug", "report", "adr", "evi"]
  },
  "derived_from_ids": {
    "type": "array",
    "items": {
      "type": "object",
      "required": ["id", "version"],
      "properties": {
        "id": {"type": "string"},
        "version": {"type": "string"},
        "required": {"type": "boolean"},
        "slice_key": {"type": "string"}
      }
    }
  }
}
```

### 校验规则引用

基于 ADR-001 [12.1] P0 Blocking Rules，必须实现的校验：

| 规则 ID | 规则描述 | 实现位置 |
|---------|----------|----------|
| P0-005 | TASK.parent_id 必须是 DEVPLAN 或 TESTPLAN | `SSOTValidator._validate_delivery_rules()` |
| P0-006 | DEVPLAN/TESTPLAN.parent_id 必须是 RELEASE | `SSOTValidator._validate_parent_required()` |
| P0-007 | DEVPLAN.derived_from_ids 至少包含一个 FEAT | `SSOTValidator._validate_delivery_rules()` |
| P0-008 | TESTPLAN.derived_from_ids 至少包含 FEAT 和 TESTSET | `SSOTValidator._validate_delivery_rules()` |
| P0-009 | RELEASE 必须声明 scope_frozen_at 后才能进入 in_dev | `SSOTValidator._validate_delivery_rules()` |
| P0-010 | RELEASE 中每个 FEAT@version 必须可解析且存在 | `SSOTValidator._validate_reference_existence()` |
| P0-011/012 | RELEASE 内每个 FEAT 必须被 DEVPLAN/TESTPLAN 覆盖 | `SSOTService.release_check()` |
| P0-015 | 存在未关闭 blocker bug 不允许 released | `SSOTService.release_check()` |
| P0-017 | RELEASE recut 必须留下审计记录 | `SSOTValidator._validate_delivery_rules()` |
| P0-018 | recut 后必须重跑 plan coverage 和 release check | `SSOTService.release_check()` |
| P0-019 | derived_from_ids 必须符合 `{id, version}` 结构 | Schema 验证 |
| P0-020 | BUG.waived 必须同时具备 waiver_reason 和 waiver_approved_by | `SSOTValidator._validate_delivery_rules()` |

---

## ADR-003: 产品部门 SSOT 设计

**版本**: v1
**状态**: frozen
**路径**: `spec/adr/ADR-003__product-department-ssot-design.md`

### 引用内容

- 产品部门作为 RELEASE owner 的职责定义
- PM 在 release cut 和 release close 中的权限

---

## ADR-007: QA 部门 SSOT 对齐与工作流重构

**版本**: v1
**状态**: frozen
**路径**: `spec/adr/ADR-007__qa-department-ssot-alignment-and-workflow-reframe.md`

### 引用内容

- QA 切换到 `TASK -> TESTPLAN -> RELEASE` 执行链的依据
- TESTPLAN.owner 固定为 `qa`
- TESTPLAN.environment_matrix 字段的来源

---

## ADR-008: 研发部门 SSOT 对齐与交付治理

**版本**: v1
**状态**: frozen
**路径**: `spec/adr/ADR-008__dev-department-ssot-alignment-and-workflow-reframe.md`

### 引用内容

- 研发执行必须通过 DEVPLAN 承接
- TASK.owner 的命名规范 (backend/frontend/data)
- 开发任务完成定义 (done vs verified)

---

## ADR-017: Gate 治理与决策模式分层

**版本**: v1
**状态**: frozen
**路径**: `spec/adr/ADR-017__gate-zhizeyujuecemoshifencengyurenjishenpipinshenjiaohu.md`

### 引用内容

- release check --enforce 的 gate 语义
- go/no-go gate 的决策模式
- state transition authority matrix 的实现

---

## ADR-022: 交付轴问题 remediation 治理

**版本**: v1
**状态**: frozen
**路径**: `spec/adr/ADR-022__delivery-axis-issue-remediation-governance.md`

### 引用内容

- bugfix 承诺必须重新进入交付轴治理闭环
- 缺陷回流路径和发布关闭标准

---

## SRC-046: 交付轴 workflow 化治理与发布闭环建设

**版本**: v1
**状态**: frozen
**路径**: `spec/source/SRC-046__jiaofuzhou-workflow-huazhiliyufabubihuanjianshe.md`

### 引用内容

- 源问题定义：建立以 RELEASE 为起点的正式交付主链
- 关键约束：ADR-001 三轴治理方向
- 预期交付影响：L1 DAG 和 L2/L3 workflow 落地

---

## 引用关系图

```
SRC-046 (源需求)
    │
    └── governed_by ──> ADR-001 (治理基线)
                            │
         ┌──────────────────┼──────────────────┐
         │                  │                  │
         v                  v                  v
    ADR-003           ADR-007/008        ADR-017/022
   (产品部门)        (QA/研发对齐)       (Gate 治理)
         │                  │                  │
         └──────────────────┼──────────────────┘
                            │
                            v
                   TECH-SRC-046-001
                   (本技术设计)
```

---

## 实施检查清单

基于上述 ADR 引用，实施时需验证：

- [ ] ID grammar 支持 `REL-*` / `DEVPLAN-REL-*` / `TESTPLAN-REL-*` / `TASK-DEVPLAN-REL-*`
- [ ] Schema v1.0 支持所有新对象类型的 properties
- [ ] SSOTValidator 实现全部 23 条 P0 规则
- [ ] SSOTService.release_check() 实现 go/no-go 判定
- [ ] SSOTService.derive_plans() 可从 RELEASE 派生计划骨架
- [ ] CLI 命令 `lee ssot release cut/check/close` 可执行
- [ ] CLI 命令 `lee ssot plan derive/check` 可执行
- [ ] Registry 支持增量 sync 和强制 rebuild
- [ ] Git Hook 在 pre-commit 和 PR CI 中生效

---

## 版本历史

| 版本 | 日期 | 变更说明 |
|------|------|----------|
| v1 | 2026-03-16 | 初始版本，整理 ADR-001 核心引用 |
