# dashboard_top_listing 批注

- **正式配置**：`config/data_modules/dashboard_top_listing.yaml`
- **主表**：`dashboard_top_listing`（source sheet: 热门商品）
- **source_deck_part**：DECK Part 7
- **批注人**：（填写）
- **最后更新**：（填写日期）

> **普适性规则**（见 `README.md`）  
> - [已采纳] 类目 meaning、DECK Part 命中规则（2026-07-09 已落地，待你继续细批注）

---

## 元信息（module_name / module_type / last_updated）

（）

---

## business_purpose

### description
（Top Listing 样本：名称、链接、图片、价格、ADO/ADGMV）

### typical_questions
（爆款对标、代表性 SKU — 是否覆盖？）

### not_suitable_for
（样本价 ≠ 全量均价 — 是否和 price_tier 区分清楚？）

---

## lineage

### source_tables.dashboard_top_listing
（）

---

## data_grain

### primary_grain.item_name
（）

---

## fields

### dimensions.item_name / item_link / item_image
（item_image 可空、不能因缺图丢记录 — PM 是否需要在图表侧强调？）

### metrics.item_price_usd
（样本价格 — meaning 是否准确？）

### metrics.current_ado(RAW) / current_adgmv(RAW)
（RAW 后缀含义 — PM/分析师是否理解？）

---

## default_charts

### top_listing_table
（table，sort current_adgmv desc，top_n=50）

### listing_price_reference
（bar/table，x=L3 或 item_name）

---

## planning_hints

（与 price_tier、keywords 组合场景）

---

## limitations

（样本价、图片可空、非全量商品池 — 补充？）

---

## 待修改清单

| 状态 | YAML 路径 | 建议修改 | 原因 |
|------|-----------|----------|------|
| | | | |
