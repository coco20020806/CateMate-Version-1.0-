# CateMate AI 核心导航

## V1 Agent 启动顺序（2026-07-09）

后续 AI / agent / Cursor 接手 CateMate 时，先按下面顺序读取：

1. `docs/V1_ACCEPTANCE_SUMMARY.md`
2. `docs/PROJECT_STATUS.md`
3. `CateMate_processeddata/processed_manifest.yaml`
4. `config/data_modules/*.yaml`
5. 与任务相关的设计文档

当前推荐主链路：

```text
natural language request
-> case config
-> requirement understanding
-> module selection
-> deterministic planning spec
-> data requirement workbook
-> confirmation gate
-> PPT-ready workbook + HTML preview
```

主入口脚本：

- 一键链路：`scripts/run_natural_language_requirement_pipeline.py`
- 推荐模式：`--planning-mode module_selection`
- 确认门禁：`scripts/check_confirmation_gate.py`
- PPT-ready + HTML：`scripts/build_ppt_ready_from_confirmed_workbook.py`

最新成功 `module_selection` run 的 manifest：

- `outputs/pipeline_manifest_livestock_healthcare_vn_20260709_175204.json`

注意：

- AI 运行时优先读取 processed data，不直接反复打开大型 raw Excel。
- `config/data_modules/*.yaml` 是业务问题层；`processed_manifest.yaml` 是数据资产层。
- 任何 PPT-ready 生成都不能绕过 confirmation gate。

更新时间：2026-07-09

本文档给后续 AI / agent / Cursor 使用。开始任何 CateMate 开发或规划任务前，优先阅读本文件，再按任务类型读取对应文档。

## 一句话目标

CateMate 是一个类目分析数据需求与 PPT-ready 数据生成系统。核心原则是：

```text
用户自然语言需求
→ RequirementUnderstandingSpec（需求理解与澄清）
→ ModuleSelectionPlan（data module 选择）
→ RequirementPlanningSpec（AI planning 或 module_selection_adapter）
→ 结构化需求 / case config
→ 数据源与类目映射确认
→ confirmation gate
→ PPT-ready workbook
```

系统不直接伪造数据。所有数据必须来自可追溯源文件或 processed data。

## AI 必读核心文件

### 1. 项目状态

文件：`docs/PROJECT_STATUS.md`

用途：
- 当前工程完成了什么；
- 主要模块入口在哪里；
- 最近一次工程收口记录；
- 当前稳定链路和下一步方向。

### 2. 产品与业务原始构想

文件：`CateMate_新产品构想.md`

用途：
- 理解产品目标；
- 理解用户作为 PM / 策略分析师的工作方式；
- 理解 CateMate 为什么要做确认链路和可追溯数据。

### 3. 数据模块目录

文件：`docs/data_module_catalog.md`

用途：
- 人类可读的数据模块说明书；
- 描述每个 Excel 公式模块能回答什么问题；
- 说明 `CNCB 中间表 By site` 和 `DECK` 如何从 raw sheet 聚合数据。

### 4. 数据模块机器配置（Schema v2）

目录：`config/data_modules/`

标准文档：`docs/data_module_schema_v2.md`

**两层分工：**
- `CateMate_processeddata/processed_manifest.yaml` — **数据资产层**（processed table、字段、行数、源 workbook/sheet）
- `config/data_modules/*.yaml` — **业务问题层**（一个业务问题一个模块：能回答什么、默认图表、排序规则、口径限制）

当前 **active v2** 模块（planning agent 候选）：
- `config/data_modules/rm_monthly_category_performance.yaml`
- `config/data_modules/dashboard_history_market_trend.yaml`
- `config/data_modules/dashboard_daily_cncb_performance.yaml`
- `config/data_modules/dashboard_price_tier_distribution.yaml`
- `config/data_modules/dashboard_top_shop.yaml`
- `config/data_modules/dashboard_keywords.yaml`
- `config/data_modules/dashboard_top_listing.yaml`

模板：`config/data_modules/_template.yaml`（loader 自动跳过）

已废弃（仅历史说明，planning 不读取）：
- `config/data_modules/sph_category_dashboard_deck.yaml` — 已拆分为上述 6 个 dashboard 子模块

