# 交付轴缺口整改方案

## 治理归属

- 类型: 项目级交付治理正文
- 正式约束来源: `ADR-001`
- 适用问题类: 第二类, 交付轴 issue
- 目标: 把缺口从“文件没补齐”收敛成“交付承诺链闭合”

## 1. 适用范围

本方案只处理三轴模型中的第二类问题: 交付轴 issue。

适用触发条件:

- `RELEASE` 未建立
- `DEVPLAN` 或 `TESTPLAN` 未生成
- `TASK` 未拆完，无法形成可执行队列
- 校验入口仍停留在旧入口，没有切到 `RELEASE -> TESTPLAN -> TASK`
- plan 已生成，但对 release scope 的覆盖不完整

不适用情况:

- 上游 `FEAT / TECH / TESTSET` 还未冻结
- 当前问题本质是需求轴错误，而不是交付轴缺口
- 当前问题本质是证据轴缺失，例如已有 `TASK`，但没有 `REPORT / EVI / BUG`

## 2. 正式口径

本方案不重新定义模型，直接继承 `ADR-001` 的正式约束:

- 交付轴唯一合法主链是 `RELEASE -> DEVPLAN / TESTPLAN -> TASK`
- `TASK` 不能直接挂在 `EPIC` 或 `FEAT` 下作为正式执行入口
- QA 校验与执行入口必须从 `TASK` 进入，再回溯到 `TESTPLAN` 和 `RELEASE`
- release 是否可发布，只能由 `release check` 聚合判定

因此，面对交付轴缺口时，修复顺序必须是:

1. 先补 `RELEASE`
2. 再补 `DEVPLAN / TESTPLAN`
3. 再补 `TASK`
4. 再切执行与校验入口
5. 最后做 coverage 和 release gate 收口

禁止反向修补:

- 先造一堆 `TASK`，再事后补 plan
- 继续让 QA 直接从 `TESTPLAN` 或自由参数启动
- 用报告或上下文包替代正式 `PLAN`
- 用口头范围替代 `RELEASE.derived_from_ids`

## 3. 现状判断矩阵

### 3.1 Case A: `RELEASE` 未建

结论:

- 当前没有合法交付根对象
- 任何后续 `DEVPLAN / TESTPLAN / TASK` 都不应视为正式对象

处理动作:

- 先确认纳入版本的 `FEAT@version` 已冻结
- 用 `release cut` 创建正式 scope
- 要求 `RELEASE.derived_from_ids` 明确 pin 住每个 `FEAT@version`

### 3.2 Case B: `DEVPLAN / TESTPLAN` 未生成

结论:

- 已有版本范围，但还没有执行承诺
- 当前只能认为 release 处于 `planned / scope_frozen`，不能进入正式执行

处理动作:

- 从 `RELEASE` 派生 `DEVPLAN / TESTPLAN` 骨架
- 为 `DEVPLAN` 补齐切片、owner、依赖、完成定义
- 为 `TESTPLAN` 补齐 `TESTSET`、环境矩阵、入口、阻断条件、放行条件

### 3.3 Case C: `TASK` 没拆完

结论:

- plan 存在，但仍不可执行
- 交付承诺还没有落到原子执行单元

处理动作:

- 以 slice 为最小单位把 plan 落成 `TASK`
- 开发任务挂到 `DEVPLAN`
- 测试任务挂到 `TESTPLAN`
- 每个 `TASK` 必须绑定上游对象和 `slice_key`

### 3.4 Case D: 校验入口未切换

结论:

- 即使对象齐全，执行口径仍然错误
- 旧入口会绕开正式交付链，导致 QA 与发布判定不可审计

处理动作:

- 强制把 QA 执行入口切到 `TASK`
- 入口链路统一走 `TASK -> TESTPLAN -> RELEASE`
- 兼容字段可以保留，但只能作为运行时桥接，不再作为正式入口

### 3.5 Case E: plan 覆盖不完整

结论:

- 最常见的隐性问题
- 文件看起来都有，但 release scope 没有被完整映射到开发和测试计划

处理动作:

- 对每个 `FEAT@version` 检查:
  - 是否至少被一个 `DEVPLAN` 覆盖
  - 是否至少被一个 `TESTPLAN` 覆盖
- 对每个 slice 检查:
  - 是否有开发任务
  - 是否有测试任务
  - 是否有后续报告/证据承接

## 4. 标准补齐流程

### Step 1: 冻结前置检查

执行目标:

- 确认 release scope 的上游对象已经具备交付前提

必须满足:

- `FEAT` 已冻结
- 相关 `TECH` 已冻结或至少达到可执行设计状态
- 相关 `TESTSET` 已冻结或至少可用于生成 `TESTPLAN`

未满足时:

- 不进入交付轴补齐
- 先回到需求轴补冻结

### Step 2: 建立 `RELEASE`

目标:

- 把“这次交付到底交什么”变成正式对象

建议命令:

```bash
lee ssot release-cut 1.4.0 --title "March MVP release" --feat FEAT-023:v5 --feat FEAT-024:v2
```

生成后必须检查:

- `RELEASE` 已落盘
- `derived_from_ids` 完整
- `release_version` 明确
- scope 内没有未冻结对象

建议补充字段:

- `scope_frozen_at`
- `rollback_plan`
- `target_env`
- `build_version`
- `build_commit`

### Step 3: 派生 `DEVPLAN / TESTPLAN`

目标:

- 把 release scope 落成研发承诺和验证承诺

建议命令:

```bash
lee ssot plan-derive REL-1.4.0
```

派生后必须补全:

- `DEVPLAN.properties.slices`
- `TESTPLAN.properties.slices`
- `TESTPLAN.properties.environment_matrix`
- 计划正文中的 owner、依赖、顺序、阻断条件、放行条件

