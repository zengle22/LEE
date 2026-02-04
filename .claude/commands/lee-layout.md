---
description: Format articles with WeChat-safe styling
---

# Lee Layout Command

Execute the article layout script to format articles with WeChat-safe styling.

## Execution

Run the Python script:
```bash
python E:/ai/lee/spec-global/departments/media/commands/article-layout/v1/executor.py "{{file_path}}"
```

## Parameters

- `file_path`: Path to the article file (required)
- `--theme`: Theme choice (wechat_red_safe, blue, minimal)
- `--platform`: Target platform (wechat, xhs, notion, feishu, generic)
- `--format`: Output format (md, html, both)
