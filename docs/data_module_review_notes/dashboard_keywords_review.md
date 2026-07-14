# dashboard_keywords 批注

- **正式配置**：`config/data_modules/dashboard_keywords.yaml`
- **主表**：`dashboard_keywords`（source sheet: keywords）
- **source_deck_part**：DECK Part 6
- **批注人**：（填写）
- **最后更新**：2026-07-09（已落地至正式 YAML）

> **普适性规则**（见 `README.md`）  
> - [已采纳] 类目 meaning、DECK Part 命中规则

---

## default_charts

- [已采纳] **默认只出 table**（`keyword_table`），不按 rank 升序
- [已采纳] 先按 L2/L3 等类目筛选，再按 `current_daily_item_click(SUM)` **降序**排列
- [已采纳] 趋势列：current 相对 benchmark 百分比 → 文字标签（大幅下降/轻微下跌/小幅上涨/大幅上涨/热度爆涨）
- [已采纳] 未选 site：罗列各 site + 关键词 + 趋势；选了单一 site：直接列关键词
- [已采纳] top_n：单 site=50，多 site=20
- [已采纳] `keyword_growth_bar` 改为非默认，仅用户明确要求 bar/增长图时

---

## limitations

- [已采纳] 关键词为静态 snapshot，当前源数据日期 **2026-06-30**

---

## 待修改清单

| 状态 | YAML 路径 | 建议修改 | 原因 |
| --- | --- | --- | --- |
| 已采纳 | `default_charts.keyword_table` | table 为主图，click 降序 + 趋势标签 | 批注 2026-07-09 |
| 已采纳 | `derived_metrics.click_trend_label` | IFS 趋势映射 | 与 DECK 公式一致 |
| 已采纳 | `limitations` | 记录 2026-06-30 静态快照 | 数据时效说明 |
| 已采纳 | `chart_rules.keyword_table` | top_n 单/多 site 规则 | 批注约定 |
