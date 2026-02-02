"""
Mock LLM Executor - 用于测试和开发

当真实 LLM API 不可用时，返回预定义的模拟响应。
"""

from typing import Dict, Any

MOCK_RESPONSES = {
    "agent.devops.architect": """# Infrastructure Architecture Design

## infra-architecture.yaml
\`\`\`yaml
# AI Marathon Coach - Infrastructure Architecture
version: "1.0"
environment: dev

components:
  backend:
    type: service
    image: ai-marathon-coach-server:latest
    ports:
      - "8081:8081"
    environment:
      - SERVER_PORT=8081
      - DB_HOST=postgres
      - DB_PORT=5432
    depends_on:
      - postgres
      - mongo
      - redis

  frontend:
    type: static
    path: ./dist
    port: 3002

  postgres:
    type: database
    image: postgres:16-alpine
    port: 5432
    volumes:
      - postgres-data:/var/lib/postgresql/data

  mongo:
    type: database
    image: mongo:7.0
    port: 27017
    volumes:
      - mongo-data:/data/db

  redis:
    type: cache
    image: redis:7-alpine
    port: 6379
\`\`\`

## env-matrix.yaml
\`\`\`yaml
environments:
  dev:
    replicas: 1
    resources:
      cpu: "500m"
      memory: "512Mi"
    auto_scaling: false

  test:
    replicas: 1
    resources:
      cpu: "1000m"
      memory: "1Gi"
    auto_scaling: false

  staging:
    replicas: 2
    resources:
      cpu: "2000m"
      memory: "2Gi"
    auto_scaling: true

  prod:
    replicas: 3
    resources:
      cpu: "4000m"
      memory: "4Gi"
    auto_scaling: true
\`\`\`

## release-strategy.md
\`\`\`markdown
# Release Strategy

## Rollback Plan

### Pre-deployment Checks
- [ ] Database backup completed
- [ ] All services healthy
- [ ] Configuration validated

### Deployment Steps
1. Deploy new version to staging
2. Run smoke tests
3. Gradual traffic shift (25% -> 50% -> 100%)
4. Monitor metrics for 30 minutes

### Rollback Triggers
- Error rate > 5%
- Response time P95 > 2s
- Any critical service failure

### Rollback Procedure
```bash
cd devops
./rollback.sh staging <version>
```
\`\`\`
""",

    "agent.devops.infra_engineer": """# IaC and CI/CD Implementation

## Docker Compose (prod)

\`\`\`yaml
version: '3.8'

services:
  backend:
    image: \\${REGISTRY}/ai-marathon-coach-server:\\${VERSION}
    ports:
      - "8081:8081"
    environment:
      - SERVER_ENV=production
      - MONGODB_URI=mongodb://mongo:27017
      - POSTGRES_HOST=postgres
      - POSTGRES_PORT=5432
    env_file:
      - .env.prod
    depends_on:
      - mongo
      - postgres
      - redis
    restart: always
\`\`\`

## GitHub Actions CI/CD

\`\`\`yaml
name: CI/CD Pipeline

on:
  push:
    branches: [main]
  pull_request:

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Run tests
        run: |
          cd backend
          go test ./...
          cd ../frontend
          npm test

  build:
    needs: test
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Build Docker images
        run: |
          docker build -t app:\\${{ github.sha }} .
          docker push app:\\${{ github.sha }}

  deploy:
    needs: build
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
    steps:
      - name: Deploy to staging
        run: |
          kubectl set image deployment/app app=app:\\${{ github.sha }}
\`\`\`
""",

    "agent.devops.verifier": """# Deployment Verification Checklist

## deployment-checklist.md
\`\`\`markdown
# Deployment Verification Checklist

## Pre-deployment
- [ ] Code review completed
- [ ] All tests passing
- [ ] Security scan passed
- [ ] Performance benchmarks met

## Post-deployment
- [ ] Backend API responding
- [ ] Frontend loading correctly
- [ ] Database connections healthy
- [ ] Redis cache working
- [ ] No errors in logs (last 15 min)

## Release Manifest

### Release: v1.0.0
- Date: 2026-01-31
- Commit: abc123
- Artifacts:
  - ai-marathon-coach-server:1.0.0
  - ai-marathon-coach-front:1.0.0
\`\`\`

## release-manifest.yaml
\`\`\`yaml
release:
  version: "1.0.0"
  date: "2026-01-31"
  commit: "abc123"

artifacts:
  backend:
    image: ai-marathon-coach-server:1.0.0
    digest: "sha256:..."

  frontend:
    image: ai-marathon-coach-front:1.0.0
    digest: "sha256:..."

rollback:
  previous_version: "0.9.0"
  rollback_script: "devops/rollback.sh"
\`\`\`
""",
}


class MockLLMExecutor:
    """Mock LLM Executor for testing"""

    def __init__(self, agent_id: str = ""):
        self.agent_id = agent_id

    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """返回模拟响应"""
        # 根据 agent_id 返回对应的模拟响应
        response_text = MOCK_RESPONSES.get(
            self.agent_id,
            "# Mock Response\n\nThis is a test response from the Mock LLM Executor."
        )

        return {
            "generated_text": response_text,
            "model": "mock-model",
            "provider": "mock",
            "tokens_used": len(response_text.split()),
            "status": "completed",
        }
