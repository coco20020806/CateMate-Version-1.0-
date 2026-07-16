# Pattern：`monthly_metric_trend`

参考实现：`data_modules/monthly_market_trend/`

Agent 在录入稿 `pattern_id = monthly_metric_trend` 时，按本 pattern 生成模块。

---

## 适用条件

- 时间粒度：月（`grass_month` 或 `grass_date` 归月）
- 空间粒度：站点（`grass_region`）
- 每次调用：**一个** `metric_id`
- 主表：**一指标一表**，列 = `grass_region`, `grass_month`, `<value_column>`

---

## 文件映射

| 录入稿章节 | 产出 |
|------------|------|
| §4 源列 | `source_schema.source_columns` |
| §5 指标 | `compute_rules.metrics` + `METRIC_SPECS` in compute.py |
| §6 延伸 | `transform_rules.per_active_metric` |
| §8 grain | `contract.source_bindings` |
| §10 planning | `contract.planning_hints` |
| §11 画图 | `contract.chart_presets` |

---

## 延伸表命名约定

对 `metric_id = {m}`，`value_column = {v}`：

| table_id | 列（核心） |
|----------|------------|
| `{m}_by_site_month` | grass_region, grass_month, {v} |
| `{m}_latest_month_by_site` | grass_region, {v} |
| `{m}_latest_month_pct_by_site` | grass_region, {v}, `{v}_pct` |
| `{m}_mom_by_site_month` | grass_region, grass_month, {v}, `{v}_mom_pct` |

---

## Python 骨架要点

1. `ComputeParams.metric_id` — Literal 由 §5 指标列表生成  
2. `_normalize_month_column` — 若录入稿启用 grass_date  
3. `_aggregate_metric` — sum 或 aov 派生  
4. `transform` — `_latest_period_slice`, `_share_of_total`, `_mom_by_site_month`  
5. `ScopedFrame` from `catemate.scope.schemas`

---

## 不宜使用本 pattern 时

- 日度主表、非 site×month grain  
- 一次调用输出多指标宽表  
- Top N、价格段分布等非趋势聚合  

→ 录入稿选 `custom`，在 §7 描述。
