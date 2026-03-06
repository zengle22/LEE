# SSOT 文档 ID/命名/引用管理系统升级方案

> **Single Source of Truth (SSOT)** - 单一事实源
> **Artifact Identity & Trace Foundation** - 产物身份与追踪基础设施

> **版本**: V1.3 (实施规格版)
> **状态**: 实施待批准
> **创建日期**: 2026-03-06
> **最后更新**: 2026-03-06

---

## 一、背景与目标

### 当前系统状态

现有 SSOT 系统已实现：
- **ArtifactType (8 种)**: CONTRACT, DOCUMENT, CODE_REF, PATCH, TEST, HANDOVER, LOG, INTERMEDIATE
- **ID 格式**: `ART-{sequence:05d}` (例如：ART-00001)
- **文件命名**: `{artifact_id}.{ext}` (例如：ART-00001.md)
- **元数据**: id, type, category, status, path, derived_from, implements, verifies 等
- **Registry**: 内存索引 + .registry.json 持久化
- **校验规则 (3 条)**:
  1. api_contract 必须有 derived_from 指向 prd_contract
  2. implementation 必须有 implements 指向 api_contract
  3. test_plan 必须有 verifies 指向 PRD 或 API

### 升级目标

根据用户提供的**SSOT 文档身份系统设计方案**，需要升级：

1. **新的对象类型系统** (12 种): SRC, EPIC, FEAT, UI, TECH, TASK, TESTSET, TC, BUG, REPORT, ADR, EVI
2. **新的 ID 规则**: 类型前缀 + 序号，父子关系体现在 ID 中
3. **新的文件命名规则**: `[ID]__[slug].[ext]`
4. **新的 metadata 规范**: id, type, title, status, version, derived_from, source_refs, related_ids, verifies, implements 等
5. **新的校验规则 (P0)**: ID 唯一性、路径唯一性、Metadata 完整性、类型合法性、引用存在性、文件名与 ID 一致性

---

## 架构决策 (V1.3)

### 单主键策略

**决策**: 新体系正式对象统一使用 `SSOT ID` 作为主键。

- 新体系正式对象直接以 `SSOT ID` (如 `FEAT-001`) 作为主 ID
- 历史 `ART-*` 只做兼容读取，不作为未来主路径
- 后续新增正式对象不再分配 `ART-*`

### 目录边界策略

**决策**: 目录层与身份层分离，避免双重事实源。

- `dirs.yaml` / `PathConfig` 只负责目录拓扑与落盘位置，不再定义正式对象文件名
- SSOT identity 负责 `id`、`type`、`slug`、最终文件名 `[ID]__[slug].[ext]`
- 最终路径由两段组成：`placement_dir + ssot_filename`
- `knowledge/` 目录用于 Agent 复盘、模式沉淀、能力演进，不参与正式对象命名规则

### ID 分类体系 (4 类)

| 类别 | 类型 | ID 格式 | 说明 |
|------|------|---------|------|
| 独立顺序型 | SRC, EPIC, FEAT, ADR | `TYPE-001` | 全局独立序号 |
| 单父唯一型 | TECH, TESTSET | `TYPE-FEAT-001` | 每个 FEAT 下唯一 |
| 单父多实例型 | UI, TASK | `TYPE-FEAT-001-01` | 每个 FEAT 下多个实例 |
| 时态/运行型 | REPORT | `TYPE-FEAT-001-YYYYMMDD` | 带日期标识 |
| 范围归属型 | TC, BUG, EVI | `TYPE-FEAT-001-XXX` | ID 体现 FEAT 范围，parent_id 指向结构父对象 |

### 关系语义分层

| 字段 | 语义 | 约束 |
|------|------|------|
| `parent_id` | 结构归属关系，单值，用于 ID 生成和目录归属 | 部分类型必填 |
| `derived_from` | 派生来源关系，多值，用于业务追踪和设计来源 | 多值 |
| `source_refs` | 源文档锚点，如 `SRC-001#3.2` | 多值，P0 只校验 base id |
| `related_ids` | 横向关联对象 | 多值 |

### 对象类型分类 (关键)

**两类对象，两种校验规则**:

| 分类 | 类型 | ID 特征 | parent_id 规则 | 校验规则 |
|------|------|---------|---------------|----------|
| **直接父对象一致型** | TECH, TESTSET, UI, TASK, REPORT | ID 中直接体现 parent | `parse_parent(id) == parent_id` | 严格一致 |
| **范围归属型** | TC, BUG, EVI | ID 体现 FEAT 范围 | `parse_scope(id) == resolve_scope(parent_id)` | 范围一致 |

---

## 二、新系统核心设计

### 2.1 新对象类型 (12 种)

| 对象类型 | 前缀 | 用途 | ID 格式示例 | parent_id 必填 | 类型分类 |
|---------|------|------|-------------|---------------|----------|
| SRC | SRC | 原始需求来源 | SRC-001 | ❌ | 独立型 |
| EPIC | EPIC | 较大的业务目标集合 | EPIC-001 | ❌ | 独立型 |
| FEAT | FEAT | 最小可独立验收业务单元 | FEAT-001 | ❌ | 独立型 |
| UI | UI | UI 原型/交互设计 | UI-FEAT-001-01 | ✅ (FEAT) | 直接父对象一致型 |
| TECH | TECH | 技术设计 | TECH-FEAT-001 | ✅ (FEAT) | 直接父对象一致型 |
| TASK | TASK | 实施任务 | TASK-FEAT-001-FE-01 | ✅ (FEAT) | 直接父对象一致型 |
| TESTSET | TESTSET | 测试集 | TESTSET-FEAT-001 | ✅ (FEAT) | 直接父对象一致型 |
| TC | TC | 测试用例 | TC-FEAT-001-001 | ✅ (TESTSET) | **范围归属型** |
| BUG | BUG | 缺陷 | BUG-FEAT-001-001 | ✅ (FEAT 或 TC) | **范围归属型** |
| REPORT | REPORT | 测试/验收/分析报告 | REPORT-FEAT-001-20260306 | ✅ (FEAT) | 直接父对象一致型 |
| ADR | ADR | 架构或业务决策 | ADR-001 | ❌ | 独立型 |
| EVI | EVI | 证据包/附件证据 | EVI-FEAT-001-001 | ✅ (FEAT/TC/BUG/TASK/TECH/REPORT) | **范围归属型** |

> **注**: 
> - 首版只允许 `ADR`，`DEC` 作为别名但不进入正式 ID 系统
> - `parent_id` 必填类型若缺失则 P0 校验失败
> - **范围归属型**对象的 ID 体现 FEAT 范围，但 parent_id 可指向更细粒度的结构父对象

### 2.2 层级关系

```
SRC / EPIC
   ↓
FEAT
   ↓
UI / TECH / TASK / TESTSET
   ↓
TC / BUG / REPORT / EVI
```

**强制结构**:
```
FEAT
  └ TESTSET
      └ TC
```

### 2.3 ID 规则设计

**基础格式**: `<PREFIX>-<IDENTIFIER>`

#### 独立顺序型
- `SRC-001`, `EPIC-001`, `FEAT-001`, `ADR-001`

#### 单父唯一型
- `TECH-FEAT-001` (每个 FEAT 下唯一)
- `TESTSET-FEAT-001` (每个 FEAT 下唯一)

#### 单父多实例型
- `UI-FEAT-001-01` (UI 引用 FEAT)
- `TASK-FEAT-001-FE-01` (TASK 引用 FEAT，子域 FE)

#### 时态/运行型
- `REPORT-FEAT-001-20260306` (带日期，**统一格式**)

#### 范围归属型
- `TC-FEAT-001-001` (测试用例，**parent_id 必须为 TESTSET**)
- `BUG-FEAT-001-001` (缺陷，parent_id 可为 FEAT 或 TC)
- `EVI-FEAT-001-001` (证据，parent_id 可为多种类型)

**约束**:
- ID 全局唯一
- Prefix 必须来自受控枚举 (首版只允许 `ADR`，`DEC` 作为别名不进入正式 ID)
- 除运行/时态对象 (REPORT) 外，不把日期混进核心主键
- ID 必须可解析 (必须能通过 IDParser 正确解析)

### 2.4 文件命名规则

**格式**: `[ID]__[slug].[ext]`

> **边界说明**: 本节定义的是正式 SSOT 对象文件名规则。目录层只能决定放到哪个目录，不能覆盖此命名规则。