提交前检查:

```bash
lee ssot plan-check DEVPLAN-REL-1.4.0 --commit
lee ssot plan-check TESTPLAN-REL-1.4.0 --commit
```

### Step 4: 完成 `TASK` 拆解

目标:

- 把 plan 变成可执行原子单元

拆解规则:

- 一个 slice 至少要有一条开发任务和一条测试任务
- `DEVPLAN` 下的任务必须体现实现边界
- `TESTPLAN` 下的任务必须体现验证入口和测试对象
- 所有 `TASK` 必须挂在 `DEVPLAN` 或 `TESTPLAN` 下

每个 `TASK` 至少应具备:

- `parent_id`
- `derived_from_ids`
- `properties.slice_key`
- owner
- acceptance / done definition
- estimate 或优先级

验收口径:

- 没有完成 `TASK` 拆解，就不能宣称 plan 可执行
- 没有测试任务，就不能宣称验证链闭合

### Step 5: 切换校验与执行入口

目标:

- 让 QA 从正式交付链入场，而不是从旧兼容入口入场

当前项目中的正式入口口径:

- `src/lee/qa/entry_router.py` 负责入口路由
- `src/lee/qa/chain_validator.py` 负责校验 `RELEASE -> TESTPLAN -> TASK`
- `src/lee/qa/workflow_launch.py` 负责把正式 `TASK` 入口桥接到运行时模板参数
- `src/lee/cli/commands/qa/execute.py` 已经按 `task_ref` 进入

执行要求:

- 只允许 `lee qa execute <TASK-TESTPLAN-...>` 进入 QA 主流程
- 不再允许把 `TESTPLAN` 直接当成最终执行入口
- 兼容字段 `test_plan_id` 仅作为运行时桥接字段存在

验证命令:

```bash
lee qa execute TASK-TESTPLAN-REL-1.4.0-001
```

入口切换完成的标志:

- 请求以 `task_ref` 为唯一入口
- 入口审计日志能回放出 `RELEASE / TESTPLAN / TASK`
- chain validator 失败时会阻断执行

### Step 6: 做 coverage 收口

目标:

- 确保不是“对象都建了”，而是真正覆盖了 release scope

建议检查命令:

```bash
lee ssot render-view feat-delivery-matrix --release-id REL-1.4.0
lee ssot release-check REL-1.4.0
lee ssot release-check REL-1.4.0 --enforce
```

必须通过的覆盖项:

- 每个 `FEAT@version` 被 `DEVPLAN` 覆盖
- 每个 `FEAT@version` 被 `TESTPLAN` 覆盖
- 每个关键 slice 同时有开发和测试路径
- release 所需报告类型齐全

## 5. 五类问题的一次性修复策略

如果当前五类问题同时存在，建议采用以下顺序一次修完:

1. 先 cut `RELEASE`
2. 立即 derive `DEVPLAN / TESTPLAN`
3. 补 plan 的 `slices / environment_matrix / owner / deps`
4. 再拆 `TASK`
5. 再把 QA 入口全部切到 `task_ref`
6. 最后做 `plan-check` 和 `release-check`

原因:

- `RELEASE` 缺失时，后面的所有对象都没有正式归属
- 先拆 `TASK` 会造成二次返工，因为后续还要回补 plan 和 slice
- 入口不切换，交付轴即使补齐也会被旧执行链绕开

## 6. 完成定义

第二类 issue 关闭前，必须同时满足以下条件:

- 至少存在一个正式 `RELEASE`
- 该 `RELEASE` 下存在正式 `DEVPLAN` 和 `TESTPLAN`
- `DEVPLAN / TESTPLAN` 已通过基础 `plan-check`
- 所有必需 slice 都已落成 `TASK`
- QA 主入口已切换为 `task_ref`
- `release-check` 不再报 scope 覆盖缺失

建议附加通过项:

- `rollback_plan` 已补齐
- `render-view release-dashboard` 可直接用于人工审查
- 所有 release 级报告类型已经按约定预留或生成

## 7. 常见误区

- 误区一: 先把测试跑起来，后面再补 `RELEASE`
  - 后果: 执行链无法审计，结果无法进入正式发布判定
- 误区二: `TESTPLAN` 有了，就等于交付轴完整
  - 后果: 缺少开发承诺链，release coverage 仍然不完整
- 误区三: `TASK` 只要存在即可
  - 后果: 没有 parent、slice、上游绑定的任务无法进入正式治理
- 误区四: 旧 `test_plan_id` 入口还能用，就先不切
  - 后果: QA 主入口会继续绕开正式交付链
- 误区五: 只看 plan 文件数量，不看 coverage
  - 后果: 文件齐了，但版本 scope 仍有漏项

## 8. 推荐执行口令

面向一次标准修复，推荐最小命令集如下:

```bash
lee ssot release-cut 1.4.0 --title "March MVP release" --feat FEAT-023:v5
lee ssot plan-derive REL-1.4.0
lee ssot plan-check DEVPLAN-REL-1.4.0 --commit
lee ssot plan-check TESTPLAN-REL-1.4.0 --commit
lee ssot render-view feat-delivery-matrix --release-id REL-1.4.0
lee qa execute TASK-TESTPLAN-REL-1.4.0-001
lee ssot release-check REL-1.4.0 --enforce
```

## 9. 最终原则

第二类 issue 的本质不是“少几个文件”，而是“交付承诺链没有闭合”。

真正的修复标准只有一句话:

从 `RELEASE` 开始，能稳定派生 `PLAN`，能落成 `TASK`，能从 `TASK` 进入 QA，能在 `release check` 中被完整聚合。
