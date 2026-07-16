# CateMate 类目分析标准流程（Blueprint Playbook）

面向报告蓝图设计：在已有 data module 能力范围内，按「先宏观、后结构、再机会、必要时日度/精准子集」组织章节。

## 推荐分析顺序

1. **市场大盘（monthly_market_trend）**
   - 先看类目在各站点的月度 GMV / Orders / AOV 趋势
   - 适用于：市场有多大、增长还是下滑、各站贡献如何

2. **站点对比（monthly_market_trend，同一 module 不同视角）**
   - 最新月各站占比、逐月环比
   - 适用于：site_comparison 意图、多站点优先级判断

3. **结构拆解**
   - 价格带分布（price_tier_distribution）：价位结构、主流价格区间
   - 头部店铺（top_shop）：哪些 shop 贡献最大
   - 头部 listing / SKU（top_listing、top_sku_info）：代表性商品、爆款对标

4. **机会洞察（keywords）**
   - 热门搜索词、点击与转化相关关键词
   - 适用于：选品、内容、投放方向

5. **日度监控（daily_cncb_performance）**
   - Shopee / CNCB 日度订单与 GMV
   - 适用于：近期波动、活动期监控、daily_performance 意图

6. **精准子集 Top SKU（top_sku_info）**
   - Sub-L3 概念或 related concept pack 下的头部 SKU
   - 当用户需求比 L3 更细（如「智能宠物碗」）时必须包含

## 章节设计规则

- 章节数量建议 **3–8 节**，每节只回答 **一个可验证子问题**
- 每节必须绑定 catalog 中真实的 `module_id`、`metric_id`（若 module 支持）、`grain`
- 按 playbook 顺序排列，但可跳过与需求无关的章节
- 不要编造 catalog 中不存在的 module 或 metric
- 不要为 module 的 `not_suitable_for` / `avoid_when` 场景强行选 module
- Sub-L3 或 related concept pack 场景应包含 Top SKU 类章节（top_sku_info）

## 常见 intent → 章节映射（参考，非硬编码）

| analysis_intent | 优先考虑 |
|-----------------|----------|
| market_trend | monthly_market_trend / gmv 或 orders |
| site_comparison | monthly_market_trend / 多站趋势与占比 |
| top_shop | top_shop / shop grain |
| top_listing | top_listing 或 top_sku_info / item grain |
| price_tier | price_tier_distribution |
| keywords | keywords |
| daily_performance | daily_cncb_performance |
| price_reference | monthly_market_trend / aov 或 top_sku_info |
