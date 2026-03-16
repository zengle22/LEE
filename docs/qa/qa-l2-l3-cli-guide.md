# QA L2/L3 流程与 `lee` CLI 使用指南

本文基于当前仓库实现整理 QA 部门的 L2/L3 流程、对应 `lee` CLI 命令、推荐用法和最小 demo。

结论先行：

- 当前 QA 执行主入口已经统一到 `lee qa execute <TASK-TESTPLAN-REL-...>`。
- 旧入口 `lee qa run`、`lee qa test-run start`、`lee qa test-set run` 仍保留命令壳，但已经被 FEAT-143 显式阻断。
- QA 有两类 L3：
  - `test_set_production`：生成 Test Set 设计资产。
  - `test_set_execute`：执行单个 Test Set。
- QA 的 L2 是 `test_plan_l2`，负责从 Test Run 初始化一路推进到 L3 调度、结果汇总、出测评估和复盘。
- 当前仓库里，入口校验和 L2 创建是可用的；要稳定跑通 L2 -> L3 执行链，还需要项目侧运行时上下文，尤其是 repo registry、SUT 配置、以及可执行的测试资产。

---

## 1. 当前实现全景

### 1.1 Canonical 入口

当前推荐链路是：

`RELEASE -> TESTPLAN -> TASK -> lee qa execute`

也就是：

1. 上游先产出 `REL-*`
2. 再产出 `TESTPLAN-REL-*`
3. 再产出 `TASK-TESTPLAN-REL-*-NNN`
4. QA 只能拿这个 `TASK` 进入执行

入口实现位于：

- `src/lee/cli/commands/qa/execute.py`
- `src/lee/qa/entry_router.py`
- `src/lee/qa/chain_validator.py`
- `src/lee/qa/workflow_launch.py`

这条链路当前做了 4 件事：

1. 检查请求是否绕过 canonical 入口。
2. 验证 `TASK -> TESTPLAN -> RELEASE` 三段链是否合法。
3. 记录审计日志。
4. 把链路信息转换成 `qa.test-plan-execution` 的 L2 工作流参数并启动编排器。

### 1.2 L2 模板

QA 的 L2 模板是：

- `spec-global/departments/qa/workflows/templates/test-plan-l2-template.yaml`

它定义了 9 个 phase：

1. `test_run_init`
2. `env_provision`
3. `env_check`
4. `test_set_execution`
5. `l3_output_validation`
6. `bug_summary`
7. `test_report`
8. `exit_evaluation`
9. `retrospective`

其中第 4 阶段 `test_set_execution` 声明了：

- `spawns_l3: true`
- `l3_template_id: template.qa.test_set_execute`

也就是说，L2 的职责不是亲自做单个 Test Set 的执行，而是调度 L3。

### 1.3 L3 模板

QA 当前有两个核心 L3：

#### A. Test Set 生产 L3

- 模板：`spec-global/departments/qa/workflows/templates/test-set-production-l3-template.yaml`
- registry key：`qa.test-set-production`

它负责把 FEAT/需求输入转成 Test Set 设计资产，阶段为：

1. `requirement_analysis`
2. `strategy_design`
3. `test_set_generation`
4. `test_set_review`
5. `output_validation`

这是“产测试设计资产”的 L3，不是“跑测试”的 L3。

#### B. Test Set 执行 L3

- 模板：`spec-global/departments/qa/workflows/templates/test-set-execute-l3-template.yaml`
- registry key：`qa.test-set-execution`

它负责执行单个 Test Set，执行阶段在模板里以 `stage + steps` 定义，主要步骤为：

1. `case_generation`
2. `script_translation`
3. `script_execution`
4. `behavior_compliance`
5. `result_judgment`
6. `tse_assembly`
7. `bug_drafting`

其中最关键的是：

- `script_execution` 只负责执行，不负责判定。
- `behavior_compliance` 是 anti-mock 合规门。
- `result_judgment` 负责基于证据做通过/失败判断。
- `tse_assembly` 输出 TSE。
- `bug_drafting` 为失败用例起草 bug。

