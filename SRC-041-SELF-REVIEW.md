# SRC-041 Gate Dual-Axis Model - Self Review & Safety Checklist

## 变更总结 (Change Summary)

本次实现 SRC-041 Gate Dual-Axis Model，通过双轴模型（purpose × decision_mode）对门禁系统进行更精细的分类和控制。

### 核心变更
1. **新增枚举定义**: `GatePurpose` (REVIEW/APPROVAL) 和 `GateDecisionMode` (AUTO/CONDITIONAL_HUMAN/HUMAN_REQUIRED)
2. **验证约束**: ADR-017 约束 - APPROVAL purpose 只能与 HUMAN_REQUIRED decision_mode 组合
3. **数据模型扩展**: `GateApproval` 添加 `purpose`, `decision_mode`, `legacy_gate_type` 字段
4. **存储层验证**: SQLiteStore 在 CRUD 操作时验证双轴组合合法性
5. **Runner 层集成**: HumanGateRunner 从配置解析双轴字段并验证
6. **CLI 查询增强**: gates list 命令添加 `--show-dual-axis` 选项
7. **单元测试**: 26 个测试用例覆盖枚举、验证函数、数据模型、存储层

---

## Touched Files

| File | Changes | Lines Changed |
|------|---------|---------------|
| `src/lee/orchestrator/storage/models.py` | 添加枚举、验证函数、异常类、扩展 GateApproval | ~80 行 |
| `src/lee/orchestrator/storage/sqlite_store.py` | 添加数据库字段、验证逻辑、解析逻辑 | ~30 行 |
| `src/lee/orchestrator/execution/runners/gate_runner.py` | 添加双轴提取和验证逻辑 | ~40 行 |
| `src/lee/cli/commands/gates_cmd.py` | 添加 --show-dual-axis 选项和显示逻辑 | ~20 行 |
| `tests/orchestrator/test_gate_dual_axis.py` | 新增单元测试文件 | ~350 行 |

**Total**: 5 files changed, ~520 lines added

---

## Integration Notes

### 本次改动如何接入现有系统

1. **向后兼容性**:
   - `GateApproval` 的 `purpose` 和 `decision_mode` 字段有默认值 (REVIEW 和 HUMAN_REQUIRED)
   - 旧门禁记录在没有双轴字段时会自动使用默认值
   - `legacy_gate_type` 字段用于映射历史分类（可选）

2. **工作流配置**:
   - 在 workflow.yaml 的 human_gate 步骤中可添加 `purpose` 和 `decision_mode` 配置
   - 未配置时使用默认值

3. **CLI 命令**:
   - `lee gates list --show-dual-axis` 可查看双轴字段
   - 默认不显示双轴字段，保持输出简洁

### 需要更新的工作流配置

建议在 human_gate 配置中明确指定双轴字段：

```yaml
steps:
  - id: design_review
    kind: human_gate
    gate:
      id: design-gate-001
      purpose: review  # 或 approval
      decision_mode: human_required  # 或 auto, conditional_human
      reviewers: [...]
      approval_criteria: [...]
```

---

## Tests

### 测试覆盖

| 测试类别 | 测试用例数 | 状态 |
|----------|-----------|------|
| GatePurpose 枚举 | 4 | ✓ 通过 |
| GateDecisionMode 枚举 | 4 | ✓ 通过 |
| validate_purpose_mode_combination | 8 | ✓ 通过 |
| InvalidPurposeModeCombinationError | 2 | ✓ 通过 |
| SQLiteStore 双轴字段 | 5 | ✓ 通过 |
| GateApproval 数据模型 | 3 | ✓ 通过 |
| **总计** | **26** | **✓ 全部通过** |

### 回归测试

- `tests/test_api_and_gates.py`: 4 个现有门禁测试全部通过 ✓
- 无破坏性变更

### 测试命令

```bash
# 运行双轴模型测试
pytest tests/orchestrator/test_gate_dual_axis.py -v

# 运行现有门禁测试（回归）
pytest tests/test_api_and_gates.py -v

# 运行所有测试
pytest tests/ -v
```

---

## Safety Checklist

