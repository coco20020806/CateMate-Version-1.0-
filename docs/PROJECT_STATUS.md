# CateMate 工程状态

## V1 最新状态（2026-07-09）

CateMate V1 已完成一条可验收的端到端链路：

```text
自然语言需求
-> case config 草稿
-> RequirementUnderstandingSpec
-> ModuleSelectionPlan
-> deterministic RequirementPlanningSpec
-> 数据需求 / 确认 workbook
-> Streamlit 人工确认
-> confirmation gate
-> PPT-ready workbook
-> HTML 图表预览
```

当前推荐主链路是 `module_selection` 模式；旧的 `ai_direct` AI planning 模式仍保留用于对照。

最近一次成功跑通的 `module_selection` 产物：

- `outputs/pipeline_manifest_livestock_healthcare_vn_20260709_175204.json`
- `outputs/generated_case_config_livestock_healthcare_vn_20260709_175204.yaml`
- `outputs/requirement_understanding_livestock_healthcare_vn_20260709_175204.json`
- `outputs/module_selection_livestock_healthcare_vn_20260709_175204.json`
- `outputs/planning_spec_from_module_selection_livestock_healthcare_vn_20260709_175204.json`
- `outputs/category_analysis_data_requirement_from_planning_livestock_healthcare_vn_20260709_175204.xlsx`

V1 收口验收说明见：`docs/V1_ACCEPTANCE_SUMMARY.md`。

当前边界：

- 正式 PPT 自动生成不属于 V1，后续单独设计。
- HTML preview 是图表形态预览，不是最终 PPT。
- data module 文案与业务判断仍需要 PM 逐步人工校验。
- 对某些模块应为 selected 还是 optional 的判断，需要通过真实案例继续调优。

更新时间：2026-07-09

## 当前阶段

CateMate MVP 已完成第一条可运行闭环，并开始接入 AI planning layer：

```text
自然语言需求
  ↓
RequirementUnderstandingSpec（v1）
  ↓
ModuleSelectionPlan（v1，可选独立运行）
  ↓
module_selection_adapter → RequirementPlanningSpec（确定性，v1 新增）
  或 case config / AI planning（RequirementPlanningSpec，旧链路保留）
  ↓
数据需求/确认 workbook
  ↓
Streamlit 人工确认
  ↓
confirmation gate
  ↓
PPT-ready workbook
```

说明：AI planning → 确认 workbook 已打通；自然语言一键串联脚本已支持 `ai_direct` 与 `module_selection` 双模式（中间产物均保留）。

## 已完成模块

### 0. Pydantic Schema 基础层

核心代码：

- `catemate/schemas/enums.py`
- `catemate/schemas/category_requirement.py`
- `catemate/schemas/confirmation.py`
- `catemate/schemas/ppt_ready.py`

当前已固化的枚举：

- 确认状态：`待确认`、`待补充`、`已补充`、`已确认`、`不需要`、`阻塞`
- 图表类型：`bubble`、`bar`、`trend`、`share`、`table`
- 类目层级：`L1`、`L2`、`L3`、`unknown`
- 数据源状态：`available`、`missing`、`partial`、`not_needed`、`blocked`

用途：

- 为 DeepSeek / OpenAI 的结构化输出做准备。
- 为 LlamaIndex Workflow 节点输入输出做准备。
- 减少 dict / Excel 行 / dataclass 之间的隐式字段约定。

### 1. 数据需求/确认模块

入口：

- `scripts/run_category_requirement_demo.py`

核心代码：

- `catemate/modules/category_analysis_data_requirement.py`
- `catemate/data/source_scanner.py`
- `catemate/data/category_tree.py`

输出：

- 数据需求/确认 workbook
- 预处理类目树 `CateMate_processeddata/sph_category_tree_lookup.csv`

### 2. 确认门禁

入口：

- `scripts/check_confirmation_gate.py`

核心代码：

- `catemate/core/confirmation_gate.py`
- `catemate/core/confirmation_reader.py`
- `catemate/core/confirmation_writer.py`

规则：

- 只有 `已确认` 和 `不需要` 可以通过。
- `待确认`、`待补充`、`已补充`、`阻塞` 都会阻止 PPT-ready workbook 生成。

### 3. Streamlit V1 总控台

入口：

- `app/streamlit_dashboard.py`（推荐）
- `app/streamlit_app.py`（兼容转发）

当前交互（双阶段确认）：

