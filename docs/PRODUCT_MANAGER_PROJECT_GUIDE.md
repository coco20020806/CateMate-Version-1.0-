# CateMate 产品经理项目手册

## V1 给 PM 的当前结论（2026-07-09）

CateMate V1 已经不是单点 demo，而是一条可以从自然语言需求跑到数据需求确认 workbook 的工作流。确认完成后，也已经可以生成 PPT-ready workbook 和 HTML 图表预览。

你现在主要需要验收的不是代码细节，而是这几件事：

1. AI 对需求的理解是否符合真实业务语境。
2. module selection 是否选对了数据模块，哪些应该 selected，哪些可以 optional，哪些应该 rejected。
3. 生成的 `图表PPT数据需求` 是否像一个真实分析师会准备的图表数据清单。
4. `确认记录` 里的问题是否适合拿来和提需方确认。
5. PPT-ready workbook / HTML preview 是否足够支持后续人工调整和 PPT 制作。

最近一次可验收的 `module_selection` 运行产物：

- `outputs/pipeline_manifest_livestock_healthcare_vn_20260709_175204.json`
- `outputs/requirement_understanding_livestock_healthcare_vn_20260709_175204.json`
- `outputs/module_selection_livestock_healthcare_vn_20260709_175204.json`
- `outputs/planning_spec_from_module_selection_livestock_healthcare_vn_20260709_175204.json`
- `outputs/category_analysis_data_requirement_from_planning_livestock_healthcare_vn_20260709_175204.xlsx`

完整 V1 验收说明见：`docs/V1_ACCEPTANCE_SUMMARY.md`。

当前建议你重点校验：

- `dashboard_price_tier_distribution` 在 VN livestock / Pet Healthcare 这类需求里，是应该默认 selected，还是保持 optional。
- `config/data_modules/*.yaml` 中每个模块的业务描述、默认图表、适用/不适用场景是否符合你的真实工作经验。

更新时间：2026-07-08

本文档是 CateMate 项目的唯一“人类阅读总入口”。它面向产品经理 / 策略分析师，用来记录项目目标、开发进程、已有功能、技术选择、当前规则和下一步方向。

如果后续你想快速了解“这个项目现在做到哪里了”，优先读这个文件。

## 1. 项目目标

CateMate 的目标是把类目分析工作流程系统化：

```text
用户提出自然语言需求
→ AI 理解需求并拆成结构化任务
→ 系统判断需要哪些数据、哪些类目映射、哪些确认
→ 用户在确认工作台中确认或补充
→ confirmation gate 判断是否可以继续
→ 生成 PPT-ready workbook
→ 后续再扩展为报告 / PPT 生成
```

当前阶段的核心不是直接生成漂亮 PPT，而是先把“数据需求确认”和“可追溯数据输出”跑通。

## 2. 产品原则

1. 不伪造数据  
   所有输出都必须来自 raw workbook 或 processed data。

2. 先确认，再生成  
   只有确认记录全部变成 `已确认` 或 `不需要`，才能进入 PPT-ready workbook 生成。

3. AI 负责执行和初步判断，人负责关键确认  
   类目映射、数据是否足够、缺失项是否可以接受，都需要保留给用户确认。

4. PPT-ready workbook 是内部数据包  
   它不负责对外脱敏。脱敏规则留给后续 PPT / 报告生成模块。

5. processed data 是 AI 可读数据库  
   AI 日常运行时优先读取 processed data，而不是反复打开大型 Excel。

## 3. 当前已完成的功能

### 3.1 数据需求 / 确认 workbook

系统可以根据真实案例生成一份数据需求 workbook，包含：

- 需求摘要
- 类目映射候选
- 分析计划
- 数据需求清单
- 源数据检查
- 预处理规划
- 图表 PPT 数据需求
- 确认记录

核心代码：

- `catemate/modules/category_analysis_data_requirement.py`
- `scripts/run_category_requirement_case.py`

### 3.2 confirmation gate

系统可以读取 workbook 中的 `确认记录`，判断是否允许进入 PPT-ready workbook 生成。

通过状态：

- `已确认`
- `不需要`

阻塞状态：

- `待确认`
- `待补充`
- `已补充`
- `阻塞`

如果某个确认项的 `是否阻止PPT-ready生成` 为 `否`，它可以作为非阻塞提醒保留在确认工作台里，不会阻止后续生成。

核心代码：

- `catemate/core/confirmation_gate.py`
- `scripts/check_confirmation_gate.py`

### 3.3 Streamlit V1 总控台

总控台分为两个视图：**新建需求**（默认首页）与 **历史需求**（查看、继续、完善过去的需求）。

单页完成 V1 全流程，含**双阶段确认**：

