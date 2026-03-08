---
id: ADR-001
ssot_type: adr
title: SSOT delivery chain hard governance
status: frozen
version: v1
parent_id:
derived_from_ids: []
source_refs: []
owner: governance
tags: [ssot, governance, delivery]
properties:
  adr_kind: governance_baseline
  frozen_at: 2026-03-08T00:00:00+08:00
---
# SSOT 交付链硬治理设计

## 1. 决策

本方案正式废弃 OpenSpec P1-P7 作为治理主链，不再把阶段进度文档视为真源。

从现在开始，LEE 只保留一套正式 SSOT 主体系：

- 需求轴：定义业务真相
- 交付轴：定义版本承诺与执行编排
- 证据轴：定义执行事实与发布事实

OpenSpec 旧文档、旧 phase progress、旧软治理说明只作为历史材料或证据，不再参与正式判定，不再要求前向兼容。

## 2. 设计目标

- 让 AI 不再直接从 `EPIC/FEAT` 跳到实现，而必须先进入交付计划对象。
- 把 `版本范围`、`开发拆解`、`测试拆解`、`发布判定` 变成正式 SSOT 对象，而不是自由文本。
- 用脚本硬校验替代“阅读规范后自觉遵守”。
- 保持与现有实现路径对齐：`ssot-agent-output schema`、`ArtifactManager.create_ssot()`、`SSOTValidator`、`lee ssot` CLI 是正式扩展点。

## 3. 当前实现锚点

当前仓库已经有可直接扩展的硬路径：

- 对象类型定义：[E:/ai/LEE/src/lee/orchestrator/execution/artifacts/types.py](E:/ai/LEE/src/lee/orchestrator/execution/artifacts/types.py)
- SSOT 落盘目录策略：[E:/ai/LEE/src/lee/orchestrator/execution/artifacts/placement.py](E:/ai/LEE/src/lee/orchestrator/execution/artifacts/placement.py)
- SSOT 对象物化入口：[E:/ai/LEE/src/lee/orchestrator/execution/artifacts/manager.py](E:/ai/LEE/src/lee/orchestrator/execution/artifacts/manager.py)
- Agent 输出契约物化：[E:/ai/LEE/src/lee/orchestrator/execution/artifacts/ssot_contract.py](E:/ai/LEE/src/lee/orchestrator/execution/artifacts/ssot_contract.py)
- SSOT 校验与链路分析：[E:/ai/LEE/src/lee/orchestrator/execution/artifacts/ssot_service.py](E:/ai/LEE/src/lee/orchestrator/execution/artifacts/ssot_service.py)
- CLI 入口：[E:/ai/LEE/src/lee/cli/commands/ssot.py](E:/ai/LEE/src/lee/cli/commands/ssot.py)
- 正式输出契约 schema：[E:/ai/LEE/spec-global/core/contracts/ssot-agent-output/v1/schema.json](E:/ai/LEE/spec-global/core/contracts/ssot-agent-output/v1/schema.json)

这意味着本方案不需要新造第二套系统，只需要扩展现有 SSOT 类型、关系、校验器和命令面。

## 4. 总体模型

### 4.1 三轴模型

```text
需求轴
SRC -> EPIC -> FEAT -> TECH -> TESTSET -> TC

交付轴
RELEASE -> DEVPLAN -> TASK
        -> TESTPLAN -> TASK

证据轴
TASK -> EVI / REPORT / BUG / CODE_REF / PATCH / TEST_RUN / DEPLOY_LOG
RELEASE -> RELEASE_REPORT / DEPLOY_EVI / GO_NO_GO_REPORT
```

### 4.2 三轴职责

- 需求轴回答：为什么做、做什么、验收到什么边界。
- 交付轴回答：这次版本承诺什么、如何拆解、按什么顺序推进。
- 证据轴回答：实际上做了什么、测了什么、是否达到发布条件。

### 4.3 AI 行为约束

- AI 不能直接根据 `FEAT` 自行开工。
- AI 必须先收到某个 `DEVPLAN` 或 `TESTPLAN` 下的 `TASK`。
- AI 产生的所有代码、报告、测试结果、部署结果都只能回写到证据轴。
- `RELEASE` 是唯一合法的发版判定对象。

## 5. 正式对象模型

### 5.1 保留对象

- `SRC`
- `EPIC`
- `FEAT`
- `TECH`
- `TESTSET`
- `TC`
- `TASK`
- `BUG`
- `REPORT`
- `EVI`
- `ADR`

### 5.2 新增对象

- `RELEASE`
- `DEVPLAN`
- `TESTPLAN`

### 5.3 对象职责定义

#### `EPIC`

- 业务目标簇。
- 管理一组 `FEAT`。
- 不直接挂开发执行任务。

#### `FEAT`

- 最小独立可验收业务单元。
- 是需求真源。
- 必须能独立绑定 `TECH` 与 `TESTSET`。

#### `TECH`

- 某个 `FEAT` 的实现设计。
- 不承担版本范围职责。

#### `TESTSET`

- 某个 `FEAT` 的测试真源。
- 定义覆盖目标、验收范围、测试切片。

#### `RELEASE`

- 某次版本切面与发布基线。
- 定义本次版本纳入哪些 `FEAT@version`。
- 是交付轴根对象。
- 是最终发布 gate 的唯一判断对象。

#### `DEVPLAN`

- 某个 `RELEASE` 下的研发实施计划。
- 负责把多个 `FEAT/TECH` 拆成可执行 `TASK`。
- 必须明确顺序、owner、依赖、完成定义。

#### `TESTPLAN`

- 某个 `RELEASE` 下的验证计划。
- 负责把多个 `FEAT/TESTSET` 拆成验证任务与验证轮次。
- 必须明确环境、入口、阻断条件、放行条件。

#### `TASK`

- 原子执行单元。
- 只能隶属于 `DEVPLAN` 或 `TESTPLAN`。
- 不能直接挂在 `EPIC` 或 `FEAT` 下。
- 通过关系字段引用它实现或验证的目标对象。

#### `REPORT`

- 结构化结果对象。
- 允许类型细分为：开发报告、测试报告、发布报告、回归报告、go/no-go 报告。
- 不能替代 `PLAN` 或 `RELEASE`。

#### `EVI`

- 证据对象。
- 保存日志、截图、命令输出、测试产物、部署产物、diff、运行轨迹等。

#### `BUG`

- 执行反馈对象。
- 影响 `TESTPLAN` 与 `RELEASE` 的判定。
- 只有在确认需求错误时才回推修改 `FEAT`。

## 6. 关系模型

### 6.1 主关系

