# Dev 部门 L2/L3 流程与 `lee` CLI 使用指南

更新时间：2026-03-15

## 1. 先说结论

当前仓库里，Dev 部门有两套需要区分的东西：

1. `canonical` 现役实现
   - Feature 主入口：`template.dev.feature_delivery_l2`
   - Bugfix 主入口：`template.dev.bugfix_delivery_l2`

2. 当前 `lee run` 直接暴露的入口 / alias
   - `dev.feature-delivery` 是 canonical Feature Delivery L2
   - `dev.bugfix-delivery` 是 canonical Bugfix Delivery L2
   - `dev.feature` 是兼容入口，但运行时会重定向到 `dev.feature-delivery`
   - `dev.bugfix` 是兼容入口，但运行时会重定向到 `dev.bugfix-delivery`

也就是说：

- 如果你想看“现在 Dev 部门标准流程怎么设计”，以 `spec-global/departments/dev/README.md` 和两个 canonical L2 模板为准。
- 如果你想看“现在 CLI 实际能直接敲什么命令”，以 `config/workflow-registry.yaml` 和 `src/lee/cli` 为准。
- 现在设计和 CLI 主链已经基本收口，差别主要只剩“用户看到的兼容 key”和“内部执行的 canonical key”两层。

## 2. 当前 canonical 流程

### 2.1 Feature Delivery L2

主模板：

- `spec-global/departments/dev/workflows/templates/feature-delivery-l2-template.yaml`

阶段顺序：

1. `tech_design`
2. `contract_design`
3. `backend_dev`
4. `frontend_dev`
5. `integration`
6. `evidence_pack`
7. `smoke_gate`

关键约束：

- 共享输入是 `formal_ssot_id`、`source_refs`、`governing_adrs`、`repo_context`、`repo_frontend`、`repo_backend`
- `contract_design` 完成前，前后端不得启动
- `contract_design` 绑定 `gate.dev.contract_freeze_gate`
- `smoke_gate` 必须在 `evidence_pack` 后执行
- 生命周期按 `Ready -> In Progress -> Evidence Pack Produced -> Closed` 收口

### 2.2 Feature 对应的现役 L3

1. `template.dev.tech_design_l3`
   - 作用：从正式 FEAT 派生 TECH 桥接对象
   - 主要步骤：`analyze_feature -> draft_tech_spec -> self_review -> publish_tech`

2. `template.dev.feature_contract_l3`
   - 作用：在 TECH 之后冻结结构真相源
   - 主要步骤：`api_contract_design -> data_contract_design -> event_contract_design -> contract_self_review -> contract_freeze`

3. `template.dev.feature_be_l3`
   - 作用：后端 UTDD 实现
   - 主要步骤：`write_ut -> implement_backend -> refactor_backend -> coverage_gate -> publish_backend`
   - 约束：覆盖率阈值 80%

4. `template.dev.feature_fe_l3`
   - 作用：前端 UTDD 实现
   - 主要步骤：`write_ut -> implement_ui -> refactor_ui -> coverage_gate -> publish_frontend`
   - 约束：覆盖率阈值 80%

5. `template.dev.feature_integration_l3`
   - 作用：联调、结构性问题归因、回滚边界判断
   - 主要步骤：`integration_planning -> integration_execution -> structural_issue_routing -> integration_reporting`

6. `template.dev.evidence_pack_l3`
   - 作用：证据收口，给最终 smoke gate 提供输入
   - 主要步骤：`collect_evidence -> audit_evidence -> package_evidence -> review_package`

### 2.3 Bugfix Delivery L2

主模板：

- `spec-global/departments/dev/workflows/templates/bugfix-delivery-l2-template.yaml`

阶段顺序：

1. `triage`
2. `root_cause`
3. `fix_design`
4. `fix_implementation`
5. `verification`
6. `evidence_pack`
7. `merge_or_reject`

关键约束：

- 共享输入是 `bug_ssot_id`、`severity`、`reproduction_evidence`
- 默认是 `1 bug -> 1 workflow`
- 批量修复只有在“五同原则”满足时才允许
- `merge_or_reject` 前必须先完成 `evidence_pack`

### 2.4 Bugfix 对应的现役 L3

1. `template.dev.bugfix_triage_l3`
   - `validate_bug_input -> classify_bug_path -> review_batch_eligibility -> publish_triage`

2. `template.dev.bugfix_root_cause_l3`
   - `reproduce_issue -> analyze_root_cause -> review_root_cause -> publish_root_cause`

3. `template.dev.bugfix_fix_design_l3`
   - 作用：约束修复边界、验证面与回滚策略

4. `template.dev.bugfix_fix_impl_l3`
   - `prepare_fix_workspace -> implement_fix -> self_review_fix -> publish_fix_impl`

5. `template.dev.bugfix_verification_l3`
   - `prepare_verification -> execute_verification -> review_verification -> publish_verification`

6. `template.dev.bugfix_evidence_pack_l3`
   - 作用：缺陷修复证据收口并给最终合并决策提供输入

## 3. 这些流程是怎么落到运行时的

