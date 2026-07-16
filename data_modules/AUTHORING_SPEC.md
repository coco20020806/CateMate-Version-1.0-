# CateMate 数据模块写作指示文件

位置：`data_modules/AUTHORING_SPEC.md`  
更新时间：2026-07-15  
状态：**正式指示文件** — Agent 生成或修改模块时必须遵循。  
参考实现：`data_modules/monthly_market_trend/`

---

## 0. 你要先理解的两件事

每个模块必须写清：

1. **源底表有哪些列（Excel 表头）** → `source_schema.yaml → source_columns`  
2. **Python 如何用这些列算数** → `source_schema.yaml → compute_rules / transform_rules` + `compute.py` / `transforms.py`

```text
用户填写 MODULE_INTAKE_TEMPLATE.md
        ↓
Agent 读本文 + 录入稿
        ↓
data_modules/<module_id>/
  source_schema.yaml
  contract.yaml
  compute.py
  transforms.py
  __init__.py
data_modules/<module_id>_review.md    # 人读镜像（可选）
tests/data_modules/<module_id>/
tests/fixtures/data_modules/<module_id>/
```

**外部 Scope**（`catemate/scope/`）：读底表、filter、组 `ScopedFrame`。**不在** `compute.py` 里做。

---

## 1. Agent 工作流（收到录入稿 / 自然语言后）

### 1.1 步骤

```text
1. 读 data_modules/MODULE_INTAKE_TEMPLATE.md（用户已填）或用户消息
2. 对照本文 §3 检查必填项；缺项向用户确认
3. 选定实现模式（§4）：优先复用已有 pattern
4. 生成/更新：
     source_schema.yaml   # 先写
     contract.yaml
     compute.py           # 列名常量与 source_schema 一致
     transforms.py
     __init__.py
5. 写 tests + fixture（表头 = 源列名）
6. pytest tests/data_modules/<module_id>/
7. 同步 <module_id>_review.md（摘要，不重复全文）
```

### 1.2 硬性边界

| 写死（Python + source_schema） | 可后调 |
|--------------------------------|--------|
| 源列名、group_by、聚合、延伸规则 | `chart_presets`（`binding: soft`） |
| 输出表 schema（contract.outputs） | HTML / PPT 样式 |
| | 外部 Scope 取数实现 |

**禁止**：`compute.py` 读 Excel 路径、做业务 filter、画图、LLM 算数。

---

## 2. 标准目录与文件职责

```text
data_modules/
  AUTHORING_SPEC.md              # 本文
  MODULE_INTAKE_TEMPLATE.md      # ★ 用户填写录入稿
  <module_id>/
    source_schema.yaml           # 列名 + 算数规则（机读主契约）
    contract.yaml                # 业务、outputs 登记、bindings、chart_presets
    compute.py
    transforms.py
    __init__.py
  <module_id>_review.md          # 人读批注 / 摘要
```

### 2.1 `source_schema.yaml` 结构（与 monthly_market_trend 对齐）

```yaml
schema_version: source_schema_v1
module_id: <module_id>

source_columns:
  required: []              # compute 前必须存在
  required_one_of: {}       # 可选：时间列二选一等
  soft_expected: {}         # 可选：缺则不阻塞，metadata 标记

compute_rules:
  active_metric: ...        # 若每次只算一个指标
  time_normalization: ...   # 可选：grass_date → grass_month
  group_by: [...]
  metrics: {}               # 每指标：table_id、源列、聚合方式
  output_metadata: []

transform_rules:
  per_active_metric: []     # 或自定义 transform 列表
  metric_table_map: {}
```

### 2.2 `contract.yaml` 结构

```yaml
schema_version: data_module_v3
module_id: ...
module_name: ...
module_type: ...
source_schema_ref: source_schema.yaml

source_bindings:            # 可选：声明可用 grain / 底表（给编排器）
  allowed_grains: [category, shop, item]
  by_grain: { ... }

business_purpose: { ... }
scope_expectations: { ... }
compute_params: { ... }    # 如 metric_id required

outputs:
  primary: [...]            # 每个 metric 一张主表
  derived: [...]            # 延伸表登记

chart_presets: [...]        # binding: soft
planning_hints: { ... }
limitations: [...]
```

### 2.3 `compute.py` 约定

- 从 `catemate.scope.schemas` 引入 `ScopedFrame`（与 Scope 层统一）
- 顶部 **列名常量** + `METRIC_SPECS`（若多指标模式）
- 签名：`compute(params, frame: ScopedFrame) -> dict[str, pd.DataFrame]`
- 返回 **单张主表**（一指标一表模式）或契约登记的多表
- `result.attrs` 至少：`scope_label`, `module_id`, `metric_id`（如适用）, `input_quality`

