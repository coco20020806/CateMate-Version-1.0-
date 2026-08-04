# CateMate 数据模块目录

更新时间：2026-07-09

> **Schema v2（2026-07-09）**  
> 机器可读配置已升级为「一个业务问题一个 data module」。详见 `docs/data_module_schema_v2.md`。  
> - **processed_manifest.yaml** = 数据资产层（底层 processed table）  
> - **config/data_modules/*.yaml** = 业务问题模块（规划 agent 优先读取 `status: active` 的 v2 模块）  
> - `sph_category_dashboard_deck.yaml` 已 deprecated，拆分为 6 个 dashboard 子模块

本文档用于给后续规划 agent 阅读：当用户提出类目分析需求时，agent 应先理解现有数据模块能回答什么问题，再决定读取、配置或生成哪些数据。

## 全局规则

### 类目树

- 类目树是通用基础数据，不属于某一个 case。
- 原始来源：`CateMate_rawdata/SPH 气泡图_月度趋势图 for RM .xlsx`
- 实际观察到的 sheet 名：`SPH类目树`
- 处理方式：预处理成 lookup 后放入 `CateMate_processeddata`。
- 使用方式：后续所有类目映射优先查 processed lookup，而不是每次临时读取原始 Excel。

### 多源分析

一个需求可以同时使用多个 raw workbook。不要把 case 理解成“只能选择一个 Excel”。

当前核心 raw workbook：

1. `SPH 气泡图_月度趋势图 for RM .xlsx`
   - 主要用于月度类目 GMV / Orders 聚合、YoY、ABS、气泡图、月度趋势。
   - 关键公式 sheet：`CNCB 中间表 By site`
   - 主要 raw sheet：`Raw data`

2. `2026 SPH 品类数据看板.xlsx`
   - 主要用于市场趋势、跨境卖家、品牌卖家、价格段、Top Shop、关键词、Top Listing。
   - 关键公式 sheet：`DECK`
   - 主要 raw/source sheets：`过去数据`、`daily data`、`price tier`、`price tier2`、`top shop`、`keywords`、`热门商品`

## 数据模块一：RM 月度类目表现

### 来源

- Workbook：`SPH 气泡图_月度趋势图 for RM .xlsx`
- 公式/中间表 sheet：`CNCB 中间表 By site`
- Raw sheet：`Raw data`

### Raw Data 字段

`Raw data` 关键字段：

- `grass_region`
- `cb_level1_global_be_category`
- `level2_global_be_category`
- `level3_global_be_category`
- `grass_month`
- `gmv_usd`
- `orders`

### 通用处理规则

`CNCB 中间表 By site` 主要通过 `SUMIFS` 从 `Raw data` 聚合：

- 按站点过滤：`grass_region`
- 按类目过滤：
  - L1：`cb_level1_global_be_category`
  - L2：`level2_global_be_category`
  - L3：`level3_global_be_category`
- 按月份过滤：`grass_month`
- 聚合指标：
  - GMV：`SUM(gmv_usd)`
  - Orders：`SUM(orders)`
  - ABS / 客单价：`GMV / Orders`
  - YoY：`当前期 / 去年同期 - 1`

### 可回答的问题

该模块适合回答：

- 某个 L1/L2/L3 在各站点的 GMV 表现如何？
- 各站点 Orders 表现如何？
- 各站点 GMV YoY / Orders YoY 如何？
- 各站点客单价 ABS 如何？
- 某个类目按月趋势如何？
- 某个 L2 下不同 L3 的站点表现如何？
- 适合气泡图、折线趋势图、站点对比表。

### 已识别子模块

#### RM-01 L2 by site YoY

- 公式区域特征：`CNCB 中间表 By site` 前部，标题含 `L2维度`、`YoY 数据`
- 输入：
  - 选定 L2
  - 当前年份 / 当前月份
  - 去年年份 / 同月份
- 输出：
  - site
  - GMV
  - GMV YoY
  - Orders
  - Orders YoY
  - ABS
  - ABS change
- 图表用途：
  - 站点分布
  - YoY 气泡图
  - 各站点客单价参考

#### RM-02 L2 by site 气泡图数据

- 来源：RM-01 的结果二次整理
- 输出：
  - ADG 气泡图：site, GMV/ADG, GMV YoY, ABS
  - ADO 气泡图：site, Orders/ADO, Orders YoY, ABS
- 图表用途：
  - 规模、增速、客单价三维展示

#### RM-03 L3 by site YoY

- 公式区域特征：标题含 `L3维度`
- 输入：
  - 选定 L2
  - 选定 L3
  - 当前年份 / 月份
  - 去年同期
- 输出：
  - site
  - GMV
  - GMV YoY
  - Orders
  - Orders YoY
  - ABS
- 图表用途：
  - 目标 L3 的站点表现
  - L3 机会判断

#### RM-04 月度趋势 by site

- 公式区域特征：标题含 `月度趋势`
- 输入：
  - 选定 L2 或 L3
  - 月份序列
  - site
- 输出：
  - site × month
  - GMV 或 Orders
- 图表用途：
  - 多站点折线趋势图
  - 判断季节性、持续增长或下滑

## 数据模块二：2026 SPH 品类数据看板 / DECK

### 来源

- Workbook：`2026 SPH 品类数据看板.xlsx`
- 公式/整合 sheet：`DECK`
- 用户输入区：
  - `C3`：L1
  - `C4`：L2
  - `C5`：L3
  - `C6`：Top shop ADG 阈值
  - 日期口径由 `A1`、`G3:G5` 生成

### DECK 引用源 sheet

`DECK` 公式引用到：

- `过去数据`
- `daily data`
- `price tier`
- `price tier2`
- `top shop`
- `keywords`
- `热门商品`

### 源 sheet 字段概览

#### 过去数据

关键字段：

- `grass_region`
- `cb_level1_global_be_category`
- `level2_global_be_category`
- `level3_global_be_category`
- `grass_month`
- `gmv_usd`
- `orders`

主要用途：

- 市场整体趋势
- GMV / Orders 年度增长
- ABS / 客单价
- 最近 12 个月趋势

#### daily data

关键字段：

- `grass_date`
- `year`
- `month`
- `grass_region`
- `cb_level1_global_be_category`
- `level2_global_be_category`
- `level3_global_be_category`
- `marketplace_order(SUM)`
- `marketplace_gmv_usd(SUM)`
- `cncb_order(SUM)`
- `cncb_gmv_usd(SUM)`
- `marketplace_ads_gmv_usd(SUM)`
- `marketplace_campaign_gmv_usd(SUM)`
- `marketplace_lpp_gmv_usd(SUM)`
- `marketplace_cfs_gmv_usd(SUM)`
- `marketplace_sold_skus(SUM)`
- `cncb_sold_skus(SUM)`
- `marketplace_live_skus(SUM)`

主要用途：

- 跨境卖家占比
- CNCB penetration
- 广告、活动、CFS 等订单/GMV来源

#### price tier / price tier2

关键字段：

- `year_month`
- `seller_type`
- `grass_region`
- `cluster`
- `cb_level1_global_be_category`
- `level2_global_be_category`
- `level3_global_be_category`
- `Price_Range_USD`
- `ADO`
- `ADO_proportion`
- `ADO_CNCB_Penetration`
- `ADG`
- `ADG_proportion`
- `ADG_CNCB_penetration`
- `Live_SKUs`
- `Live_SKUs_proportion`
- `Live_SKUs_penetration`
- `SKU_Eff`
- `Mall_ADO`
- `Mall_ADG`
- `P3M_New_Live_SKUs`
- `YTD_New_Live_SKUs`
- `lpp_ado(SUM)`
- `lpp_adg(SUM)`
- `cfs_ado(SUM)`
- `cfs_adg(SUM)`
- `campaign_ado(SUM)`
- `campaign_adg(SUM)`

主要用途：

- 不同价格段 GMV / Orders / SKU 分布
- 价格段 YoY
- Mall 卖家占比与客单价
- 新品 SKU 表现

#### top shop

关键字段：

- `update_date`
- `grass_region`
- `cb_level1_global_be_category`
- `level2_global_be_category`
- `level3_global_be_category`
- `shop_id`
- `shop_link`
- `ggp_account_name`
- `is_cnrm_managed`
- `user_name`
- `mtd_adgmv_usd(SUM)`
- `mtd_ado(SUM)`
- `mtd_ads_adgmv_usd(SUM)`
- `mtd_ads_ado(SUM)`
- `mtd_campaign_adgmv_usd(SUM)`
- `mtd_cfs_adgmv_usd(SUM)`

主要用途：

- Top Shop 排行
- 头部卖家 GMV 占比
- 头部卖家订单来源
- 广告、直播、短视频、活动、CFS 等贡献

#### keywords

关键字段：

- `seller_type`
- `grass_region`
- `cb_level1_global_be_category`
- `level2_global_be_category`
- `level3_global_be_category`
- `keyword`
- `keyword_rank(SUM)`
- `current_daily_item_click(SUM)`
- `benchmark_daily_item_click(SUM)`
- `daily_item_click_growth(SUM)`
- `daily_item_click_diff(SUM)`

主要用途：

- 近期广告热词
- 点击增长潜力词

#### 热门商品

关键字段：

- `item_name`
- `item_link`
- `item_image`
- `grass_region`
- `cb_level1_global_be_category`
- `level2_global_be_category`
- `level3_global_be_category`
- `item_price_usd`
- `current_ado(RAW)`
- `current_adgmv(RAW)`

主要用途：

- Top Listing
- 商品价格样本
- 商品链接与图片素材

### DECK 已识别 Part

#### DECK-01 Part 1：市场整体趋势 & 增长潜力

- 来源 sheet：`过去数据`
- 处理规则：
  - 按 L1/L2/L3 输入决定类目过滤层级。
  - 按 site 聚合 GMV / Orders。
  - 对比上个月与去年上个月，计算 YoY。
  - 计算 ABS：GMV / Orders。
  - 生成最近 12 个月趋势。
- 可描述：
  - 各市场销售额增长
  - 各市场订单增长
  - 各市场客单价
  - 各市场月度趋势

#### DECK-02 Part 2：跨境卖家

- 来源 sheet：`daily data`
- 处理规则：
  - 按类目和站点聚合 Marketplace GMV / CNCB GMV。
  - 计算跨境卖家市场占有率：`cncb_gmv_usd / marketplace_gmv_usd`。
- 可描述：
  - 跨境卖家占比
  - CNCB 在该类目/市场的渗透情况

#### DECK-03 Part 3：品牌卖家市场占有率 & 平均客单

- 来源 sheet：`price tier`
- 处理规则：
  - 按类目、站点、价格段聚合 ADG / ADO。
  - 使用 Mall_ADG / Mall_ADO 计算 Mall 卖家占比和 Mall ABS。
- 可描述：
  - 品牌/Mall 卖家市场占比
  - Mall vs non-Mall 客单价差异

#### DECK-04 Part 4：不同价格段 GMV 分布情况 & 增速

- 来源 sheet：`price tier`、`price tier2`
- 处理规则：
  - `price tier` 表示当前期价格段表现。
  - `price tier2` 表示对比期价格段表现。
  - 按 `Price_Range_USD`、site、类目聚合 ADG / ADO / Live_SKUs 等。
  - 计算价格段占比与 YoY。
- 可描述：
  - 各价格段 GMV / Orders 贡献
  - 各价格段增长
  - SKU 分布和效率

#### DECK-05 Part 5：Top Shop 排行

- 来源 sheet：`top shop`
- 处理规则：
  - 按类目、站点、ADG 阈值过滤。
  - 按 `mtd_adgmv_usd(SUM)` 或 `mtd_ado(SUM)` 排名。
- 可描述：
  - 各市场 Top Shop
  - 头部卖家集中度

#### DECK-06 Part 5：Top Shop 市场占比 & 订单来源 & 广告情况

- 来源 sheet：`top shop`
- 处理规则：
  - 汇总头部卖家 GMV。
  - 计算头部卖家 GMV / TTL GMV。
  - 计算广告、AMS、直播、短视频、活动、CFS 等来源占比。
- 可描述：
  - 头部卖家市场占比
  - 头部卖家的流量/订单来源结构
  - 广告和活动贡献

#### DECK-07 Part 6：近期广告热词

- 来源 sheet：`keywords`
- 处理规则：
  - 按类目、站点筛选关键词。
  - 按 keyword_rank 排序。
  - 使用 current vs benchmark click 计算增长。
- 可描述：
  - 热门关键词
  - 点击增长潜力词

#### DECK-08 Part 7：Top Listing

- 来源 sheet：`热门商品`
- 处理规则：
  - 按类目、站点筛选商品。
  - 按 `current_ado(RAW)` 或 `current_adgmv(RAW)` 排名。
  - 保留 item name、link、image、price。
- 可描述：
  - Top listing 商品清单
  - 商品图、链接、价格、订单/GMV表现

## 给规划 agent 的使用建议

当用户提出一个类目分析需求时：

1. 先用 processed 类目树定位 L1/L2/L3 候选。
2. 再判断需求需要哪些问题类型：
   - 大盘趋势 / YoY / ABS：优先看 RM 模块或 DECK Part 1。
   - 站点比较 / 气泡图：优先看 RM 模块。
   - 价格段：看 DECK Part 4。
   - Top listing：看 DECK Part 7。
   - Top shop：看 DECK Part 5。
   - 关键词：看 DECK Part 6。
   - 跨境卖家占比：看 DECK Part 2。
   - Mall/品牌卖家：看 DECK Part 3。
3. 对每个分析块生成数据需求时，记录：
   - `source_workbook`
   - `source_sheet`
   - `formula_reference_sheet`
   - `filter_fields`
   - `metric_fields`
   - `derived_metrics`
   - `can_answer`
   - `limitations`

## 当前限制

- 本文档基于公式引用和表头结构整理，尚未逐格复刻所有公式。
- `CNCB 中间表 By site` 中部分区域是为前台展示或 Google Sheet 函数生成的辅助结果，程序化复用时应优先复刻底层 `SUMIFS` 逻辑。
- `DECK` 部分公式含 Google Sheet 函数痕迹，自动化时应改写为 Pandas/SQL 风格聚合，而不是直接执行原公式。
