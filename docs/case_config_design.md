# CateMate Case Config 设计（阶段一）

更新时间：2026-07-08

## 目标

将类目分析数据需求 workbook 的案例内容从代码硬编码中抽离，改为 YAML 配置驱动。

当前链路：

`RequirementContext / CategoryAnalysisCaseConfig`  
→ `CategoryAnalysisRequirementSpec`  
→ 数据需求/确认 workbook  
→ Streamlit 确认工作台  
→ confirmation gate

## 当前支持字段

`CategoryAnalysisCaseConfig` 主要字段：

- `case_id`
- `project_name`
- `original_request`
- `target_category_text`
- `business_background`
- `delivery_audience`
- `delivery_format`
- `target_sites`
- `time_range`
- `category_keywords`
- `analysis_plan`
- `data_requirements`
- `preprocess_plan`
- `chart_requirements`
- `static_confirmation_items`（映射到 `confirmation_templates`）

说明：

- `static_confirmation_items` 用于静态确认项模板（如源数据文件、交付敏感性、时间范围、价格段分析、关键词搜索量同比）。
- 类目映射确认项仍由类目匹配候选动态生成，不在 YAML 中写死。
- `chart_type` 已可在配置中预留，但当前写 Excel 时仍保持原列结构，不额外新增列。
- 一个 case 可以同时使用多个源文件：`source_file_keywords` 用于选择主分析数据源，`category_tree_source_keywords` 用于选择通用类目树源文件。

## 使用方式

示例配置：

- `config/cases/hkcb_collectible.yaml`
- `config/cases/pet_healthcare_vn.yaml`

运行命令：

```bash
python scripts/run_category_requirement_case.py config/cases/hkcb_collectible.yaml
python scripts/run_category_requirement_case.py config/cases/pet_healthcare_vn.yaml
```

可选参数：

- `--raw-data-dir`
- `--processed-data-dir`
- `--output`

## 兼容性说明

- 本阶段未接入 AI。
- 保持原 8 个 sheet 名称与主要中文列名不变。
- `build_requirement_workbook(...)` 入口保持兼容（新增可选 `case_config` 参数，不影响旧调用）。
- 旧 demo 脚本仍可运行。
- confirmation gate 的读取列结构保持不变。

## 当前两个样例

### HKCB Collectible

- 配置文件：`config/cases/hkcb_collectible.yaml`
- 源数据：`SPH 气泡图_月度趋势图 for RM .xlsx`
- 类目映射：可通过 `SPH类目树` 自动生成候选，再由用户确认。
- 主要验证点：从用户前台类目文本匹配到 Hobbies & Collections / Collectible Items 下的候选 L3。

### VN Pet Healthcare

- 配置文件：`config/cases/pet_healthcare_vn.yaml`
- 源数据：`2026 SPH 品类数据看板.xlsx`
- 类目树源数据：`SPH 气泡图_月度趋势图 for RM .xlsx`
- 关键 sheet：`DECK`、`过去数据`、`price tier`、`热门商品`
- 类目映射：通过通用 `SPH类目树` 自动生成 Pet Healthcare 下的候选 L3，并保留 `Pets > Pet Healthcare` 作为业务确认项。
- 主要验证点：同一数据需求生成器可以支持趋势、价格段、平均价格、Top listing 等不同分析需求。

## 后续建议

- 逐步将 case config 与 PPT-ready 规格通过 schema 对齐。
- 在 case config 层补充更细粒度的验证规则（例如必填确认模板项检查）。