- **阶段 A 澄清 gate**：`catemate/understanding/clarification.py`；manifest 状态 `awaiting_clarification` / `clarification_completed`；`run_pipeline_continue_from_manifest` 续跑。
- **阶段 B workbook gate**：`app/confirmation_editor.py`；须保存确认结果后才可 PPT-ready。
- 单页串联：新建需求 → 理解 → 澄清 → module selection → workbook 确认 → PPT-ready。

新增代码：

- `catemate/understanding/clarification.py`
- `app/clarification_editor.py`
- `scripts/validate_clarification_gate.py`

### 4. PPT-ready workbook 生成器

入口：

- `scripts/build_ppt_ready_workbook.py`

核心代码：

- `catemate/modules/ppt_ready_workbook.py`

当前输出 sheet：

- `ppt_data_catalog`
- `data_notes`
- `site_performance_l2`
- `l3_distribution`
- `monthly_trend_by_site`

当前计算逻辑：

- 数据源：`CateMate_rawdata/SPH 气泡图_月度趋势图 for RM .xlsx`
- Sheet：`Raw data`
- 默认筛选：`Hobbies & Collections > Collectible Items`
- 最新月份：从源数据自动识别
- YoY：最新月份 vs 去年同月
- GMV：`gmv_usd` 求和
- Orders：`orders` 求和
- ABS：`GMV / Orders`

## 当前基线产物

已生成并验收字段结构的 PPT-ready workbook：

- `outputs/ppt_ready_workbook_20260707_222836.xlsx`

第二个真实案例的 PPT-ready workbook：

- `outputs/ppt_ready_pet_healthcare_vn_20260708_120702.xlsx`

## 设计约束

- PPT-ready workbook 是内部数据包，不是对外交付物。
- 脱敏规则留到后续 PPT 生成模块。
- HTML preview 预留开关，但当前不实现。
- 缺数据项不能生成假数据。
- 价格段和关键词模块暂不做。

## 建议下一步

优先级建议：

1. 用 HKCB Collectible 和 VN Pet Healthcare 双案例验收 planning quality。
2. 让数据需求项进一步引用 processed fields。
3. 将第二案例的独立生成器抽象进通用 PPT-ready workbook 生成框架。
4. 让 PPT-ready 生成逐步改读 processed CSV。
5. 后续再实现 HTML preview 和 PPT 生成。

## 第二案例：VN Pet Healthcare

源文件：

- `CateMate_rawdata/2026 SPH 品类数据看板.xlsx`

目标口径：

- Site: `VN`
- L1: `Pets`
- L2: `Pet Healthcare`

已支持输出：

- `vn_pet_health_trend`：来自 `过去数据`，用于大盘趋势。
- `vn_pet_health_price_tier`：来自 `price tier`，用于价格段分布。
- `vn_pet_health_avg_price`：来自 `热门商品`，用于 Top listing 口径下的 L3 平均价格参考。
- `vn_pet_health_top_listing`：来自 `热门商品`，用于 Top listing。

注意：

- `avg_price_by_l3` 的平均价来自 Top listing 源，不代表全量 SKU 均价。
- `DECK` 中 Part 1 / Part 4 的公式只作为逻辑参考，实际计算从底层 sheet 重新筛选 `VN > Pets > Pet Healthcare`。

## 2026-07-09 Module Selection → Planning Adapter v1

新增：
- `catemate/planning/module_selection_adapter.py` — 确定性 `ModuleSelectionPlan` → `RequirementPlanningSpec`
- `scripts/run_module_selection_to_planning.py`
- `scripts/validate_planning_from_module_selection.py`
- `docs/module_selection_to_planning_design.md`

扩展：
- `PlanningChartProposal` 增加 chart_intent / x_axis / y_axis / series / sort_rule / optional 等可选字段
- `RequirementPlanningSpec.validation_warnings`
- workbook「图表PPT数据需求」在有扩展字段时追加中文列

规则：
- proposed_charts 来自 selected / needs_confirmation / optional 模块的 selected_chart_intents
- rejected 模块不进 charts，写入 source_notes
- 旧 AI planning 链路保留，尚未接入一键主流水线

## 2026-07-09 Module Selection Layer v1

新增：
- `catemate/module_selection/` — schemas、context、prompt、selector、validator
- `scripts/run_module_selection.py`
- `scripts/validate_module_selection.py`
- `docs/module_selection_layer_design.md`

规则：
- 遍历 7 个 active data modules，每个必须有 decision
- selected 继承 default_charts；validator 自动补齐遗漏与 source_tables
- adapter v1 可独立运行；尚未接入一键主流水线

