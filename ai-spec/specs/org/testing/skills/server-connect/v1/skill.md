# Server Connect Skill v1.0
# 服务器连接技能 - SSH/云服务器安全连接

## 概述

Server Connect 技能负责建立与云服务器的安全 SSH 连接。
支持密钥认证和密码认证，优先推荐密钥认证方式。

## 技能标识

- **ID**: skill.test.server_connect
- **名称**: Server Connect
- **版本**: 1.0
- **所有者**: test-governance

## 适用 Agent

- agent.test.test_env_admin

---

## 1. 连接配置

### 1.1 基础配置

```yaml
ssh_config:
  host: "192.168.1.100"          # 服务器地址
  port: 22                        # SSH 端口
  user: "deploy"                  # 用户名

  # 认证方式 (二选一)
  auth:
    method: "key"                 # key | password
    key_path: "~/.ssh/deploy_key" # 私钥路径 (method=key)
    passphrase_ref: "vault:ssh_passphrase"  # 密钥密码引用 (可选)
    password_ref: "vault:ssh_password"      # 密码引用 (method=password)

  # 连接选项
  options:
    connect_timeout: 30           # 连接超时 (秒)
    server_alive_interval: 60     # 心跳间隔
    server_alive_count_max: 3     # 最大心跳失败次数
    strict_host_key_checking: "accept-new"  # 首次连接自动接受
```

### 1.2 跳板机配置 (可选)

```yaml
jump_host:
  enabled: true
  host: "bastion.example.com"
  port: 22
  user: "jump_user"
  key_path: "~/.ssh/bastion_key"
```

---

## 2. 连接流程

### 2.1 前置检查

```yaml
pre_checks:
  - name: "检查私钥文件存在"
    action: "file_exists"
    path: "{key_path}"
    on_fail: "error: 私钥文件不存在"

  - name: "检查私钥权限"
    action: "file_permission"
    path: "{key_path}"
    expected: "600"
    on_fail: "warn: 建议设置 chmod 600"

  - name: "解析密码/密钥密码"
    action: "resolve_secret"
    ref: "{passphrase_ref | password_ref}"
    on_fail: "error: 无法获取凭证"
```

### 2.2 建立连接

```bash
# 密钥认证
ssh -i {key_path} \
    -o ConnectTimeout=30 \
    -o ServerAliveInterval=60 \
    -o StrictHostKeyChecking=accept-new \
    {user}@{host} -p {port}

# 通过跳板机
ssh -J {jump_user}@{jump_host}:{jump_port} \
    -i {key_path} \
    {user}@{host} -p {port}
```

### 2.3 连接验证

```yaml
verification:
  - name: "测试连接"
    command: "echo 'Connection successful'"
    timeout: 10

  - name: "获取服务器信息"
    command: "uname -a && cat /etc/os-release | head -5"
    save_to: "server_info"

  - name: "检查工作目录"
    command: "ls -la {work_dir} || mkdir -p {work_dir}"
```

---

## 3. 远程命令执行

### 3.1 单命令执行

```yaml
exec_command:
  command: "docker ps"
  timeout: 30
  capture_output: true
  capture_stderr: true
```

### 3.2 脚本执行

```yaml
exec_script:
  local_script: "scripts/deploy.sh"
  remote_path: "/tmp/deploy.sh"
  args: ["--env", "test"]
  cleanup: true  # 执行后删除
```

### 3.3 文件传输

```yaml
file_transfer:
  # 上传文件
  upload:
    local: "dist/app.tar.gz"
    remote: "{work_dir}/app.tar.gz"
    mode: "0644"

  # 下载文件
  download:
    remote: "{work_dir}/logs/app.log"
    local: "output/logs/app.log"

  # 同步目录
  sync:
    local: "config/"
    remote: "{work_dir}/config/"
    delete: false  # 不删除远程多余文件
```

---

## 4. 安全规则

### 4.1 凭证管理

```yaml
security:
  credentials:
    # 支持的凭证来源
    sources:
      - type: "env"
        prefix: "SSH_"
      - type: "vault"
        path: "secret/test-env/ssh"
      - type: "file"
        path: "~/.ssh/credentials.json"
        encrypted: true

    # 禁止行为
    forbidden:
      - "在命令行参数中传递密码"
      - "在日志中记录凭证"
      - "将凭证存储在代码仓库"
```

### 4.2 日志脱敏

```yaml
log_sanitization:
  patterns:
    - pattern: "(password|passwd|pwd)=\\S+"
      replace: "{password}=***REDACTED***"
    - pattern: "-----BEGIN.*PRIVATE KEY-----"
      replace: "***PRIVATE_KEY_REDACTED***"
    - pattern: "\\b\\d{1,3}\\.\\d{1,3}\\.\\d{1,3}\\.\\d{1,3}\\b"
      replace: "***IP_REDACTED***"
      apply_to: "public_logs_only"
```

---

## 5. 错误处理

```yaml
error_handling:
  connection_refused:
    retry: 3
    interval: 10
    escalate_after: 3
    message: "SSH 连接被拒绝，检查防火墙和 SSH 服务"

  authentication_failed:
    retry: 0
    message: "认证失败，检查用户名/密钥/密码"

  timeout:
    retry: 2
    interval: 5
    message: "连接超时，检查网络和服务器状态"

  host_key_changed:
    retry: 0
    message: "主机密钥变更，可能存在安全风险"
    action: "require_manual_confirmation"
```

---

## 6. 输出

### 6.1 连接状态

```yaml
connection_status:
  connected: true
  host: "192.168.1.100"
  user: "deploy"
  auth_method: "key"
  connected_at: "2026-01-14T10:00:00Z"
  server_info:
    os: "Ubuntu 22.04.3 LTS"
    kernel: "5.15.0-91-generic"
    arch: "x86_64"
```

### 6.2 会话信息

```yaml
session:
  id: "sess-abc123"
  started_at: "2026-01-14T10:00:00Z"
  commands_executed: 5
  bytes_transferred:
    upload: 1024000
    download: 512000
```

---

## 7. 最佳实践

### 7.1 密钥管理

- 为每个环境使用独立的部署密钥
- 定期轮换密钥 (建议每 90 天)
- 使用 ed25519 算法 (优于 RSA)
- 密钥文件权限设置为 600

### 7.2 连接安全

- 禁用密码认证 (仅限密钥)
- 使用非标准端口 (可选)
- 配置 fail2ban 防止暴力破解
- 通过跳板机访问内网服务器

### 7.3 会话管理

- 设置合理的超时时间
- 使用心跳保持长连接
- 命令执行设置超时
- 正确关闭连接释放资源

---

## 版本历史

| 版本 | 日期 | 变更说明 |
|------|------|----------|
| 1.0 | 2026-01-14 | 初始版本 |