1. **需求澄清**（理解阶段）：`clarifying_questions` 逐条自然语言回答或跳过 → manifest `awaiting_clarification` → `clarification_completed`
2. **数据需求确认**（workbook 阶段）：勾/差确认项 → confirmation gate → PPT-ready

当前交互：

- 打开总控台默认进入「新建需求」，不会自动加载某条历史 manifest。
- 新建需求生成成功后，会自动切换到「历史需求」并定位到该 manifest，无需手动刷新。
- 「历史需求」中可选择任意 manifest，继续澄清、续跑、确认或查看 PPT-ready。
- 「新建需求」页底部可展开「最近需求」快捷入口，一键回到未完成需求。
- 新建需求后 pipeline 可能在澄清 gate 暂停；须在「需求澄清」区块答完再继续。
- workbook 确认项显示短标签 + 完整确认问题（`原因` 列 / UI 正文）。
- 澄清问题**不再重复**写入 workbook「确认记录」。
- 同类 workbook 确认项自动分组；`✓` / `×` / `...` 编辑状态。
- 须先「保存确认结果」到磁盘后，门禁才允许生成 PPT-ready。
- CLI 跑完新需求后，在「历史需求」点「刷新并选中最新」同步列表。

入口：

- `app/streamlit_dashboard.py`（V1 总控台）
- `app/clarification_editor.py` / `app/confirmation_editor.py`（可复用 UI 组件）
- `app/streamlit_app.py`（兼容入口，转发至总控台）

续跑 CLI：`python scripts/run_natural_language_requirement_pipeline.py --continue-from-manifest outputs/pipeline_manifest_*.json`

### 3.4 PPT-ready workbook

已有两类生成方式：

1. 案例专用生成器（HKCB Collectible / VN Pet Healthcare）
2. **通用 v1 生成器**（推荐：在总控台确认保存后一键生成）

确认完成后，可以用通用脚本从「已确认 workbook + planning spec + processed data」生成 PPT-ready workbook。

注意：

- 第一版是**通用数据表集合**，不是 PPT；
- 也不做脱敏；
- 生成前必须通过 confirmation gate；
- 数据只来自 processed CSV；
- workbook 会写明每张表来自哪个源文件 / 源 sheet，以及主要空值或缺失原因（不编造、不补数）；
- 默认会额外生成一个 HTML 图表预览，方便你快速判断趋势/占比/柱状图是否合理；需要网络加载图表库。可用 `--no-html-preview` 关闭。
- 预览会对重复的月度趋势图做降级说明（只完整展示时间覆盖更完整的一张）。
- 日度图会按真实日期（grass_date）画，不会错用 month。
- 价格段图按 `[0,1)` → 更高价格段 的自然顺序排列，不按 GMV 大小乱序。

入口：

- `scripts/build_ppt_ready_from_confirmed_workbook.py`
- 设计说明：`docs/ppt_ready_workbook_design.md`

案例专用代码仍保留：

- `catemate/modules/ppt_ready_workbook.py`
- `catemate/modules/pet_healthcare_ppt_ready_workbook.py`

### 3.5 Case config

真实案例已经可以被抽成 YAML 配置。

当前案例：

- `config/cases/hkcb_collectible.yaml`
- `config/cases/pet_healthcare_vn.yaml`

这一步的意义是：未来 AI 可以先生成或修改 case config，再交给系统生成 workbook。

### 3.6 Processed data

已经建立 AI 可读的数据层：

- `CateMate_processeddata/source_tables/*.csv`
- `CateMate_processeddata/processed_manifest.yaml`

当前 processed data 来源包括：

- `SPH 气泡图_月度趋势图 for RM .xlsx`
- `2026 SPH 品类数据看板.xlsx`

AI 规划或数据生成时，应该先读：

1. `docs/AI_CORE_INDEX.md`
2. `config/data_modules/*.yaml`（**优先 v2 active 模块**，见 `docs/data_module_schema_v2.md`）
3. `CateMate_processeddata/processed_manifest.yaml`（核对 table_id 与字段）

**两层分工：**
- **processed table**（manifest）= 数据资产层
- **data module v2** = 业务问题模块（一个业务问题一个 YAML）
- `sph_category_dashboard_deck.yaml` 已 deprecated，仅作历史说明

### 3.6.5 Requirement Understanding Layer（v1）

在 module selection / planning 之前，可先把自然语言需求转成 `RequirementUnderstandingSpec`：

- 默认推进，业务细节不清写入 assumptions / non-blocking questions；
- 支持用户补充后更新 spec；
- 尚未接入主流水线，可独立 CLI 运行。

入口：