---

## 2. 相关 `lee` CLI 命令

### 2.1 推荐命令

#### `lee qa execute`

用途：QA 正式执行入口，启动 L2。

```bash
lee qa execute TASK-TESTPLAN-REL-1.4.0-001 --project-dir . --triggered-by qa-user
```

常用参数：

- `--project-dir`：项目目录
- `--triggered-by`：操作人或系统标识
- `--entry-source`：入口来源，取值 `cli|api|ui`
- `--max-steps`：本次向前推进多少步

#### `lee qa audit log`

用途：查询 QA 执行审计日志。

```bash
lee qa audit log --task-ref TASK-TESTPLAN-REL-1.4.0-001 --project-dir .
lee qa audit log --release-ref REL-1.4.0 --project-dir .
```

#### `lee qa sut ...`

用途：管理被测系统地址和运行环境配置。

常见命令：

```bash
lee qa sut init staging --base-url https://app-staging.example.com --project-dir .
lee qa sut show staging --project-dir .
lee qa sut list --project-dir .
lee qa sut url staging --project-dir .
```

### 2.2 设计资产相关命令

#### `lee qa test-set create`

用途：启动 Test Set 生产 L3，生成 Test Set 设计资产。

```bash
lee qa test-set create checkout \
  --requirement spec/requirements/features/FEAT-143__xxx.md \
  --tech-design spec/tech/TECH-FEAT-143-016__xxx.md \
  --project-dir .
```

另外还有：

```bash
lee qa test-set list --project-dir .
lee qa test-set show TESTSET-FEAT-143 --project-dir .
```

#### `lee qa test-plan ...`

用途：人工创建/查看旧式 `qa/test-plans/*.yaml` 资产。当前更像资产管理命令，不是推荐执行入口。

```bash
lee qa test-plan create TESTPLAN-REL-1.4.0 -s checkout -t TESTSET-FEAT-143 --project-dir .
lee qa test-plan list --project-dir .
lee qa test-plan show TESTPLAN-REL-1.4.0 --project-dir .
```

#### `lee qa test-run ...`

当前仍保留两个辅助命令：

```bash
lee qa test-run status --project-dir .
lee qa test-run approve <gate_id> --project-dir .
```

注意：

- `lee qa test-run start` 不是推荐入口，当前已被封禁。

### 2.3 通用编排观察命令

当 `lee qa execute` 启动了工作流后，可以继续使用通用命令观察或推进：

```bash
lee status <workflow_id> --project-dir .
lee gates list --workflow-id <workflow_id> --project-dir .
lee gates show --workflow-id <workflow_id> --project-dir .
lee gates approve --workflow-id <workflow_id> --gate-id <gate_id> --approver qa-lead --project-dir .
lee approve <workflow_id> <gate_id> --approver qa-lead --project-dir .
```

---

## 3. 已阻断的旧入口

以下命令名义上还在，但当前实现会直接提示改用 `lee qa execute`：

```bash
lee qa run ...
lee qa test-run start ...
lee qa test-set run ...
```

这是 FEAT-143 的明确收口，不是文档约定，而是 CLI 代码里直接抛错。

---

## 4. 实际运行链路

### 4.1 `lee qa execute` 的执行路径

执行 `lee qa execute TASK-TESTPLAN-REL-...` 时，当前实现实际走的是：

1. `ExecutionRequest` 接收 `task_ref`
2. `BypassBlocker` 检测是否存在旁路执行
3. `ChainValidator` 验证 `TASK -> TESTPLAN -> RELEASE`
4. `AuditLogger` 写入审计日志
5. `build_test_plan_execution_params()` 从 SSOT 链提取：
   - `test_plan_id`
   - `build_version`
   - `build_commit`
   - `environment`
   - `base_url`
   - `target_test_sets`
   - `release_ref`
   - `task_ref`
6. `render_test_plan_execution_template()` 渲染 `test-plan-l2-template.yaml`
7. `pm_workflow("create")` 创建 department 级工作流
8. `pm_workflow("run_until_blocked")` 向前推进执行