- `EPIC -> FEAT`：`parent`
- `FEAT -> TECH`：`parent`
- `FEAT -> TESTSET`：`parent`
- `TESTSET -> TC`：`parent`
- `RELEASE -> DEVPLAN`：`parent`
- `RELEASE -> TESTPLAN`：`parent`
- `DEVPLAN -> TASK`：`parent`
- `TESTPLAN -> TASK`：`parent`

### 6.2 交叉关系

- `DEVPLAN.derived_from = [FEAT, TECH, ADR?]`
- `TESTPLAN.derived_from = [FEAT, TESTSET, ADR?]`
- `TASK.implements = [FEAT, TECH]`
- `TASK.verifies = [FEAT, TESTSET, TC]`
- `REPORT.derived_from = [TASK, DEVPLAN, TESTPLAN, RELEASE]`
- `EVI.derived_from = [TASK, REPORT, BUG, RELEASE]`
- `BUG.derived_from = [TESTPLAN, REPORT, TASK]`
- `RELEASE.derived_from_ids = [{id, version}]`

### 6.3 关键约束

- `TASK.parent` 必须是 `DEVPLAN` 或 `TESTPLAN`。
- 一个 `TASK` 不能同时属于两个 plan。
- `RELEASE` 必须显式 pin 住 `FEAT` 版本，而不是引用“最新 FEAT”。
- `DEVPLAN` 和 `TESTPLAN` 必须同属一个 `RELEASE`。
- `RELEASE` 不允许直接引用 `TASK` 作为 scope truth，`TASK` 只能作为执行事实。
- `REPORT` 不允许充当需求或计划真源。

## 7. 版本与冻结

### 7.1 双版本原则

必须显式区分：

- 需求版本：`FEAT.version`
- 发布版本：`RELEASE.version`

版本引用结构统一定义为：

```yaml
derived_from_ids:
  - id: FEAT-023
    version: v5
  - id: FEAT-024
    version: v2
```

约束：

- 不再使用裸字符串 `FEAT-023@v5` 作为正式 machine-readable 字段
- `FEAT-023@v5` 只允许作为文档中的人类可读简写
- 脚本、校验器、CLI 一律读取 `derived_from_ids: [{id, version}]`
- 建议扩展为：

```yaml
derived_from_ids:
  - id: FEAT-023
    version: v5
    required: true
    slice_key: feat-023-core
```

字段语义：

- `id`
  - 上游正式对象 ID
- `version`
  - 被 pin 的冻结版本
- `required`
  - 是否为 release 必需范围
- `slice_key`
  - 若该引用仅作用于某个 feature slice，可显式绑定 slice

示例：

- `FEAT-023@v5` 是需求的第 5 次冻结
- `REL-1.4.0` 引用的是 `FEAT-023@v5`
- 后续 `FEAT-023@v6` 形成新版本，不会污染 `REL-1.4.0`

### 7.2 冻结规则

- `EPIC/FEAT/TECH/TESTSET` 冻结后才允许进入 `RELEASE`
- `RELEASE` 冻结 scope 后，新增需求只能进入新 release 或重新 cut release
- `DEVPLAN/TESTPLAN` 进入 `committed` 后不能自由增删 scope，只能追加经过审计的变更记录
- `REPORT/EVI` 不冻结 scope，只冻结事实快照

### 7.3 冻结 FEAT 的变更规则

核心原则：

- 不允许重新打开已冻结 `FEAT` 并原地修改旧版本
- 旧版本一旦被冻结并被 `RELEASE` 引用，就永远保持不可变
- 所有需求变更必须通过 `同一 FEAT 的新版本` 或 `新 FEAT` 进入系统

判定矩阵：

- 表述澄清、说明补充、非验收边界变更：
  - 使用同一个 `FEAT` 生成新版本
  - 例如 `FEAT-023@v6 supersedes FEAT-023@v5`
- 业务规则、验收标准、范围发生变化，但仍属于同一个独立业务单元：
  - 仍使用同一个 `FEAT` 生成新版本
  - 下游 `TECH/TESTSET/DEVPLAN/TESTPLAN` 必须按受影响范围重派生
- 变更已经形成新的独立验收边界、可独立排期、可独立发布或可独立回滚：
  - 必须新建 `FEAT`
  - 不得继续挤入原 `FEAT` 的版本链
- 实现缺陷、测试发现、代码偏差：
  - 默认走 `BUG`
  - 只有确认是需求真源错误，才允许升级为 `FEAT` 新版本或新 `FEAT`

### 7.4 RELEASE 引用 FEAT 版本的规则

- `RELEASE` 必须 pin 到明确的 `derived_from_ids: [{id, version}]`
- 已被某个 `RELEASE` 引用的 `FEAT@version` 不会自动升级到更新版本
- `FEAT` 产生新版本后，默认进入新的 `RELEASE`
- 只有显式批准 `recut release scope`，才允许当前 `RELEASE` 从 `FEAT@vN` 切换到 `FEAT@vN+1`

### 7.5 RELEASE recut 规则

如果一个已进入交付中的 `RELEASE` 要改用新的 `FEAT` 版本，必须执行 `release recut`，且满足以下条件：

- 变更原因被记录到 `RELEASE` 的变更日志
- 被替换的 `FEAT@version` 与新版本关系明确可追溯
- 受影响的 `DEVPLAN` 必须重新校验 coverage
- 受影响的 `TESTPLAN` 必须重新校验 coverage
- 已完成的相关 `TASK` 必须重新判断是否失效、部分失效或可复用
- `release check` 必须重新执行

不允许的情况：

- 直接修改 `RELEASE` front matter 中的 `FEAT` 引用但不留下审计记录
- 不重跑 plan coverage 和 release gate
- 通过口头约定默认“当前版本顺带吃进去”

## 8. 文件真源与 Registry 投影

### 8.1 文件真源

正式 SSOT 主文件必须是 Git 中可审阅、可 diff、可回滚的 checked-in 文件。

`.artifacts/.registry.json` 仍然保留，但它的角色变成：

- 运行时索引
- 关系缓存
- CLI 查询加速层
- 由正式文件投影生成

正式真源不是 `.artifacts`，而是 `spec/`、`tests/`、`docs/reports/` 下的正式对象文件。

### 8.2 文件格式

正式 SSOT 文件统一使用 `Markdown + YAML front matter`：

```md
---
id: REL-1.4.0
ssot_type: release
title: 2026-03 MVP release
status: planned
version: v1
parent_id:
derived_from_ids:
  - id: FEAT-023
    version: v5
  - id: FEAT-024
    version: v2
source_refs:
  - FEAT-023#acceptance
owner: delivery
tags: [mvp, march]
properties:
  branch: release/1.4.0
  target_env: staging
---

# Summary
...
```

脚本只以 front matter 的结构字段做治理判定，正文只承载人类可读说明。

### 8.2.1 Front Matter Minimal Templates

以下模板定义正式对象的最小结构字段，schema 与 validator 必须以此为基线。

#### `RELEASE`

