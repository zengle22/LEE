# QA L3 模板解析技术债评估

## 结论

当前不建议在这轮把 QA L3 模板解析从手工映射彻底改成统一自动发现。

风险评估：中等。

建议处理方式：先保留现有修复，在文档中明确维护点，把这件事记为技术债，后续和 `TemplateManager` / workflow registry 的统一收口一起做。

## 当前实现

QA L3 spawn 现在依赖：

- `l3_template_id` 从 L2 phase metadata 透传
- `src/lee/orchestrator/execution/orchestrator.py` 中 `_resolve_l3_template_path()`

当前做法是：

- 先把 `template.qa.test_set_execute`、`template.qa.test_set_production` 这种逻辑 ID
- 映射成真实模板文件路径
- 再用这个真实路径去 `spawn_workflow`

这解决了一个真实故障：

- 临时项目或测试目录里没有完整 framework template registry 布局时
- 只传逻辑 ID 会让 runtime 找不到 QA 模板

## 为什么这轮不直接改成自动解析

表面上看，`config/workflow-registry.yaml` 已经有 QA workflow 条目，像是可以直接拿来解析。

但现在有三个结构性问题：

1. registry key 不是模板 ID  
   registry 里是 `qa.test-set-execution`，模板里真正写的是 `template.qa.test_set_execute`。两套命名空间还没有统一。

2. `TemplateManager` 的默认查找语义和 QA 模板布局并不完全一致  
   它支持直接文件路径、`template_dir/*.yaml`、`workflow.*` 风格 ID，但并不会天然理解 QA 这套逻辑 ID。

3. 当前修复已经把 child spawn 改成“按真实路径创建”  
   这保证了最小项目和测试环境可运行。如果继续抽象成自动发现，需要重新定义：
   - 优先查 registry 还是查磁盘
   - registry key 与模板 ID 怎么对齐
   - 缓存键到底按 workflow key、template id 还是 path

这些问题如果只在 QA 侧单独修，会把“局部便利”写进编排器核心，后面更难统一。

## 技术债内容

后续如果要清理这笔债，建议按下面顺序做：

1. 定义统一的模板标识规则  
   至少明确 workflow key、template id、磁盘路径三者的主从关系。

2. 给 runtime 提供统一解析入口  
   让 `orchestrator` 不再手写 QA/dev 模板映射。

3. 保留 path fallback  
   即使 registry 丢失或未同步，也要允许已解析出的真实路径直接 spawn。

4. 为新增模板补回归测试  
   至少覆盖：
   - registry 命中
   - path fallback
   - 临时项目运行
   - QA / dev 混合模板解析

## 触发重构的信号

出现以下任一情况时，说明这笔技术债值得优先处理：

- QA L3 模板数量继续增加
- 其他部门也开始复用同样的 `template.<dept>.*` 逻辑 ID
- 新模板接入时频繁忘记维护 `_resolve_l3_template_path()`
- 需要让外部项目按 registry 动态扩展 L3 模板
