# 数据模块录入稿 — top_sku_info（已定稿）

> Agent 依据：`AUTHORING_SPEC.md` + 本录入稿生成模块。  
> 定稿日期：2026-07-15

- **录入稿路径**：`data_modules/top_sku_info_INTAKE.md`
- **填表人**：fei.kong
- **填写日期**：2026-07-15

---

## §1 模块身份

| 字段 | 填写 |
|------|------|
| `module_id`（英文 snake_case） | `top_sku_info` |
| `module_name`（中文名） | Top SKU 商品信息 |
| `module_type` | `listing` |
| `status` | `active` |
| 替代的旧 v2 模块（无则留空） | `dashboard_top_listing`、`data_modules/top_listing`（**确认替代**） |

---

## §2 业务说明

### 2.1 一句话描述

读取外部 Scope 已过滤的 **item 文件夹**（`item_l3_category_csv`）商品明细，在指定 **站点 × 时间** 切片内，按 **orders** 或 **gmv_usd** 排序，输出 Top N SKU 及其商品信息（名称、链接、价格等）。

### 2.2 典型能回答的问题

- 该分类的头部商品是什么？
- 该分类一般卖什么？典型商品是什么？
- 某站点、某时间下，按订单量 / GMV 排名的代表性 SKU 有哪些？
- 头部 SKU 的价格、价格带等参考信息是什么？

### 2.3 明确不回答的问题

- 全量 SKU 均价或市场价格结构（应使用价格段分布类模块）
- 店铺级经营分析
- 跨站点汇总排名（本模块以 **单站点 × 单时间切片** 为展示单元）
- 月度趋势、环比等时间序列问题（应使用 `monthly_market_trend`）

### 2.4 决策支持场景（可选）

- 爆款商品对标与选品参考
- 了解类目头部 SKU 的价格带与链接信息
- 按订单量 vs 按 GMV 两种视角审视头部商品差异

---

## §3 实现模式

选择一种（Agent 据此选代码骨架）：

- [ ] **`monthly_metric_trend`** — 月度、站点×月份、每次一个指标、三延伸表
- [x] **`custom`** — Top N SKU 榜单；须在 §7 写清算数规则

### 3.1 主表粒度（本模块自定义）

| 项 | 填写 |
|----|------|
| 切片维度 | `grass_region`（站点）× 时间（`grass_month` 或归月后的 `grass_date`） |
| 排名单元 | 每个 **站点 × 时间切片** 内，对 SKU 按指标排序取 Top N |
| 时间处理 | 同 `monthly_market_trend`：`grass_month` 优先；仅有 `grass_date` 时解析并归一到月（`YYYY-MM-01`） |

---

## §4 源底表列名（Excel / CSV 表头）

> 数据源：**必须**使用 item 文件夹数据（`item_l3_category_csv`，`loader: category_folder`）。

### 4.1 必需列（缺则报错）

| column | 含义 | dtype |
|--------|------|-------|
| `grass_region` | 站点/区域（展示维度「某个 site」） | string |
| `item_name` | 商品名称（SKU 标识） | string |
| `item_link` | 商品链接 | string |

### 4.2 二选一必需（时间列，处理同 `monthly_market_trend`）

说明：时间列至少有一列；仅有 `grass_date` 时 compute 归一到 `grass_month` 用于切片。

| column | 含义 |
|--------|------|
| `grass_month` | 月份 |
| `grass_date` | 日期（将聚合/归一为 `grass_month`） |

### 4.3 至少其一必需（排序指标列）

说明：`orders` 与 `gmv_usd` **至少传入一列**；理想情况两列都有。  
`sort_by=both` 时：两列都有 → 各出一套表；**仅有一列 → 自动降级为按该列排序**（不报错、不产出缺列那套表）。

| column | 含义 |
|--------|------|
| `orders` | 订单量（排序指标候选） |
| `gmv_usd` | GMV 美元（排序指标候选） |

### 4.4 软期望列（缺不阻塞，输出 metadata 标记）

| column | 含义 |
|--------|------|
| `item_price_usd` | 商品价格（美元） |
| `price_range` | 价格带 |
| `cb_level1_global_be_category` | 一级类目 |
| `level2_global_be_category` | 二级类目 |
| `level3_global_be_category` | 三级类目 |
| `shop_id` | 店铺 ID |
| `item_image` | 商品图片 URL（**可有可没有**；当前业务不依赖，缺不阻塞） |

---

## §5 指标 / 排序维度定义

本模块不是「聚合指标主表」模式，而是 **榜单排序维度**。每次调用可指定排序规则；默认 **两种排序结果都输出**（源数据仅有一列指标时自动降级为单列排序）。

| sort_metric_id | 显示名 | 源列 | 排序方向 | 说明 |
|----------------|--------|------|----------|------|
| `orders` | 按订单量 | `orders` | desc | 源列 `orders` 存在时可用 |
| `gmv` | 按 GMV | `gmv_usd` | desc | 源列 `gmv_usd` 存在时可用 |

**`sort_by` 与可用列的对应关系（已确认）**：

