# 类目分析数据需求模块

## 模块目标

`category_analysis_data_requirement` 是 CateMate v1 的第一个业务模块。它不直接生成正式报告，而是把类目分析需求转成一份 Excel 形式的数据需求集合。

这份 workbook 需要回答：

1. 用户到底想分析什么类目、什么场景、什么交付对象。
2. 当前源数据能支持哪些分析块。
3. 哪些数据缺失，缺失会影响什么。
4. 前台类目和后台分析类目之间如何映射。
5. 哪些判断需要用户确认。

## 第一版输入

- 用户原始需求文本。
- 目标类目文本，可以是 L1/L2/L3，也可以是前台类目路径或商品描述。
- `CateMate_rawdata` 中的 SPH Excel 源数据。

## 第一版输出

输出一个 Excel workbook，建议包含：

- `需求摘要`
- `类目映射候选`
- `分析计划`
- `数据需求清单`
- `源数据检查`
- `预处理规划`
- `图表PPT数据需求`
- `确认记录`

这份 workbook 是前置确认产物，不是最终 PPT-ready 数据 workbook。最终用于绘制 PPT 的数据 workbook 只能在确认记录全部通过后生成。

## 确认门禁规则

CateMate v1 必须遵守以下规则：

1. `确认记录` 中所有确认项必须是 `已确认` 或 `不需要`，才允许生成 PPT-ready workbook。
2. 如果存在 `待确认`、`待补充`、`已补充` 或 `阻塞`，系统不能生成 PPT-ready workbook，只能输出缺口反馈和下一步动作。
3. 用户补充数据后，系统不能直接视为完成。状态应先进入 `已补充`。
4. Agent 需要重新检查补充数据是否符合原缺口要求，例如文件是否存在、字段是否完整、口径是否能解决原分析块。
5. 复检通过后，状态才可以转为 `已确认`。
6. 复检不通过时，应回到 `待补充`，或者在必须项无法解决时标记为 `阻塞`。

状态定义：

- `待确认`：需要用户判断或确认。
- `待补充`：需要用户提供额外数据或字段。
- `已补充`：用户已放入数据，但 Agent 尚未确认可用。
- `已确认`：Agent 已确认该项可进入后续生成。
- `不需要`：用户确认跳过该项。
- `阻塞`：必须项无法满足，且不能通过跳过解决。

## 本案例中的关键规则

HKCB Collectible Category Insight 需求中，提需方给出的前台类目是：

- Shopee > Games, Books & Hobbies > Hobby Toys > Action Figures
- Shopee > Toys, Games & Collectibles > Character > Movies & Anime

但当前 SPH 类目树和 Raw data 中更接近的后台类目是：

- Hobbies & Collections > Collectible Items > Action Figurines
- Hobbies & Collections > Collectible Items > Anime & Manga Collectibles

因此系统需要提示：这是候选映射，不是自动等同，需要用户确认。

## 数据处理理解

`Raw data` 是底层月度数据，主要字段为：

- 站点：`grass_region`
- L1：`cb_level1_global_be_category`
- L2：`level2_global_be_category`
- L3：`level3_global_be_category`
- 月份：`grass_month`
- GMV：`gmv_usd`
- Orders：`orders`

`CNCB 中间表 By site` 通过公式说明了核心聚合逻辑：

- 按站点、月份、类目层级筛选。
- 聚合 GMV 和 Orders。
- 计算 YoY。
- 计算客单价，即 GMV / Orders。
- 输出气泡图可用结构。

`SPH类目树` 需要预处理为一张可搜索表。原表有层级空白行，因此预处理时需要向下继承 L1/L2/L3/L4。

## 后续扩展

这个模块后续可以接入：

- Pydantic AI：结构化理解用户需求。
- LlamaIndex Workflows：编排澄清、检查、确认、生成 workbook 的流程。
- Streamlit：提供本地交互页面。
- PPT-ready workbook 生成器：必须先调用确认门禁，通过后再生成作图数据表。