### 4.2 编排器如何识别 L2

`derive_workflow_creation_metadata()` 会根据模板 `kind` 判断：

- `l2_workflow_template` -> 创建 department 级工作流实例
- `l3_workflow_template` -> 创建 task 级工作流实例

这也是为什么 QA 的 `test-plan-l2-template.yaml` 会直接被当成 L2 实例蓝本，而不是普通 task workflow。

### 4.3 当前一个重要实现现实

虽然 QA L2 模板已经声明了 `test_set_execution -> spawn QA L3`，但当前编排器的 L2/L3 spawn 主体仍复用了更通用的 point/repo 派生逻辑。

这带来一个现实要求：

- 项目目录里必须有足够的运行时上下文，尤其是 repo registry。
- 如果缺少 `.lee/repos.yaml` 或对应 repo 映射，L2 能启动，但在 `test_set_execution` 阶段可能无法稳定 spawn 出可执行的 L3。

我在本仓库里跑最小 demo 时，实际看到的就是：

- canonical 入口校验通过
- L2 成功创建并进入 `running`
- 但 `test_set_execution` 因 repo registry 缺失持续报 `points failed to spawn L3`

所以现状应理解为：

- 入口规范：已落地
- L2 模板：已落地
- L3 模板：已落地
- 运行前提约束：需要项目侧上下文配合
- 最小裸目录 demo：通常只能证明“进入 L2”，不能证明“完整 L2 -> L3 跑完”

### 4.4 新增：入口前置检查

当前 `lee qa execute` 在创建 L2 前会先检查三类前置条件：

- `.lee/repos.yaml`
- `tests/runtime/<environment>/sut.yaml`
- `spec/qa/test-sets/*.yaml`

如果缺失，CLI 不会直接继续推进，而是会：

1. 自动生成一个模板文件
2. 输出明确的文件路径和填写提示
3. 以 `QA-PREFLIGHT-001` 阻断本次执行

详细说明见 `docs/qa/qa-execution-prerequisites.md`。

---

## 5. 推荐使用方式

### 场景 A：你要生成 Test Set 设计资产

用：

```bash
lee qa test-set create <module> --requirement <path> [--tech-design <path>] --project-dir .
```

适用场景：

- 需求或 FEAT 已冻结
- QA 需要先产出测试设计资产
- 还没有进入正式 Test Run

### 场景 B：你要正式执行 QA 测试流程

先保证存在 canonical SSOT 链：

- `REL-*`
- `TESTPLAN-REL-*`
- `TASK-TESTPLAN-REL-*-NNN`

然后执行：

```bash
lee qa execute TASK-TESTPLAN-REL-1.4.0-001 --project-dir . --triggered-by qa-user
```

执行后通常继续这样观察：

```bash
lee status <workflow_id> --project-dir .
lee qa audit log --task-ref TASK-TESTPLAN-REL-1.4.0-001 --project-dir .
```

如果卡在人工门禁，再用：

```bash
lee gates list --workflow-id <workflow_id> --project-dir .
lee gates approve --workflow-id <workflow_id> --gate-id <gate_id> --approver qa-lead --project-dir .
```

### 场景 C：你只是想看环境配置

```bash
lee qa sut list --project-dir .
lee qa sut show staging --project-dir .
lee qa sut url staging --project-dir .
```

---

## 6. 最小 demo

下面这个 demo 是基于当前仓库代码验证过的最小路径，目标是证明 canonical 入口和 L2 创建链路能跑起来。

### 6.1 准备最小 SSOT 链

需要至少有：

- `REL-1.4.0`
- `TESTPLAN-REL-1.4.0`
- `TASK-TESTPLAN-REL-1.4.0-001`

测试里就是这样种数据的：

