# Docker Deploy Skill v1.0
# Docker 部署技能 - 容器化应用部署与管理

## 概述

Docker Deploy 技能负责在云服务器上执行 Docker 容器部署。
支持 Docker Compose、单容器部署、镜像构建等多种模式。

## 技能标识

- **ID**: skill.test.docker_deploy
- **名称**: Docker Deploy
- **版本**: 1.0
- **所有者**: test-governance

## 适用 Agent

- agent.test.test_env_admin

---

## 1. 前置检查

### 1.1 Docker 环境验证

```yaml
prerequisites:
  - name: "Docker 已安装"
    command: "docker --version"
    expected: "Docker version"
    on_fail: "error: Docker 未安装"

  - name: "Docker 服务运行中"
    command: "docker info"
    expected: "Server Version"
    on_fail: "error: Docker 服务未启动，运行 systemctl start docker"

  - name: "Docker Compose 已安装"
    command: "docker-compose --version || docker compose version"
    expected: "version"
    on_fail: "warn: Docker Compose 未安装"
    required: false

  - name: "用户在 docker 组"
    command: "groups | grep docker"
    expected: "docker"
    on_fail: "warn: 用户不在 docker 组，可能需要 sudo"
```

### 1.2 资源检查

```yaml
resource_check:
  disk:
    min_available: "5GB"
    path: "/var/lib/docker"
    command: "df -h /var/lib/docker | tail -1 | awk '{print $4}'"

  memory:
    min_available: "1GB"
    command: "free -g | grep Mem | awk '{print $7}'"
```

---

## 2. 部署模式

### 2.1 Docker Compose 部署

```yaml
docker_compose:
  # 配置
  config:
    file: "docker-compose.test.yml"
    project_name: "{app_name}-test"
    env_file: ".env.test"

  # 部署命令
  commands:
    # 拉取最新镜像
    pull: "docker-compose -f {file} pull"

    # 启动服务 (后台)
    up: "docker-compose -f {file} -p {project_name} up -d"

    # 查看状态
    ps: "docker-compose -f {file} -p {project_name} ps"

    # 查看日志
    logs: "docker-compose -f {file} -p {project_name} logs --tail=100"

    # 停止服务
    down: "docker-compose -f {file} -p {project_name} down"

    # 重建并启动
    rebuild: "docker-compose -f {file} -p {project_name} up -d --build"

  # 部署流程
  deploy_steps:
    - step: "停止旧容器"
      command: "docker-compose -f {file} -p {project_name} down"
      ignore_error: true

    - step: "拉取最新镜像"
      command: "docker-compose -f {file} pull"
      timeout: 300

    - step: "启动服务"
      command: "docker-compose -f {file} -p {project_name} up -d"
      timeout: 120

    - step: "等待服务就绪"
      action: "wait_for_healthy"
      timeout: 60
```

### 2.2 单容器部署

```yaml
single_container:
  # 容器配置
  config:
    image: "{registry}/{image_name}:{tag}"
    container_name: "{app_name}-test"
    ports:
      - "8080:8080"
    volumes:
      - "{work_dir}/data:/app/data"
      - "{work_dir}/logs:/app/logs"
    env_file: ".env.test"
    restart: "unless-stopped"
    networks:
      - "test-network"

  # 部署命令
  commands:
    # 拉取镜像
    pull: "docker pull {image}"

    # 停止并删除旧容器
    remove: "docker stop {container_name} && docker rm {container_name}"

    # 运行新容器
    run: |
      docker run -d \
        --name {container_name} \
        -p {ports} \
        -v {volumes} \
        --env-file {env_file} \
        --restart {restart} \
        --network {network} \
        {image}

    # 查看日志
    logs: "docker logs {container_name} --tail=100"

    # 进入容器
    exec: "docker exec -it {container_name} /bin/sh"
```

### 2.3 镜像构建部署

```yaml
build_and_deploy:
  # 构建配置
  build:
    dockerfile: "Dockerfile"
    context: "."
    target: "production"  # 多阶段构建目标
    build_args:
      - "ENV=test"
      - "VERSION={version}"
    cache_from:
      - "{registry}/{image_name}:latest"

  # 构建命令
  commands:
    build: |
      docker build \
        -f {dockerfile} \
        -t {image_name}:{tag} \
        --target {target} \
        --build-arg ENV=test \
        --build-arg VERSION={version} \
        {context}

    # 推送到镜像仓库 (可选)
    push: "docker push {registry}/{image_name}:{tag}"

  # 完整流程
  steps:
    - "docker build -t {image_name}:{tag} ."
    - "docker stop {container_name} || true"
    - "docker rm {container_name} || true"
    - "docker run -d --name {container_name} {image_name}:{tag}"
```

---

## 3. 容器健康检查

### 3.1 等待容器就绪