**示例**:
```
FEAT-023__generate-weekly-plan.md
TECH-FEAT-023__weekly-plan-design.md
TESTSET-FEAT-023__weekly-plan.yaml
TC-FEAT-023-001__missing-goal-validation.yaml
```

**Slug 生成算法 (固定顺序)**:

```
输入：title (字符串), 可选显式 slug

步骤:
1. 若显式提供 slug，使用该 slug；否则从 title 生成
2. 中文字符转拼音 (使用 pinyin 库)
3. 全量转小写
4. 非 [a-z0-9] 字符替换为 -
5. 合并连续 - 为单个 -
6. 去除首尾 -
7. 截断至 50 字符
8. 若为空，回退为 "untitled"

输出：slug 字符串
```

**示例**:
```
"生成首版周训练计划" → "sheng-cheng-shou-ban-zhou-xun-lian-ji-hua"
"Generate Weekly Plan" → "generate-weekly-plan"
"用户管理模块 (后端)" → "yong-hu-guan-li-mo-kuai-hou-duan"
```

- 单词间用 `-`
- 允许后续修改（修改后同步更新 registry.path）

### 2.5 Metadata 规范

**必填字段**:
```yaml
id: FEAT-023
type: feature
title: 生成首版周训练计划
status: active
```

**推荐字段**:
```yaml
version: v1
parent_id: EPIC-002              # 结构归属关系，单值
derived_from:                    # 派生来源关系，多值
  - EPIC-002
source_refs:                    # 源文档锚点
  - SRC-001#3.2
related_ids:                    # 横向关联
  - UI-FEAT-023-01
  - TECH-FEAT-023
verifies: []
implements: []
owner: product
tags:
  - training-plan
  - mvp
last_updated: "2026-03-06T10:00:00Z"  # ISO8601 字符串
```

**字段语义**:
- `parent_id`: 结构归属关系，单值，用于 ID 生成和目录归属 (**部分类型必填**)
- `derived_from`: 派生来源关系，多值，用于业务追踪
- `source_refs`: 源文档锚点，如 `SRC-001#3.2` (**P0 只校验 base id**)
- `related_ids`: 横向关联对象

### 2.5.1 文件重命名策略

当 title / slug 改变时的处理规则：

- `id` 不变时，允许重命名文件
- 重命名只允许修改 `slug` 段，不允许修改 `id` 段
- 重命名后必须同步更新 registry.path
- 文档关系不受影响，因为关系只认 ID

### 2.6 状态机与版本管理

```
draft → active → frozen → archived
                   ↘ deprecated
```

**状态语义**:
- `draft`: 草稿态，可频繁修改
- `active`: 当前有效版本，参与正式链路
- `frozen`: 已冻结，作为 gate、发布，回放依据
- `archived`: 历史归档，不再参与现行链路
- `deprecated`: 已废弃，但保留引用历史

**版本与状态关系**:
| 状态 | 版本规则 |
|------|----------|
| `draft` | version 可自由变更 |
| `active` | version 递增，允许修改；**同一 ID 的不同版本实例中，只允许一个处于 active 状态** |
| `frozen` | **version 不可变更** (冻结后版本固定) |
| `archived` | version 不可变更 |
| `deprecated` | version 不可变更 |

> **重要**: 
> - `frozen` 对象的 version 不能改变。若需修改，必须创建新版本 (v2) 并设为 `active`，原版本保持 `frozen`。
> - 同一 ID 的不同版本实例中，只允许一个 `active` 版本，避免多版本并存歧义。例如：`FEAT-001` 的 `v1` 和 `v2` 共享同一 ID，但同一时刻只能有一个为 `active`。

### 2.7 层级关系设计

#### 强约束层 (P0 Blocking)