```yaml
---
id: REL-1.4.0
ssot_type: release
title: March MVP release
status: planned
version: v1
parent_id:
derived_from_ids:
  - id: FEAT-023
    version: v5
    required: true
    slice_key: feat-023-core
source_refs: []
owner: delivery
tags: []
properties:
  scope_frozen_at:
  target_env: staging
  rollback_plan:
  recuts: []
---
```

#### `DEVPLAN`

```yaml
---
id: DEVPLAN-REL-1.4.0
ssot_type: devplan
title: Dev plan for REL-1.4.0
status: draft
version: v1
parent_id: REL-1.4.0
derived_from_ids:
  - id: FEAT-023
    version: v5
source_refs: []
owner: delivery
tags: []
properties:
  coverage_summary:
  slices: []
---
```

#### `TESTPLAN`

```yaml
---
id: TESTPLAN-REL-1.4.0
ssot_type: testplan
title: Test plan for REL-1.4.0
status: draft
version: v1
parent_id: REL-1.4.0
derived_from_ids:
  - id: FEAT-023
    version: v5
source_refs: []
owner: qa
tags: []
properties:
  environment_matrix: []
  coverage_summary:
  slices: []
---
```

#### `TASK`

```yaml
---
id: TASK-DEVPLAN-REL-1.4.0-001
ssot_type: task
title: Implement FEAT-023 core
status: todo
version: v1
parent_id: DEVPLAN-REL-1.4.0
derived_from_ids:
  - id: FEAT-023
    version: v5
source_refs: []
owner: backend
tags: []
properties:
  slice_key: feat-023-core
  acceptance: []
  estimate:
---
```

#### `BUG`

```yaml
---
id: BUG-FEAT-023-001
ssot_type: bug
title: Duplicate email check fails
status: active
version: v1
parent_id: FEAT-023
derived_from_ids: []
source_refs: []
owner: qa
tags: []
properties:
  bug_state: open
  severity: blocker
  found_in_release: REL-1.4.0
  source_report_id: REPORT-REL-1.4.0-FEAT-023-TEST-001
  waiver_reason:
  waiver_approved_by:
---
```

#### `REPORT`

```yaml
---
id: REPORT-REL-1.4.0-TEST-001
ssot_type: report
title: Test report for REL-1.4.0
status: active
version: v1
parent_id: REL-1.4.0
derived_from_ids: []
source_refs: []
owner: qa
tags: []
properties:
  report_kind: test_execution
  subject_id: REL-1.4.0
  result: pass
  summary:
  evidence_refs: []
  slice_key:
---
```

### 8.3 文件命名

继续沿用当前 `create_ssot()` 已经采用的命名规则：

```text
[ID]__[slug].md
```

### 8.4 Registry Rebuild Protocol

正式规则：

- front matter 文件是唯一真源
- `.artifacts/.registry.json` 是可丢弃缓存，不拥有 truth ownership
- registry 与磁盘内容冲突时，永远以磁盘 front matter 为准

必须支持的运行模式：

- `cold rebuild`
  - 全量扫描正式 SSOT 目录
  - 重新生成 registry 与关系索引
- `incremental refresh`
  - 只刷新变更文件
  - 通过文件时间戳或内容 hash 检测脏对象

建议命令：

- `lee ssot rebuild-registry`
  - 全量从磁盘重建
- `lee ssot sync`
  - 增量同步变更文件

执行协议：

1. CLI 在执行 `validate / impact / show-chain / release check` 前，必须先确认 registry 未过期
2. 若检测到磁盘 front matter 比 registry 新，则先执行增量 refresh
3. 若 registry 缺失、损坏或 schema 版本不匹配，则强制执行 cold rebuild

禁止行为：

- 只改 registry 不改正式文件
- 允许 registry 覆盖磁盘 front matter
- 在 registry 过期时继续执行发布判定

## 9. 目录布局

基于当前 [placement.py](E:/ai/LEE/src/lee/orchestrator/execution/artifacts/placement.py) 的放置策略，建议升级为：

```text
spec/
  source/
  requirements/
    epics/
    features/
  tech/
  delivery/
    releases/
    devplans/
    testplans/
  tasks/
  adr/
tests/
  cases/
  bugs/
docs/
  reports/
    testing/
    delivery/
    release/
    evidence/
```

映射规则：

- `SRC -> spec/source`
- `EPIC -> spec/requirements/epics`
- `FEAT -> spec/requirements/features`
- `TECH -> spec/tech`
- `RELEASE -> spec/delivery/releases`
- `DEVPLAN -> spec/delivery/devplans`
- `TESTPLAN -> spec/delivery/testplans`
- `TASK -> spec/tasks`
- `TC -> tests/cases`
- `BUG -> tests/bugs`
- `REPORT -> docs/reports/{testing|delivery|release}`
- `EVI -> docs/reports/evidence`

## 10. ID 规则

建议新 ID 体系如下：

- `SRC-001`
- `EPIC-001`
- `FEAT-001`
- `TECH-FEAT-001`
- `TESTSET-FEAT-001`
- `TC-TESTSET-FEAT-001-001`
- `REL-1.4.0`
- `DEVPLAN-REL-1.4.0`
- `TESTPLAN-REL-1.4.0`
- `TASK-DEVPLAN-REL-1.4.0-001`
- `TASK-TESTPLAN-REL-1.4.0-001`
- `BUG-FEAT-001-001`
- `REPORT-REL-1.4.0-TEST-001`
- `EVI-TASK-DEVPLAN-REL-1.4.0-001-001`

规则重点：

- `RELEASE` 是独立根对象。
- `DEVPLAN/TESTPLAN` 的 ID 中体现 release scope。
- `TASK` 的 ID 中体现 plan scope。
- `BUG/EVI/REPORT` 允许带范围前缀，保证可定位。

### 10.1 ID Grammar Migration

这一步必须是实施前置，而不是跟普通 schema 扩展并列处理。

正式约束：

- 新增 `RELEASE / DEVPLAN / TESTPLAN` 之前，必须先更新 `id_parser / id_generator / validate_parent_consistency`
- 在新 grammar 生效前，不允许把新对象写入正式主链

建议 grammar：

- `REL-<semver>`
- `DEVPLAN-REL-<semver>`
- `TESTPLAN-REL-<semver>`
- `TASK-DEVPLAN-REL-<semver>-<slice-or-seq>`
- `TASK-TESTPLAN-REL-<semver>-<slice-or-seq>`
- `REPORT-REL-<semver>-<kind>-<seq>`

解析规则：

- `RELEASE`
  - 独立根对象，无 `parent_id`
- `DEVPLAN / TESTPLAN`
  - `parent_id` 必须是 `RELEASE`
- `TASK`
  - `parent_id` 必须是 `DEVPLAN` 或 `TESTPLAN`
  - `parse_parent(id)` 必须能恢复到 plan scope
