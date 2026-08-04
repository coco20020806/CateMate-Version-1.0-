# CateMate Data Module Schema v2

更新时间：2026-07-09

## 定位

CateMate 数据配置分两层：

| 层 | 文件 | 职责 |
|----|------|------|
| **数据资产层** | `CateMate_processeddata/processed_manifest.yaml` | 描述 processed table：来源 workbook/sheet、字段、行数、CSV 路径 |
| **业务问题层** | `config/data_modules/*.yaml` | 描述“一个业务问题一个模块”：能回答什么、用哪些 table、字段语义、默认图表、排序与口径限制 |

Planning agent / chart generation agent **优先读取 v2 data module**，再按需引用 manifest 中的字段细节。

## 设计原则

1. **一个业务问题一个 module** — 不再把整份 DECK 看板塞进一个大模块。
2. **字段必须来自 manifest** — `fields.*.field` 不得编造 processed 中不存在的列名。
3. **图表语义可执行** — `default_charts` 应能指导 trend/bar/share/table 的 x/y/series/sort。
4. **保守缺失处理** — `chart_rules.missing_value_policy` 默认不补空、不发明 YoY。
5. **deprecated 模块不参与规划** — `status: deprecated` 的 YAML 仅供历史说明。

## 顶层结构

```yaml
schema_version: data_module_v2   # 必填
module_id: string              # 必填，唯一
module_name: string            # 必填
module_type: string            # 如 market_trend / daily_performance / price_tier / ranking / keyword / listing
status: active | deprecated    # 必填；deprecated 不被 planning 读取
owner: CateMate
last_updated: "YYYY-MM-DD"
```

## business_purpose

描述模块解决的业务问题。

```yaml
business_purpose:
  description: string          # 一段话说明模块用途
  typical_questions:           # 典型可回答问题（给 planning agent）
    - string
  decision_support:            # 可支持的决策类型
    - string
  not_suitable_for:            # 明确不适合的场景
    - string
```

## lineage

描述模块引用的 processed tables（不重复 manifest 的全部字段，但写明角色与聚合规则）。

```yaml
lineage:
  source_workbook_pattern: string   # 如 *RM*.xlsx
  source_workbook_name: string      # 人类可读默认 workbook 名
  formula_sheet: string | null      # 如 CNCB 中间表 By site / DECK
  source_tables:
    - table_id: string              # 必须存在于 processed_manifest
      source_sheet: string
      processed_table: string       # 相对路径，如 source_tables/xxx.csv
      role: string                  # 在模块内的角色
      extraction_rule: string       # 如何从 raw 抽取（简述）
      aggregation_rule: string      # 默认聚合方式（简述）
```

一个 module 可引用多个 `table_id`（例如价格段当前期 + 对比期）。

## data_grain

```yaml
data_grain:
  time_grain: monthly | daily | snapshot | mixed | none
  primary_grain:                  # 主粒度字段组合
    - field_name
  category_levels:
    - L1 | L2 | L3
  default_filters:
    - category
    - site
    - time_range
```

## fields

字段语义层（列名必须与 manifest 一致）。

```yaml
fields:
  dimensions:
    - field: string
      meaning: string
      role: site | time | category_l1 | category_l2 | category_l3 | price_tier | seller | keyword | item | other
      required: true | false
  metrics:
    - field: string
      meaning: string
      aggregation: sum | avg | max | min | first | none
      default_axis: y | none
      derived: true | false
      derivation: string | null
      null_rule: string | null
```

## derived_metrics

模块内可计算的派生指标（不写回 processed data）。

```yaml
derived_metrics:
  - metric_id: string
    meaning: string
    expression: string              # 人类可读表达式，如 gmv_usd / orders
    required_fields:
      - field
    null_rule: string
```

## default_charts

给 planning / PPT-ready 的默认图表意图。