| sort_by | orders 列 | gmv_usd 列 | 实际产出 |
|---------|-----------|------------|----------|
| `orders` | 任意 | 任意 | 仅 orders 排序表 |
| `gmv` | 任意 | 任意 | 仅 gmv 排序表 |
| `both`（默认） | 有 | 有 | orders + gmv 两套表 |
| `both`（默认） | 有 | **无** | **仅 orders 排序表**（自动降级） |
| `both`（默认） | **无** | 有 | **仅 gmv 排序表**（自动降级） |

**主表命名约定**：

| sort_metric_id | top_n | table_id |
|----------------|-------|----------|
| `orders` | 5 | `top_sku_by_orders_top5` |
| `orders` | 10 | `top_sku_by_orders_top10` |
| `orders` | 20 | `top_sku_by_orders_top20` |
| `gmv` | 5 | `top_sku_by_gmv_top5` |
| `gmv` | 10 | `top_sku_by_gmv_top10` |
| `gmv` | 20 | `top_sku_by_gmv_top20` |

**自定义 `top_n` 表名规则（已确认）**：`top_sku_by_{orders|gmv}_top{N}`  
例：`top_n=15` → `top_sku_by_orders_top15`、`top_sku_by_gmv_top15`

> 用户显式指定 `top_n` 时，仅产出该档位对应排序规则下的表。

**输出列**：

- 维度：`grass_region`, `grass_month`（统一展示归一后的月份，不单独保留原始 `grass_date`）
- 排名：`rank`（竞争排名：1, 2, 2, 4…）
- 商品：`item_name`, `item_link`
- 指标：`orders`, `gmv_usd`（有则带出）
- 软字段：`item_price_usd`, `price_range`, `item_image`（有则带出；`item_image` 可有可无）

---

## §6 延伸表

本模块 **不需要** `monthly_metric_trend` 标准三延伸表（最新月 / 占比 / 环比）。

**自定义延伸（当前无需求）**：

| output_table_id | 来源表 | transform 类型 | 说明 |
|-----------------|--------|----------------|------|
| — | — | — | 暂无 |

---

## §7 自定义算数规则（`custom` 模式）

### 7.1 compute 逻辑

```text
输入：ScopedFrame（外部 Scope 已按类目 filter 的 item 文件夹明细）

1. 校验必需列（§4.1）与时间列（§4.2 至少其一）
2. 校验排序指标列（§4.3 至少其一）
3. 时间归一（同 monthly_market_trend）：
     - 有 grass_month → 直接用
     - 仅 grass_date → parse → 归一到 grass_month（YYYY-MM-01）
4. 软期望列缺失 → 不阻塞；result.attrs["input_quality"] 记录缺失列名
5. 解析调用参数（§9）：
     - top_n：用户指定 → 仅该档位表；未指定 → 默认 top 5、10、20 三档
     - sort_by：orders | gmv | both（默认 both）
     - sort_by=both 时：若仅 orders 或仅 gmv 列存在 → **自动降级**为按可用列排序，不报错
6. 对每个 (grass_region, grass_month) 切片：
     - 按 item_name 聚合 orders、gmv_usd（sum）
     - 同一 item_name + grass_region + grass_month 下，item_link / 软字段理论上应一致；
       若异常出现多值，取 **第一行（first）**
     - 按指定 sort_metric 降序排序，竞争排名（1,2,2,4），取 top_n
7. 输出 dict[table_id → DataFrame]
```

### 7.2 transform 逻辑

无延伸 transform；榜单即最终交付表。

### 7.3 已确认算数细节

- [x] 同一 `item_name` 多行：先 `groupby(grass_region, grass_month, item_name)` 再 sum 指标
- [x] `item_link` / 软字段冲突：理论上不应出现；异常时取 **first（第一行）**
- [x] 并列排名：**竞争排名**（1, 2, 2, 4）
- [x] 未指定 `top_n`：一次调用产出 **top 5 + top 10 + top 20 三档**（每种生效的 sort_by 各三档）
- [x] `sort_by=both` 仅一列指标：自动降级为按该列排序
- [x] 自定义 `top_n` 表名：`top_sku_by_{orders|gmv}_top{N}`

---

## §8 数据源绑定（V2 编排 / Scope）

**仅支持 item grain**；必须使用 item 文件夹数据。

支持的 grain（维度）：

- [ ] category
- [ ] shop
- [x] item

| grain | 默认 table_id | 候选表 | 备注 |
|-------|---------------|--------|------|
| category | — | — | 不使用 |
| shop | — | — | 不使用 |
| item | `item_l3_category_csv` | `[item_l3_category_csv]` | `loader: category_folder`；`requires_scope: [category_l1, category_l2, category_l3]` |

> 取数、类目 filter 由外部 Scope 完成；本模块不实现 filter。

---

## §9 Scope / 调用约定

| 项 | 填写 |
|----|------|
| 每次调用必填参数 | `grass_region`（或由 Scope 限定单站）；时间切片（`grass_month` 或可归月的 `grass_date`） |
| 可变参数 `top_n` | 整数；用户可自由指定（仅该档位）。**未给指令时默认一次调用产出 top 5、10、20 三档** |
| 可变参数 `sort_by` | `orders` \| `gmv` \| `both`；默认 **`both`**。两列都有 → 最多 6 张表；仅一列 → 自动降级为 3 张表 |
| Scope 由外部完成 | **是**（类目路径、item 文件夹解析在 Scope） |
| 同一模块多次 Run 场景 | 不同 `top_n`；不同 `sort_by`；不同站点或时间切片 |

