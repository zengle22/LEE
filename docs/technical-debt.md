# Technical Debt

本文档记录 LEE 项目的技术债务，按优先级排序。

---

## QA E2E 测试模块

**模块**: `lee/qa/`
**完成日期**: 2026-02-27
**状态**: 核心功能已完成，以下为后续改进建议

### 短期优化 (1-2周)

#### 高优先级

1. **接入真实 LLM API**
   - **当前**: 使用 `MockLLMClient` 返回预设响应
   - **影响**: 无法实际生成测试代码
   - **建议**: 接入 Anthropic Claude 或 OpenAI API
   - **文件**: `lee/qa/utils/llm.py`, `lee/qa/generator/playwright_gen.py`

2. **集成日志模块**
   - **当前**: `logger.py` 覆盖率 0%，未使用
   - **影响**: 调试困难，无执行日志
   - **建议**: 在各模块中集成 `QALogger`
   - **文件**: `lee/qa/utils/logger.py`

#### 中优先级

3. **完善 Docker Runner**
   - **当前**: Docker 测试失败，模块覆盖率 0%
   - **影响**: 容器化执行不可用
   - **建议**: 修复 Docker 命令构建和结果解析
   - **文件**: `lee/qa/runner/docker.py`

4. **实现 RuntimeValidator**
   - **当前**: `RuntimeValidator` 只有占位符
   - **影响**: 缺少运行时验证层
   - **建议**: 实现实际执行期间的验证逻辑
   - **文件**: `lee/qa/validator/runtime_validator.py`

### 中期扩展 (1-2月)

#### 中优先级

5. **支持多浏览器测试**
   - **当前**: 仅支持 Chromium
   - **建议**: 添加 Firefox 和 WebKit 支持
   - **文件**: `lee/qa/runner/local.py`

6. **并行测试执行**
   - **当前**: 串行执行测试
   - **影响**: 大量测试时执行时间过长
   - **建议**: 使用 pytest-xdist 实现并行执行

7. **测试报告可视化**
   - **当前**: 仅输出 JSON 结果
   - **建议**: 生成 HTML 测试报告
   - **文件**: `lee/qa/runner/base.py`

8. **CI/CD 集成**
   - **当前**: 无 CI 集成
   - **建议**: 添加 GitHub Actions/Jenkins 配置模板

### 长期规划 (3-6月)

#### 低优先级

9. **测试用例智能生成**
   - **建议**: 基于页面结构自动发现可测试场景

10. **自愈合测试系统**
    - **建议**: 测试失败时自动修复并重试

11. **跨浏览器测试矩阵**
    - **建议**: 自动在不同浏览器/版本组合下运行测试

12. **性能基准测试**
    - **建议**: 添加页面加载时间、API 响应时间等性能指标验证

---

## Artifact Management System

### Phase 1 改进点

#### 高优先级

1. **`_get_git_info` 相对路径计算健壮性** (`manager.py:468-513`)
   - **问题**: 当前相对路径计算逻辑可能在不同工作目录下失败
   - **影响**: reference_mode adopt 可能在某些场景下记录错误的 git_repo_path
   - **修复**: 使用更健壮的路径计算，考虑边界情况

#### 中优先级

2. **CLI 命令集成测试缺失**
   - **问题**: `src/lee/cli/commands/artifacts.py` 没有对应的测试文件
   - **影响**: CLI 功能变更可能引入回归
   - **修复**: 添加 CLI 命令的 click.testing 集成测试

3. **性能基准测试缺失**
   - **问题**: 没有性能基准测试，无法衡量 registry 重建等操作的性能
   - **影响**: 大规模产出物场景下性能退化难以发现
   - **修复**: 添加针对 rebuild、register、查询等关键路径的基准测试

#### 低优先级

4. **类型注解改进**
   - **问题**: `manager.py:468` 使用 `tuple[Optional[str], Optional[str]]` 语法 (Python 3.9+)
   - **影响**: 项目最低 Python 版本兼容性需确认
   - **修复**: 如需兼容 3.8，改为 `Tuple[Optional[str], Optional[str]]`

5. **错误信息可读性**
   - **问题**: 某些错误消息可以更详细
   - **影响**: 用户体验
   - **修复**: 改进错误消息，添加上下文信息

### Phase 2 改进点

#### 中优先级

1. **artifacts_root 路径处理重复** (`integration.py:55-58, 336-340`)
   - **状态**: 已识别但未重构
   - **建议**: 提取为 `_get_artifacts_root()` 私有方法

2. **类型推断规则可扩展性**
   - **状态**: 当前硬编码在 `_infer_artifact_type`
   - **建议**: 考虑从配置文件加载类型推断规则

#### 低优先级

3. **非文本文件处理**
   - **当前**: 非文本文件被跳过 (`register_file:226`)
   - **建议**: 考虑记录二进制文件元数据而不读取内容