- `REPORT`
  - 可通过 `properties.report_kind` 细分，但 ID 至少要能恢复 release scope

校验器必须基于 grammar，而不是仅基于字符串前缀猜测。

## 10.2 Query Semantics

在版本化和 slice 化之后，查询命令必须采用以下固定语义：

### `impact`

- `lee ssot impact FEAT-023`
  - 默认查看该对象所有版本的总体影响
- `lee ssot impact FEAT-023 --version v5`
  - 只查看 `FEAT-023@v5` 的影响范围
- `lee ssot impact REL-1.4.0 --slice feat-023-core`
  - 只查看该 release 下指定 slice 的影响范围

### `show-chain`

- `lee ssot show-chain REL-1.4.0`
  - 必须展开到 `derived_from_ids[{id, version}]`
- `lee ssot show-chain TASK-DEVPLAN-REL-1.4.0-001`
  - 必须能展示：
    - parent plan
    - parent release
    - bound slice
    - implements/verifies 的上游对象

### `build-index`

- index 必须同时包含：
  - 正式对象节点
  - 父子边
  - `derived_from_ids[{id, version}]` 边
  - `implements/verifies` 边
- `slice` 默认不单独作为正式对象节点
- `slice` 作为 node property 或 edge property 参与索引

### 默认规则

- 不带 `--version` 时，CLI 必须明确说明是“全部版本视图”还是“最新冻结版本视图”
- 对 release 相关查询，默认以 `RELEASE` 里 pin 住的版本为准，不自动推断最新版本

## 11. 状态机

### 11.1 需求轴状态

- `draft`
- `reviewed`
- `frozen`
- `superseded`
- `deprecated`

#### 需求轴状态转换

允许的主路径：

- `draft -> reviewed`
- `reviewed -> frozen`
- `frozen -> superseded`
- `draft -> deprecated`
- `reviewed -> deprecated`

禁止的路径：

- `frozen -> draft`
- `frozen -> reviewed`
- `superseded -> frozen`
- `deprecated -> draft`

冻结门槛：

- `EPIC` 冻结前必须至少有明确范围、目标、非目标
- `FEAT` 冻结前必须具备明确 acceptance、business rules、scope、source refs
- `TECH` 冻结前必须具备实现边界、接口、依赖、风险
- `TESTSET` 冻结前必须具备验证范围、测试切片、关键用例入口

冻结动作：

- 写入 `frozen_at`
- 固化 `version`
- 固化 `source_refs`
- 将当前对象设为只读对象

冻结后的变更处理：

- 不允许回退到可编辑状态
- 只能通过 `新版本 supersedes 旧版本` 或 `新对象替代旧对象`

状态转换权限矩阵见 `11.6`。

### 11.2 交付轴状态

#### `RELEASE`

- `draft`
- `planned`
- `scope_frozen`
- `in_dev`
- `in_test`
- `go_no_go`
- `released`
- `aborted`

`RELEASE` 转换规则：

- `draft -> planned`
  - 条件：release 范围初步选定，至少包含一个已冻结 `FEAT@version`
- `planned -> scope_frozen`
  - 条件：scope pin 完成，受纳入对象均已冻结，变更窗口关闭
- `scope_frozen -> in_dev`
  - 条件：`DEVPLAN` 已生成并通过 coverage 校验
- `in_dev -> in_test`
  - 条件：开发侧 blocker task 已完成，提测报告已存在
- `in_test -> go_no_go`
  - 条件：`TESTPLAN` 主体完成，blocker bug 清零或被显式豁免
- `go_no_go -> released`
  - 条件：`release check --enforce` 通过，发布报告与部署证据齐备
- `draft|planned|scope_frozen|in_dev|in_test|go_no_go -> aborted`
  - 条件：版本取消、策略变化、scope 作废

限制：

- `released` 不可回退
- `scope_frozen` 之后修改 scope 必须走 `release recut`
- `release recut` 不改变旧对象历史，只生成新的审计记录和新的 scope 版本

状态转换权限矩阵见 `11.6`。

#### `DEVPLAN / TESTPLAN`

- `draft`
- `committed`
- `in_progress`
- `blocked`
- `completed`
- `cancelled`

`DEVPLAN / TESTPLAN` 转换规则：

- `draft -> committed`
  - 条件：任务分解完成、覆盖范围通过校验、owner 和依赖完整
- `committed -> in_progress`
  - 条件：至少一个子 `TASK` 进入 `doing`
- `in_progress -> blocked`
  - 条件：存在 blocker 依赖或上游 scope 变化
- `blocked -> in_progress`
  - 条件：阻断消除且重校验通过
- `in_progress -> completed`
  - 条件：所有必需 `TASK` 达到 `done/verified`
- `draft|committed|in_progress|blocked -> cancelled`
  - 条件：release 取消或计划被新版本替代

冻结门槛：

- `DEVPLAN/TESTPLAN` 不使用 `frozen` 状态，而使用 `committed` 表达“交付承诺已锁定”
- `committed` 后 scope 不允许静默变化
- scope 变化必须生成 change log 或 recut 记录

状态转换权限矩阵见 `11.6`。

#### `TASK`

- `todo`
- `doing`
- `blocked`
- `done`
- `verified`
- `dropped`

`TASK` 转换规则：

- `todo -> doing`
- `doing -> blocked`
- `blocked -> doing`
- `doing -> done`
- `done -> verified`
- `todo|doing|blocked -> dropped`

完成门槛：

- Dev task `done` 需要代码、变更说明、最小证据
- Test task `done` 需要测试执行记录
- `verified` 需要上游 plan 或 reviewer 的验收通过

回退约束：

- `verified` 不直接回到 `doing`
- 若 scope 变化导致任务失效，应新建任务或标记旧任务为 `dropped/replaced`

状态转换权限矩阵见 `11.6`。

### 11.3 证据轴状态

#### `REPORT / EVI / BUG`

- `draft`
- `active`
- `frozen`
- `archived`

`REPORT / EVI` 转换规则：

- `draft -> active`
- `active -> frozen`
- `frozen -> archived`

冻结门槛：

- `REPORT` 必须有明确结论、关联对象、关键证据引用
- `EVI` 必须可定位到真实产物、日志或附件

`BUG` 采用双字段：

- `status`
  - 使用统一对象状态：`draft/active/frozen/archived`
- `bug_state`
  - 使用缺陷生命周期状态：`open/triaged/in_fix/in_verify/closed/waived`

其中：

- `status` 解决对象治理问题：是否进入正式主链、是否冻结、是否归档
- `bug_state` 解决缺陷处理问题：是否修复、是否验证、是否豁免

`BUG` 转换规则建议单列为业务状态：

