# dashboard_daily_cncb_performance 批注

- **正式配置**：`config/data_modules/dashboard_daily_cncb_performance.yaml`
- **主表**：`dashboard_daily_data`（source sheet: daily data）
- **批注人**：（填写）
- **最后更新**：2026-07-09（已落地至正式 YAML）

> **普适性规则**（见 `README.md`）  
> - [已采纳] 类目 meaning、DECK Part 仅写入命中规则（2026-07-09 全模块同步）

---

## 元信息（module_name / module_type / last_updated）

- [已采纳] `module_name` 去掉 DECK Part 2 前缀，改为「Shopee/CNCB 表现」

---

## business_purpose

### description

- [已采纳] 去掉开头「DECK Part 2」；补充「源数据日度、默认按月聚合」
- [已采纳] 在 description / lineage / planning_hints 中保留 DECK Part 2 作为**显式定位词**（用户明确说时能命中），但模块名与默认描述不以 DECK 开头，避免误导向其他 Part

### typical_questions

- [已采纳] 改为面向前序 agent 命中场景（CNCB 渗透、单渠道、月度趋势、DECK Part 2、日度关键词触发等）

### not_suitable_for

（无新增）

---

## lineage

### source_tables.dashboard_daily_data

- [已采纳] `aggregation_rule` 默认按月，日度/按年按需

---



## data_grain



### time_grain / primary_grain

- [已采纳] `time_grain: mixed`；`primary_grain` 首位改为 `month`



### fields.month / fields.year / fields.grass_date

- [已采纳] 默认 month；保留 grass_date（日度）、year（按年）能力

---



## fields



### 类目 dimensions

- [已采纳] meaning 改为「一级类目 / 二级类目 / 三级类目」



### metrics 渠道字段

- [已采纳] 保持不变



### metrics SKU 字段

- [已采纳] 新增可选 `sku_performance_by_month` 图表

---



## default_charts

- [已采纳] `monthly_performance_trend`：默认 x=month，日度关键词时改 grass_date
- [已采纳] `cncb_site_penetration_latest_month`：最新月、by site、CNCB 渗透率 100% 横柱
- [已采纳] 渠道拆为 ads / campaign / lpp / cfs 四张独立图，不默认合并

---



## chart_rules

- [已采纳] 新增 `aggregation`：默认 month、缺失日汇报

---



## planning_hints

- [已采纳] use_when 对齐 DECK Part 2 典型图与字段语义；avoid_when 禁止默认日度轴、禁止合并渠道

---



## limitations

- [已采纳] 优先 by month；日度关键词才用 grass_date；渠道单独展示

---



## 待修改清单


| 状态  | YAML 路径 | 建议修改  | 原因               |
| --- | ------- | ----- | ---------------- |
| 已采纳 | 全文      | 见上方各节 | 2026-07-09 批注已落地 |