- `scripts/run_requirement_understanding.py`
- `scripts/update_requirement_understanding.py`
- `docs/requirement_understanding_layer_design.md`

### 3.6.6 Module Selection Layer（v1）

在 understanding spec `ready_for_module_selection` 之后，可运行 module selection：

- 遍历全部 active data modules，输出 `ModuleSelectionPlan`；
- selected 模块继承 `default_charts`；
- validator 兜底补齐遗漏模块与图表配置。

入口：

- `scripts/run_module_selection.py`
- `scripts/validate_module_selection.py`
- `docs/module_selection_layer_design.md`

### 3.6.7 Module Selection → Planning Adapter（v1）

在已有 `ModuleSelectionPlan` 后，可用确定性 adapter 生成 `RequirementPlanningSpec`，不再依赖 AI 发明图表：

- `proposed_charts` 来自各模块 `selected_chart_intents`；
- optional / rejected 模块按规则标记；
- 输出可继续走 `run_planning_to_requirement_workbook.py`。

入口：

- `scripts/run_module_selection_to_planning.py`
- `scripts/validate_planning_from_module_selection.py`
- `docs/module_selection_to_planning_design.md`

### 3.7 自然语言需求 → Case Config 草稿（v1）

现在可以把你的一段自然语言需求先转成 case config 草稿 YAML。

意义：

- 先把需求结构化，便于你人工复核；
- 避免 AI 直接写 Excel；
- 后续可继续进入 planning 和确认 workbook 流程。

入口：

- `scripts/run_natural_language_to_case_config.py`
- `docs/natural_language_case_config_design.md`

### 3.8 AI Planning Layer（v1）

已经新增最小 AI 规划层，并能进入确认 workbook 流程：

- 读取 case config、processed manifest、data module YAML；
- 调用 DeepSeek 或 OpenAI-compatible 模型；
- 输出 `RequirementPlanningSpec` JSON；
- 再用确定性代码把 planning JSON 转成数据需求/确认 workbook。

对产品经理的意义：

AI 先给出“能做哪些分析、用哪些数据表、还缺哪些确认”，这些内容会出现在确认 workbook 里，方便你继续人工确认；AI 不会直接写最终 Excel。

入口：

- `scripts/run_ai_planning_case.py`
- `scripts/run_planning_to_requirement_workbook.py`
- `docs/ai_planning_layer_design.md`

### 3.9 自然语言一键到确认 workbook（推荐）

现在可以从自然语言需求**一键**生成两种模式产物：

- `--planning-mode ai_direct`（旧链路）：case config YAML + planning spec JSON + workbook + manifest
- `--planning-mode module_selection`（新链路）：case config YAML + understanding JSON + module selection JSON + planning spec JSON + workbook + manifest

注意：这是串联器，不是黑盒。每一步产物都会单独保存到 `outputs/`，方便你逐步复核。原来的独立脚本仍然可用。

试用更顺的地方：跑完一键链路后打开确认工作台，会自动定位最新这一轮的 workbook，并告诉你它对应哪份 case config / planning spec。

入口：

- `scripts/run_natural_language_requirement_pipeline.py`
- 再打开：`streamlit run app/streamlit_dashboard.py`

## 4. Processed data 更新规则

processed data 不是覆盖式数据库，而是持续扩充式数据库。

当前默认更新方式是 `append_merge`：

- 新源文件中出现的新行会补充进 processed data；
- processed data 已有、但新源文件中没有的数据会保留；
- 完全重复的行不会重复累积；
- 当前用 `__all_columns__` 做整行去重，避免因为业务 key 不够细而误合并数据。

这意味着，当你后续提供结构相同的新版本 Excel 时，系统可以把新数据补进 processed data，而不是把旧数据清空。

相关配置和脚本：

- `config/processed_data_sources.yaml`
- `scripts/preprocess_raw_data_sources.py`
- `docs/processed_data_design.md`

## 5. 当前技术选择

### 5.1 语言与运行方式

当前以 Python 为主。

原因：

- 适合处理 Excel / CSV；
- 适合后续接 AI API；
- 适合构建轻量本地工具；
- 与 Streamlit、Pydantic、pandas、openpyxl 等工具生态匹配。

### 5.2 数据结构

使用 Pydantic schema 固化核心对象：

- 需求上下文
- 数据需求 workbook spec
- 确认项
- PPT-ready workbook spec
- case config

核心目录：

- `catemate/schemas/`

### 5.3 前端

当前使用 Streamlit 做本地确认工作台。

原因：

- MVP 阶段足够快；
- 适合你作为第一版用户直接操作；
- 暂时不需要复杂账号、权限和部署。

后续如果要给更多人使用，可以再升级为正式 Web 前端。

### 5.4 AI 接入