- `open`
- `triaged`
- `in_fix`
- `in_verify`
- `closed`
- `waived`

其中：

- blocker bug 未 `closed/waived` 时，阻断 `RELEASE -> released`
- `BUG.status` 即使为 `active/frozen`，也不能替代 `bug_state`

### 11.4 BUG Formal Fields

为了让 `release check` 可执行，`BUG` 至少需要以下结构字段：

```yaml
properties:
  bug_state: open
  severity: blocker
  found_in_release: REL-1.4.0
  source_report_id: REPORT-REL-1.4.0-FEAT-023-TEST-001
  waiver_reason:
  waiver_approved_by:
```

字段约束：

- `severity`
  - 枚举：`blocker / critical / major / minor / trivial`
- `found_in_release`
  - 必须指向某个 `RELEASE`
- `source_report_id`
  - 必须指向触发该 bug 的 `REPORT`
- `waiver_reason`
  - 当 `bug_state == waived` 时必填
- `waiver_approved_by`
  - 当 `bug_state == waived` 时必填

release gate 判定：

- `severity == blocker` 且 `bug_state not in [closed, waived]`
  - 直接阻断发布
- `bug_state == waived`
  - 必须同时存在 `waiver_reason` 和 `waiver_approved_by`

### 11.5 REPORT Formal Fields

为了让 gate 与审计稳定执行，`REPORT` 至少需要以下结构字段：

```yaml
properties:
  report_kind: test_execution
  subject_id: REL-1.4.0
  result: pass
  summary:
  evidence_refs:
    - EVI-TASK-DEVPLAN-REL-1.4.0-001-001
  slice_key:
```

字段约束：

- `report_kind`
  - 枚举：`dev_progress / test_execution / regression / release / go_no_go / recut_audit`
- `subject_id`
  - 该 report 的直接主题对象
- `result`
  - 枚举：`pass / fail / warning / info / approved / rejected`
- `summary`
  - 单段结论摘要，不能为空
- `evidence_refs`
  - 指向 `EVI` 或普通 artifact
- `slice_key`
  - 如果该 report 只属于某个 feature slice，则必填

release gate 的 hard requirement：

- 至少一个 `report_kind=release`
- 至少一个 `report_kind=test_execution`
- 至少一个 `report_kind=go_no_go`

### 11.6 派生视图状态

下列状态不手工填写，只能由脚本派生：

- `FEAT.delivery_status`
- `FEAT.test_status`
- `FEAT.release_status`
- `RELEASE.progress_summary`

### 11.7 Transition Authority Matrix

状态机必须同时定义“谁能改状态、通过什么命令改、需要什么证据”。

| 对象 | 转换 | Actor | Command | Required Evidence | Denied If |
|---|---|---|---|---|---|
| `FEAT` | `reviewed -> frozen` | requirement reviewer / governance script | `lee ssot freeze <FEAT_ID>` | acceptance、rules、scope、source refs 完整 | 存在缺失字段 |
| `TECH` | `reviewed -> frozen` | tech reviewer | `lee ssot freeze <TECH_ID>` | design sections 完整 | 依赖对象未冻结 |
| `TESTSET` | `reviewed -> frozen` | qa reviewer | `lee ssot freeze <TESTSET_ID>` | coverage、cases、entry 完整 | FEAT 未冻结 |
| `RELEASE` | `planned -> scope_frozen` | release manager / release cut script | `lee ssot release cut` | `derived_from_ids` 完整且可解析 | scope 中存在未冻结对象 |
| `DEVPLAN` | `draft -> committed` | delivery planner | `lee ssot plan check --commit` | coverage、owner、deps 完整 | scope 未覆盖 |
| `TESTPLAN` | `draft -> committed` | qa planner | `lee ssot plan check --commit` | coverage、environment、entry 完整 | scope 未覆盖 |
| `TASK` | `doing -> done` | task executor | `lee ssot task close` | 最小证据、结果摘要 | 缺少 output/evidence |
| `TASK` | `done -> verified` | reviewer / plan gate | `lee ssot task verify` | review result 或 plan gate 通过 | 关联 plan 未通过 |
| `REPORT` | `active -> frozen` | reporter / gate script | `lee ssot freeze <REPORT_ID>` | 结论 + evidence refs | evidence 不存在 |
| `RELEASE` | `go_no_go -> released` | release gate | `lee ssot release close` | `release check --enforce` 通过 | blocker bug 未关闭 |

规则：

- 未在矩阵中的状态转换默认不允许
- 每个状态转换都必须有明确命令入口
- 命令必须在执行时重跑对应校验，而不是只改字段

### 11.8 冻结与提交的统一定义

为了避免“状态名很多但语义混乱”，本体系统一采用两个关键门槛：

- `frozen`
  - 适用于需求真源与事实快照
  - 含义：该版本内容不可再编辑，只能被替代
- `committed`
  - 适用于交付计划
  - 含义：该版本计划已成为执行承诺，不能静默改 scope

对应关系：

- `EPIC/FEAT/TECH/TESTSET` 走到 `frozen`，表示真源冻结
- `RELEASE` 走到 `scope_frozen`，表示版本范围冻结
- `DEVPLAN/TESTPLAN` 走到 `committed`，表示交付承诺冻结
- `REPORT/EVI` 走到 `frozen`，表示事实快照冻结

## 12. 硬治理规则

### 12.1 P0 Blocking 规则

以下规则失败必须直接阻断：

1. 所有正式对象文件必须存在且 front matter 可解析。
2. `id`、`ssot_type`、`title`、`status`、`version` 必填。
3. `ssot_type` 必须属于正式枚举。
4. `parent_id` 必须满足对象类型规则。
5. `TASK.parent_id` 必须是 `DEVPLAN` 或 `TESTPLAN`。
6. `DEVPLAN.parent_id` 与 `TESTPLAN.parent_id` 必须是 `RELEASE`。
7. `DEVPLAN.derived_from_ids` 至少包含一个 `FEAT`。
8. `TESTPLAN.derived_from_ids` 至少包含一个 `FEAT` 和一个 `TESTSET`。
9. `RELEASE` 必须声明 `scope_frozen_at` 后才能进入 `in_dev`。
10. `RELEASE` 中每个 `FEAT@version` 必须可解析且真实存在。
11. `RELEASE` 内每个 `FEAT` 必须至少被一个 `DEVPLAN` 覆盖。
12. `RELEASE` 内每个 `FEAT` 必须至少被一个 `TESTPLAN` 覆盖。
13. `REPORT/EVI/BUG` 必须能追溯到 `TASK`、`PLAN` 或 `RELEASE`。
14. `released` 状态的 `RELEASE` 必须具备发布报告、测试报告和部署证据。
15. 存在未关闭 blocker bug 的 `RELEASE` 不允许进入 `released`。
16. 已冻结 `FEAT` 不允许原地修改，只允许新增版本或新增 `FEAT`。
17. `RELEASE` 如果切换到新的 `FEAT` 版本，必须留下 recut 审计记录。
18. `RELEASE recut` 后，受影响的 `DEVPLAN/TESTPLAN/release check` 必须重新通过。
19. `derived_from_ids` 必须符合 `{id, version}` 结构，且 `id/version` 都必须存在。
20. `BUG.waived` 必须同时具备 `waiver_reason` 和 `waiver_approved_by`。
21. registry 过期或与磁盘 front matter 不一致时，不允许执行 release 判定。
22. `REPORT` 必须包含合法的 `report_kind / subject_id / result / evidence_refs`。
23. `RELEASE` 必须存在 `report_kind=release / test_execution / go_no_go` 三类报告。