---

## §10 Planning（模块选中提示）

### 10.1 建议命中（explicit_triggers）

- 头部商品 / Top SKU / 热门商品 / 典型商品
- 该分类卖什么 / 代表性 listing
- 按 orders 或 gmv 排名的商品样本
- item 文件夹 / L3 类目商品明细

### 10.2 建议避免（avoid_when）

- 价格段分布、均价结构
- 店铺排名
- 月度市场趋势、环比
- 需要全量 SKU 而非 Top N 样本

---

## §11 画图预设（软参考，可后改）

| preset_id | sort_metric_id | output_table_id | suggested_chart_type |
|-----------|----------------|-----------------|----------------------|
| `top_sku_orders_table_5` | orders | `top_sku_by_orders_top5` | table |
| `top_sku_orders_table_10` | orders | `top_sku_by_orders_top10` | table |
| `top_sku_orders_table_20` | orders | `top_sku_by_orders_top20` | table |
| `top_sku_gmv_table_5` | gmv | `top_sku_by_gmv_top5` | table |
| `top_sku_gmv_table_10` | gmv | `top_sku_by_gmv_top10` | table |
| `top_sku_gmv_table_20` | gmv | `top_sku_by_gmv_top20` | table |

> 主交付为 Data Workbook 表族；图表为软绑定，可后调。

---

## §12 单测样例

**样例数据来源**（真实 item 文件夹 CSV）：

`CateMate_rawdata/item/Pets/Pet Accessories/Bowls & Feeders/2604-2606.csv`

**fixture 建议**：从上述文件抽取 **PH 站、`grass_month=2026-06-01`** 的 3 行作为 `sample_scoped.csv`（Scope 已过滤后的子集）：

| grass_month | grass_region | item_name（缩写） | orders | gmv_usd | item_link |
|-------------|--------------|-------------------|--------|---------|-----------|
| 2026-06-01 | PH | Wireless Pet Water Fountain… | 18.0 | 345.07 | demo.marketplace.example/…/51111240917 |
| 2026-06-01 | PH | DODO 3.2L Cat Fountain… | 2.0 | 78.75 | demo.marketplace.example/…/25532335819 |
| 2026-06-01 | PH | Automatic Chicken Waterer… | 0.333 | 0.844 | demo.marketplace.example/…/51761600086 |

（完整 `item_name` / `item_link` 以源 CSV 为准；fixture 可保留源文件表头全部列。）

**断言用例 A**：`grass_region=PH`，`grass_month=2026-06-01`，`top_n=2`，`sort_by=orders`

- 表 `top_sku_by_orders_top2` 共 2 行
- rank 1 → Wireless Pet Water Fountain（orders=18）
- rank 2 → DODO 3.2L Cat Fountain（orders=2）

**断言用例 B**：同上切片，`top_n=2`，`sort_by=gmv`

- 表 `top_sku_by_gmv_top2` 共 2 行
- rank 1 → Wireless Pet Water Fountain（gmv≈345.07）
- rank 2 → DODO 3.2L Cat Fountain（gmv≈78.75）

**断言用例 C**：`sort_by=both` 且输入 **仅含 `orders` 列**（去掉 gmv_usd）

- 只产出 `top_sku_by_orders_top*` 系列，**不产出** `top_sku_by_gmv_top*`
- 不报错；`attrs` 可标记 `sort_by_degraded=true`

**断言用例 D**：缺 `item_image` 列

- compute 不报错；`input_quality` 含 `item_image`（若登记为 soft_expected）

---

## §13 其他备注

- 列名使用 **源 Excel/CSV 表头**，与 `monthly_market_trend` 一致，不用逻辑列名。
- `rawdata_catalog` 中 `item_l3_category_csv` 当前登记列不含 `grass_date`、`item_link`、`item_price_usd`、`price_range`；本模块按业务需要扩展期望，以实际 item 文件夹 CSV 为准。
- `item_image`：软期望、可有可无；当前交付不依赖图片列。
- 与现有 `data_modules/top_listing` 差异：旧模块用 `current_adgmv(RAW)` / `current_ado(RAW)`，无站点×时间切片；本模块用 `gmv_usd` / `orders` + site×period Top N。

---

## Agent 生成清单（填完后由 Agent 勾选）

- [x] `data_modules/top_sku_info/source_schema.yaml`
- [x] `data_modules/top_sku_info/contract.yaml`
- [x] `data_modules/top_sku_info/compute.py`
- [x] `data_modules/top_sku_info/transforms.py`
- [x] `data_modules/top_sku_info/__init__.py`
- [x] `data_modules/top_sku_info_review.md`
- [x] `tests/data_modules/top_sku_info/test_compute.py`
- [x] `tests/fixtures/data_modules/top_sku_info/sample_scoped.csv`
- [x] `pytest` 通过