用途：
- 给规划 agent / chart generation agent 机器读取；
- 描述业务问题、source tables、字段语义、default_charts、limitations；
- planning agent 应**优先读 v2 active 模块**，再按需引用 manifest 字段细节。

### 5. Processed Data 设计

文件：`docs/processed_data_design.md`

用途：
- 说明 `CateMate_processeddata` 是给 AI 读取的数据层；
- 说明 processed CSV 与源 workbook/sheet 的追溯关系；
- 说明如何更新 processed data。

### 6. Processed Data 抽取配置

文件：`config/processed_data_sources.yaml`

用途：
- 定义从哪些 workbook/sheet 抽取哪些表；
- 定义输出 CSV；
- 定义去重键、更新模式、重要字段；
- 后续新增源表时先改这里。

### 7. Processed Data Manifest

文件：`CateMate_processeddata/processed_manifest.yaml`

用途：
- 记录每张 processed table 的源 workbook、sheet、字段、行数、抽取时间；
- 人工确认时通过它回源文件；
- AI 使用 processed data 时也应引用其中的 table_id 和 source 信息。

### 8. Requirement Understanding Layer（v1）

文件：`docs/requirement_understanding_layer_design.md`

核心代码：
- `catemate/understanding/schemas.py`
- `catemate/understanding/prompt_builder.py`
- `catemate/understanding/generator.py`
- `catemate/understanding/updater.py`
- `catemate/understanding/readiness.py`
- `scripts/run_requirement_understanding.py`
- `scripts/update_requirement_understanding.py`

用途：
- 在 module selection / planning 之前理解自然语言需求；
- 输出 `RequirementUnderstandingSpec`（默认 `ready_for_module_selection`）；
- 支持用户补充后更新 spec；
- **不**选 data module，**不**生成 planning spec / workbook。

### 8.5 Module Selection Layer（v1）

文件：`docs/module_selection_layer_design.md`

核心代码：
- `catemate/module_selection/schemas.py`
- `catemate/module_selection/context.py`
- `catemate/module_selection/prompt_builder.py`
- `catemate/module_selection/selector.py`
- `catemate/module_selection/validator.py`
- `scripts/run_module_selection.py`
- `scripts/validate_module_selection.py`

用途：
- 在 `ready_for_module_selection` 后遍历全部 active data modules；
- 输出 `ModuleSelectionPlan`（selected/optional/rejected/needs_confirmation）；
- 继承 module `default_charts`；validator 确定性兜底；
- **不**直接生成 workbook；planning 由下一层 adapter 或 AI planning 负责。

### 8.6 Module Selection → Planning Adapter（v1）

文件：`docs/module_selection_to_planning_design.md`

核心代码：
- `catemate/planning/module_selection_adapter.py`
- `scripts/run_module_selection_to_planning.py`
- `scripts/validate_planning_from_module_selection.py`

用途：
- 确定性把 `ModuleSelectionPlan` 转成 `RequirementPlanningSpec`；
- `proposed_charts` 来自 `selected_chart_intents`，不从零发明图表；
- optional / rejected 按规则处理；旧 AI planning 链路保留。

### 9. Case Config 设计

文件：`docs/case_config_design.md`

用途：
- 说明 case config 如何驱动数据需求 workbook；
- 说明一个需求可以同时使用多个源文件；
- 记录 HKCB Collectible 和 VN Pet Healthcare 两个样例。

### 10. Case Config 文件

目录：`config/cases/`

当前文件：
- `config/cases/hkcb_collectible.yaml`
- `config/cases/pet_healthcare_vn.yaml`

用途：
- 描述真实需求样例；
- 作为需求结构化的目标格式之一；
- 后续 AI 可以先产出 case config 草稿。

### 11. 自然语言 → Case Config 草稿

文件：`docs/natural_language_case_config_design.md`

核心代码：
- `catemate/case_generation/prompt_builder.py`
- `catemate/case_generation/generator.py`
- `catemate/case_generation/context_loader.py`
- `scripts/run_natural_language_to_case_config.py`

用途：
- 将用户自然语言需求转成 `CategoryAnalysisCaseConfig` 草稿；
- 输出 YAML 供人工复核；
- 作为 planning / workbook 流程前置步骤。

### 12. AI Planning Layer

文件：`docs/ai_planning_layer_design.md`