### 12.2 P1 Warning 规则

以下规则告警但不立即阻断：

1. `FEAT` 已冻结但 14 天内未被纳入任何 `RELEASE`
2. `TASK` 缺少 owner、estimate、acceptance
3. `TESTPLAN` 缺少 environment matrix
4. `RELEASE` 缺少 rollback plan
5. `REPORT` 缺少关联证据

### 12.3 P2 Hygiene 规则

- slug 规范
- tags 规范
- section 完整性
- owner 命名统一
- 枚举字段大小写统一

## 13. CLI 与脚本设计

本方案不另起新工具，直接扩展 `lee ssot`。

### 13.1 保留并升级现有命令

- `lee ssot build-index`
- `lee ssot validate`
- `lee ssot impact`
- `lee ssot show-chain`

升级方向：

- `validate` 支持完整三轴规则，而不再停留在旧的 `prd/api/implementation/test_plan` v1 规则
- `build-index` 输出对象类型、父子关系、release scope、状态摘要

### 13.2 新增命令

#### `lee ssot lint`

- 扫描正式 SSOT 文件
- 校验 front matter、ID、目录、命名、必填字段

#### `lee ssot plan derive`

- 从 `RELEASE + FEAT + TECH + TESTSET` 自动生成 `DEVPLAN`、`TESTPLAN` 草案
- 只生成骨架，不直接生成实现代码

#### `lee ssot plan check <PLAN_ID>`

- 校验计划是否覆盖 release scope
- 校验任务是否完备

#### `lee ssot task check <TASK_ID>`

- 校验任务是否具备合法 parent、合法关系、合法完成定义

#### `lee ssot release check <REL_ID>`

- 聚合 release 下所有对象与证据
- 输出 go/no-go 检查结果

#### `lee ssot release cut`

- 创建 release scope
- pin `FEAT@version`
- 初始化关联 plan 骨架

#### `lee ssot release close <REL_ID>`

- 只有在 `release check` 通过时才能关闭为 `released`

#### `lee ssot render-view`

- 生成面向人类的派生视图：
  - release dashboard
  - feat delivery matrix
  - test coverage summary

## 14. CI / Git Hook 硬治理

### 14.1 pre-commit

针对变更文件执行：

- `lee ssot lint --changed-only`
- `lee ssot validate --changed-only`

### 14.2 PR CI

执行：

- 全量 schema 校验
- 受影响对象校验
- release impact 分析
- 若修改 `FEAT/TECH/TESTSET`，自动检查受影响的 `RELEASE`

### 14.3 release gate CI

发布分支或发布标签时执行：

- `lee ssot release check <REL_ID> --enforce`
- 测试报告与部署证据存在性检查
- blocker bug 检查
- release scope 与实际变更比对

CI 失败必须是硬失败，不允许“建议修复后继续”。

## 15. 运行流程

### 15.1 需求进入交付

1. `EPIC/FEAT` 冻结
2. `TECH/TESTSET` 冻结
3. 创建 `RELEASE`
4. release pin 住若干 `FEAT@version`
5. 生成 `DEVPLAN` 与 `TESTPLAN`
6. 从 plan 生成 `TASK`

### 15.2 AI 执行

1. AI 领取 `TASK`
2. AI 读取上游 `FEAT/TECH/TESTSET`
3. AI 执行并产出代码、测试、报告、证据
4. 结果回写到 `REPORT/EVI/BUG`
5. 脚本更新派生状态

### 15.3 发布

1. `TESTPLAN` 完成
2. blocker bug 清零或显式豁免
3. `release check` 聚合校验
4. 生成 `RELEASE_REPORT`
5. `RELEASE` 进入 `released`

### 15.4 典型 L1 工作流

结论：这套 `RELEASE` 研发管理工作流适合建成一个 L1 DAG，而不是线性流水线。

原因：

- `DEVPLAN` 和 `TESTPLAN` 都依赖 release scope，但二者可以并行准备
- 同一 release 下多个 feature 的开发任务天然是并行图
- 测试准备可以早于全部开发完成，只需要等待对应提测切片
- bug 修复与回归验证本身就是带回边的受控 DAG，不适合纯串行

推荐把 L1 定位为：

- 只编排正式 SSOT 对象与阶段 gate
- 不直接做具体编码、测试、部署
- 把具体执行委派给 L2/L3 agent 或任务执行器

### 15.5 典型 L1 DAG 示例

场景：

- `REL-1.4.0`
- 纳入 `FEAT-023@v5` 用户注册
- 纳入 `FEAT-024@v2` 邮箱验证
- 纳入 `FEAT-031@v3` 邀请码注册

L1 DAG 示意：

```text
[release_scope_init]
    -> [release_scope_validate]
    -> [release_scope_freeze]

[release_scope_freeze]
    -> [derive_devplan]
[release_scope_freeze]
    -> [derive_testplan]

[derive_devplan]
    -> [dev_task_pack_feat_023]
[derive_devplan]
    -> [dev_task_pack_feat_024]
[derive_devplan]
    -> [dev_task_pack_feat_031]

[derive_testplan]
    -> [test_ready_feat_023]
[derive_testplan]
    -> [test_ready_feat_024]
[derive_testplan]
    -> [test_ready_feat_031]

[dev_task_pack_feat_023]
    -> [dev_acceptance_gate]
[dev_task_pack_feat_024]
    -> [dev_acceptance_gate]
[dev_task_pack_feat_031]
    -> [dev_acceptance_gate]

[dev_acceptance_gate]
    -> [test_execution]

[test_ready_feat_023]
    -> [test_execution]
[test_ready_feat_024]
    -> [test_execution]
[test_ready_feat_031]
    -> [test_execution]

[test_execution]
    -> [bug_triage]
[bug_triage]
    -> [bugfix_replan]
[bugfix_replan]
    -> [targeted_regression]
[targeted_regression]
    -> [release_check]

[test_execution]
    -> [release_check]

[release_check]
    -> [go_no_go_gate]
[go_no_go_gate]
    -> [deploy_and_capture_evidence]
[deploy_and_capture_evidence]
    -> [release_close]
```