### 3.1 CLI 入口

`lee` 的统一入口在：

- `pyproject.toml`
- `src/lee/cli/main.py`
- `src/lee/__main__.py`

入口命令：

```bash
lee
python -m lee
```

`src/lee/cli/main.py` 里当前注册的核心工作流命令包括：

- `run`
- `status`
- `watch`
- `approve`
- `gates`
- `workflow`
- `adr`
- `epic`
- `feat`

### 3.2 `lee run` 的工作方式

`lee run <workflow_key>` 的主逻辑在：

- `src/lee/cli/commands/run.py`

它会做几件事：

1. 从 `config/workflow-registry.yaml` 找到 `workflow_key`
2. 解析 `--spec`，把 YAML/JSON 注入为参数
3. 渲染模板到 `.workflow/rendered/*.yaml`
4. 创建 workflow instance
5. 执行 Plan 或直接执行
6. 在遇到 Gate 时阻塞，等待 `approve/gates` 决策

### 3.3 L2/L3 实例生成与 L3 spawn

核心代码：

- `src/lee/orchestrator/core/workflow_generator.py`
- `src/lee/orchestrator/execution/orchestrator.py`

职责划分：

- `generate_l2_instance()`：把 L2 模板渲染成运行时 instance
- `generate_l3_instance()`：把 Point 或阶段输入渲染成 L3 instance
- `_spawn_l3_for_point()`：运行期为 L2 phase 生成并挂起/启动对应 L3

运行时实例路径：

- L2/L3 运行时实例写入 `.workflow/instances/...`
- 不再写回 `spec-global` 模板目录

### 3.4 Gate 与审批

核心代码：

- `src/lee/orchestrator/execution/gate_operations.py`
- `src/lee/cli/commands/gates_cmd.py`
- `src/lee/cli/commands/approve.py`

你可以：

- 用 `lee status <workflow_id>` 看 pending gates
- 用 `lee gates list <workflow_id>` 列出门禁
- 用 `lee gates approve` / `lee approve` 批准
- 用 `lee gates reject` 拒绝并指定 rollback/spawn 动作
- 用 `lee gates decide` 交互式处理

## 4. 当前 CLI 暴露的 Dev 相关命令

### 4.1 通用命令

```bash
python -m lee --help
python -m lee run --help
python -m lee status --help
python -m lee watch --help
python -m lee gates --help
python -m lee workflow --help
```

### 4.2 当前 registry 中的 Dev 工作流键

来自 `config/workflow-registry.yaml`：

1. `dev.feature`
   - 路径：`spec-global/departments/dev/workflows/templates/feature-delivery-l2-template.yaml`
   - 状态：兼容入口；内部重定向到 `dev.feature-delivery`
   - 必填：`project`、`module`、`feature_point_id`

2. `dev.feature-delivery`
   - 路径：`spec-global/departments/dev/workflows/templates/feature-delivery-l2-template.yaml`
   - 状态：canonical alias，推荐新用法
   - 必填：`formal_ssot_id`、`source_refs`、`governing_adrs`、`repo_context`、`repo_frontend`、`repo_backend`

3. `dev.bugfix`
   - 路径：`spec-global/departments/dev/workflows/templates/bugfix-delivery-l2-template.yaml`
   - 状态：兼容入口；内部重定向到 `dev.bugfix-delivery`
   - 必填：`bug_id`、`bug_description`、`project`、`repo`

4. `dev.bugfix-delivery`
   - 路径：`spec-global/departments/dev/workflows/templates/bugfix-delivery-l2-template.yaml`
   - 状态：canonical alias，推荐新用法
   - 必填：`bug_ssot_id`、`severity`、`reproduction_evidence`

## 5. 推荐使用方式

### 5.1 看设计和实现时

优先看这些文件：

- `spec-global/departments/dev/README.md`
- `spec-global/departments/dev/workflows/templates/feature-delivery-l2-template.yaml`
- `spec-global/departments/dev/workflows/templates/bugfix-delivery-l2-template.yaml`
- `src/lee/orchestrator/core/workflow_generator.py`
- `src/lee/orchestrator/execution/orchestrator.py`
- `src/lee/orchestrator/execution/gate_operations.py`

### 5.2 真要走 CLI 时

当前建议分两种认知：

1. “我要跑当前公开 CLI 支持的入口”
   - 用 `lee run dev.feature`
   - 用 `lee run dev.bugfix`
   - 或更推荐：`lee run dev.feature-delivery`、`lee run dev.bugfix-delivery`
   - 其中前两者仍是兼容路径，但会在运行时自动转换到 canonical 参数集和模板

2. “我要对齐 Dev 当前 canonical 设计”
   - 直接用 `lee run dev.feature-delivery`
   - 或 `lee run dev.bugfix-delivery`

## 6. Demo

### 6.1 命令级 Demo：查看 CLI 能力

```bash
python -m lee --help
python -m lee run --help
python -m lee workflow --help
python -m lee gates --help
```

### 6.2 canonical alias Demo：Feature