```yaml
default_charts:
  - chart_intent: string
    default_chart_type: trend | bar | share | table | bubble
    title_template: string
    x_axis: string | null
    y_axis:
      - string
    series: string | null
    dimensions:
      - string
    sort_rule: time_ascending | metric_desc | price_range_natural_order | rank_ascending | none
    top_n: number | null
    dedupe_group: string | null       # 同类图表去重分组
    notes:
      - string
```

### sort_rule 说明

| 值 | 含义 |
|----|------|
| `time_ascending` | 时间轴升序（grass_month / grass_date） |
| `metric_desc` | 按主指标降序 Top N |
| `price_range_natural_order` | Price_Range_USD 从低到高（01_[0,1) …） |
| `rank_ascending` | 排名类字段升序 |
| `none` | 不额外排序 |

## chart_rules

跨图表规则。

```yaml
chart_rules:
  dedupe:
    enabled: true | false
    dedupe_group: string | null
    prefer:
      - longer_time_window
      - table_id:rm_raw_data
  sorting:
    default: string
    special:
      Price_Range_USD: price_range_natural_order
  missing_value_policy:
    do_not_fill_null: true
    do_not_invent_yoy: true
    explain_nulls: true
```

## planning_hints

给 planning agent 的选用提示。

```yaml
planning_hints:
  use_when:
    - string
  avoid_when:
    - string
  preferred_over:
    - module_id
  can_combine_with:
    - module_id
```

## limitations

模块级限制（必填，至少一条）。

```yaml
limitations:
  - string
```

## 与 v1 的兼容

v1 模块常见字段：`supported_questions`、`chart_types`、`filter_dimensions`。  
v2 对应关系：

| v1 | v2 |
|----|-----|
| `supported_questions` | `business_purpose.typical_questions` |
| `chart_types` | `default_charts[].default_chart_type` |
| `filter_dimensions` | `data_grain.default_filters` + `fields.dimensions` |
| `source_tables` | `lineage.source_tables` |

`context_loader` 会同时摘要 v1/v2 字段，但 **只加载 `status: active` 的模块**。

### V3 Python 模块（`data_modules/<id>/contract.yaml`）

- 加载函数：`load_v2_data_module_contracts(directory, active_only=True)`（默认 `active_only=True`）
- **仅 `status: active`** 进入 V2 solve loop（蓝图 catalog、plan、execution）
- `draft` / `deprecated` 不参与编排；保留 `compute.py` 供单测与后续启用
- 当前 active：`monthly_market_trend`、`top_sku_info`
- 校验：`python scripts/validate_v3_data_modules.py`

## 文件约定

- 模板：`config/data_modules/_template.yaml`（以下划线开头，loader 自动跳过）
- 活跃模块：`status: active`
- 历史模块：`status: deprecated`，可含 `split_into` 列表说明拆分去向
- 批注文档：`docs/data_module_review_notes/`（产品侧自然语言批注，不直接改 YAML）

## 普适性配置约定

1. **类目 meaning**：L1/L2/L3 统一为「一级类目 / 二级类目 / 三级类目」。
2. **DECK Part**：
   - 不在 `module_name`、`business_purpose.description`、`default_charts.title_template` 中显性展示；
   - 写入 `lineage.source_deck_part`、`planning_hints.explicit_triggers`、`typical_questions`、`use_when` / `avoid_when`。

## 当前 v2 模块清单（2026-07-09）

| module_id | 业务问题 |
|-----------|----------|
| `rm_monthly_category_performance` | 长时间窗口类目月度趋势 |
| `dashboard_history_market_trend` | DECK Part 1 市场历史趋势 |
| `dashboard_daily_cncb_performance` | 日度 Marketplace/CNCB 表现 |
| `dashboard_price_tier_distribution` | 价格段分布与对比 |
| `dashboard_top_shop` | Top Shop 排名 |
| `dashboard_keywords` | 热门关键词 |
| `dashboard_top_listing` | Top Listing 商品样本 |

已废弃：`sph_category_dashboard_deck`（拆分为上述 6 个 dashboard 子模块）。
