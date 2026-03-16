# Evidence Pack Packaging Rules

1. 所有 Evidence Pack 必须包含 `evidence-manifest.yaml`
2. 必须存在以下子目录：
   - `code-diff/`
   - `test-reports/`
   - `review-records/`
   - `deployment-records/`
   - `integration-report/`
3. 目录中至少保留 README 或示例占位文件，说明证据来源与命名规则
4. 证据命名优先使用 `formal_ssot_id` 作为前缀
5. Integration report 和 review records 必须能追溯到上游 source refs
