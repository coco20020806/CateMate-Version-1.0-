# Module Selection → Planning Adapter 设计（v1）

更新时间：2026-07-09

## 为什么需要 adapter

Module Selection Layer v1 已能遍历全部 active data modules，并为每个模块输出 `selected_chart_intents`（含 chart_type、x_axis、y_axis、sort_rule 等继承字段）。

若仍让 AI 直接生成 `RequirementPlanningSpec`，模型可能：

- 发明不存在的图表；
- 忽略 module selection 已确定的 chart intents；
- 与 data module YAML 的 default_charts 不一致。

因此新增 **确定性 adapter**，把 `ModuleSelectionPlan` 转成 `RequirementPlanningSpec` 草稿，尽量不再让 AI 自由发挥。

## 链路位置

```text
自然语言需求
  ↓
RequirementUnderstandingSpec（v1）
  ↓
ModuleSelectionPlan（v1）
  ↓
module_selection_adapter（确定性 Python，本设计）
  ↓
RequirementPlanningSpec
  ↓
requirement_adapter（确定性 Python，已有）
  ↓
数据需求/确认 workbook
```

旧 AI planning 链路保留，不删除：

```text
case config + data modules → AI planner → RequirementPlanningSpec
```

两条链路最终都汇入 `requirement_adapter` → workbook。

## 核心代码

- `catemate/planning/module_selection_adapter.py`
  - `build_planning_spec_from_module_selection()`
  - `validate_planning_spec_against_module_selection()`
- `scripts/run_module_selection_to_planning.py`
- `scripts/validate_planning_from_module_selection.py`

## 转换规则

### 从 RequirementUnderstandingSpec 继承

- `case_id`、`project_name`、`interpreted_request`
- `target_categories`（inferred_category / target_category_text）
- `assumptions`、`missing_data_questions`（clarifying_questions）

### 从 ModuleSelectionPlan 生成 proposed_charts

遍历以下三类模块的 `selected_chart_intents`：

| 模块决策 | optional 标记 | selection_reason |
|---------|--------------|------------------|
| selected | `false` | module.reason + matched_user_need |
| needs_confirmation | `false` | 同上 + 「模块待用户确认」 |
| optional | `true` | 同上 + 「optional module」；title 加「（可选）」 |

每个 `SelectedChartIntent` → 一个 `PlanningChartProposal`：

- `chart_id`: `{module_id}_{chart_intent}`（安全化、截断）
- `title`: `chart_title` 中 `{category}` 替换为 inferred_category
- `chart_type` / `table_ids` / `metrics(y_axis)` / `dimensions` / `sort_rule` / `top_n` / `rule_source` 继承自 selection
- 新增字段：`chart_intent`、`x_axis`、`y_axis`、`series`、`module_decision`、`selection_reason`、`optional`

维度组装规则（确定性）：

- `trend`: dimensions = x_axis + series + chart.dimensions
- `share`: 保留 chart.dimensions，必要时补 x_axis
- `bar`: x_axis 置前
- `table`: metrics 可为空，dimensions 来自 chart.dimensions

### rejected module

- **不**进入 `proposed_charts`
- 写入 `source_notes`: `Rejected module <module_id>: <reason>`

### 无 chart intents 的模块

- 生成 `validation_warnings`，adapter 不崩溃
- 该模块不产生 chart

## PlanningChartProposal 新增字段（均可选，旧 JSON 兼容）

- `chart_intent`
- `x_axis`
- `y_axis`
- `series`
- `sort_rule`
- `top_n`
- `rule_source`
- `module_decision`
- `selection_reason`
- `optional`

`RequirementPlanningSpec` 另增 `validation_warnings: list[str]`。

## Workbook 兼容

`requirement_adapter._build_chart_requirements` 把新字段映射到 `ChartDataRequirementRow`。

`category_analysis_data_requirement._write_chart_ppt_requirements` 仅在行中存在扩展字段时追加列：

- 图表意图、X轴、Y轴、系列、排序规则、是否可选、模块选择理由

旧 planning JSON 无这些字段时，workbook 不出现扩展列（或列为空，不影响 confirmation gate）。

## 校验

`validate_planning_spec_against_module_selection` 检查：

- non-optional chart 的 `data_module_id` 来自 selected / needs_confirmation
- optional chart 来自 optional module
- `chart_intent` / `table_ids` / `chart_type` 与 selection 一致
- rejected module 不出现在 proposed_charts
- chart 数量与 selection 中 intent 数量一致

以 `SERIOUS:` 前缀标记严重不一致；校验脚本对严重错误 `exit 1`。

## CLI

```bash
python scripts/run_module_selection_to_planning.py \
  --understanding-spec outputs/requirement_understanding_*.json \
  --module-selection-plan outputs/module_selection_*.json

python scripts/validate_planning_from_module_selection.py \
  --planning-spec outputs/planning_spec_from_module_selection_*.json \
  --module-selection-plan outputs/module_selection_*.json
```

## 主 pipeline 接入（已实现）

`scripts/run_natural_language_requirement_pipeline.py` 已支持：

- `--planning-mode ai_direct`：旧链路（自然语言 → case config → AI planning → workbook）
- `--planning-mode module_selection`：新链路（自然语言 → case config + understanding + module selection + deterministic planning → workbook）
- stop flags：
  - 通用：`--stop-after-case-config`、`--stop-after-planning`
  - 新链路：`--stop-after-understanding`、`--stop-after-module-selection`

当前 v1 **不修改** Streamlit、PPT-ready、confirmation gate、AI provider 配置。