### 2.4 `transforms.py` 约定

- 签名：`transform(primary_tables, derived_specs=None) -> dict[str, pd.DataFrame]`
- **登记了的延伸表必须全部实现**（全量预计算）
- 从 `primary.attrs["metric_id"]` 解析当次指标（若适用）

---

## 3. 录入稿必填项检查（Agent 自检）

用户填写 `MODULE_INTAKE_TEMPLATE.md` 后，Agent 须能解析出：

| # | 项 | 产出到 |
|---|-----|--------|
| 1 | `module_id` / `module_name` / `module_type` | contract |
| 2 | 业务问题 / 不适用场景 | contract.business_purpose |
| 3 | 实现模式 `pattern_id` | 决定 compute/transform 骨架 |
| 4 | 源列：required / required_one_of / soft_expected | source_schema |
| 5 | 主表 grain（如 site×month） | compute_rules.group_by |
| 6 | 指标列表（id、源列、聚合、派生公式） | compute_rules.metrics |
| 7 | 延伸表（用哪些 transform） | transform_rules |
| 8 | planning 命中 / 避免 | contract.planning_hints |
| 9 | allowed_grains + 底表（可选） | contract.source_bindings |

---

## 4. 实现模式（pattern_id）

### 4.1 `monthly_metric_trend`（参考：`monthly_market_trend`）

适用：月度、按站×月聚合、**每次调用一个指标**、标准三延伸表。

| 项 | 规格 |
|----|------|
| group_by | `grass_region`, `grass_month` |
| 时间 | `grass_month` 或 `grass_date`（归月） |
| 指标 | 用户定义列表；每项一张主表 `{metric_id}_by_site_month` |
| 延伸（每指标） | `{id}_latest_month_by_site`, `{id}_latest_month_pct_by_site`, `{id}_mom_by_site_month` |
| compute_params | `metric_id` required |

**克隆步骤**：复制 `monthly_market_trend` 的 compute/transform 结构，替换 `METRIC_SPECS`、模块 id、contract 文案。

### 4.2 `custom`

适用：grain、聚合、延伸逻辑与 4.1 显著不同。  
Agent 须从零写 `compute_rules` 与 Python，并在录入稿 **§7 自定义规则** 写清。

---

## 5. 平台标准 Transform（延伸表选用）

| transform_id | 含义 | 典型输出 |
|--------------|------|----------|
| `latest_period_slice` | 取 period 最大一期 | 无时间维 |
| `share_of_total` | 占比 | `{value_column}_pct` |
| `period_growth` | 逐期环比 | `{value_column}_mom_pct` |
| `rank_top_n` | Top N | listing/shop 类 |
| `cumulative_in_window` | 窗内累计 | |

新 transform 须先扩展本文 + 平台实现，再在模块引用。

---

## 6. 单测交付

```text
tests/data_modules/<module_id>/test_compute.py
tests/fixtures/data_modules/<module_id>/sample_scoped.csv
```

覆盖建议：

- 各 `metric_id` 主表形状与聚合
- 时间归一（若有 `grass_date`）
- 缺 soft_expected 列不阻塞
- 延伸表数量与关键数值
- 缺 required 列报错

---

## 7. 与 V2 架构关系

- **Scope × Module**：本目录只写 Module；Scope 在 `catemate/scope/`  
- **category / shop / item**：共用同一 module 时，差异写在 `contract.source_bindings` + Scope，不在 compute 写死 filter  
- **Data Workbook**：编排层多次调用 `compute(metric_id=...)`，每次一张主表 + 三张延伸表

---

## 8. 检查清单（生成完成后）

- [ ] 录入稿字段已全部反映到 YAML/Python  
- [ ] `source_schema` 与 `compute.py` 列名常量一致  
- [ ] `contract.outputs` 与 compute/transform 产出表 id 一致  
- [ ] `chart_presets` 均为 `binding: soft`  
- [ ] pytest 通过  
- [ ] `<module_id>_review.md` 已更新摘要  

---

## 9. 相关文档

- 录入模板：`MODULE_INTAKE_TEMPLATE.md`  
- 参考模块：`monthly_market_trend/`  
- V2 总览：`docs/CATEMATE_V2_DESIGN_OVERVIEW.md`  

---

## 修订记录

| 日期 | 说明 |
|------|------|
| 2026-07-15 | 初稿：源列名模型 |
| 2026-07-15 | 对齐 monthly_market_trend：一指标一表、三延伸、录入模板流程 |