先准备一个最小 spec 文件，比如 `tmp_dev_feature_delivery.yaml`：

```yaml
formal_ssot_id: FEAT-DEMO-001
source_refs:
  - spec/features/demo-feature.md
governing_adrs:
  - ADR-008
repo_context:
  repo_id: lee-backend
  type: backend
  branch: demo/l3
repo_frontend: lee-frontend
repo_backend: lee-backend
```

执行：

```bash
python -m lee run dev.feature-delivery ^
  --spec tmp_dev_feature_delivery.yaml ^
  --project-dir E:\ai\LEE ^
  --new-task "demo dev feature run"
```

适用场景：

- 验证当前 registry 与 CLI 主链是否通
- 观察 `run -> status -> gates -> approve` 的完整交互

### 6.3 canonical alias Demo：Bugfix

先准备 `tmp_dev_bugfix_delivery.yaml`：

```yaml
bug_ssot_id: BUG-DEMO-001
severity: P1
reproduction_evidence:
  summary: open page -> click submit -> 500
repo_context:
  repo_id: lee-backend
  type: backend
```

执行：

```bash
python -m lee run dev.bugfix-delivery ^
  --spec tmp_dev_bugfix_delivery.yaml ^
  --project-dir E:\ai\LEE ^
  --new-task "demo bugfix run"
```

注意：

- 这条命令走的是 canonical `bugfix-delivery-l2-template.yaml`

### 6.4 兼容入口 Demo

如果你是为了兼容旧脚本，也仍然可以用：

```bash
python -m lee run dev.feature --spec tmp_dev_feature_compat.yaml --project-dir E:\ai\LEE
python -m lee run dev.bugfix --spec tmp_dev_bugfix_compat.yaml --project-dir E:\ai\LEE
```

这两条命令现在都会在内部重定向到 canonical L2：

- `dev.feature -> dev.feature-delivery`
- `dev.bugfix -> dev.bugfix-delivery`

兼容参数会自动改写，例如：

- `feature_point_id -> formal_ssot_id`
- `feature_spec -> source_refs`
- `bug_id -> bug_ssot_id`
- `bug_description` / `reproduction_steps -> reproduction_evidence`

### 6.5 `lee demo` 端到端 Demo

只看解析、选 key 和模板渲染，不创建实例：

```bash
python -m lee demo --project-dir E:\ai\LEE\.tmp\demo-dry-run --dry-run
```

跑真实实例，但不自动审批 gate，让流程停在阻塞点：

```bash
python -m lee demo --project-dir E:\ai\LEE\.tmp\demo-gated-run --no-approve
```

默认行为是自动生成 demo spec，并依次尝试：

- Dev：`dev.feature-delivery`，找不到再退回 `dev.feature`
- QA：`qa.test-plan-execution`，找不到再退回 `qa.regression`
- DevOps：`devops.deploy`

### 6.6 运行中查看状态

```bash
python -m lee status
python -m lee status <workflow_id>
python -m lee watch <workflow_id>
python -m lee gates list <workflow_id>
python -m lee gates show <workflow_id>
```

### 6.7 门禁处理 Demo

批准：

```bash
python -m lee gates approve <workflow_id> <gate_id> --approver shado
```

拒绝并回滚：

```bash
python -m lee gates reject <workflow_id> <gate_id> ^
  --approver shado ^
  --comments "contract mismatch" ^
  --action rollback ^
  --target-step contract_design
```

交互式处理：

```bash
python -m lee gates decide <workflow_id> --approver shado
```

## 7. 当前已知偏差

### 7.1 兼容 key 仍然存在

`dev.feature` / `dev.bugfix` 还没有从 CLI 表层彻底删除。

当前策略是：

- 保留旧 key，避免旧脚本直接失效
- 在 `lee run` / `lee demo` 内部重定向到 canonical alias
- 兼容参数自动改写成 canonical 参数

### 7.2 `lee demo` 已切到“优先选可用 canonical key”

当前行为是：

- Dev 优先 `dev.feature-delivery`，回退 `dev.feature`
- QA 优先 `qa.test-plan-execution`，回退 `qa.regression`
- DevOps 使用 `devops.deploy`
- 支持 `--dry-run`
- 找不到 workflow 时显式跳过

## 8. 实际建议

如果你的目标是“梳理当前 Dev 部门实现”：

- 看 canonical 模板和 orchestrator 代码

如果你的目标是“今天就要用命令跑”：

- 优先用 `lee run dev.feature-delivery` / `lee run dev.bugfix-delivery`
- 兼容脚本再继续使用 `lee run dev.feature` / `lee run dev.bugfix`
- 在评审、培训、写文档时要明确标注兼容入口与 canonical alias 的区别

如果你的目标是“把 CLI 和 canonical 对齐”：

- 当前这一步已经完成：
  - 新增 `dev.feature-delivery`
  - 新增 `dev.bugfix-delivery`
  - `dev.feature` / `dev.bugfix` 已在运行时重定向到 canonical alias
  - `lee demo` 改为优先选择可用的 canonical / 已注册 workflow，并支持 `--dry-run`