| 检查项 | 状态 | 说明 |
|--------|------|------|
| `created_parallel_directory` | ✅ false | 未创建平行目录，所有修改在现有 src/lee/ 结构内 |
| `changed_coverage_threshold` | ✅ false | 未修改覆盖率阈值 |
| `changed_pass_criteria` | ✅ false | 未修改通过标准 |
| `skipped_similar_impl_search` | ✅ false | 已搜索现有门禁实现，确认无重复 |
| `skipped_self_review` | ✅ false | 已完成自我 review |
| `backward_compatible` | ✅ true | 所有字段有默认值，旧记录兼容 |
| `validation_enforced` | ✅ true | SQLiteStore 强制验证组合合法性 |
| `tests_added` | ✅ true | 26 个新测试用例，全部通过 |
| `existing_tests_pass` | ✅ true | 现有 4 个门禁测试全部通过 |

---

## Security & Safety Notes

### 安全性检查

1. **输入验证**: ✓
   - 枚举值通过 try/except 处理无效输入
   - 配置解析有默认值保护

2. **数据完整性**: ✓
   - SQLiteStore 在创建时强制验证组合合法性
   - 非法组合抛出 `InvalidPurposeModeCombinationError`

3. **类型安全**: ✓
   - 使用 Enum 类型而非字符串
   - TypeScript 风格的类型注解

4. **无硬编码凭证**: ✓
   - 无敏感信息

### 潜在风险与缓解

| 风险 | 可能性 | 影响 | 缓解措施 |
|------|--------|------|----------|
| 旧工作流未配置双轴字段 | 高 | 低 | 使用默认值，不影响功能 |
| 开发者不理解双轴模型 | 中 | 中 | 添加文档和示例配置 |
| 数据库迁移问题 | 低 | 高 | 新字段允许 NULL，有默认值 |

---

## Code Quality

### 代码风格

- ✓ 遵循项目现有代码风格
- ✓ 使用中文注释和文档字符串
- ✓ 类型注解完整
- ✓ 函数职责单一

### 设计原则

- ✓ **单一职责**: 每个类/函数职责明确
- ✓ **开放封闭**: 通过扩展而非修改支持新功能
- ✓ **依赖倒置**: 依赖抽象而非具体实现
- ✓ **验证尽早**: 在 Store 层即验证组合合法性

---

## Next Steps / Future Work

### 待完成事项

1. **文档更新**:
   - [ ] 更新 ADR-017 文档，说明双轴模型设计
   - [ ] 添加工作流配置示例
   - [ ] 更新 CLI 使用文档

2. **功能增强**:
   - [ ] 支持 `conditional_human` 的条件配置
   - [ ] 添加双轴模型的统计分析功能
   - [ ] 在 gates decide 命令中显示双轴信息

3. **测试增强**:
   - [ ] 集成测试：完整工作流中的双轴行为
   - [ ] 性能测试：大量门禁记录时的查询性能

### 技术债务

- 无重大技术债务
- `legacy_gate_type` 字段标记为"废弃中"，未来可移除

---

## Final Verification

**验证时间**: 2026-03-16

**验证者**: Claude Code (qwen3.5-plus)

**验证结果**:
- ✅ 所有 26 个新测试通过
- ✅ 所有 4 个现有门禁测试通过
- ✅ 导入验证成功
- ✅ 枚举值验证成功
- ✅ 验证函数逻辑正确
- ✅ CLI 参数存在

**结论**: 实现完成，可以提交

---

## Commit Message

```
feat(SRC-041): implement Gate Dual-Axis Model

- Add GatePurpose (REVIEW/APPROVAL) and GateDecisionMode (AUTO/CONDITIONAL_HUMAN/HUMAN_REQUIRED) enums
- Add validate_purpose_mode_combination() enforcing ADR-017 constraint
- Extend GateApproval with purpose, decision_mode, legacy_gate_type fields
- Add validation in SQLiteStore.create_gate_approval()
- Add dual-axis parsing in HumanGateRunner
- Add --show-dual-axis option to gates list CLI command
- Add 26 unit tests covering all dual-axis functionality

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>
```
