# PPT-ready Workbook 设计说明

## 1. 定位

PPT-ready workbook 是 CateMate 在确认流程完成后生成的内部数据包。

它不是正式分析报告，也不是对外交付物，而是供后续制作 PPT、图表或 HTML 预览使用的标准化数据表集合。

核心原则：

- Excel 负责保存干净、扁平、可追溯的数据。
- 不在这一层做对外脱敏。
- 不在这一层生成正式 PPT。
- 不在确认记录全部通过前生成。

## 2. 生成前置条件

系统必须先通过 confirmation gate。

只有数据需求/确认 workbook 的 `确认记录` 中所有确认项均为以下状态之一时，才允许生成 PPT-ready workbook：

- `已确认`
- `不需要`

如果仍存在以下状态，则不能生成：

- `待确认`
- `待补充`
- `已补充`
- `阻塞`

用户补充数据后，Agent 必须复检新增数据是否解决原始缺口。复检通过后，状态才能从 `已补充` 转为 `已确认`。

## 3. 第一版支持的图表数据类型

第一版优先支持四类常见 PPT 图表所需的数据结构：

1. 气泡图
   - 用于展示规模、增速、客单价等多指标对比。
   - 典型字段：维度、GMV、GMV YoY、Orders YoY、客单价、气泡大小。

2. 柱状图
   - 用于展示站点、类目、L3 的体量或贡献对比。
   - 典型字段：维度、GMV、Orders、占比、同比。

3. 趋势图
   - 用于展示月度 GMV、Orders、客单价等变化。
   - 典型字段：月份、站点、类目、指标值。

4. 占比图
   - 用于展示站点占比、L3 占比、GMV share、Orders share。
   - 典型字段：维度、GMV、GMV share、Orders、Orders share。

图表类型不需要用户在一开始手动指定。Agent 可根据数据结构和分析目标提出建议，但建议需要进入确认流程。

## 4. 数据粒度规则

数据粒度不固定写死，由 Agent 根据需求和数据结构判断，并交给用户确认。

常见粒度包括：

- 某个 L1/L2/L3 by site：看各站点表现。
- 某个 L2 by L3：看 L2 下各 L3 体量和占比。
- 某个类目 by month：看月度趋势。
- 某个类目 by site by month：看不同站点的趋势差异。

如果用户选择多个 L3，默认分别展示每一个 L3，不自动合并成一个目标类目组。

## 5. YoY 口径

第一版默认参考现有中间表中的增速计算方式。

当前 SPH 样例中，中间表主要通过指定月份做同期对比，例如：

- 当前选择月份 GMV vs 去年同月 GMV
- 当前选择月份 Orders vs 去年同月 Orders
- 客单价 = GMV / Orders

如果用户明确提出其他口径，例如 YTD、MAT、近 12 个月、月度同比序列，则作为额外需求进入确认流程。

## 6. 脱敏规则

PPT-ready workbook 是内部数据包，不是对外交付物，因此这一层不做脱敏。

对外交付脱敏规则属于后续“从 PPT-ready workbook 生成 PPT”的模块，不在当前 MVP 中实现。

## 7. Sheet 命名规则

Sheet 名可以机器友好，但必须人能看懂。

建议使用英文小写加下划线，例如：

- `ppt_data_catalog`
- `data_notes`
- `confirmed_assumptions`
- `site_performance_l2`
- `l3_distribution`
- `selected_l3_by_site`
- `monthly_trend_by_site`
- `yoy_bubble_data`
- `site_share`

## 8. 通用追溯字段

每张 PPT-ready 数据表应尽量带上以下字段，便于追溯和后续自动化：

- `source_file`
- `source_sheet`
- `category_level`
- `category_name`
- `parent_category`
- `site`
- `metric_period`
- `calculation_note`
- `confirmed_mapping`

具体数据表可以根据粒度增减字段，但不应丢失关键口径信息。

## 9. 第一版候选 Sheet

第一版可考虑生成以下 sheet：

1. `ppt_data_catalog`
   - 列出 workbook 中所有数据表、适合图表类型、可用状态、缺失原因。

2. `data_notes`
   - 记录数据源、时间范围、站点范围、类目映射、币种、口径说明。

3. `confirmed_assumptions`
   - 记录确认流程中最终通过的类目、时间范围、分析块和跳过项。

4. `site_performance_l1`
   - L1 by site 的 GMV、Orders、客单价和 YoY。

5. `site_performance_l2`
   - L2 by site 的 GMV、Orders、客单价和 YoY。

6. `l3_distribution`
   - L2 下各 L3 的 GMV、Orders、占比和 YoY。

7. `selected_l3_by_site`
   - 用户勾选的重点 L3，分别按站点展示。

8. `monthly_trend_by_site`
   - 月度趋势数据，可用于多折线图。

9. `yoy_bubble_data`
   - 气泡图专用数据。

10. `site_share`
    - 各站点 GMV/Orders 占比数据。

缺数据项，例如价格段分布和关键词搜索量，先进入 `ppt_data_catalog` 和 `data_notes` 标记，不生成虚假数据表。

## 10. HTML Preview

系统预留 `generate_preview_html` 开关。

第一版先不实现 HTML preview。未来如果用户开启该选项，系统可以额外生成一个 HTML 文件，用于快速预览图表大致形态。