## 2026-07-09 Requirement Understanding Layer v1

新增：
- `catemate/understanding/` — schemas、prompt、generator、updater、readiness
- `scripts/run_requirement_understanding.py`
- `scripts/update_requirement_understanding.py`
- `scripts/validate_understanding_readiness.py`
- `docs/requirement_understanding_layer_design.md`

规则：
- 默认 `ready_for_module_selection`，谨慎追问
- 不选 data module，不生成 planning spec / workbook
- readiness 确定性兜底，非阻塞口径问题不阻塞

## 2026-07-09 Data Module Schema v2

新增/更新：
- `docs/data_module_schema_v2.md` — v2 标准字段说明
- `config/data_modules/_template.yaml` — 新模块模板
- 7 个 active v2 业务问题模块（见 `docs/AI_CORE_INDEX.md` §4）
- `config/data_modules/sph_category_dashboard_deck.yaml` — 标记 `status: deprecated`，作为 legacy index

代码适配：
- `catemate/planning/context_loader.py` — 跳过 `_template.yaml` 与 deprecated 模块；摘要输出 v2 字段（typical_questions、default_charts 等）
- `catemate/case_generation/context_loader.py` — 同步跳过 deprecated

规则：
- processed_manifest = 数据资产层；data module v2 = 业务问题层
- planning agent 只读取 `status: active` 的模块
- V3 Python 模块（`data_modules/*/contract.yaml`）：solve loop 当前仅 **2 个 active**（`monthly_market_trend`、`top_sku_info`）；其余为 draft
- deprecated 旧 deck 模块不参与候选，避免重复选择大模块

## 2026-07-08 数据模块目录

新增文档：
- `docs/data_module_catalog.md`

用途：
- 记录 `SPH 气泡图_月度趋势图 for RM .xlsx` 中 `CNCB 中间表 By site` 的数据来源、处理规则和可回答问题。
- 记录 `2026 SPH 品类数据看板.xlsx` 中 `DECK` 的 Part 1-7 数据来源、处理规则和可回答问题。
- 给后续规划 agent 使用：先阅读数据模块能描述什么问题，再决定读取、配置或生成哪些数据。

关键结论：
- 类目树是通用基础数据，来自 `SPH 气泡图_月度趋势图 for RM .xlsx` 的 `SPH类目树`，预处理后放入 `CateMate_processeddata`。
- 一个分析需求可以同时使用多个 raw workbook。
- `CNCB 中间表 By site` 主要基于 `Raw data` 做站点、类目、月份维度的 GMV / Orders / YoY / ABS 聚合。
- `DECK` 主要基于 `过去数据`、`daily data`、`price tier`、`price tier2`、`top shop`、`keywords`、`热门商品` 支持市场趋势、跨境卖家、品牌卖家、价格段、Top Shop、关键词、Top Listing 等模块。

## 2026-07-08 Processed Data 数据层

新增配置：
- `config/data_modules/rm_monthly_category_performance.yaml`
- `config/data_modules/sph_category_dashboard_deck.yaml`
- `config/processed_data_sources.yaml`

新增脚本：
- `scripts/preprocess_raw_data_sources.py`

新增文档：
- `docs/processed_data_design.md`

新增 processed 输出：
- `CateMate_processeddata/source_tables/rm_raw_data.csv`
- `CateMate_processeddata/source_tables/dashboard_history.csv`
- `CateMate_processeddata/source_tables/dashboard_daily_data.csv`
- `CateMate_processeddata/source_tables/dashboard_price_tier.csv`
- `CateMate_processeddata/source_tables/dashboard_price_tier2.csv`
- `CateMate_processeddata/source_tables/dashboard_top_shop.csv`
- `CateMate_processeddata/source_tables/dashboard_keywords.csv`
- `CateMate_processeddata/source_tables/dashboard_top_listing.csv`
- `CateMate_processeddata/processed_manifest.yaml`

规则：
- AI 运行时优先读取 `CateMate_processeddata`，不直接打开大型 Excel。
- 人工确认和追溯时，通过 `processed_manifest.yaml` 回到源 workbook / sheet / 字段。
- 当前抽取模式为 `append_merge`，同结构新版本 Excel 到来后重新运行脚本，会按 `dedupe_keys` 更新同 key 数据、追加新 key 数据，并保留新源文件中没有但 processed 中已有的历史数据。

## 2026-07-08 Confirmation Gate 非阻塞确认项