核心代码：
- `catemate/ai/settings.py`
- `catemate/ai/client.py`
- `catemate/planning/schemas.py`
- `catemate/planning/context_loader.py`
- `catemate/planning/prompt_builder.py`
- `catemate/planning/planner.py`
- `catemate/planning/requirement_adapter.py`
- `scripts/run_ai_planning_case.py`
- `scripts/run_planning_to_requirement_workbook.py`

用途：
- 读取 case config + processed manifest + data module YAML；
- 调用 DeepSeek / OpenAI-compatible provider；
- 输出 `RequirementPlanningSpec` JSON；
- 再由确定性 adapter 转成数据需求/确认 workbook。

两步入口：
1. `scripts/run_ai_planning_case.py`：只生成 planning JSON
2. `scripts/run_planning_to_requirement_workbook.py`：从 JSON 生成 workbook

### 13. 自然语言一键需求链路（主入口）

脚本：`scripts/run_natural_language_requirement_pipeline.py`

用途：
- `--planning-mode ai_direct`：自然语言 → case config YAML → AI planning JSON → 数据需求/确认 workbook；
- `--planning-mode module_selection`：自然语言 → case config YAML + understanding JSON + module selection JSON + deterministic planning JSON → 数据需求/确认 workbook；
- 每一步产物单独保存，方便产品经理复核；
- 不替代三个独立脚本，只做 Python 内串联。

同步输出 pipeline manifest：
- `outputs/pipeline_manifest_<case_id>_<timestamp>.json`
- 记录本轮 `planning_mode`、`case_config_path`、`understanding_spec_path`、`module_selection_plan_path`、`planning_spec_path`、`requirement_workbook_path`
- 不含 API key；中途失败也会写入已完成产物路径

核心代码：
- `catemate/pipeline/manifest.py`

### 14. Streamlit 与 pipeline manifest

- `app/streamlit_dashboard.py` 打开时优先读取 `outputs/` 中最新的 `pipeline_manifest_*.json`
- 若 manifest 内 workbook 有效，则默认选中该 workbook，并展示关联 case config / planning spec
- 同时展示 confirmation gate 摘要（总数 / 已确认 / 不需要 / 待确认 / 阻塞 / 非阻塞提醒 / 可否 PPT-ready）
- 仍可手动选择任意旧 workbook；无关联 manifest 时照常编辑确认项

## 关键代码入口

### 数据需求 workbook

- `catemate/modules/category_analysis_data_requirement.py`
- `scripts/run_category_requirement_case.py`
- `scripts/run_category_requirement_demo.py`

### 确认门禁

- `catemate/core/confirmation_gate.py`
- `catemate/core/confirmation_reader.py`
- `catemate/core/confirmation_writer.py`
- `scripts/check_confirmation_gate.py`

### Streamlit V1 总控台

- `app/streamlit_dashboard.py`
- 单页完成：新建需求 → manifest 复核 → 确认编辑 → PPT-ready 生成
- `app/confirmation_editor.py` 提供可复用的确认编辑 UI
- `app/streamlit_app.py` 为兼容入口，转发至总控台

### PPT-ready workbook

案例专用（仍保留）：
- `catemate/modules/ppt_ready_workbook.py`
- `catemate/modules/pet_healthcare_ppt_ready_workbook.py`
- `scripts/build_ppt_ready_workbook.py`
- `scripts/build_pet_healthcare_ppt_ready_workbook.py`

通用 v1（推荐新链路使用）：
- `catemate/ppt_ready/`
- `scripts/build_ppt_ready_from_confirmed_workbook.py`
- 输入：confirmed requirement workbook + planning spec + processed data
- **必须先通过 confirmation gate**；失败则不写文件
- 只读 processed CSV，不读 raw Excel；不做 PPT / 脱敏
- 默认同步生成 `*_preview.html`（可用 `--no-html-preview` 关闭）


### Processed Data 抽取

- `scripts/preprocess_raw_data_sources.py`

### AI Planning Layer

- `catemate/ai/`
- `catemate/planning/`
- `scripts/run_ai_planning_case.py`
- `scripts/run_planning_to_requirement_workbook.py`
- `docs/ai_planning_layer_design.md`

### 自然语言 Case Config 生成

- `catemate/case_generation/`
- `scripts/run_natural_language_to_case_config.py`
- `docs/natural_language_case_config_design.md`

### 自然语言一键需求链路（主入口）

