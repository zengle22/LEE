# Technical Debt

本文档记录 LEE 项目的技术债务，按优先级排序。

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
