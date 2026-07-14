# Module Selection Layer 设计（v1）

更新时间：2026-07-09

## 定位

Module Selection 是 **业务分析动作选择** 层：在 Requirement Understanding 之后、AI Planning 之前，决定哪些 data module 参与后续分析。

```text
RequirementUnderstandingSpec (ready_for_module_selection)
        ↓
ModuleSelectionPlan
        ↓
RequirementPlanningSpec（后续，本层不实现）
```

本层：
- **遍历**所有 active data modules
- 为每个 module 给出 decision + reason
- 为 selected 模块继承 `default_charts` / `chart_rules` / `limitations`
- **不**生成 planning spec 或 workbook

## 与上下游关系

| 层 | 输入 | 输出 |
|----|------|------|
| Requirement Understanding | 自然语言 | `RequirementUnderstandingSpec` |
| **Module Selection（本层）** | Understanding spec + active modules | `ModuleSelectionPlan` |
| AI Planning | case config + modules + manifest | `RequirementPlanningSpec` |

## 为什么必须遍历所有 active module

CateMate 有 7 个 active v2 模块，每个模块回答不同业务问题。  
Module selection 必须对 **每一个** active module 明确判断：

- 选（selected）
- 可选（optional）
- 需确认（needs_confirmation）
- 不选（rejected）

避免 AI 只挑熟悉的模块而遗漏可选项；rejected 也必须有理由，便于人工复核。

## 四种 decision 状态

| decision | 含义 |
|----------|------|
| `selected` | 明确匹配用户需求，进入后续 planning |
| `optional` | 可能有用但不强制，如重复趋势口径的备选模块 |
| `needs_confirmation` | 建议纳入但需用户确认，不阻塞推进 |
| `rejected` | 明确不匹配，必须写 reason |

## selected_chart_intents 如何继承

1. AI 优先从 `module.default_charts` 挑选与 `analysis_intents` 匹配的 `chart_intent`
2. Validator 用 default_chart 补齐 `x_axis` / `y_axis` / `series` / `dimensions` / `sort_rule`
3. 若 AI 未给 chart，validator 按 intent 启发式自动补齐
4. 新增 chart 必须 `rule_source=system_inferred` + `override_reason`（v1 尽量少）

## Validator 兜底规则

`validate_and_normalize_module_selection_plan()`：

- 漏掉的 active module → 自动 `rejected`，reason 固定
- 未知 module_id → `global_warnings` 并移除
- 空 `source_tables` → 从 `lineage.source_tables` 填充
- 空 `selected_chart_intents` → 从 `default_charts` 自动匹配
- chart 字段不在 module fields → `global_warnings`（不抛异常）
- `inherited_chart_rules` / `inherited_limitations` 从 module YAML 补齐

## 趋势模块重复处理

`rm_monthly_category_performance` vs `dashboard_history_market_trend`：

- 默认优先 RM（长时间窗口）
- 用户明确 DECK/看板/近12个月 → 可将 history 标 optional 或 selected
- 两者不应无说明地同时 selected；reason 需说明口径差异

## 代码入口

| 组件 | 路径 |
|------|------|
| Schema | `catemate/module_selection/schemas.py` |
| Context | `catemate/module_selection/context.py` |
| Prompt | `catemate/module_selection/prompt_builder.py` |
| Selector | `catemate/module_selection/selector.py` |
| Validator | `catemate/module_selection/validator.py` |
| CLI | `scripts/run_module_selection.py` |
| 验证 | `scripts/validate_module_selection.py` |

## 示例：VN Pet Healthcare

Understanding：`market_trend`, `top_listing`, `keywords`, `price_tier`, `price_reference`

期望 selection：
- **selected**：`rm_monthly_category_performance`（或 history 为 optional）、`dashboard_top_listing`、`dashboard_keywords`、`dashboard_price_tier_distribution`
- **rejected/optional**：`dashboard_daily_cncb_performance`（无日度需求）、`dashboard_top_shop`（无头部卖家需求）

## 示例：HKCB Collectible

Understanding：`market_trend`, `price_tier`, `keywords`, `site_comparison`

期望 selection：
- **selected**：`rm_monthly_category_performance`、`dashboard_price_tier_distribution`、`dashboard_keywords`
- **optional/rejected**：`dashboard_top_listing`、`dashboard_top_shop`（需有理由）

## CLI

```bash
python scripts/run_module_selection.py \
  --understanding-spec outputs/requirement_understanding_xxx.json

python scripts/validate_module_selection.py \
  --module-selection-plan outputs/module_selection_xxx.json

python scripts/validate_module_selection.py   # 无参数运行内置单元测试
```
