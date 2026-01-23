# Strategy Department (STG) - 策略部门

## 部门职责

负责市场洞察、商业机会发现、战略分析。通过系统化的流程，将模糊的市场信号转化为可验证的商业机会假设，并交付给产品部门进行验证。

---

## 核心工作流：商业机会发现

### 一句话描述
> **这是一个"可冻结、可复盘、可移交"的需求发现流水线**

### 5 层架构

```
Layer 1: Search Agent      (事实采集层)
  └─ 输出: 搜索信号数据

Layer 2: Analysis Agents   (分析层)
  ├─ User Signal Agent         (谁在搜 & 为什么)
  ├─ Industry Structure Agent  (行业处在哪)
  └─ Supply/Competition Agent  (方案解决得如何)

Layer 3: Market Freeze      (冻结层) 🔒
  └─ 输出: 冻结的市场信号 (系统稳定性根)

Layer 4: Business Opportunity (机会构建层)
  └─ 输出: 可验证的商业机会假设

Layer 5: Product Handoff    (交付层)
  └─ 输出: 标准产品交付文档
```

---

## 已创建的 Spec 文件

### Agents (5个)
- ✅ search_agent - 搜索采集 Agent
- ✅ user_signal_agent - 用户信号分析 Agent
- ✅ industry_structure_agent - 行业结构分析 Agent
- ✅ supply_competition_agent - 供给竞争分析 Agent
- ✅ business_opportunity_agent - 商业机会构建 Agent

### Contracts (2个)
- ✅ market_signal_freeze - 市场信号冻结契约
- ✅ product_handoff - 产品交付模板

### Workflows (1个)
- ✅ opportunity_discovery - 商业机会发现工作流

---

## 核心原则

1. **分析必须在 freeze 层收敛**
2. **机会必须在 handoff 层"对产品部门负责"**
3. **只能引用，不可推翻**
4. **诚实呈现风险**

更多详情请参考各层级的 spec 文件。
