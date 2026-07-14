# CateMate Processed Data 设计

更新时间：2026-07-08

## 目标

`CateMate_processeddata` 是专门给 AI 读取的数据层。AI 运行时应优先读取 processed data，而不是每次打开大型源 Excel。

人工确认、追溯和审计时，仍然要能回到源文件、源 sheet 和源字段。

## 当前目录结构

```text
CateMate_processeddata/
  sph_category_tree_lookup.csv
  source_tables/
    rm_raw_data.csv
    dashboard_history.csv
    dashboard_daily_data.csv
    dashboard_price_tier.csv
    dashboard_price_tier2.csv
    dashboard_top_shop.csv
    dashboard_keywords.csv
    dashboard_top_listing.csv
  processed_manifest.yaml
```

## 配置文件

抽取规则记录在：

```text
config/processed_data_sources.yaml
```

每张 processed 表都需要记录：

- `table_id`
- `source_workbook_keywords`
- `source_sheet`
- `output_csv`
- `description`
- `important_fields`
- `dedupe_keys`
- `update_mode`

当前默认 `update_mode` 使用 `append_merge`：

- 新源文件中出现的新 key 会追加到 processed CSV。
- 新源文件中和旧 processed CSV 相同 key 的记录，会用新源文件记录更新。
- 旧 processed CSV 中存在、但新源文件中不存在的 key 会被保留。

也就是说，`CateMate_processeddata` 是持续扩充的数据层，不是每次被完整覆盖的临时缓存。

每张表必须尽量配置 `dedupe_keys`。这些字段用于判断一行数据是否代表同一个业务事实。例如：

- 月度类目表现：站点 + L1 + L2 + L3 + 月份
- 价格段数据：月份 + seller type + 站点 + 类目 + 价格段
- Top listing：商品链接

如果某张表没有配置 `dedupe_keys`，脚本会退化为纯追加模式，重复运行可能产生重复行。

## 抽取脚本

```bash
python scripts/preprocess_raw_data_sources.py
```

可选参数：

```bash
python scripts/preprocess_raw_data_sources.py --config config/processed_data_sources.yaml --raw-data-dir CateMate_rawdata --processed-data-dir CateMate_processeddata
```

## 追溯关系

每次抽取后会生成：

```text
CateMate_processeddata/processed_manifest.yaml
```

manifest 会记录：

- processed table id
- output csv
- source workbook
- source sheet
- row count
- column count
- columns
- important fields
- source modified time
- extracted time
- update mode
- dedupe keys
- incoming / existing / added / updated / retained row counts

规划 agent 使用 processed CSV 做数据判断；当用户需要人工确认时，根据 manifest 回到源 workbook/sheet。

## 当前抽取表

### rm_raw_data

- 来源：`SPH 气泡图_月度趋势图 for RM .xlsx` / `Raw data`
- 用途：月度类目 GMV / Orders / YoY / ABS / 趋势

### dashboard_history

- 来源：`2026 SPH 品类数据看板.xlsx` / `过去数据`
- 用途：DECK Part 1，市场整体趋势和增长潜力

### dashboard_daily_data

- 来源：`2026 SPH 品类数据看板.xlsx` / `daily data`
- 用途：DECK Part 2，跨境卖家、CNCB 占比、广告/活动来源

### dashboard_price_tier / dashboard_price_tier2

- 来源：`2026 SPH 品类数据看板.xlsx` / `price tier`、`price tier2`
- 用途：DECK Part 3/4，Mall 卖家、价格段分布、价格段 YoY

### dashboard_top_shop

- 来源：`2026 SPH 品类数据看板.xlsx` / `top shop`
- 用途：DECK Part 5，Top Shop 排行、头部卖家占比和订单来源

### dashboard_keywords

- 来源：`2026 SPH 品类数据看板.xlsx` / `keywords`
- 用途：DECK Part 6，近期广告热词和点击增长

### dashboard_top_listing

- 来源：`2026 SPH 品类数据看板.xlsx` / `热门商品`
- 用途：DECK Part 7，Top Listing 商品清单、价格、链接、图片

## 后续建议

1. 规划 agent 的数据读取入口：先读 `config/data_modules/*.yaml`（v2 active 模块），再读 `processed_manifest.yaml` 核对字段。
2. 对大型 CSV 增加按类目/站点过滤后的缓存表，减少 AI 每次扫描的行数。
3. 如果后续数据量继续变大，可将 CSV 替换或补充为 DuckDB/Parquet，但仍保留 manifest 追溯关系。

## Data Module Schema v2（2026-07-09）

与 processed table 的关系：

| 层 | 文件 | 职责 |
|----|------|------|
| 数据资产层 | `processed_manifest.yaml` | table_id、columns、row_count、source workbook/sheet |
| 业务问题层 | `config/data_modules/*.yaml` | business_purpose、default_charts、chart_rules、limitations |

一个 data module 可引用一个或多个 processed table（例如价格段当前期 + 对比期）。  
标准字段说明见 `docs/data_module_schema_v2.md`。
