---
title: LEE MCP Server
author: LEE Team
date: 2026-01-29
version: 1.0
last_updated: 2026-02-19
---

# LEE MCP Server

简单的 MCP (Model Context Protocol) 服务器实现，用于 LEE 系统的测试和开发。

## 功能

提供示例 MCP 工具：
- `deploy` - 部署应用到指定环境
- `run_tests` - 运行项目测试
- `generate_code` - 生成代码文件

## 安装

```bash
cd mcp-server
npm install
```

## 运行

```bash
# 启动服务器
npm start

# 开发模式（自动重启）
npm run dev

# 运行测试客户端
npm test
```

服务器将在 `http://localhost:3000` 启动。

## API 端点

### 健康检查
```
GET /health
```

### 列出所有工具
```
GET /tools
```

### 调用工具
```
POST /tools/:tool_name
Content-Type: application/json

{
  "arguments": {
    "param1": "value1",
    "param2": "value2"
  }
}
```

## 示例调用

### 部署工具
```bash
curl -X POST http://localhost:3000/tools/deploy \
  -H "Content-Type: application/json" \
  -d '{
    "arguments": {
      "environment": "staging",
      "project": "/path/to/project",
      "branch": "main"
    }
  }'
```

### 运行测试
```bash
curl -X POST http://localhost:3000/tools/run_tests \
  -H "Content-Type: application/json" \
  -d '{
    "arguments": {
      "project": "/path/to/project",
      "test_type": "unit"
    }
  }'
```

## 集成到 LEE

在 `skill.yaml` 中配置：

```yaml
kind: skill
id: ci.deploy
version: 1.0

engine:
  type: mcp
  server_url: http://localhost:3000/mcp
  tool: deploy
  timeout: 600
  arguments:
    environment: staging
    project: {{ project_dir }}
    branch: main
```

## 开发

### 添加新工具

在 `server.js` 的 `tools` 对象中添加：

```javascript
const tools = {
  // ... 现有工具

  my_new_tool: {
    name: 'my_new_tool',
    description: '工具描述',
    parameters: {
      param1: {
        type: 'string',
        description: '参数描述',
        required: true
      }
    },
    handler: async (args) => {
      // 实现工具逻辑
      return {
        success: true,
        message: '执行成功'
      };
    }
  }
};
```

## 注意事项

- 这是开发测试服务器，生产环境需要更完善的实现
- 添加认证和授权机制用于生产部署
- 实现错误处理和日志记录
- 添加速率限制和安全防护
