"""
Mock LLM Executor - 用于测试和开发

当真实 LLM API 不可用时，返回预定义的模拟响应。
"""

from typing import Dict, Any

MOCK_RESPONSES = {
    "agent.devops.architect": r"""# Infrastructure Architecture Design

=== infra-architecture.yaml ===
```yaml
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

  postgres:
    type: database
    image: postgres:16-alpine
    port: 5432

  mongo:
    type: database
    image: mongo:7.0
    port: 27017

  redis:
    type: cache
    image: redis:7-alpine
    port: 6379
```

=== env-matrix.yaml ===
```yaml
environments:
  dev:
    replicas: 1
    resources:
      cpu: "500m"
      memory: "512Mi"

  prod:
    replicas: 3
    resources:
      cpu: "4000m"
      memory: "4Gi"
```

=== release-strategy.md ===
```markdown
# Release Strategy

## Deployment Steps
1. Deploy to staging
2. Run smoke tests
3. Gradual traffic shift

## Rollback Plan
- Trigger: Error rate > 5%
- Procedure: ./rollback.sh <version>
```
""",

    "agent.devops.infra_engineer": r"""=== docker-compose.prod.yml ===
```yaml
version: '3.8'
services:
  backend:
    image: ${REGISTRY}/ai-marathon-coach-server:${VERSION}
    ports:
      - "8081:8081"
    env_file:
      - .env.prod
```

=== cicd/github-actions/ci.yml ===
```yaml
name: CI/CD
on: [push]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - run: go test ./...
```
""",

    "agent.devops.verifier": r"""=== deployment-checklist.md ===
```markdown
# Deployment Verification Checklist

## Post-deployment Checks
- [x] Backend API responding
- [x] Frontend loading correctly
- [x] Database connections healthy
```

=== release-manifest.yaml ===
```yaml
release:
  version: "1.0.0"
  date: "2026-01-31"
  artifacts:
    backend:
      image: ai-marathon-coach-server:1.0.0
```
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
            "# Mock Response\n\nThis is a test response."
        )

        return {
            "generated_text": response_text,
            "model": "mock-model",
            "provider": "mock",
            "tokens_used": len(response_text.split()),
            "status": "completed",
        }
