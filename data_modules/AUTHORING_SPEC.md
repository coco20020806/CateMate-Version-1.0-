# CateMate 数据模块写作指示文件

位置：`data_modules/AUTHORING_SPEC.md`  
更新时间：2026-07-15  
状态：**正式指示文件** — Agent 写每个模块时必须遵循。

---

## 0. 模块核心结构（必读）

每个模块必须清楚回答两件事：

1. **源底表必须有哪些列？** — Excel/CSV 表头即 `column` 名，写在 `source_schema.yaml → source_columns`  
2. **Python 怎么处理这些列？** — 写在 `source_schema.yaml → compute_rules / transform_rules`，并在 `compute.py` / `transforms.py` **用相同列名实现**

```text
source_schema.yaml          ← 列名契约 + 处理规则（人读 + 机读）
    ↓ 列名一致
compute.py / transforms.py  ← 写死的 Python 实现
    ↓
contract.yaml               ← 业务说明、输出表 schema、chart_presets
```

**外部 Scope 模块**（不在本目录）：读 Excel、过滤行、选数据源 → 传入带原始列名的 DataFrame。

---

## 1. Agent 收到自然语言后怎么做

### 1.1 交付流程

```text
1. 解析需求 → 确定源列名 + 聚合/派生规则
2. 创建/更新 data_modules/<module_id>/
     source_schema.yaml    # 源列名 + compute/transform 规则
     contract.yaml
     compute.py
     transforms.py
3. 更新 data_modules/<module_id>_review.md
4. 单测 fixture 使用与 source_columns 一致的列名
5. pytest tests/data_modules/<module_id>/
```

### 1.2 硬性边界

| 写死在 Python + source_schema | 可后期调整 |
|-------------------------------|------------|
| 源列名与算数规则 | 外部 Scope 取数；chart_presets |
| 延伸 transform 规则 | HTML/PPT 样式 |

**不要**在 compute 里读 Excel 路径、做类目过滤、画图。

---

## 2. 架构共识（摘要）

**实际语义 = Scope（取数）× Compute（按源列名算数）**

| 已拍板 | 决定 |
|--------|------|
| 模块目录 | `data_modules/<module_id>/` |
| 列名 | **源表列名**为唯一算数输入名 |
| 算数 | `source_schema` + `compute.py` + `transforms.py` |
| 画图 | `chart_presets`，`binding: soft` |
| market_trend | 主表 `grass_region × grass_month`；过滤由外部 Scope |

---

## 3. 标准目录结构

```text
data_modules/
  AUTHORING_SPEC.md
  <module_id>_review.md
  <module_id>/
    source_schema.yaml      # ★ 源列名 + 处理规则
    contract.yaml
    compute.py
    transforms.py
```

---

## 4. source_schema.yaml 模板

```yaml
schema_version: source_schema_v1
module_id: <module_id>

source_columns:
  required:
    - column: grass_region          # Excel 列名
      meaning: 站点
      dtype: string
      used_by: [compute.group_by, scope.filter]
    - column: gmv_usd
      meaning: GMV（美元）
      dtype: float
      used_by: [compute.sum]
  optional:
    - column: level2_global_be_category
      meaning: 二级类目
      used_by: [scope.filter]

compute_rules:
  primary_table_id: <table_id>
  group_by: [grass_region, grass_month]
  aggregate:
    - column: gmv_usd
      function: sum
  derive:
    - output_column: aov
      expression: gmv_usd / orders
      null_when: orders is null or orders == 0
  output_columns: [grass_region, grass_month, gmv_usd, orders, aov]

transform_rules:
  - output_table_id: ...
    transform_id: latest_period_slice
    period_column: grass_month
    ...
```

**写作要求：**

- `required` 列：compute 运行前必须存在  
- `optional` 列：仅 Scope 过滤用，compute 不读也可  
- `compute_rules` 中每一 `column` 必须出现在 `source_columns` 或 `derive.output_column`  
- `compute.py` 顶部用常量声明列名，注释指向 `source_schema.yaml`

---

## 5. compute.py 模板

```python
# Must match source_schema.yaml
COL_SITE = "grass_region"
COL_GMV = "gmv_usd"
REQUIRED_SOURCE_COLUMNS = (COL_SITE, ...)

def compute(params, frame: ScopedFrame) -> dict[str, pd.DataFrame]:
    _validate_source_columns(frame)
    # group_by / sum / derive — 列名与 source_schema.yaml 一致，不做 rename
```

---

## 6. contract.yaml

- `source_schema_ref: source_schema.yaml`  
- `business_purpose` / `planning_hints` / `outputs` / `chart_presets`  
- **不在 contract 重复列名** — 列名以 `source_schema.yaml` 为准

---

## 7. 外部 Scope（不在模块目录）

- 数据源、Excel/sheet、行级 filter 由**独立取数模块**实现  
- 数据模块只声明对传入列的要求（`source_schema.yaml`）  
- `contract.yaml → scope_expectations` 仅说明「假定收到已过滤行」

---

## 8. 检查清单

- [ ] `source_schema.yaml` 列名与底表 manifest/Excel 一致  
- [ ] `compute.py` / `transforms.py` 列名常量与 `source_schema` 同步  
- [ ] fixture CSV 表头 = 源列名  
- [ ] 单测通过  
- [ ] `chart_presets` 均为 `binding: soft`

---

## 9. 参考实现

- 模块：`data_modules/monthly_market_trend/`  
- 批注：`data_modules/monthly_market_trend_review.md`

---

## 修订记录

| 日期 | 说明 |
|------|------|
| 2026-07-15 | 源列名 + compute_rules 模型；废弃 input_schema 逻辑列 |
