# Vibe Kanban 局域网访问配置

## 📌 概述

本配置允许局域网内其他设备通过浏览器访问 Vibe Kanban。

## 🚀 快速启动

### 方式一：使用启动脚本（推荐）

```bash
./start-vibe-kanban.sh
```

### 方式二：手动启动

```bash
HOST=0.0.0.0 PORT=3000 npx vibe-kanban
```

## 📱 访问地址

- **本机访问**: http://localhost:3000
- **局域网访问**: http://192.168.0.113:3000

局域网内任何设备的浏览器都可以访问上述地址。

## 🔍 检查配置状态

```bash
./check-lan-access.sh
```

该脚本会检查：
- vibe-kanban 进程状态
- 端口监听状态
- 本地和局域网访问测试
- macOS 防火墙状态

## ⚙️ 配置说明

### 环境变量

| 变量 | 值 | 说明 |
|------|-----|------|
| `HOST` | `0.0.0.0` | 监听所有网络接口 |
| `PORT` | `3000` | 指定端口号 |

### 防火墙设置

如果 macOS 防火墙阻止连接，请：

1. 打开「系统设置」→「网络」→「防火墙」
2. 确保「允许传入连接」已启用
3. 或为 vibe-kanban 添加防火墙例外

## 🔧 故障排除

### 无法从局域网访问

1. **确认 vibe-kanban 正在运行**
   ```bash
   ps aux | grep vibe-kanban
   ```

2. **确认端口监听状态**
   ```bash
   lsof -i :3000
   ```
   应该显示 `*:3000` (LISTEN)

3. **测试本地访问**
   ```bash
   curl http://localhost:3000
   ```

4. **测试局域网访问**
   ```bash
   curl http://192.168.0.113:3000
   ```

5. **检查防火墙**
   - macOS 防火墙可能阻止传入连接
   - 确保防火墙允许 vibe-kanban 接受连接

### 端口被占用

如果端口 3000 被占用，可以更改端口：

```bash
HOST=0.0.0.0 PORT=3001 npx vibe-kanban
```

## 📖 相关文件

- `start-vibe-kanban.sh` - 启动脚本
- `check-lan-access.sh` - 检查脚本

## 📝 注意事项

- 每次重启电脑后需要重新启动 vibe-kanban
- IP 地址可能会变化（如果是动态分配）
- 局域网访问仅在相同网络内有效
