# rm_monthly_category_performance 批注

- **正式配置**：`config/data_modules/rm_monthly_category_performance.yaml`
- **主表**：`rm_raw_data`
- **source_deck_part**：（无，非 DECK 模块）
- **批注人**：（填写）
- **最后更新**：（填写日期）

> **普适性规则**（见 `README.md`）  
> - [已采纳] 类目 meaning：一级/二级/三级类目（2026-07-09 已落地）  
> - 本模块无 DECK Part；`avoid_when` 中保留「用户提 DECK Part 1 → 转 dashboard_history」指引

---

## 元信息（module_name / module_type / last_updated）

（对模块名称、类型、更新日期的批注）

---

## business_purpose

### description
（当前 YAML：长时间窗口类目月度表现，站点对比，L1/L2/L3 GMV/Orders/AOV）

### typical_questions
（哪些问题是 PM 日常真的会问的？有没有漏掉或多余的？）

### decision_support
（决策支持是否准确？）

### not_suitable_for
（不适用场景是否完整？）

---

## lineage

### source_workbook / formula_sheet
（workbook 名、公式 sheet 描述是否和实际 Excel 一致？）

### source_tables.rm_raw_data
（role / extraction_rule / aggregation_rule 是否需要更贴近业务口径？）

---

## data_grain

### time_grain / primary_grain
（月度粒度是否够用？主粒度字段是否对？）

### default_filters
（默认过滤维度是否和 PM 分析习惯一致？）

---

## fields

### dimensions
（grass_region、类目 L1/L2/L3、grass_month 的 meaning / role 是否准确？）

### metrics.gmv_usd
（）

### metrics.orders
（）

### derived_metrics.aov
（aov = gmv_usd / orders；orders 为 0 时空值规则是否符合业务？）

---

## default_charts

### monthly_trend
（trend，x=grass_month，y=gmv_usd/orders，series=grass_region）

### site_comparison
（bar，x=grass_region）

### aov_by_site
（是否需要默认出这张图？）

---

## chart_rules.dedupe

（与 dashboard_history_market_trend 重复时优先 rm — 是否符合实际？）

---

## planning_hints

### use_when / avoid_when / preferred_over
（规划 agent 选用提示是否准确？）

---

## limitations

（限制说明是否够？有没有 PM 常踩的坑要补充？）

---

## 待修改清单

| 状态 | YAML 路径 | 建议修改 | 原因 |
|------|-----------|----------|------|
| | | | |