| 类型 | parent_id 规则 | 类型分类 |
|------|---------------|----------|
| `SRC` | 可选 | 独立型 |
| `EPIC` | 可选 | 独立型 |
| `FEAT` | 可选 (若存在，必须为 `EPIC`；`SRC` 应使用 `source_refs` 指向) | 独立型 |
| `UI` | **必填**，必须为 `FEAT` | 直接父对象一致型 |
| `TECH` | **必填**，必须为 `FEAT` | 直接父对象一致型 |
| `TASK` | **必填**，必须为 `FEAT` | 直接父对象一致型 |
| `TESTSET` | **必填**，必须为 `FEAT` | 直接父对象一致型 |
| `TC` | **必填**，必须为 `TESTSET` | **范围归属型** |
| `BUG` | **必填**，必须为 `FEAT` 或 `TC` | **范围归属型** |
| `REPORT` | **必填**，必须为 `FEAT` | 直接父对象一致型 |
| `EVI` | **必填**，必须为 `FEAT`/`TC`/`BUG`/`TASK`/`TECH`/`REPORT` | **范围归属型** |
| `ADR` | 可选 | 独立型 |

> **注**: `REPORT.parent_id = FEAT` 意味着 REPORT 不是测试执行树的直接节点。报告与测试集的关系应通过 `related_ids` 或 `verifies` 在 metadata 中建立。

#### 推荐层 (P1 Warning)

- 建议 FEAT 有明确上游来源 (EPIC 或 SRC)
- 建议 TECH/TESTSET 关联 FEAT
- 建议 TC 关联 TESTSET (已通过 P0 强制)

### 2.8 P0 校验规则

#### P0 Blocking (必须通过)

| 规则编号 | 规则名称 | 描述 |
|---------|---------|------|
| 1 | ID 唯一性 | 同一 workspace 中不得有重复 ID |
| 2 | 路径唯一性 (active) | 一个 path 只能对应一个 active 对象 |
| 3 | Metadata 完整性 | id/type/title/status 必填 |
| 4 | 类型合法性 | type 必须在受控枚举中 |
| 5 | 引用存在性 | derived_from/related_ids/verifies/implements 中的 ID 必须存在 |
| 6 | 文件名与 ID 一致性 | 文件名左侧 ID 与头部 id 必须相同 |
| 7 | ID 格式合法且可解析 | ID 必须符合所属类型的格式规范，并可被 IDParser 正确解析 |
| 8 | **直接父对象一致型**: `parse_parent(id) == parent_id` | 适用于 TECH, TESTSET, UI, TASK, REPORT |
| 9 | **范围归属型**: `parse_scope(id) == resolve_scope(parent_id)` | 适用于 TC, BUG, EVI |
| 10 | **parent_id 必填检查** | 必填类型若缺失 parent_id 则失败 |
| 11 | **TC 结构强制** | `TC.parent_id 必须为 TESTSET` |

#### P1 Warning (建议通过)

| 规则编号 | 规则名称 | 描述 |
|---------|---------|------|
| 12 | 父子类型推荐关系检查 | 检查 parent_id 类型是否符合推荐关系 |
| 13 | 孤儿对象检查 | 无上游、无下游且非根对象发出警告 |
| 14 | slug 规范检查 | slug 长度、字符规范检查 |

---

## 三、Registry 索引结构

### 索引字段定义

Registry 必须维护以下索引以支持 O(1) 查找：

```python
class SSOTRegistry:
    def __init__(self):
        # 主索引：id → ArtifactMetadata
        self.id_index: Dict[str, ArtifactMetadata] = {}
        
        # 类型索引：type → List[id]
        self.type_index: Dict[str, List[str]] = {}
        
        # 父索引：parent_id → List[id]
        self.parent_index: Dict[str, List[str]] = {}
        
        # 路径索引：path → id
        self.path_index: Dict[str, str] = {}
        
        # 状态索引：status → List[id]
        self.status_index: Dict[str, List[str]] = {}
        
        # 关系索引 (P0 简化版): id → List[related_id]
        # 重要说明:
        # - P0 阶段将 derived_from, related_ids, verifies, implements 合并存储
        # - 此索引仅作辅助查询，不保留关系类型语义
        # - 关系语义判断必须读取 metadata 原字段 (derived_from, related_ids, verifies, implements)
        # - P1 建议升级为带关系类型的边索引：Dict[str, Dict[str, List[str]]]
        #   格式：from_id -> { relation_type -> [to_id...] }
        self.relation_index: Dict[str, List[str]] = {}
```

### 索引操作

