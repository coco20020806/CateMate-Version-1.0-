# dashboard_top_shop 批注

- **正式配置**：`config/data_modules/dashboard_top_shop.yaml`
- **主表**：`dashboard_top_shop`（source sheet: top shop）
- **source_deck_part**：DECK Part 5
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
（Top Shop 排名、头部卖家、广告/直播/活动贡献）

### typical_questions
（MTD ADGMV 排名、CNRM 管理店铺等 — 是否覆盖？）

### not_suitable_for
（榜单≠全量市场 — 表述是否够直白？）

---

## lineage

### source_tables.dashboard_top_shop
（）

---

## data_grain

### primary_grain.shop_id
（update_date 快照口径 — PM 如何理解 MTD？）

---

## fields

### dimensions.shop_id / user_name / is_cnrm_managed
（）

### metrics.mtd_adgmv_usd(SUM) / mtd_ado(SUM)
（MTD 含义、SUM 后缀是否和源表一致？）

### metrics.mtd_ads_adgmv_usd(SUM) / mtd_campaign_adgmv_usd(SUM) / mtd_ls_adgmv_usd(SUM) / mtd_cfs_adgmv_usd(SUM)
（渠道字段 naming 是否易懂？是否漏字段？）

---

## default_charts

### top_shop_table
（table，sort mtd_adgmv desc，top_n=50 — 50 是否合适？）

### channel_contribution
（bar/share，top_n=20 — 默认出不出？）

---

## planning_hints

（）

---

## limitations

（当前：shop 为样本榜单，不代表完整市场结构 — 还要补充什么？）

---

## 待修改清单

| 状态 | YAML 路径 | 建议修改 | 原因 |
|------|-----------|----------|------|
| | | | |
