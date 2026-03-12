# Raw-to-Src 部署说明

这不是独立服务栈部署，而是 `workflow.product.task.raw_to_src` 的独立运行配置。

## 运行

```powershell
./run.ps1 -ProjectDir E:\ai\LEE -SpecPath E:\ai\LEE\spec\adr\ADR-012__raw-to-src-yu-src-to-epic-fencengchaifen.md
```

## 健康检查

```powershell
python -m lee.cli.main workflow-registry health --layer raw-to-src --project-dir E:\ai\LEE
```

健康项：

- workflow template 已注册
- template 引用的 contract 可解析
- raw 层无需预置 canonical SRC 输入

## 回滚

- 停止新的 `product.raw-to-src` 运行
- 回退 `config/workflow-registry.yaml`
- 回退 `spec-global/departments/product/workflows/templates/raw-to-src/v1/workflow.yaml`

## 联合部署

- `raw-to-src` 可独立运行
- 若需要联动完整主链，继续执行 `product.main`