```python
# 添加对象
registry.add(artifact)

# 移除对象
registry.remove(artifact_id)

# 按 ID 查询
artifact = registry.get_by_id("FEAT-001")

# 按类型查询
artifacts = registry.get_by_type("feature")

# 按父 ID 查询
children = registry.get_by_parent("FEAT-001")

# 按路径查询
artifact = registry.get_by_path("/path/to/file.md")

# 按状态查询
active = registry.get_by_status("active")

# 重建索引
registry.rebuild()
```

---

## 四、ID 解析规则 (核心)

### 4.1 两类对象的解析策略

**关键区分**:

| 分类 | 类型 | 解析函数 | 校验规则 |
|------|------|---------|---------|
| **直接父对象一致型** | TECH, TESTSET, UI, TASK, REPORT | `parse_parent(id)` | `parse_parent(id) == parent_id` |
| **范围归属型** | TC, BUG, EVI | `parse_scope(id)` | `parse_scope(id) == resolve_scope(parent_id)` |

### 4.2 parse_parent 函数 (直接父对象一致型)

```python
def parse_parent(id: str) -> Optional[str]:
    """
    从 ID 中解析直接父对象 ID
    
    适用于：TECH, TESTSET, UI, TASK, REPORT
    
    规则:
    - TECH-FEAT-001 → FEAT-001
    - TESTSET-FEAT-001 → FEAT-001
    - UI-FEAT-001-01 → FEAT-001
    - TASK-FEAT-001-FE-01 → FEAT-001
    - REPORT-FEAT-001-20260306 → FEAT-001
    """
    parts = id.split('-')
    
    if len(parts) < 2:
        return None
    
    prefix = parts[0]
    
    # 独立型：无 parent
    if prefix in ('SRC', 'EPIC', 'FEAT', 'ADR'):
        return None
    
    # 范围归属型：不应使用此函数
    if prefix in ('TC', 'BUG', 'EVI'):
        raise ValueError(f"{id} 是范围归属型对象，应使用 parse_scope()")
    
    # 直接父对象一致型
    if prefix in ('TECH', 'TESTSET', 'UI', 'TASK', 'REPORT'):
        # TYPE-FEAT-001[-*] → FEAT-001
        if len(parts) >= 3:
            return f"{parts[1]}-{parts[2]}"
        return None
    
    return None
```

### 4.3 parse_scope 函数 (范围归属型)

```python
def parse_scope(id: str) -> Optional[str]:
    """
    从 ID 中解析归属范围 (FEAT)
    
    适用于：TC, BUG, EVI
    
    规则:
    - TC-FEAT-001-001 → FEAT-001
    - BUG-FEAT-001-001 → FEAT-001
    - EVI-FEAT-001-001 → FEAT-001
    """
    parts = id.split('-')
    
    if len(parts) < 3:
        return None
    
    prefix = parts[0]
    
    # 范围归属型：TYPE-FEAT-XXX-SEQ
    if prefix in ('TC', 'BUG', 'EVI'):
        # 返回 FEAT-XXX
        return f"{parts[1]}-{parts[2]}"
    
    return None
```

### 4.4 resolve_scope 函数

```python
def resolve_scope(parent_id: str) -> Optional[str]:
    """
    从 parent_id 解析归属范围
    
    P0 阶段规则:
    - 只支持已知类型的单跳解析，不支持无限递归链
    - 若 parent_id 是 FEAT，直接返回
    - 若 parent_id 是 TC/BUG/TECH/TASK/TESTSET/UI/REPORT，按已知规则解析到 FEAT
    - 超出已知类型则返回 None
    
    已知类型白名单:
    - FEAT: 直接返回
    - TC, BUG, EVI: TYPE-FEAT-XXX-SEQ → FEAT-XXX
    - TECH, TESTSET, UI, TASK, REPORT: TYPE-FEAT-XXX → FEAT-XXX
    """
    if not parent_id:
        return None
    
    parts = parent_id.split('-')
    prefix = parts[0]
    
    # 直接是 FEAT
    if prefix == 'FEAT':
        return f"{parts[1]}-{parts[2]}" if len(parts) >= 3 else parent_id
    
    # 已知类型：单跳解析到 FEAT
    if prefix in ('TC', 'BUG', 'EVI'):
        # TC-FEAT-001-001 → FEAT-001
        return f"{parts[1]}-{parts[2]}" if len(parts) >= 3 else None
    
    if prefix in ('TECH', 'TESTSET', 'UI', 'TASK', 'REPORT'):
        # TECH-FEAT-001 → FEAT-001
        return f"{parts[1]}-{parts[2]}" if len(parts) >= 3 else None
    
    # P0 阶段：未知类型不支持，返回 None
    return None
```