已落地 AI planning layer v1：

- OpenAI-compatible 作为默认 provider，默认连接 `http://127.0.0.1:8080/v1`；
- 默认模型为 `gpt-5.5`，默认 API key 为 `pwd`；
- DeepSeek 保留为可选 provider（`deepseek-v4-pro`）；
- 当前输出是 `RequirementPlanningSpec` JSON，不直接写 Excel。

详情见：

- `docs/ai_planning_layer_design.md`
- `scripts/run_ai_planning_case.py`

## 6. 当前核心目录说明

### `docs/`

项目文档。

最重要的几个：

- `PRODUCT_MANAGER_PROJECT_GUIDE.md`：给人看的项目总手册。
- `AI_CORE_INDEX.md`：给 AI / Cursor / agent 看的总索引。
- `PROJECT_STATUS.md`：偏工程状态记录。
- `ai_planning_layer_design.md`：AI planning layer 设计。
- `data_module_catalog.md`：数据模块方法论说明（人类可读）。
- `data_module_schema_v2.md`：业务问题模块机器配置标准（planning agent 优先读 active v2 YAML）。
- `processed_data_design.md`：processed data 设计。
- `ppt_ready_workbook_design.md`：PPT-ready workbook 设计。

### `config/`

配置文件。

- `config/cases/`：真实案例配置。
- `config/data_modules/`：数据模块机器可读配置。
- `config/processed_data_sources.yaml`：raw data 到 processed data 的抽取规则。

### `catemate/`

核心代码。

- `catemate/modules/`：业务模块。
- `catemate/core/`：确认门等核心逻辑。
- `catemate/schemas/`：Pydantic 数据结构。
- `catemate/data/`：数据扫描、类目树等数据辅助能力。
- `catemate/config/`：配置读取。
- `catemate/ai/`：AI provider settings / client。
- `catemate/planning/`：AI planning layer。

### `scripts/`

可直接运行的本地脚本。

常用：

- `scripts/preprocess_raw_data_sources.py`
- `scripts/run_natural_language_requirement_pipeline.py`（自然语言一键主入口）
- `scripts/run_natural_language_to_case_config.py`
- `scripts/run_category_requirement_case.py`
- `scripts/run_ai_planning_case.py`
- `scripts/run_planning_to_requirement_workbook.py`
- `scripts/check_confirmation_gate.py`
- `scripts/build_ppt_ready_workbook.py`
- `scripts/build_pet_healthcare_ppt_ready_workbook.py`

### `CateMate_rawdata/`

存放用户下载或提供的原始 Excel。

### `CateMate_processeddata/`

存放 AI 可读的 processed data。

### `outputs/`

存放生成出来的 workbook。

## 7. 已验证的真实案例

### 7.1 HKCB Collectible

目标：

- Hobbies & Collections / Collectible Items 类目分析。

已完成：

- 数据需求 workbook；
- 确认 gate；
- PPT-ready workbook；
- case config。

### 7.2 VN Pet Healthcare

目标：

- 越南畜牧相关需求，最终定位到 Pets > Pet Healthcare。

已完成：

- 新源 workbook 识别；
- DECK 逻辑拆解；
- Pet Healthcare PPT-ready workbook；
- case config；
- processed data 抽取。

## 8. 当前还没做的部分

1. 规划质量双案例验收与 prompt 优化  
   planning → workbook 已打通，但 Collectible / Pet Healthcare 规划质量仍需继续验收。

2. 通用 PPT-ready 口径深化  
   v1 框架已可用，但类目精确过滤、多表合并、YoY 口径等仍偏保守，很多情况是 partial + notes。

3. HTML 图表预览  
   v1 已默认随 PPT-ready workbook 生成 HTML 预览（可用 `--no-html-preview` 关闭）；仍非正式 PPT。

4. PPT 自动生成  
   当前只生成 PPT-ready 数据 + HTML 验收预览，不直接生成 PPT。

5. 多用户产品化前端  
   当前 Streamlit 先服务你本人。

## 9. 下一阶段建议

建议下一步优先做三件事：

1. 用 HKCB Collectible 和 VN Pet Healthcare 双案例验收 preparation / PPT-ready 质量。
2. 让数据需求项进一步引用 processed fields。
3. 在不猜测字段的前提下，逐步收紧通用 PPT-ready 的过滤与聚合口径。

这样 AI 不是“凭感觉规划”，而是基于现有数据模块、processed data 和确认规则进行规划。

## 10. 给后续开发者 / AI 的一句话

CateMate 的重点不是把一次分析写死，而是把“需求理解、数据确认、数据追溯、PPT-ready 输出”变成可复用流程。任何新增功能都应该优先保护这条链路的稳定性。
