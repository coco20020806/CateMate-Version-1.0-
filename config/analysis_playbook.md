# CateMate 类目分析标准流程（Blueprint Playbook）

面向报告蓝图设计：在**当前已启用的 V2 data module** 范围内组织章节。  
上游流程中，用户**已确认目标 L3 类目**（见 `RequirementUnderstandingSpec` 中的 `category_positioning.confirmed_candidates`）。  
本 playbook 不再判断 L1/L2/L3 映射，只在此基础上决定分析对象与章节结构。

## 当前 V2 已启用 module（solve loop 唯一能力边界）

| module_id | 用途 |
|-----------|------|
| `monthly_market_trend` | 月度 GMV / Orders / AOV 趋势（输出粒度：月） |
| `top_sku_info` | L3 子集或 item 粒度下的 Top SKU 排名 |

其余 `data_modules/` 下的 module 为 **draft**，保留实现与单测，**不得**出现在蓝图或执行计划中。  
用户说「最近」「近期」时，一律解释为**最近若干完整月份**，使用 `monthly_market_trend`，不要计划日度输出。

---

## 1. 分析对象判断（在已确认 L3 前提下）

进入蓝图设计前，先判断用户需求对应的是哪一种对象：

| 类型 | 含义 | 识别依据（参考） |
|------|------|------------------|
| **L3 类目本身** | 分析整个已确认 L3 的市场与结构 | `sub_l3_concept.is_sub_l3 = false`，且无 `related_concept_pack` |
| **L3 类目子集** | 分析 L3 内更细的概念/商品集合（如「智能宠物碗」之于「Bowls & Feeders」） | `sub_l3_concept.is_sub_l3 = true`，或存在 `related_concept_pack` |

若用户同时确认多个 L3，则对每个 L3 分别套用下列流程（可在蓝图中用多章节或并列 section 体现）。

---

## 2. 分析流程

### 2A. L3 类目本身（标准流程）

Scope 按已确认 L3 筛选，组织章节建议如下：

1. **市场大盘**（`monthly_market_trend`）  
   各站点月度 GMV / Orders / AOV 趋势。回答：市场多大、增还是减、各站贡献如何。

2. **站点对比**（`monthly_market_trend`，同 module 不同视角）  
   最新月各站占比、逐月环比。适用于 `site_comparison` 或多站点优先级判断。

### 2B. L3 类目子集（两段分析 + 对比）

子集分析须先收窄 Scope，再与父级 L3 对照，判断子集在类目中的表现。

**第一阶段：子集**

1. 在 Scope 中用 `item_name`（及 `related_concept_pack` 相关性规则）筛出子集数据。  
2. 对子集使用 `monthly_market_trend` 看月度销量/GMV 趋势（`orders` 或 `gmv`）。  
3. **必须包含** Top SKU 章节（`top_sku_info`），回答子集内头部商品有哪些。

**第二阶段：父级 L3**

1. 将 Scope 放宽到**已确认的整个 L3 类目**（不再应用子集 item_name 过滤）。  
2. 对 L3 整体再使用 `monthly_market_trend` 跑月度趋势。

**第三阶段：子集 vs L3 对比**

1. 计算子集与 L3 整体在 GMV、Orders、份额等维度上的占比与对比。  
2. 据此判断：该子集概念在所在 L3 中是强势细分、小众 niche，还是与大盘趋势一致/背离。  
3. 蓝图中应为对比结论预留明确章节或子问题（如「子集占 L3 GMV 比例如何？」），仍用 `monthly_market_trend` 产出月度表。

---

## 3. 章节设计规则

- 章节数量建议 **2–6 节**，每节只回答 **一个可验证子问题**。  
- 每节必须绑定 catalog 中真实的 `module_id`、`metric_id`、`grain`（仅限上述 2 个 active module）。  
- 按本章推荐顺序排列，但可跳过与需求无关的章节。  
- 输出时间粒度统一为**月**（`grass_month`）；不得规划日度表或 `daily_table` presentation。  
- **L3 子集**场景必须包含 `top_sku_info`；对比段应写清比较维度。

---

## 4. analysis_intent → 章节映射（参考，非硬编码）

| analysis_intent | 优先考虑 |
|-----------------|----------|
| market_trend | `monthly_market_trend` / gmv 或 orders |
| site_comparison | `monthly_market_trend` / 多站趋势与占比 |
| top_listing | `top_sku_info` / item grain |
| top_shop | `monthly_market_trend` / shop grain（若未来启用 shop 级 active module） |
| price_tier | `monthly_market_trend` / 暂以月度 GMV 趋势替代 |
| keywords | 当前无 active module，跳过 |
| daily_performance | 用 `monthly_market_trend` 最近月份替代，不选日度 module |
| price_reference | `monthly_market_trend` / aov 或 `top_sku_info` |