### 4.5 P0 校验规则 8 & 9 实现

```python
def validate_parent_consistency(artifact) -> Optional[str]:
    """
    校验 parent_id 一致性
    
    根据对象类型使用不同规则：
    - 直接父对象一致型：parse_parent(id) == parent_id
    - 范围归属型：parse_scope(id) == resolve_scope(parent_id)
    """
    prefix = artifact.id.split('-')[0]
    
    # 直接父对象一致型
    if prefix in ('TECH', 'TESTSET', 'UI', 'TASK', 'REPORT'):
        parsed = parse_parent(artifact.id)
        if parsed != artifact.parent_id:
            return f"ID {artifact.id} 解析出 parent {parsed}，但 parent_id 设置为 {artifact.parent_id}"
    
    # 范围归属型
    elif prefix in ('TC', 'BUG', 'EVI'):
        parsed_scope = parse_scope(artifact.id)
        resolved_scope = resolve_scope(artifact.parent_id)
        if parsed_scope != resolved_scope:
            return f"ID {artifact.id} 归属范围 {parsed_scope}，但 parent_id {artifact.parent_id} 归属范围 {resolved_scope}"
    
    # 独立型：无需校验
    elif prefix in ('SRC', 'EPIC', 'FEAT', 'ADR'):
        pass
    
    return None
```

---

## 五、source_refs 锚点规则

### 格式定义

```
source_refs:
  - SRC-001#3.2          # 章节锚点
  - SRC-001#decision-4   # 命名锚点
  - SRC-001#section-1    # 命名锚点
  - SRC-001              # 无锚点，引用整个文档
```

### P0 校验规则

**只校验 base id 存在**:

```python
def validate_source_refs(source_refs: List[str]) -> List[str]:
    """
    校验 source_refs
    
    P0 阶段只校验 base id 存在，不校验锚点
    """
    errors = []
    for ref in source_refs:
        # 提取 base id
        base_id = ref.split('#')[0]
        
        # 校验 base id 存在
        if not registry.exists(base_id):
            errors.append(f"source_refs 引用不存在的 ID: {base_id}")
    
    return errors
```

> **设计理由**: 锚点校验需要解析目标文档结构，实现成本过高。P0 阶段只确保引用的文档存在即可。

---

## 六、实施计划

### 阶段 1: 基础设施准备 (MVP 核心)

| 任务 | 文件 | 优先级 |
|------|------|--------|
| 定义新类型枚举 | `types.py` | P0 |
| 创建 ID 生成器 | `id_generator.py` | P0 |
| 创建 ID 解析器 | `id_parser.py` | P0 |
| 更新数据模型 | `models.py` | P0 |
| 更新文件命名规则 | `manager.py` | P0 |

### 阶段 2: Registry 和校验增强

| 任务 | 文件 | 优先级 |
|------|------|--------|
| 扩展 Registry 索引 | `registry.py` | P1 |
| 实现新校验规则 | `ssot_service.py` | P1 |

### 阶段 3: CLI 和集成

| 任务 | 文件 | 优先级 |
|------|------|--------|
| 更新 CLI 命令 | `artifacts.py` | P2 |

---

## 七、关键文件修改清单

| 文件 | 修改内容 | 优先级 |
|------|----------|--------|
| `types.py` | 新增 SSOTType 枚举 | P0 |
| `id_generator.py` | 新建 - ID 生成逻辑 | P0 |
| `id_parser.py` | 新建 - ID 解析逻辑 (含 parse_parent, parse_scope, resolve_scope) | P0 |
| `models.py` | 新增 SSOTMetadata 类 (parent_id, source_refs)，扩展 ArtifactMetadata | P0 |
| `manager.py` | 文件命名规则，ID 生成调用 | P0 |
| `registry.py` | 新增索引 (id/type/parent/path/status/relation) | P1 |
| `ssot_service.py` | P0+P1 校验规则，分层校验 (含类型感知的一致性校验) | P1 |
| `artifacts.py` (CLI) | 新增命令 | P2 |

