# QA 执行前置检查与模板补全指南

## 1. 目的

从 2026-03-15 起，`lee qa execute` 在真正创建 QA L2 之前，会先做一次执行前置检查。

检查目标只有三类：

- `.lee/repos.yaml`
- 对应环境的 SUT 配置
- `TESTPLAN` 指向的 Test Set 设计资产

如果缺失，CLI 不会直接硬失败，也不会继续把流程推到后面才报错，而是：

1. 自动生成一个可编辑的模板文件
2. 直接提示文件路径和下一步动作
3. 以 `QA-PREFLIGHT-001` 阻断本次执行

这样做的目的，是把问题提前暴露在入口，而不是让 L3 已经启动后再因为上下文不完整停在中途。

## 2. 当前会检查什么

### 2.1 Repo Registry

检查路径：

- `.lee/repos.yaml`

用途：

- 让编排器知道有哪些 repo
- 让执行器和 agent 能拿到 repo 上下文
- 让 layer -> repo 的映射不是空值

如果缺失：

- CLI 会优先尝试自动发现 git repo，生成 `.lee/repos.yaml`
- 如果无法发现，也会生成一个最小模板

你需要补什么：

- `repo_id`
- `path`
- `type`

推荐至少明确前后端 repo；否则后续 phase 可能退化成空 repo 上下文。

### 2.2 SUT 配置

检查路径：

- `tests/runtime/<environment>/sut.yaml`

其中 `<environment>` 取自 `TESTPLAN` 或 `RELEASE` 推导出的执行环境。

用途：

- 告诉 QA runner 去测哪个系统
- 提供 `base_url`
- 需要时补充认证、协议和额外配置

如果缺失：

- CLI 会生成一个带 `template_status: fill_required` 的模板文件

你需要补什么：

- `base_url`
- `protocol`
- `auth_type`
- 必要时补 `extras`

补完后：

- 把 `template_status` 改为 `ready`
- 或者直接删除 `template_status` 字段

### 2.3 Test Set 设计资产

检查路径：

- `spec/qa/test-sets/ts-<test_set_id_slug>.yaml`

用途：

- QA L2 知道要执行哪些 Test Set
- QA L3 在运行时需要这些设计资产作为输入或追踪锚点

如果缺失：

- CLI 会为缺失的 `TESTSET-*` 生成模板文件

你需要补什么：

- `test_set_id`
- `module`
- `title`
- `traceability`
- `scope`
- `cases`

如果你不想手填，推荐先走正式资产生成：

```bash
lee qa test-set create <module> --requirement <path>
```

补完后同样需要：

- 把 `template_status` 改为 `ready`
- 或删除该字段

## 3. CLI 行为示例

当缺失前置条件时：

```bash
lee qa execute TASK-TESTPLAN-REL-1.4.0-001 --project-dir .
```

典型输出会包含：

```text
status=BLOCKED error_code=QA-PREFLIGHT-001
- [repo_registry] 缺少 repo registry，已生成初始模板。
  path=.../.lee/repos.yaml
- [sut_config] 缺少环境 'staging' 的 SUT 配置，已生成模板。
  path=.../tests/runtime/staging/sut.yaml
- [test_set] 缺少目标 Test Set 资产 'TESTSET-FEAT-143'，已生成模板。
  path=.../spec/qa/test-sets/ts-testset-feat-143.yaml
```

这时不要继续重跑，先把对应模板补全。

## 4. 推荐操作顺序

1. 先检查 `.lee/repos.yaml` 是否能正确映射实际 repo。
2. 再补 `tests/runtime/<environment>/sut.yaml`，确保目标环境、域名和认证信息准确。
3. 最后补 `spec/qa/test-sets/*.yaml`，确保测试范围和 cases 不是占位内容。
4. 完成后重跑 `lee qa execute ...`。

## 5. 为什么要在入口阻断

这是为了避免两类更难排查的问题：

- L3 已经起了，但执行器拿不到 repo 上下文，后续 step 才报空 repo warning
- runner 或 compliance step 才发现 SUT / 测试资产不完整，错误位置离根因太远

入口前置检查的目标不是替代后续校验，而是把最常见、最可修复的缺失项提前收口。