更新确认门规则：
- `确认记录` 中如果 `是否阻止PPT-ready生成` 明确为 `否`，该确认项不会阻止 PPT-ready workbook 生成。
- 未填写或填写为 `是` 的确认项仍按状态判断：只有 `已确认` / `不需要` 可以通过。
- 该规则用于支持 AI planning spec 中的非阻塞提醒项，例如“是否仅分析 VN，还是需要其他站点对比”。

## 2026-07-08 项目总入口文档

新增人类阅读总入口：
- `docs/PRODUCT_MANAGER_PROJECT_GUIDE.md`

用途：
- 给产品经理 / 策略分析师快速了解项目目标、开发进程、已有功能、技术选择、核心目录和下一步方向。
- 与 `docs/AI_CORE_INDEX.md` 分工：前者给人读，后者给 AI / Cursor / agent 读。

同时在 `docs/AI_CORE_INDEX.md` 中固化了规划 / 数据生成 agent 的启动流程：
1. 先读 `docs/AI_CORE_INDEX.md`
2. 再读 `CateMate_processeddata/processed_manifest.yaml`
3. 再读 `config/data_modules/*.yaml`
4. 如需业务方法论，再读对应 docs
5. 如需具体案例，再读 `config/cases/*.yaml`

## 2026-07-08 AI Planning Layer v1

新增文档：
- `docs/ai_planning_layer_design.md`

新增代码：
- `catemate/ai/settings.py`
- `catemate/ai/client.py`
- `catemate/planning/schemas.py`
- `catemate/planning/context_loader.py`
- `catemate/planning/prompt_builder.py`
- `catemate/planning/planner.py`
- `scripts/run_ai_planning_case.py`

能力：
- 支持 `deepseek` 与 `openai_compatible` 两种 provider；
- 默认 provider 为 `openai_compatible`，默认连接 `http://127.0.0.1:8080/v1`；
- 默认模型为 `gpt-5.5`，默认 API key 为 `pwd`；
- DeepSeek 保留为可选 provider，默认模型 `deepseek-v4-pro`；
- 读取 case config + processed manifest + data module YAML；
- 输出 `RequirementPlanningSpec` JSON；
- 本阶段不写 Excel，不影响 Streamlit 与 PPT-ready 生成器。

## 2026-07-08 Planning Spec 接入 Requirement Workbook

新增代码：
- `catemate/planning/requirement_adapter.py`
- `scripts/run_planning_to_requirement_workbook.py`

改动：
- `CategoryAnalysisRequirementSpec` 相关 row schema 增加可选 planning 字段；
- `ConfirmationItem` 增加可选 `source` / `planning_question_id` / `blocks_ppt_ready`；
- workbook writer 在有 planning 字段时追加中文列；
- `build_requirement_workbook` 增加可选 `planning_spec` 参数，旧链路兼容。

能力：
- `RequirementPlanningSpec` → `CategoryAnalysisRequirementSpec` → 数据需求/确认 workbook；
- 数据需求清单可写 `module_id` / `table_id`；
- 图表需求可写 grain / metrics / dimensions；
- missing_data_questions 进入确认记录；
- confirmation gate 与 Streamlit 原核心字段保持兼容。

## 2026-07-08 自然语言需求到 Case Config 草稿

新增文档：
- `docs/natural_language_case_config_design.md`

新增代码：
- `catemate/case_generation/prompt_builder.py`
- `catemate/case_generation/generator.py`
- `scripts/run_natural_language_to_case_config.py`

能力：
- 输入用户自然语言需求，输出 `CategoryAnalysisCaseConfig` 草稿 YAML；
- 复用 `CategoryAnalysisCaseConfig` schema 做校验；
- 草稿 YAML 可直接进入 planning（`run_ai_planning_case.py`）与 planning→workbook（`run_planning_to_requirement_workbook.py`）流程；
- 本阶段不直接生成 workbook，不改 Streamlit 与 PPT-ready。

## 2026-07-08 自然语言一键需求链路

新增代码：
- `scripts/run_natural_language_requirement_pipeline.py`
- `catemate/case_generation/context_loader.py`（抽离 request / reference helpers，供独立脚本与一键脚本复用）

能力：
- 一键串联支持双模式：
  - `--planning-mode ai_direct`：自然语言 → case config YAML → AI planning JSON → 数据需求/确认 workbook
  - `--planning-mode module_selection`：自然语言 → case config YAML → understanding JSON → module selection JSON → deterministic planning JSON → 数据需求/确认 workbook
