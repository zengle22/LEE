# 规格 SSOT（可 gate、可冻结）

**Config Key**: `spec_dir`  
**Structure**: `flat`  
**Naming**: `default`

## Subdirectories

- `requirements/`
- `api/`
- `data/`
- `ui/`
- `adr/`


## Gate Workflow

本目录下的规格文档需要经过 gate 流程才能冻结：
1. 创建规格草稿
2. 提交 gate 审查
3. 冻结后变为只读