- `scripts/run_natural_language_requirement_pipeline.py`
- `catemate/pipeline/manifest.py`
- 串联：自然语言 → case config →（ai_direct 或 module_selection）→ 确认 workbook
- 额外输出：`outputs/pipeline_manifest_<case_id>_<timestamp>.json`
- 中间产物均保留；独立分步脚本仍可用
- Streamlit 默认读取最新 manifest

## 数据读取规则

1. AI 运行时优先读取 `CateMate_processeddata`。
2. 不要在规划阶段反复打开大型 Excel。
3. 需要判断一个数据模块能否回答问题时，先读：
   - `config/data_modules/*.yaml`
   - `CateMate_processeddata/processed_manifest.yaml`
   - `docs/data_module_catalog.md`
4. 只有需要新增数据模块、验证源字段、或人工追溯时，才打开源 Excel。
5. 类目映射优先读 processed 类目树：
   - `CateMate_processeddata/sph_category_tree_lookup.csv`

## 规划 / 数据生成 Agent 固定启动流程

后续任何规划 agent、数据生成 agent、Cursor 执行者在开始处理一个新类目分析需求前，必须按以下顺序读取项目上下文：

1. 先读本文件：
   - `docs/AI_CORE_INDEX.md`

2. 再读 processed data manifest：
   - `CateMate_processeddata/processed_manifest.yaml`

   用途：
   - 判断当前 AI 数据库里有哪些 table；
   - 判断每张 table 来自哪个 raw workbook / sheet；
   - 判断字段、行数、更新时间、抽取规则；
   - 后续输出数据需求或 PPT-ready workbook 时引用可追溯来源。

3. 再读数据模块机器配置：
   - `config/data_modules/*.yaml`

   用途：
   - 判断已有数据模块能回答什么业务问题；
   - 判断适合生成哪些图表类型；
   - 判断数据限制和注意事项；
   - 决定是否需要用户补充新数据。

4. 如需理解业务方法论，再读：
   - `docs/data_module_catalog.md`
   - `docs/category_analysis_data_requirement_module.md`
   - `docs/ppt_ready_workbook_design.md`

5. 如需处理具体案例，再读：
   - `config/cases/*.yaml`
   - `docs/example_case_hkcb_collectible_workflow.md`
   - `docs/example_case_vn_livestock_pet_healthcare.md`

默认原则：

- agent 不直接从大型 Excel 开始工作；
- agent 先判断 processed data 和 data module 是否足够；
- 如果不足，输出需要用户确认或补充的数据清单；
- 只有新增数据模块、核验字段、或人工追溯时，才打开 raw workbook。

## 确认门禁规则

PPT-ready workbook 生成前，确认记录必须全部是：

- `已确认`
- `不需要`

如果确认记录中的 `是否阻止PPT-ready生成` 明确为 `否`，该项不会阻止 PPT-ready workbook 生成，但仍会保留在确认工作台中供用户查看和处理。

除非该列明确为 `否`，以下状态都会阻止生成：

- `待确认`
- `待补充`
- `已补充`
- `阻塞`

如果用户补充了新数据，应先标记为 `已补充`，由 agent 复检后再转为 `已确认`。

## 重要方法论

### 数据需求模块

文件：
- `docs/category_analysis_data_requirement_module.md`

记录：
- 数据需求 workbook 的目标；
- 确认记录如何服务真实工作；
- 为什么先产出 Excel 数据需求集合，而不是直接产出报告。

### PPT-ready workbook

文件：
- `docs/ppt_ready_workbook_design.md`

记录：
- PPT-ready workbook 是纯数据表；
- 支持图表类型；
- 不做对外脱敏；
- 可选 HTML 预览后续再做。

### 示例案例

文件：
- `docs/example_case_hkcb_collectible_workflow.md`
- `docs/example_case_vn_livestock_pet_healthcare.md`

记录：
- 两个真实案例的业务背景、需求来源、数据源和处理思路。

## 当前下一阶段建议

1. planning spec → requirement workbook 已打通；后续重点是双案例验收规划质量。
2. 让数据需求项进一步补齐 processed fields 级别细节。
3. 通用 PPT-ready v1 已可用（含默认 HTML preview）；后续按案例丰富过滤与口径（仍须只读 processed data）。
4. 视需要再接正式 PPT 生成，且不得绕过 confirmation gate。