```python
manager.create_ssot(... formal_id="REL-1.4.0", ...)
manager.create_ssot(... formal_id="TESTPLAN-REL-1.4.0", parent_id="REL-1.4.0", ...)
manager.create_ssot(... formal_id="TASK-TESTPLAN-REL-1.4.0-001", parent_id="TESTPLAN-REL-1.4.0", ...)
```

### 6.2 执行命令

```bash
lee qa execute TASK-TESTPLAN-REL-1.4.0-001 \
  --project-dir <demo-project> \
  --triggered-by qa-demo-user \
  --max-steps 20
```

### 6.3 典型输出

在当前仓库里，我实际跑到的结果大致如下：

```text
[ok] [1/7] request parsed
[ok] [2/7] bypass check passed
[ok] [3/7] chain validation passed
[ok] [4/7] audit logged: AUDIT-TASK-TESTPLAN-REL-1.4.0-001-XXXXXXX
[ok] [5/7] workflow template rendered: test-plan-l2-template-YYYYMMDDHHMMSS.yaml
[ok] [6/7] workflow created: wf_department_xxxxxxxx
[ok] [7/7] execution advanced: running
status=RUNNING task_ref=TASK-TESTPLAN-REL-1.4.0-001
testplan_ref=TESTPLAN-REL-1.4.0 release_ref=REL-1.4.0
workflow_id=wf_department_xxxxxxxx
```

### 6.4 demo 后继续观察

```bash
lee status wf_department_xxxxxxxx --project-dir <demo-project>
lee qa audit log --task-ref TASK-TESTPLAN-REL-1.4.0-001 --project-dir <demo-project>
```

如果项目还没有 repo registry、可执行测试资产、SUT 配置，通常只能证明：

- 入口校验成功
- L2 成功被创建

不一定能证明：

- L3 已成功 spawn
- 单个 Test Set 已完整执行

---

## 7. 实操建议

### 7.1 推荐最小前置条件

正式使用前，至少准备：

1. canonical SSOT 链：`REL -> TESTPLAN -> TASK`
2. `.lee/repos.yaml` 或等效 repo registry
3. SUT 配置：`lee qa sut init/show`
4. 可追踪的 Test Set 资产
5. 可执行 runner 环境

### 7.2 如果你是新接手 QA 流程

建议按这个顺序理解和上手：

1. 先看 `qa execute` 入口和三段链校验。
2. 再看 L2 模板的 phase。
3. 再看 Test Set production L3 和 execute L3 的职责划分。
4. 最后再接 repo registry、SUT、runner 这些运行时条件。

### 7.3 一句话区分三个核心命令

- `lee qa test-set create`：产 Test Set 设计资产
- `lee qa execute TASK-...`：正式进 QA L2 执行链
- `lee qa audit log`：查执行审计

---

## 8. 关键源码索引

入口与校验：

- `src/lee/cli/commands/qa/execute.py`
- `src/lee/qa/entry_router.py`
- `src/lee/qa/chain_validator.py`
- `src/lee/qa/workflow_launch.py`

模板与 registry：

- `config/workflow-registry.yaml`
- `spec-global/departments/qa/workflows/templates/test-plan-l2-template.yaml`
- `spec-global/departments/qa/workflows/templates/test-set-execute-l3-template.yaml`
- `spec-global/departments/qa/workflows/templates/test-set-production-l3-template.yaml`

编排器：

- `src/lee/orchestrator/execution/workflow_runner.py`
- `src/lee/orchestrator/api/__init__.py`
- `src/lee/orchestrator/execution/orchestrator.py`
- `src/lee/orchestrator/execution/subworkflow_ops.py`

CLI 命令实现：

- `src/lee/cli/commands/qa/__init__.py`
- `src/lee/cli/commands/qa/test_set.py`
- `src/lee/cli/commands/qa/test_run.py`
- `src/lee/cli/commands/qa/test_plan.py`
- `src/lee/cli/commands/qa/audit.py`
- `src/lee/cli/commands/qa/sut.py`

测试参考：

- `tests/qa/test_execution_cli.py`
- `tests/qa/test_execution_contracts.py`
- `tests/qa/test_run_sut.py`
