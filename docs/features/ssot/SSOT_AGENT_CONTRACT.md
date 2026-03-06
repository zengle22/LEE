# SSOT Agent Contract

## Purpose

这份约束用于 agent 输出“我要生成哪些正式对象”，不再让执行层靠目录或文件名猜。

正式 schema:

- [`schema.json`](../../../spec-global/core/contracts/ssot-agent-output/v1/schema.json)

执行入口:

- [`SSOTContractMaterializer`](../../../src/lee/orchestrator/execution/artifacts/ssot_contract.py)

## Required Fields

每个输出对象至少声明：

- `key`
- `identity_kind`
- `title`

当 `identity_kind = ssot` 时，必须再声明：

- `ssot_type`

常用关系字段：

- `parent`
- `derived_from`
- `source_refs`
- `verifies`
- `implements`

## Envelope Pattern

当一个 agent 同时声明 `contracts.output_schema` 和 `contracts.ssot_output_schema` 时，推荐输出单个 envelope：

```json
{
  "business_output": {
    "...": "按原 output_schema 定义的业务内容"
  },
  "ssot_output_contract": {
    "contract_version": "1.0",
    "run_id": "demo-contract-run-001",
    "outputs": []
  }
}
```

规则：

- `business_output` 用于 `contracts.output_schema` 校验
- `ssot_output_contract` 用于 `contracts.ssot_output_schema` 校验和物化
- 如果 agent 只产出 SSOT contract，也可以直接输出 contract 本体

## Example

```yaml
contract_version: "1.0"
run_id: demo-contract-run-001
outputs:
  - key: epic
    identity_kind: ssot
    ssot_type: epic
    title: 增长基础设施
    source_refs: ["SRC-001#1.2"]

  - key: feat
    identity_kind: ssot
    ssot_type: feat
    title: 用户注册
    parent: epic
    source_refs: ["epic#scope"]

  - key: testset
    identity_kind: ssot
    ssot_type: testset
    title: 用户注册测试集
    parent: feat
    verifies: ["feat"]

  - key: retrospective_note
    identity_kind: non_ssot
    artifact_type: DOCUMENT
    category: readme
    governance_kind: knowledge
    title: 注册链路复盘记录
    depends_on: ["feat"]
```

## Runtime Rules

- `key` 是 contract 内部符号名
- `parent/verifies/implements/...` 可以引用前面输出的 `key`
- runtime 会把符号名解析成真实 ID
- 正式 SSOT 文件名仍由 SSOT 层生成：`[ID]__[slug].[ext]`
- 正式 SSOT 文件目录仍由 placement policy 决定

## Migration Pattern

推荐在现有 agent spec 中并存两套 contract 引用：

- `contracts.output_schema`: 原业务输出 schema，继续约束领域内容
- `contracts.ssot_output_schema`: 新的 SSOT 输出声明 schema，约束对象身份和关系

样板已接入：

- [`prd-writer`](../../../spec-global/departments/prd/agents/prd-writer/v1/agent.yaml)
- [`ui-designer`](../../../spec-global/departments/ui/agents/ui-designer/v1/agent.yaml)
- [`test-set-generator`](../../../spec-global/departments/qa/agents/test-set-generator/v1/agent.yaml)

## Demo

可直接运行：

```bash
python demo_ssot_contract_chain.py
```

## Runner Integration

当 agent spec 声明 `contracts.ssot_output_schema` 时，`LLMRunner` 会在普通 `output_schema` 校验之后自动：

1. 解析 agent 的结构化输出
2. 如果检测到 envelope，则用 `business_output` 做普通 schema 校验
3. 按 `ssot-agent-output` schema 校验 `ssot_output_contract`
4. 调用 `SSOTContractMaterializer` 物化正式 SSOT 文件链
5. 在步骤结果里写入 `ssot_materialized`
