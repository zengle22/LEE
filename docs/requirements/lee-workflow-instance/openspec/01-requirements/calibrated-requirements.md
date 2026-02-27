# 需求校准 - LEE Workflow Instance

## 原始需求

LEE Framework 需要实现统一的 Plan → Instance → Execute 流程。

## 校准后的需求

### 核心功能

1. **Plan Agent**
   - 输入：渲染后的模板 + 参数
   - 输出：Instance YAML + Plan Summary
   - 失败处理：换 LLM 重试

2. **Instance Generator**
   - 标准化格式
   - 版本管理
   - 包含成功/失败标准、重试配置

3. **Plan Review Gate**
   - 三级配置：simple/suggest/force
   - 审批不通过：重新 Plan，版本号 +1

4. **Orchestrator 改造**
   - 从 Instance 加载执行
   - 状态持久化

5. **重试副作用分析**
   - 触发时自动分析
   - 记录到日志

### 技术约束

- 使用现有 LEE 架构
- 复用现有 LLM Provider
- Instance 存储在 .workflow/instances/

## 可实现性确认

| 需求 | 可实现 | 说明 |
|------|--------|------|
| Plan Agent | ✅ | 复用 LLM Runner |
| Instance Generator | ✅ | 复用 Jinja2 + YAML |
| Review Gate | ✅ | 复用现有 Gate 机制 |
| Orchestrator 改造 | ✅ | 需要一定重构 |
| 重试副作用 | ✅ | 新增功能 |

## 假设

1. Plan Agent 使用现有 LLM 能力
2. 不需要新增数据库表
3. Instance 文件使用 YAML 格式

## 疑问

1. Plan Agent 需要单独的 Agent spec 还是复用？
2. Instance 版本号存储在哪里？