- 产物同 timestamp 命名，全部保留，便于复核；
- 支持 `--stop-after-case-config` / `--stop-after-understanding` / `--stop-after-module-selection` / `--stop-after-planning`；
- 不通过 subprocess 调旧脚本，而是 Python 内复用现有模块；
- 三个独立脚本继续可用；不改 Streamlit / PPT-ready / confirmation gate。

## 2026-07-08 确认工作台适配一键链路产物

新增代码：
- `catemate/pipeline/manifest.py`
- `catemate/pipeline/__init__.py`

改动：
- `scripts/run_natural_language_requirement_pipeline.py` 每步更新并保存 `pipeline_manifest_*.json`
- `app/streamlit_dashboard.py` 默认读取最新 manifest，单页完成确认编辑与 PPT-ready 生成

能力：
- 一键产物通过 manifest 绑定 case config / understanding / module selection / planning / workbook；
- Streamlit 优先打开最新一键 workbook，仍可手动选旧 workbook；
- gate 摘要含阻塞项与非阻塞提醒；`build_items` 传入 `blocks_ppt_ready` 以正确区分；
- manifest 不含 API key；失败时保留已完成路径。

## 2026-07-08 通用 PPT-ready workbook v1

新增代码：
- `catemate/ppt_ready/schemas.py`
- `catemate/ppt_ready/processed_data_reader.py`
- `catemate/ppt_ready/chart_data_builder.py`
- `catemate/ppt_ready/workbook_writer.py`
- `scripts/build_ppt_ready_from_confirmed_workbook.py`

能力：
- confirmed requirement workbook + planning spec + processed data → PPT-ready workbook；
- 生成前强制 confirmation gate；
- 输出 `ppt_data_catalog` / `data_notes` / 各 chart sheet；
- 支持 trend / share / bar / table；不支持则 `unsupported` + notes；
- 只读 processed CSV，不读 raw Excel；不让 AI 算数；不生成 PPT/HTML；不做脱敏；
- 旧案例专用 PPT-ready 脚本继续保留。

限制：
- 类目过滤仅 exact match，前台路径不自动映射；
- 多表 chart 默认只用第一个可用表；
- YoY 不发明，仅保留已有 growth 字段；
- v1 目标是可用候选数据包，不是最终业务口径定稿。

## 2026-07-08 PPT-ready 来源追溯与缺失说明增强

改动：
- `catemate/ppt_ready/schemas.py`：sheet spec 增加 lineage / missing / null 字段
- `catemate/ppt_ready/processed_data_reader.py`：新增 `get_table_lineage`
- `catemate/ppt_ready/chart_data_builder.py`：填充来源与缺失/空值说明
- `catemate/ppt_ready/workbook_writer.py`：catalog / data_notes 写入结构化追溯信息

能力：
- catalog 可看到源 workbook/sheet/csv 与规则说明；
- data_notes 含 `source_table::*` / `chart_source::*` / `missing_reason::*` / `null_reason::*`；
- aov 空值明确写“orders 为 0 或缺失，不除以 0”；
- 仍不补数据、不猜测、不读 raw Excel。

## 2026-07-08 PPT-ready HTML 图表预览 v1

新增代码：
- `catemate/ppt_ready/html_preview.py`

改动：
- `scripts/build_ppt_ready_from_confirmed_workbook.py` 默认同步输出 `*_preview.html`
- 支持 `--no-html-preview` / `--html-preview-output` / `--html-preview-max-rows`

能力：
- 基于内存 build result 生成离线可打开 HTML（Plotly CDN）；
- 按 chart_type 选择折线 / 饼 / 柱 / 表格；unsupported 不崩溃；
- Top-N / series 限制仅影响预览，不改 workbook；
- gate 未通过时不生成 workbook 也不生成 HTML；HTML 失败则脚本失败。

## 2026-07-08 PPT-ready HTML preview 语义修复

改动：
- `catemate/ppt_ready/field_utils.py`：daily 时间字段选择、价格段自然排序
- `catemate/ppt_ready/chart_data_builder.py`：日度按 grass_date；price tier 自然序写入 workbook
- `catemate/ppt_ready/html_preview.py`：重复月度 trend 去重；daily X 轴；价格段自然序

能力：
- 同类月度 GMV/Orders trend 只完整展示时间更长者，另一张降级说明；
- daily data 强制优先 grass_date；
- Price_Range_USD 不按指标降序。