---

## 八、兼容策略

### 架构决策

**单主键方案**: 新体系正式对象统一使用 `SSOT ID` 作为主键。

### 兼容规则

| 场景 | 处理方式 |
|------|----------|
| 旧 ART 对象是否允许继续创建 | **不允许**，仅做兼容读取 |
| 旧 ART 是否允许引用新 SSOT | **不允许**，分开管理 |
| 新 SSOT 是否允许 derived_from 旧 ART | **不允许**，需迁移后使用 |
| registry 如何同时存两类对象 | 分开索引：`legacy_artifacts` vs `ssot_artifacts` |
| 是否提供迁移脚本 | **V1.0 不提供**，后续版本处理 |
| demo_ssot.py 升级 | 升级为新语义，演示新 ID 体系 |

---

## 九、架构成熟度评价

### 核心提升

1. **引入 parent_id**: 区分结构归属和派生来源，解决 derived_from 语义混乱
2. **引入 IDParser**: 不再靠 regex 猜测，使用显式解析器
3. **P0 / P1 校验分层**: 避免 validator 阻断开发流程
4. **区分两类对象**: 直接父对象一致型 vs 范围归属型，解决 TC/BUG/EVI 冲突
5. **TC 结构强制**: 确保测试治理结构清晰
6. **Registry 索引**: 支持 O(1) 查找

### LEE 架构定位

```
SSOT Identity Layer
        ↑
Artifact Registry
        ↑
Workflow / Agent
```

这套系统是 **LEE 的基础设施层**，为所有工作流和 Agent 提供统一的身份和追踪基础。

---

## 附录 A. 正式落盘与 Contract 边界

### A.1 正式 SSOT 主文件落盘

- 正式 SSOT 主文件不再写入 `.artifacts/ssot/{type}/`
- `.artifacts/` 只保留 manifest、registry、索引缓存、运行态产物
- 正式主文件进入项目内容目录，由目录层 placement 决定位置

当前基线 placement：

- `SRC -> spec/source/`
- `EPIC -> spec/requirements/epics/`
- `FEAT -> spec/requirements/features/`
- `UI -> spec/ui/`
- `TECH -> spec/tech/`
- `TASK -> spec/tasks/`
- `TESTSET -> spec/testing/testsets/`
- `TC -> tests/cases/`
- `BUG -> tests/bugs/`
- `REPORT -> docs/reports/testing/`
- `ADR -> spec/adr/`
- `EVI -> docs/reports/evidence/`

### A.2 Contract 必须显式声明 SSOT 关系语义

Agent contract 不再靠目录或文件名推断治理身份，至少应显式声明：

- `identity_kind`
- `ssot_type`
- `title`
- `parent`
- `derived_from`
- `source_refs`
- `verifies`
- `implements`

关系语义由 contract 声明，真实 ID、文件名和最终路径由 runtime 实例化。

### A.3 Spec-Global 主链

`SRC -> EPIC -> FEAT -> UI / TECH / TASK / TESTSET -> TC -> REPORT / BUG -> EVI`

补充说明：

- `商业机会` 默认作为 `SRC`，不是 `EPIC`
- `EPIC` 只聚合多个 `FEAT`
- `UI/TECH/TASK/TESTSET` 一律挂 `FEAT`
- `test-plan` 保持 non-SSOT 规划文档

---

## 十、修订记录

### V1.5 (2026-03-06) - 正式落盘版

1. **移除 `.artifacts/ssot/{type}` 作为正式主文件目录**
2. **明确正式 placement 基线**: 主文件进入 `spec/tests/docs` 内容目录
3. **补充 contract 声明边界**: agent contract 必须显式声明 `identity_kind/ssot_type/relations`
4. **补充 spec-global 主链**: 固定 `SRC -> EPIC -> FEAT -> UI/TECH/TASK/TESTSET -> TC -> REPORT/BUG -> EVI`

### V1.4 (2026-03-06) - 实施基线版

基于实施前评审建议修订 (最后澄清):

