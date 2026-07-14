# Data Module 批注文档

本目录用于**产品/业务侧**对正式 YAML 配置写自然语言批注。

**不要直接改** `config/data_modules/*.yaml`。正式配置由 Cursor 按批注整理后统一更新。

## 普适性规则（所有模块适用）

1. **类目 meaning**  
   `fields.dimensions` 中 L1/L2/L3 统一写：**一级类目 / 二级类目 / 三级类目**。  
   不要使用「全球 BE 一级类目」等表述。

2. **DECK Part 表述**  
   - **不要**在以下位置显性写「DECK Part X」：  
     `module_name`、`business_purpose.description`、`default_charts.title_template`、图表 notes 中的展示文案  
   - **应该**把 DECK Part 写在命中规则里：  
     `lineage.source_deck_part`、`planning_hints.explicit_triggers`、`typical_questions`（用户明确提到时）、`use_when` / `avoid_when`  
   - 用户仅泛泛说「DECK」而未指明 Part 时，**不应**误命中本模块

## 对应关系

| 批注文档 | 正式 YAML | source_deck_part |
|----------|-----------|------------------|
| `rm_monthly_category_performance_review.md` | `rm_monthly_category_performance.yaml` | （无，非 DECK 模块） |
| `dashboard_history_market_trend_review.md` | `dashboard_history_market_trend.yaml` | Part 1 |
| `dashboard_daily_cncb_performance_review.md` | `dashboard_daily_cncb_performance.yaml` | Part 2 |
| `dashboard_price_tier_distribution_review.md` | `dashboard_price_tier_distribution.yaml` | Part 3/4 |
| `dashboard_top_shop_review.md` | `dashboard_top_shop.yaml` | Part 5 |
| `dashboard_keywords_review.md` | `dashboard_keywords.yaml` | Part 6 |
| `dashboard_top_listing_review.md` | `dashboard_top_listing.yaml` | Part 7 |

标准字段说明见：`docs/data_module_schema_v2.md`

## 推荐工作流

```text
1. 在本目录 *.md 写批注（自然语言，随便写）
2. 整理成「待修改清单」（可写在各文件底部）
3. Cursor 按清单更新正式 YAML
4. 跑验证：python scripts/validate_data_modules_v2.py
```

## 批注写法建议

- 用二级标题对应 YAML 区块，例如 `## business_purpose`、`## default_charts.price_tier_share`
- 写清楚：**现在 YAML 里是什么** → **建议改成什么** → **为什么**
- 状态标记（可选）：`[待改]` / `[已采纳]` / `[暂缓]` / `[疑问]`
- 批注历史保留在文档里，不要删旧意见，划掉或标注「已处理」即可
