# CateMate AI Planning Layer 设计（v1）

更新时间：2026-07-09

## 目标

新增一个最小 AI planning layer：读取 case config、processed manifest、data module YAML，调用 AI provider，输出结构化 `RequirementPlanningSpec` JSON；并已支持把该 JSON 确定性转换成数据需求/确认 workbook。

当前链路：

```text
case config
+ processed_manifest.yaml
+ config/data_modules/*.yaml
  ↓
ModuleSelectionPlan（v1）
  ↓
module_selection_adapter（确定性，可选）
  ↓
RequirementPlanningSpec JSON
  ↓
requirement_adapter（确定性 Python）
  ↓
CategoryAnalysisRequirementSpec
  ↓
数据需求/确认 workbook
```

## 为什么 AI 只输出 planning spec，不直接写 Excel

1. planning 层先做“能做什么 / 缺什么”的判断，避免模型直接碰大 Excel。
2. 结构化 JSON 更容易校验、回放和后续复用。
3. Excel 写入仍由现有 `CategoryAnalysisRequirementSpec -> workbook` 代码负责，职责分离更清晰。
4. planning spec 已进入确认 workbook，但仍不让 AI 直接写 Excel。

## Provider 配置

统一通过环境变量选择：

- `CATEMATE_AI_PROVIDER=openai_compatible`（默认）
- `CATEMATE_AI_PROVIDER=deepseek`

### DeepSeek

- `DEEPSEEK_API_KEY`（必填）
- `DEEPSEEK_MODEL`（可选，默认 `deepseek-v4-pro`）
- `DEEPSEEK_BASE_URL`（可选，默认 `https://api.deepseek.com`）

### OpenAI-compatible

- `CATEMATE_OPENAI_BASE_URL`（可选，默认 `http://127.0.0.1:8080/v1`）
- `CATEMATE_OPENAI_API_KEY`（可选，默认 `pwd`）
- `CATEMATE_OPENAI_MODEL`（可选，默认 `gpt-5.5`）

可选共用参数：

- `CATEMATE_AI_TEMPERATURE`（默认 `0.2`）
- `CATEMATE_AI_MAX_TOKENS`

API key 只从环境变量读取，不写进代码或文档样例。

## 输入文件

1. case config：`config/cases/*.yaml`
2. processed manifest：`CateMate_processeddata/processed_manifest.yaml`
3. data modules：`config/data_modules/*.yaml`

AI 不会直接读取大型 raw Excel。

上游可选来源：

- `scripts/run_natural_language_to_case_config.py` 先从自然语言生成 case config 草稿 YAML；
- 再把草稿作为 planning 输入；
- 或直接用一键入口 `scripts/run_natural_language_requirement_pipeline.py`
  （自然语言 → case config → planning → 确认 workbook，中间产物均保留）。
- **新链路（v1）**：`RequirementUnderstandingSpec` → `ModuleSelectionPlan` → `module_selection_adapter` → `RequirementPlanningSpec`（不调用 AI，见 `docs/module_selection_to_planning_design.md`）。

## 输出

### 1) Planning JSON

默认：

`outputs/planning_spec_<case_id>_<timestamp>.json`

对应 schema：`RequirementPlanningSpec`

核心字段：

- `interpreted_request`
- `target_categories`
- `matched_data_modules`
- `proposed_charts`
- `missing_data_questions`
- `assumptions`
- `source_notes`

### 2) 数据需求 workbook（从 planning JSON）

默认：

`outputs/category_analysis_data_requirement_from_planning_<case_id>_<timestamp>.xlsx`

写入规则：

- sheet 名称仍是原来 8 个；
- `数据需求清单` / `图表PPT数据需求` / `分析计划` / `确认记录` 可追加 planning 字段；
- `missing_data_questions` 会进入确认记录；
- confirmation gate 继续只依赖原核心确认字段。

## 代码入口

- `catemate/ai/settings.py`
- `catemate/ai/client.py`
- `catemate/planning/schemas.py`
- `catemate/planning/context_loader.py`
- `catemate/planning/prompt_builder.py`
- `catemate/planning/planner.py`
- `catemate/planning/requirement_adapter.py`
- `catemate/planning/module_selection_adapter.py`
- `scripts/run_ai_planning_case.py`
- `scripts/run_planning_to_requirement_workbook.py`
- `scripts/run_module_selection_to_planning.py`
- `scripts/validate_planning_from_module_selection.py`
- `scripts/run_natural_language_requirement_pipeline.py`（一键串联入口）

两步运行示例：

```bash
# 1. 只生成 planning JSON
python scripts/run_ai_planning_case.py --case-config config/cases/pet_healthcare_vn.yaml

# 2. 从已有 planning JSON 生成确认 workbook
python scripts/run_planning_to_requirement_workbook.py --case-config config/cases/pet_healthcare_vn.yaml --planning-spec outputs/planning_spec_pet_healthcare_vn_20260708_172245.json
```

自然语言一键串联（中间产物均保留）：

```bash
python scripts/run_natural_language_requirement_pipeline.py --request-text "……需求原文……" --planning-mode ai_direct
python scripts/run_natural_language_requirement_pipeline.py --request-text "……需求原文……" --planning-mode module_selection
```

旧链路仍可单独运行：

```bash
python scripts/run_category_requirement_case.py config/cases/pet_healthcare_vn.yaml
```

## 当前限制

- 还未做自动 JSON 修复。
- 还未做 prompt 质量评估与回归集。
- planning 接入 workbook 主要覆盖 module/table/chart/missing questions；更细的 manifest 字段补全可后续增强。
- 若本地兼容服务不支持 `response_format=json_object`，client 会自动退回普通 completion，但仍要求返回合法 JSON。
- 一键脚本只做串联，不替代独立脚本；失败时会保留已完成步骤的产物路径。

## 下一步

1. 用 HKCB Collectible 和 VN Pet Healthcare 双案例验收规划质量。
2. 数据需求清单进一步引用 processed manifest 的字段级细节。
3. 视需要补充轻量自动修复与结果比较脚本。