```yaml
wait_for_healthy:
  # 检查容器状态
  container_health:
    command: "docker inspect --format='{{.State.Health.Status}}' {container_name}"
    expected: "healthy"
    interval: 5
    timeout: 60
    retries: 12

  # 检查端口监听
  port_check:
    command: "docker exec {container_name} netstat -tlnp | grep {port}"
    timeout: 30

  # 检查日志关键字
  log_check:
    command: "docker logs {container_name} 2>&1 | grep -i 'started\\|ready\\|listening'"
    timeout: 30
```

### 3.2 服务健康检查

```yaml
service_health:
  # HTTP 检查
  http:
    url: "http://localhost:{port}/health"
    expected_status: [200, 204]
    timeout: 10
    retries: 3

  # 数据库连接检查
  database:
    command: "docker exec {db_container} pg_isready -U {db_user}"
    expected: "accepting connections"
```

---

## 4. 日志管理

### 4.1 日志采集

```yaml
logging:
  # 查看实时日志
  tail:
    command: "docker logs -f {container_name}"
    lines: 100

  # 导出日志到文件
  export:
    command: "docker logs {container_name} > {log_path} 2>&1"
    path: "output/logs/{container_name}-{timestamp}.log"

  # 按时间范围查看
  since:
    command: "docker logs --since {since} {container_name}"
    since: "1h"  # 最近 1 小时
```

### 4.2 日志配置

```yaml
log_config:
  # Docker 日志驱动
  driver: "json-file"
  options:
    max-size: "100m"
    max-file: "3"

  # 在 docker-compose 中配置
  compose_config: |
    logging:
      driver: json-file
      options:
        max-size: "100m"
        max-file: "3"
```

---

## 5. 网络管理

### 5.1 创建网络

```yaml
network:
  create:
    name: "test-network"
    driver: "bridge"
    command: "docker network create --driver bridge test-network"

  connect:
    command: "docker network connect test-network {container_name}"

  inspect:
    command: "docker network inspect test-network"
```

### 5.2 端口映射

```yaml
port_mapping:
  # 标准映射
  standard: "{host_port}:{container_port}"

  # 仅本地访问
  localhost_only: "127.0.0.1:{host_port}:{container_port}"

  # 范围映射
  range: "{start}-{end}:{start}-{end}"
```

---

## 6. 数据卷管理

### 6.1 挂载配置

```yaml
volumes:
  # 绑定挂载 (本地目录)
  bind:
    - source: "{work_dir}/data"
      target: "/app/data"
      read_only: false

  # 命名卷
  named:
    - name: "{app_name}-data"
      target: "/app/data"

  # 临时文件系统
  tmpfs:
    - target: "/tmp"
      size: "100m"
```

### 6.2 数据备份

```yaml
backup:
  # 备份数据卷
  volume:
    command: |
      docker run --rm \
        -v {volume_name}:/source:ro \
        -v {backup_dir}:/backup \
        alpine tar czf /backup/{volume_name}-{timestamp}.tar.gz -C /source .

  # 恢复数据卷
  restore:
    command: |
      docker run --rm \
        -v {volume_name}:/target \
        -v {backup_dir}:/backup:ro \
        alpine tar xzf /backup/{backup_file} -C /target
```

---

## 7. 清理策略

### 7.1 自动清理

```yaml
cleanup:
  # 清理停止的容器
  containers:
    command: "docker container prune -f"

  # 清理未使用的镜像
  images:
    command: "docker image prune -f"

  # 清理未使用的卷
  volumes:
    command: "docker volume prune -f"

  # 全面清理 (谨慎使用)
  all:
    command: "docker system prune -f"
    exclude_volumes: true
```

### 7.2 保留策略

```yaml
retention:
  # 保留最近 N 个版本的镜像
  images:
    keep: 3
    pattern: "{image_name}:*"

  # 保留最近 N 天的日志
  logs:
    keep_days: 7
```

---

## 8. 错误处理

```yaml
error_handling:
  image_not_found:
    message: "镜像不存在: {image}"
    action: "尝试拉取或检查镜像名称"

  port_in_use:
    message: "端口 {port} 已被占用"
    action: "停止占用进程或更换端口"

  container_crash:
    message: "容器启动后立即退出"
    action: "查看容器日志: docker logs {container_name}"

  out_of_memory:
    message: "容器内存不足被 OOM Kill"
    action: "增加容器内存限制或优化应用"

  volume_permission:
    message: "卷挂载权限错误"
    action: "检查目录权限和 SELinux 配置"
```

---

## 9. 最佳实践

### 9.1 镜像管理

- 使用具体版本标签，避免 `:latest`
- 使用多阶段构建减少镜像体积
- 定期清理未使用的镜像
- 使用私有镜像仓库

### 9.2 容器配置

- 不以 root 用户运行容器
- 设置合理的资源限制 (CPU/内存)
- 使用健康检查
- 配置日志轮转

### 9.3 部署策略

- 总是先停止再删除旧容器
- 部署前创建备份
- 使用 `--restart=unless-stopped`
- 测试环境使用独立网络

---

## 版本历史

| 版本 | 日期 | 变更说明 |
|------|------|----------|
| 1.0 | 2026-01-14 | 初始版本 |