HTML preview 不替代 Excel，也不作为正式交付物。

## 11. 通用 PPT-ready 生成器（v1）

新增通用框架：从已确认的 requirement workbook + planning spec + processed data 生成 PPT-ready workbook。

链路：

```text
confirmed requirement workbook
+ planning spec JSON
+ processed_manifest.yaml
+ processed CSV tables
  ↓
confirmation gate（必须通过）
  ↓
确定性 Python 聚合
  ↓
ppt_ready_workbook_<case_id>_<timestamp>.xlsx
```

原则：

- 只读 processed data，不读大型 raw Excel；
- AI 不参与数值计算；
- 不生成 PPT / HTML preview；
- 不做脱敏；
- 不支持时输出 `partial` / `unsupported` + notes，不猜测字段。

代码：

- `catemate/ppt_ready/schemas.py`
- `catemate/ppt_ready/processed_data_reader.py`
- `catemate/ppt_ready/chart_data_builder.py`
- `catemate/ppt_ready/workbook_writer.py`
- `scripts/build_ppt_ready_from_confirmed_workbook.py`

脚本入口：

```bash
# 推荐：通过 pipeline manifest
python scripts/build_ppt_ready_from_confirmed_workbook.py \
  --pipeline-manifest outputs/pipeline_manifest_<case_id>_<timestamp>.json

# 或显式指定
python scripts/build_ppt_ready_from_confirmed_workbook.py \
  --requirement-workbook <confirmed.xlsx> \
  --planning-spec <planning_spec.json>
```

输出至少包含：

1. `ppt_data_catalog`
2. `data_notes`
3. 每个 `proposed_charts` 对应的 chart data sheet

### 11.1 来源追溯与缺失说明（增强）

`ppt_data_catalog` 现在额外记录：

- `source_workbook_names` / `source_sheets`：来自 `processed_manifest.yaml` 的 `source_workbook_name` / `source_sheet`
- `processed_csv_paths`：processed CSV 相对项目路径或文件名
- `source_rule_note`：本 sheet 如何使用 source table（例如只用第一张表、Top 50 等）
- `missing_data_note`：基于证据的缺失汇总（字段找不到、table 不存在、unsupported 等）
- `null_reason_note`：空值可解释原因（例如 aov 因 orders=0/缺失而不计算除以 0）

`data_notes` 增加结构化行：

- `source_table::<table_id>`：workbook / sheet / csv / columns
- `chart_source::<chart_id>`：chart 与源表绑定
- `missing_reason::<chart_id>` / `null_reason::<chart_id>`：仅在有证据时写入

空值说明规则：

- 不补数据、不猜测；
- aov 空：orders 为 0 或缺失，系统不计算除以 0；
- 字段存在但部分行为空：提示回溯 source_workbook/source_sheet；
- unsupported：明确写 v1 不支持该 chart_type。

### 11.2 HTML 图表预览（v1）

生成 PPT-ready workbook 时**默认**同步生成 HTML 预览：

```text
outputs/ppt_ready_workbook_<case_id>_<timestamp>.xlsx
outputs/ppt_ready_workbook_<case_id>_<timestamp>_preview.html
```

用途：辅助产品/业务验收图表类型、粒度与来源说明；**不是正式 PPT**。

代码：`catemate/ppt_ready/html_preview.py`

CLI：

```bash
# 默认生成 HTML
python scripts/build_ppt_ready_from_confirmed_workbook.py \
  --requirement-workbook <confirmed.xlsx> \
  --planning-spec <planning.json>

# 关闭 HTML
python scripts/build_ppt_ready_from_confirmed_workbook.py ... --no-html-preview

# 指定路径 / 限制预览行数
python scripts/build_ppt_ready_from_confirmed_workbook.py ... \
  --html-preview-output outputs/my_preview.html \
  --html-preview-max-rows 1000
```

图表选择概览：

- `trend` → 折线图（可按 site series；最多 8 条）
- `share` → ≤8 项饼图，否则横向条形 Top10+Others；必要时可预览内计算 share，但不改 workbook
- `bar` → 柱状图（Top 15）
- `table` → 可读表格（可显示 item_image 缩略图）
- `unsupported` / 缺字段 → 说明卡片 + 样例表，不崩溃

原则：

- 基于内存中的 build result 生成，不再读 xlsx / raw Excel；
- Top-N / 截断只影响 HTML；
- confirmation gate 未通过则 workbook 与 HTML 都不生成；
- HTML 需网络加载 Plotly CDN。

预览语义规则（v1 fix）：

1. **重复月度趋势降级**：同类 GMV/Orders 月度 trend（不同源表）只完整展示时间窗口更长的一张；另一张放在 Deduplicated / Hidden charts，并说明被哪张替代。优先保留 `rm_raw_data`。
2. **日度时间轴**：`dashboard_daily_data` / daily / 日度 → workbook 与 HTML 均优先按 `grass_date` 聚合，不用 `month`。
3. **价格段顺序**：`Price_Range_USD` 按自然顺序（如 `01_[0,1)` → `09_[20,Inf)`），不按 GMV/ADO/share 降序；截断也在自然序之后。

这些规则只影响图表表达/预览，不改 processed 源数据。

旧的案例专用生成器（Collectible / Pet Healthcare）继续保留，互不替代。
