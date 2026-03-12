# Src-to-Epic 部署说明

这不是独立服务栈部署，而是 `workflow.product.task.src_to_epic` 的独立运行配置。

## 运行

```powershell
./run.ps1 -ProjectDir E:\ai\LEE -SpecPath E:\ai\LEE\output\design-frozen\LEE-src-freeze.yaml
```

## 健康检查

```powershell
python -m lee.cli.main workflow-registry health --layer src-to-epic --project-dir E:\ai\LEE --input-path E:\ai\LEE\output\design-frozen\LEE-src-freeze.yaml
```

健康项：

- workflow template 已注册
- template 引用的 contract 可解析
- 输入对象是 canonical `SRC` 或 `source_freeze`

## 故障隔离验证

- `raw-to-src` 失败时，只要已有 `SRC` 或 `source_freeze` 存在，`src-to-epic` 仍可单独运行
- `src-to-epic` 失败不会回滚已落盘的 canonical `SRC`

## 回滚

- 停止新的 `product.src-to-epic` 运行
- 回退 `config/workflow-registry.yaml`
- 回退 `spec-global/departments/product/workflows/templates/src-to-epic/v1/workflow.yaml`
