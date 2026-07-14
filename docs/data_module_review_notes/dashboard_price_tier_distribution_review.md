# dashboard_price_tier_distribution 批注

- **正式配置**：`config/data_modules/dashboard_price_tier_distribution.yaml`
- **主表**：`dashboard_price_tier` + `dashboard_price_tier_prior`
- **source_deck_part**：DECK Part 3/4
- **批注人**：（填写）
- **最后更新**：（填写日期）

> **普适性规则**（见 `README.md`）  
> - [已采纳] 类目 meaning：一级/二级/三级类目（2026-07-09）  
> - [已采纳] `module_name` / `description` / 图表标题不含 DECK Part；命中规则见 `explicit_triggers`  
> - [已采纳] `description` 改为「价格段订单/GMV/Live SKU 结构…」（待你继续批注其他字段）

---

## 元信息（module_name / module_type / last_updated）

（）

---

## business_purpose

### description
（当前 YAML：「价格段 GMV/Orders/SKU 分布」）

> **示例批注（可删改）**  
> - [待改] 建议改成「价格段订单/GMV/Live SKU 结构」  
> - 原因：真实工作里更关注价格带贡献，而不是字面「GMV/Orders 分布」

### typical_questions
（ADO/ADG/Live_SKUs、占比、当前 vs 对比期 — 是否完整？）

### not_suitable_for
（）

---

## lineage

### dashboard_price_tier / dashboard_price_tier_prior
（当前期 vs 对比期 role 描述是否清楚？）

---

## data_grain

### primary_grain.Price_Range_USD
（价格段自然顺序 01_[0,1) … — 是否需要写进 business_purpose？）

### default_filters.seller_type
（卖家类型过滤是否常用？）

---

## fields

### dimensions.Price_Range_USD
（）

### metrics.ADO
（meaning：平均日订单 — 是否准确？）

### metrics.ADG
（当前 YAML meaning：平均日 GMV（当前期））

> **示例批注（可删改）**  
> - [待改] meaning 需强调：ADG 是**日均 GMV**，不是期间总 GMV，也不是简单 SUM 后的 GMV

### metrics.ADO_proportion / ADG_proportion / Live_SKUs_proportion
（proportion 字段 — 是否禁止重算 share？PM 是否理解？）

### metrics.lpp_ado(SUM) / campaign_ado(SUM) 等营销字段
（是否要在 default_charts 里体现？字段太多如何取舍？）

---

## default_charts

### price_tier_distribution
（bar，x=Price_Range_USD，sort=price_range_natural_order）

### price_tier_share
（当前 default_chart_type: share）

> **示例批注（可删改）**  
> - [待改] 价格段多时不宜默认饼图（share）；建议默认**柱状占比图**或 stacked bar  
> - 原因：9 个价格段饼图可读性差

### current_vs_prior_price_tier
（对比期必须引用 prior 表 — PM 如何理解「当前期/对比期」？）

---

## chart_rules.sorting

### Price_Range_USD: price_range_natural_order
（必须按价格带自然序，不按指标降序 — 确认）

---

## planning_hints

（）

---

## limitations

（proportion 不重算、对比期必须用 prior 表 — 还要补充什么？）

---

## 待修改清单

| 状态 | YAML 路径 | 建议修改 | 原因 |
|------|-----------|----------|------|
| 待改 | `business_purpose.description` | 「价格段订单/GMV/Live SKU 结构」 | 更贴近实际分析关注点 |
| 待改 | `fields.metrics.ADG.meaning` | 强调「日均 GMV」 | 避免与总 GMV 混淆 |
| 待改 | `default_charts.price_tier_share.default_chart_type` | 考虑 bar 而非 share | 价格段多时可读性 |