### 15.6 L1 DAG 节点职责

- `release_scope_init`
  - 创建 `RELEASE`
  - 绑定候选 `FEAT@version`
- `release_scope_validate`
  - 校验 scope 中对象是否全为 frozen
- `release_scope_freeze`
  - 将 `RELEASE` 置为 `scope_frozen`
- `derive_devplan`
  - 生成 `DEVPLAN`
  - 生成开发 `TASK`
- `derive_testplan`
  - 生成 `TESTPLAN`
  - 生成测试 `TASK`
- `dev_task_pack_feat_*`
  - 执行 feature implementation slice
  - 产出代码证据、开发报告
- `test_ready_feat_*`
  - 预置环境、数据、用例、入口
- `dev_acceptance_gate`
  - 聚合开发切片是否达到提测条件
- `test_execution`
  - 执行正式验证
  - 产出测试报告、缺陷、证据
- `bug_triage`
  - 对 blocker/non-blocker 缺陷分类
- `bugfix_replan`
  - 对 blocker bug 派生修复任务
- `targeted_regression`
  - 对修复范围执行回归
- `release_check`
  - 聚合 plan/task/report/evi/bug
  - 判断是否满足 go/no-go 前提
- `go_no_go_gate`
  - 正式做发布决定
- `deploy_and_capture_evidence`
  - 部署并保存部署证据
- `release_close`
  - 写入 release report
  - 将 `RELEASE` 置为 `released`

### 15.7 L1 DAG 的硬约束

- `release_scope_freeze` 之前不允许生成正式 `DEVPLAN/TESTPLAN`
- `derive_testplan` 可以和 `derive_devplan` 并行
- 系统必须支持 `feature slice` 粒度提测，而不是只能等整个 release 开发完成
- `test_execution` 必须同时依赖：
  - 对应 feature slice 的开发切片完成
  - 对应 feature slice 的测试准备完成
- `release_check` 不能只看测试是否通过，必须同时看：
  - release scope 是否仍一致
  - blocker bug 是否关闭
  - 核心 report/evi 是否齐备
- `release_close` 前必须再次执行 `release check --enforce`

### 15.8 Feature Slice 提测规则

为了避免 DAG 在执行时退化成串行流水线，正式规定：

- `RELEASE` 是汇总与发布单位
- `feature slice` 是开发提测与验证的最小并行单位
- 每个纳入 release 的 `FEAT@version` 至少对应一个开发 slice 和一个测试 slice

允许的路径：

- `FEAT-023 slice` 开发完成后，可以先进入该 slice 的测试执行
- 不必等待 `FEAT-024/031` 全部开发完成

release 级收口规则：

- 单个 feature slice 可以先测、先回归、先关闭
- 但 `RELEASE` 只有在所有必需 slice 都完成且 blocker 清零后才能 `released`

建议派生对象：

- `TASK-DEVPLAN-REL-1.4.0-023-*` 表示 `FEAT-023` 的开发切片任务
- `TASK-TESTPLAN-REL-1.4.0-023-*` 表示 `FEAT-023` 的测试切片任务
- `REPORT-REL-1.4.0-FEAT-023-TEST-*` 表示该 feature slice 的测试报告

### 15.9 Slice Data Model

为了让 feature slice 成为可校验对象，`DEVPLAN` 与 `TESTPLAN` 必须至少声明：

```yaml
properties:
  slices:
    - slice_key: feat-023-core
      feat_id: FEAT-023
      feat_version: v5
      required: true
      dependencies: []
    - slice_key: feat-024-mail
      feat_id: FEAT-024
      feat_version: v2
      required: true
      dependencies:
        - feat-023-core
```

约束：

- `slice_key` 在同一 plan 内必须唯一
- 每个 `slice` 必须绑定一个明确的 `feat_id + feat_version`
- `TASK` 必须通过 `properties.slice_key` 绑定到某个 slice
- `REPORT` 必须通过 `properties.slice_key` 指向其对应 slice
- `release check` 必须按 slice 聚合，而不是只按整版聚合

## 15.10 Evidence Artifact Boundary

以下对象不进入正式 SSOT 主对象枚举：

- `CODE_REF`
- `PATCH`
- `TEST_RUN`
- `DEPLOY_LOG`

治理规则：

- 它们作为普通 artifact 或外部引用进入证据体系
- 正式主链只通过 `EVI` 或 `REPORT.properties.evidence_refs` 关联它们
- `release check` 不直接读取这些 artifact 作为 truth source，而是通过 `EVI/REPORT` 聚合结果

这样可以保持：

- 正式主链稳定
- 证据载体灵活
- 运行时 artifact 不污染对象模型

## 15.11 Recut Audit Carrier

`release recut` 的审计记录统一采用双层载体：

- 小范围 scope 调整
  - 写入 `RELEASE.properties.recuts[]`
- 重大 scope 变更
  - 额外生成 `REPORT`
  - `report_kind = recut_audit`

`RELEASE.properties.recuts[]` 最小结构：

```yaml
properties:
  recuts:
    - recut_id: recut-20260308-001
      reason: feat-023 acceptance changed
      old_refs:
        - id: FEAT-023
          version: v5
      new_refs:
        - id: FEAT-023
          version: v6
      approved_by: release_manager
      changed_at: 2026-03-08T10:00:00+08:00
```

约束：

- 每次 recut 必须留下唯一 `recut_id`
- 如果影响多个 slice 或多个 plan，必须额外生成 `recut_audit` report
- `release check` 必须读取 `recuts[]` 和 `recut_audit report` 两者

## 16. 与现有 Task Brief / Context Bundle 的关系

当前系统中的以下对象保留，但明确降级为辅助对象，不进入正式主链：

- `task_brief`
- `task_context_bundle`

它们的角色是：

- 帮助 agent 压缩输入上下文
- 帮助交接和审计
- 帮助查看执行历史

它们不是正式 `PLAN`，也不是正式 `TASK`。

## 17. 本 ADR 的 SSOT 归属

本 ADR 自身就是这套治理规则的正式真源，不再依赖 `docs/` 下的平行正文。

### 17.1 归属类型

本 ADR 的正式归属：

- `ADR`

不属于：

- `FEAT`
  - 因为它不是业务功能需求
- `RELEASE`
  - 因为它不是某次版本范围对象

可接受但非首选：

- `SRC`
  - 若团队希望把它作为治理源头文档看待，可以接受
  - 但语义不如 `ADR` 准确

### 17.2 正式对象

本 ADR 的正式对象定义如下：

```yaml
id: ADR-001
ssot_type: adr
title: SSOT delivery chain hard governance
status: frozen
version: v1
parent_id:
derived_from_ids: []
source_refs: []
owner: governance
tags: [ssot, governance, delivery]
properties:
  adr_kind: governance_baseline
```