1. **明确 FEAT.parent_id 规则**: 若存在，仅允许 `EPIC`；`SRC` 应使用 `source_refs` 指向
2. **明确 resolve_scope() 边界**: P0 阶段只支持已知类型的单跳解析，不支持无限递归链
3. **明确 relation_index 语义**: 仅作 P0 辅助索引，关系语义判断必须读取 metadata 原字段
4. **精确 active 版本规则**: 同一 ID 的不同版本实例中，只允许一个处于 active 状态
5. **补充 REPORT 说明**: `REPORT.parent_id = FEAT` 意味着 REPORT 不是测试执行树直接节点

### V1.3 (2026-03-06) - 实施规格版

基于架构评审建议修订 (解决 P0 级冲突):

1. **区分两类对象**: 直接父对象一致型 (TECH/TESTSET/UI/TASK/REPORT) vs 范围归属型 (TC/BUG/EVI)
2. **修正规则 8**: 改为仅适用于直接父对象一致型：`parse_parent(id) == parent_id`
3. **新增规则 9**: 范围归属型使用 `parse_scope(id) == resolve_scope(parent_id)`
4. **重命名函数**: `parse_parent()` → 保留用于直接父对象一致型；新增 `parse_scope()` 用于范围归属型
5. **简化 slug 算法**: 固定 8 步顺序 (显式→拼音→小写→替换→合并→trim→截断→回退)
6. **补充 active 版本规则**: 同一逻辑对象同一时刻只允许一个主版本处于 active
7. **说明 relation_index**: 标注为 P0 简化实现，P1 建议升级为带关系类型的边索引

### V1.2 (2026-03-06) - 架构评审后修订

基于架构评审建议修订：

1. 增加 P0 规则 8: `parse_parent(id) == parent_id` (ID 与 parent_id 一致性)
2. 增加 P0 规则 10: `TC.parent_id 必须为 TESTSET` (强制测试结构)
3. 统一 REPORT ID: 只保留 `REPORT-FEAT-001-YYYYMMDD` 格式，移除 `REPORT-TESTSET-FEAT-001-RUN001`
4. 明确 slug 生成算法：定义完整的 slug 生成步骤 (转小写、拼音转换、截断 50 字符)
5. 定义 Registry 索引结构：明确 id_index, type_index, parent_index, path_index, status_index, relation_index
6. 明确 source_refs 规则：P0 只校验 base id 存在，不校验锚点
7. 补充版本与状态关系：`frozen` 对象 version 不可变更
8. 明确 parent_id 必填规则：UI, TECH, TASK, TESTSET, TC, BUG, REPORT, EVI 必填 parent_id

### V1.1 (2026-03-06) - 评审后修订

基于评审建议修订：

1. **增加 parent_id**: 区分结构归属 (parent_id) 和派生来源 (derived_from)
2. **补 P0 规则 7**: ID 格式合法且可解析 (必须通过 IDParser)
3. **统一 ADR**: 首版只保留 `ADR`，`DEC` 不进入正式 ID 系统
4. **补文件重命名策略**: 明确 slug 变更如何同步 registry
5. **明确 REPORT 日期型 ID**: 除时态对象外，不把日期混进核心主键

### V1.0 (2026-03-06)

基于审核建议修订：

1. **明确单主键策略**: 新体系使用 SSOT ID 作为主键，ART 仅兼容读取
2. **修正 ID 分类**: 改为 4 类 (独立顺序型、单父唯一型、单父多实例型、时态/运行型)
3. **增加 parent_id**: 区分结构归属 (parent_id) 和派生来源 (derived_from)
4. **引入 IDParser**: 不再靠 regex 猜测，使用显式解析器
5. **校验分层**: P0 Blocking + P1 Warning 两层
6. **修正 source_refs**: 校验时提取 base id
7. **补充兼容策略**: 明确架构决策和兼容规则
8. **Slug 策略**: 明确英文/拼音优先，显式传入
9. **层级关系**: 改为强约束 + 推荐约束两层

---

## 十一、参考文档

- [SSOT 用户指南](SSOT_USER_GUIDE.md)
- [SSOT API 参考](SSOT_API_REFERENCE.md)
- [SSOT 最佳实践](SSOT_BEST_PRACTICES.md)
- [SSOT Agent Contract](SSOT_AGENT_CONTRACT.md)
- [Spec-Global SSOT Contract Chain](../../../spec-global/SSOT_CONTRACT_CHAIN.md)
- [产出物管理系统架构](../../architecture/artifact-management-system.md)
