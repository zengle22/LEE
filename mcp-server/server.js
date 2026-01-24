/**
 * LEE MCP Server
 * 简单的 MCP 协议服务器实现
 *
 * 用于测试和开发
 */

const express = require('express');
const cors = require('cors');

const app = express();
const PORT = 3000;

// 中间件
app.use(cors());
app.use(express.json());

// 工具注册表
const tools = {
  // 示例工具: 部署
  deploy: {
    name: 'deploy',
    description: '部署应用到指定环境',
    parameters: {
      environment: {
        type: 'string',
        description: '目标环境 (staging/production)',
        required: true,
        enum: ['staging', 'production']
      },
      project: {
        type: 'string',
        description: '项目路径',
        required: true
      },
      branch: {
        type: 'string',
        description: 'Git 分支',
        required: false,
        default: 'main'
      }
    },
    handler: async (args) => {
      const { environment, project, branch = 'main' } = args;

      console.log(`[部署] 环境: ${environment}, 项目: ${project}, 分支: ${branch}`);

      // 模拟部署过程
      await new Promise(resolve => setTimeout(resolve, 1000));

      return {
        success: true,
        deployment_id: `deploy-${Date.now()}`,
        environment,
        project,
        branch,
        status: 'deployed',
        url: `https://${environment}.example.com`,
        outputs: [
          'deployment-report.json',
          'deployment-log.txt'
        ],
        message: `成功部署 ${project} (${branch}) 到 ${environment}`
      };
    }
  },

  // 示例工具: 运行测试
  run_tests: {
    name: 'run_tests',
    description: '运行项目测试',
    parameters: {
      project: {
        type: 'string',
        description: '项目路径',
        required: true
      },
      test_type: {
        type: 'string',
        description: '测试类型',
        required: false,
        enum: ['unit', 'integration', 'e2e'],
        default: 'unit'
      }
    },
    handler: async (args) => {
      const { project, test_type = 'unit' } = args;

      console.log(`[测试] 项目: ${project}, 类型: ${test_type}`);

      // 模拟测试运行
      await new Promise(resolve => setTimeout(resolve, 500));

      return {
        success: true,
        test_type,
        total_tests: 42,
        passed: 40,
        failed: 2,
        coverage: '87.5%',
        duration: '5.2s',
        outputs: [
          'test-report.xml',
          'coverage-report.html'
        ],
        message: `测试完成: 40/42 通过`
      };
    }
  },

  // 示例工具: 生成代码
  generate_code: {
    name: 'generate_code',
    description: '生成代码文件',
    parameters: {
      prompt: {
        type: 'string',
        description: '生成提示',
        required: true
      },
      language: {
        type: 'string',
        description: '编程语言',
        required: false,
        default: 'python'
      },
      output_path: {
        type: 'string',
        description: '输出文件路径',
        required: true
      }
    },
    handler: async (args) => {
      const { prompt, language, output_path } = args;

      console.log(`[代码生成] 语言: ${language}, 提示: ${prompt.substring(0, 50)}...`);

      // 模拟代码生成
      await new Promise(resolve => setTimeout(resolve, 800));

      const code = `// Generated code for: ${prompt}\n// Language: ${language}\n\nconsole.log("Hello, ${prompt}!");\n`;

      return {
        success: true,
        code,
        language,
        output_path,
        lines: code.split('\n').length,
        message: `代码生成完成: ${output_path}`
      };
    }
  }
};

// MCP 端点
app.post('/tools/:tool_name', async (req, res) => {
  const { tool_name } = req.params;
  const { arguments: args = {} } = req.body;

  console.log(`\n[MCP 调用] 工具: ${tool_name}`);
  console.log(`参数:`, JSON.stringify(args, null, 2));

  // 检查工具是否存在
  const tool = tools[tool_name];
  if (!tool) {
    return res.status(404).json({
      error: `Tool not found: ${tool_name}`,
      available_tools: Object.keys(tools)
    });
  }

  try {
    // 执行工具
    const result = await tool.handler(args);

    console.log(`[MCP 响应]`, JSON.stringify(result, null, 2));

    res.json(result);

  } catch (error) {
    console.error(`[MCP 错误]`, error);

    res.status(500).json({
      error: error.message,
      tool: tool_name,
      success: false
    });
  }
});

// 列出所有工具
app.get('/tools', (req, res) => {
  const tools_list = Object.keys(tools).map(key => ({
    name: tools[key].name,
    description: tools[key].description,
    parameters: tools[key].parameters
  }));

  res.json({
    tools: tools_list,
    count: tools_list.length
  });
});

// 健康检查
app.get('/health', (req, res) => {
  res.json({
    status: 'ok',
    server: 'LEE MCP Server',
    version: '1.0.0',
    tools_count: Object.keys(tools).length
  });
});

// 启动服务器
app.listen(PORT, () => {
  console.log('\n' + '='.repeat(60));
  console.log('🚀 LEE MCP Server');
  console.log('='.repeat(60));
  console.log(`✅ Server running at http://localhost:${PORT}`);
  console.log(`📋 Available tools: ${Object.keys(tools).length}`);
  console.log('');
  console.log('Available endpoints:');
  console.log(`  - GET  /health           - 健康检查`);
  console.log(`  - GET  /tools            - 列出所有工具`);
  console.log(`  - POST /tools/:tool_name - 调用工具`);
  console.log('');
  console.log('Available tools:');
  Object.keys(tools).forEach(key => {
    console.log(`  - ${key}: ${tools[key].description}`);
  });
  console.log('='.repeat(60));
});

// 优雅关闭
process.on('SIGINT', () => {
  console.log('\n\n👋 Shutting down MCP server...');
  process.exit(0);
});