### 17.3 冻结规则

该 ADR 的状态流转应为：

- `draft -> reviewed -> frozen`

冻结门槛：

- 对象模型稳定
- 状态机稳定
- P0/P1 规则稳定
- 至少完成一轮架构评审

冻结后含义：

- 它成为后续 `schema / validator / CLI / workflow` 实现的治理真源
- 下游实现必须通过 `source_refs` 或 `derived_from_ids` 回指该 ADR
- 不允许原地修改旧版本，只允许新版本 supersede

### 17.4 下游引用规则

建议以下对象显式引用该 ADR：

- `schema.json` 改造
- `id_parser / id_generator` 改造
- `SSOTValidator` 改造
- `release check / plan derive` 命令
- L1 workflow spec

推荐方式：

- `source_refs: [ADR-001#section-id]`

统一示例：

```yaml
source_refs:
  - ADR-001#10-id-grammar-migration
  - ADR-001#11-7-transition-authority-matrix
  - ADR-001#15-9-slice-data-model
```

建议约定：

- `#section-id` 使用稳定的章节锚点语义，而不是临时行号
- schema 改造优先引用：
  - `ADR-001#8-2-1-front-matter-minimal-templates`
  - `ADR-001#10-1-id-grammar-migration`
- validator 改造优先引用：
  - `ADR-001#11-7-transition-authority-matrix`
  - `ADR-001#12-1-p0-blocking-rules`
- release workflow 改造优先引用：
  - `ADR-001#15-4-typical-l1-workflow`
  - `ADR-001#15-9-slice-data-model`

### 17.5 边界

本 ADR 冻结后，属于：

- 治理 SSOT

不属于：

- 产品需求 SSOT
- 具体 release scope
- 具体 feature 设计

因此它提供的是治理约束，不直接替代：

- `FEAT`
- `TECH`
- `TESTSET`
- `RELEASE`

## 18. 与旧 OpenSpec 的切割

### 18.1 明确废弃

以下内容不再作为正式治理输入：

- P1-P7 phase progress 文档
- OpenSpec “阶段状态” 判定
- 基于规范文本自觉遵守的软治理

### 18.2 可保留的部分

若某些 workflow runner 仍然有执行价值，可以保留为：

- 执行器模板
- 脚本编排模板
- 示例流程

但它们不再拥有 truth ownership。正式真源一律回到 SSOT 文件和 SSOT 校验脚本。

## 19. 对现有代码的具体改造点

### 19.1 类型层

修改 [E:/ai/LEE/src/lee/orchestrator/execution/artifacts/types.py](E:/ai/LEE/src/lee/orchestrator/execution/artifacts/types.py)

- 在 `SSOTType` 中新增：
  - `RELEASE = "release"`
  - `DEVPLAN = "devplan"`
  - `TESTPLAN = "testplan"`
- 更新 `ObjectCategory.get_parent_requirement()`
- 调整 `TASK` 的 parent 合法性，不再固定为 `FEAT`

### 19.2 目录层

修改 [E:/ai/LEE/src/lee/orchestrator/execution/artifacts/placement.py](E:/ai/LEE/src/lee/orchestrator/execution/artifacts/placement.py)

- 增加 `RELEASE/DEVPLAN/TESTPLAN` 的 placement
- 将 `REPORT` 细分到 release/testing/delivery 子目录时，可先通过 `properties.report_kind` 解决，不必立即拆类型

### 19.3 Schema 层

修改 [E:/ai/LEE/spec-global/core/contracts/ssot-agent-output/v1/schema.json](E:/ai/LEE/spec-global/core/contracts/ssot-agent-output/v1/schema.json)

- 扩展 `ssot_type` 枚举
- 增加 plan/release 所需的结构字段
- `derived_from_ids` 改为结构化对象数组，不再用字符串列表承载 release scope
- 增加 `BUG` 双字段和 waiver 字段
- 增加 `PLAN.properties.slices[]` 结构

### 19.4 物化层

修改 [E:/ai/LEE/src/lee/orchestrator/execution/artifacts/ssot_contract.py](E:/ai/LEE/src/lee/orchestrator/execution/artifacts/ssot_contract.py)

- 支持 materialize `release/devplan/testplan`
- 物化时同步 front matter 与 registry metadata

### 19.5 校验层

修改 [E:/ai/LEE/src/lee/orchestrator/execution/artifacts/ssot_service.py](E:/ai/LEE/src/lee/orchestrator/execution/artifacts/ssot_service.py)

- 将 `validate()` 从旧 v1 truth-chain 规则升级到三轴规则
- 保留旧规则为 legacy validator，避免逻辑混杂
- 扩展 `SSOTValidator` 的 P0/P1 规则集

### 19.6 CLI 层

修改 [E:/ai/LEE/src/lee/cli/commands/ssot.py](E:/ai/LEE/src/lee/cli/commands/ssot.py)

- 增加 `lint`
- 增加 `plan derive`
- 增加 `plan check`
- 增加 `release cut`
- 增加 `release check`
- 增加 `release close`
- 增加 `render-view`

## 20. 迁移策略

### 20.1 第一阶段：立新不迁旧

- 新增 `RELEASE/DEVPLAN/TESTPLAN`
- 新功能只走新链
- 旧 OpenSpec 文档不自动迁移

### 20.2 第二阶段：建立 release 驱动

- 所有新开发需求必须先进入 `RELEASE`
- 禁止直接从 `FEAT` 创建执行任务

### 20.3 第三阶段：接入 CI 阻断

- PR 校验
- release gate 校验
- merge 阻断

### 20.4 第四阶段：派生旧视图

如需保留原先的“阶段进度展示”，只能作为派生报表生成，不允许人工维护。

## 21. 最小落地顺序

建议按以下顺序实施：

1. 先做 `ID grammar migration`，更新 parser/generator/parent consistency
2. 扩 `SSOTType`、`placement`、`schema`
3. 明确 front matter 真源并实现 `registry rebuild/sync`
4. 扩 `create_ssot()` 与 `ssot_contract materializer`
5. 扩 `SSOTValidator` 的 plan/release/slice/bug 规则
6. 扩 `lee ssot validate/build-index`
7. 增加 `release check`
8. 增加 `plan derive`
9. 接 CI / git hooks
10. 最后再做派生视图和 dashboard

## 22. 最终原则

最终只保留三条硬原则：

- 需求只能定义真相，不能直接代表交付承诺。
- 交付只能通过 `RELEASE -> PLAN -> TASK` 进入执行。
- 发布只能依据 `REPORT/EVI/BUG` 聚合后的 `RELEASE` 判定，不依据口头状态或阶段文档判定。

这三条一旦落成脚本和 CI，AI 才会真正运行在受控轨道上。

