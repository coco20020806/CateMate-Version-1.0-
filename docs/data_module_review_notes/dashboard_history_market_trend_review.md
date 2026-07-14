# dashboard_history_market_trend 批注

- **正式配置**：`config/data_modules/dashboard_history_market_trend.yaml`
- **主表**：`dashboard_history`（source sheet: 过去数据）
- **source_deck_part**：DECK Part 1
- **批注人**：（填写）
- **最后更新**：2026-07-09（已落地至正式 YAML）

> 普适性规则见本目录 `README.md`（类目 meaning、DECK Part 命中规则）

---

## 元信息

- [已采纳] `module_name` 去掉「（DECK Part 1）」→「看板市场历史趋势」

---

## business_purpose

- [已采纳] `description` 不以 DECK 开头，改为基于「过去数据」sheet 的描述
- [已采纳] `typical_questions` 首条为 DECK Part 1 强命中场景

---

## fields

### 类目 dimensions

- [已采纳] meaning 改为一级类目 / 二级类目 / 三级类目

---

## default_charts

- [已采纳] `market_history_trend.title_template` 去掉「（DECK Part 1）」

---

## planning_hints

- [已采纳] 新增 `explicit_triggers`：DECK Part 1 / 过去数据 等
- [已采纳] `avoid_when`：仅泛泛提 DECK 未指明 Part 1 时不命中

---

## 待修改清单

| 状态 | YAML 路径 | 建议修改 | 原因 |
| --- | --- | --- | --- |
| 已采纳 | 全文 + 普适规则 | 见上方各节 | 2026-07-09 批注已落地 |
