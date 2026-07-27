# CateMate V2 设计构想（迭代中）

> **状态：迭代中（Living doc）** — 描述 V2 目标架构与已落地能力；**Streamlit 默认主链路为 `v2_solve_loop`**。  
> 更新时间：2026-07-27（v1.2.0）  
> V1 对照：[CATEMATE_V1_DESIGN_OVERVIEW.md](CATEMATE_V1_DESIGN_OVERVIEW.md)

---

## 核心设计思想：Data Agent 的模块化边界

> **AI 负责「问什么 / 怎么编排」；写死的 Data Module + Scope 负责「算什么 / 算对」——用模块化边界换取 Agent 灵活性与数值正确率的平衡。**

| 层 | 职责 | 典型载体 | LLM？ |
|----|------|----------|-------|
| **认知层** | 理解需求、确认类目、生成 Concept Pack / Blueprint、指标扩展、结论与可视化提案 | `understanding/`、`orchestration/blueprint_*`、`conclusion_brief/`、`html_report/` | 是（可 fallback） |
| **契约层** | 限制 Agent 能调用的能力面；写死算数与列契约 | `data_modules/*/compute.py`、`source_schema.yaml`、`output_grain_policy.yaml`、active 白名单 | 否 |
| **取数层** | 决定哪些行进入计算；Sub-L3 可审计过滤 | `scope/`、`if_related`、`subset_precompute`、`scope_kind` | 否（词表可由 LLM 生成，打分确定性） |

```mermaid
flowchart LR
  subgraph flex [灵活性_LLM]
    U[理解与澄清]
    B[Blueprint编排]
    C[消费层叙事]
  end
  subgraph correct [正确率_确定性]
    S[Scope取数]
    M[Module_compute]
    W[Data_Workbook]
  end
  U --> B --> S --> M --> W --> C
```

这样设计的原因：纯 LLM data agent 容易「编数字」；纯规则系统又难覆盖自然语言分析意图。CateMate 把**意图编排**交给 LLM，把**数值正确性**钉在可测试的 Python 模块上。

---

## V2 要解决什么

V1 已验证：**理解 → 选模块 → 确认 → PPT-ready** 的流程骨架可用，但业务算数仍大量依赖通用 `groupby` 猜测，模块是「YAML 说明书」而非确定性数据产品。

V2 聚焦一个更硬的目标：

> 如何把分析目标翻译成 **可编排、可缺数协商、可审计的 Data Workbook**——其中每一个数字都来自 **写死的 Python 模块**，而不是 Excel 公式或 LLM 即兴聚合？

PPT / HTML / Conclusion Brief 在 V2 中是**消费层**（可后调）；**Data Workbook** 是主交付物。

---

## V2 核心公式

```text
实际分析语义 = 取数方式（Scope）× 计算内核（Data Module）
```

- **Scope（外部取数）**：决定哪些行进入计算——站点、时间、类目/店铺/商品过滤、Sub-L3 `if_related`、数据源选择。  
- **Data Module（计算内核）**：只规定**源列名 + Python 聚合规则**；不在模块内写死「研究哪个品类」、不规定 Excel 从哪来。

同一内核可被多次调用（不同 `scope_kind`、不同 `metric_id`），用于对照分析：

| scope_kind | 含义 |
|------------|------|
| `standard` | 普通 L3 / Top SKU |
| `subset` | Sub-L3 精准子集（item + Concept Pack） |
| `parent_l3` | 父级 L3 全量（category） |
| `comparison` | 子集占父 L3 份额（派生表，非 catalog 源） |

---

## V2 与 V1 的关系

| 维度 | V1（兼容链路） | V2（默认主链路） |
|------|----------------|------------------|
| 模块形态 | `config/data_modules/*.yaml` 扁平说明书 | `data_modules/<id>/` 目录化 + `compute.py` |
| 算数 | 通用 `chart_data_builder` groupby | 每模块写死 Python + 单测 |
| 源数据 | `CateMate_rawdata/` 扁平 Excel | `rawdata/{category,shop,item}/` 分维度 |
| 选能力 | 一次 module selection | **意图编排** Solve Loop：grain × module × metric × scope |
| 缺数据 | workbook `missing_data_questions` | **澄清流扩展**：用户贴文件路径 → ingest |
| 主输出 | PPT-ready + HTML | **Data Workbook**；Brief / Visual Report / PPT 为消费层 |

**原则：V1 流程骨架保留**（Streamlit、manifest、Gate A/B）；V2 替换的是 **B 面模块资产** 与 **数据供给 / 编排** 方式。

---

## V2 端到端流水线（已落地）

```mermaid
flowchart TB
  NL[自然语言目标]

  subgraph gateA [Gate A · 澄清]
    U[需求理解]
    CAT[类目确认]
    READY[solve_loop_readiness]
    CP[Concept Pack]
    CL1[业务澄清]
    CL2[rawdata 路径澄清]
    U --> CAT --> READY --> CP --> CL1
  end

  subgraph pre [Sub-L3 预计算]
    PRE[subset_precompute]
    CACHE[ScopeCache + filter artifacts]
    PRE --> CACHE
  end

  subgraph solve [Solve Loop]
    BP[ReportBlueprint]
    PLAN[AnalysisPlan]
    CHECK[catalog 检查]
    EXEC[Scope + compute + comparison]
    ADV[指标扩展]
    VF[Solve Verifier]
    BP --> PLAN --> CHECK --> EXEC --> ADV --> VF
  end

  subgraph deliver [交付]
    WB[Data Workbook]
  end

  subgraph consume [消费层]
    BRIEF[Conclusion Brief]
    VR[Visual Report / HTML]
  end

  NL --> gateA --> pre --> solve --> WB
  CHECK -->|缺源| CL2 --> CHECK
  WB --> BRIEF
  WB --> VR
```

### 跳出数据澄清 loop 的条件

1. **用户不愿继续补充** — 对 `rawdata_*` 澄清题选择跳过；计划标记为 `partial`，Workbook 的 `Gaps` 区说明未覆盖项。  
2. **数据已齐或用户确认完成** — 结束 Gate A 数据阶段，进入 Scope + compute。

---

## 分层架构（V2）

```mermaid
flowchart TB
  subgraph ui [交互层]
    ST[Streamlit]
    CE[clarification_editor]
    VE[visual_report_editor]
  end

  subgraph cognition [AI 认知层]
    UG[需求理解]
    ORCH[Solve Loop]
    BRIEF[conclusion_brief]
    VR[html_report]
  end

  subgraph raw [源数据层]
    CAT[(rawdata/category)]
    SHOP[(rawdata/shop)]
    ITEM[(rawdata/item)]
    CATALOG[rawdata_catalog]
  end

  subgraph scope [取数层]
    PRE[subset_precompute]
    SC[Scope Executor]
    SF[ScopedFrame]
  end

  subgraph modules [计算层]
    DM[data_modules/]
    CMP[comparison_compute]
  end

  subgraph out [输出层]
    DWB[Data Workbook]
    GAPS[Gaps / Plan]
  end

  ST --> UG --> ORCH
  ORCH --> CATALOG
  CATALOG --> CAT & SHOP & ITEM
  ORCH --> PRE --> SC --> SF --> DM --> DWB
  DM --> CMP --> DWB
  DWB --> GAPS
  DWB --> BRIEF
  DWB --> VR --> VE
  CE --> ORCH
```

| 层级 | 职责 | V2 载体 |
|------|------|---------|
| **意图编排** | 目标 → `AnalysisPlan`（grain、module、metric、scope_kind）；缺源则生成澄清题 | `catemate/orchestration/` |
| **源数据 catalog** | 登记 category/shop/item 下表是否 available | `config/rawdata_catalog.yaml` |
| **Scope** | 读表、filter、`if_related`、预计算缓存 | `catemate/scope/` |
| **Data Module** | 源列契约 + 写死算数 + 延伸表族 | `data_modules/<module_id>/` |
| **Data Workbook** | Plan + 各 `table_id` sheet + Gaps | `catemate/modules/data_workbook.py` |
| **消费层** | 结论简报、Visual Report Spec、HTML | `conclusion_brief/`、`html_report/` |

---

## 源数据：三维度目录

```text
CateMate_rawdata/
  category/     # 类目维度表
  shop/         # 店铺维度表
  item/         # 商品维度表
```

每张表在 **rawdata catalog** 中登记：

- `grain`：`category` | `shop` | `item`
- `table_id`、期望列、文件路径、`status`（`available` / `missing`）

用户通过 **澄清流** 粘贴本地文件路径 → 校验 → 复制/登记到对应子目录 → 预处理 → 更新 catalog。

> **已拍板**：数据补充后由用户**贴回文件完整路径**；系统在澄清合并阶段触发 ingest，不依赖自动爬取。

### Rawdata 路径约定（V2 solve loop）

| grain | 物理路径 | 典型 table_id |
|-------|----------|---------------|
| category | `CateMate_rawdata/category/*.xlsx` | `dashboard_history`, `rm_raw_data` |
| item | `CateMate_rawdata/item/{L1}/{L2}/{L3}/*.csv` | `item_l3_category_csv` |

- V2 solve loop 对 `monthly_market_trend` 的 category/item run **禁止**回退到 `CateMate_processeddata` CSV。
- `subset_l3_{metric}_share_by_site_month` 为 **comparison 派生表**，由 subset + parent primary 表计算，不是 catalog 源表。

校验：`python scripts/validate_rawdata_catalog.py`

---

## Data Module（V2 资产模型）

目录：`data_modules/<module_id>/`（写作规范见 [data_modules/AUTHORING_SPEC.md](../data_modules/AUTHORING_SPEC.md)）

```text
source_schema.yaml    # 源列名 + compute_rules + transform_rules
contract.yaml         # 业务说明、outputs 登记、chart_presets（软）
compute.py            # 写死算数
transforms.py         # 延伸表（登记即全量计算）
<module_id>_review.md # 人读批注稿
```

### 硬性 vs 软性

| 必须写死 | 可后期调整 |
|----------|------------|
| `compute.py` / `transforms.py` | `chart_presets`（`binding: soft`） |
| `source_schema` 列名与规则 | HTML / PPT / Brief 文案样式 |
| 输出表 schema | 消费层选哪张表展示 |

### 试点模块：`monthly_market_trend`

| 项 | 规格 |
|----|------|
| 每次调用 | **一个** `metric_id`：`gmv` \| `orders` \| `aov` |
| 主表 | 一指标一表，grain = `grass_region × grass_month` |
| 延伸表 | 每指标 3 张：最新月各站 / 最新月占比 / 逐月环比 |
| grain 共用 | **category / shop / item 共用同一内核**；差异仅在 Scope 过滤与 catalog 源表 |
| 取数 | **不在 module 内**；由外部 Scope 传入已过滤行 |

---

## 意图编排：AnalysisPlan

编排器输出机器可读计划，示例（Sub-L3）：

```yaml
goal: PH 智能宠物碗趋势 + Top SKU
runs:
  - run_id: r1
    scope_kind: subset
    grain: item
    module_id: monthly_market_trend
    metric_id: gmv
    related_concept_pack: { ... }

  - run_id: r2
    scope_kind: parent_l3
    grain: category
    module_id: monthly_market_trend
    metric_id: gmv

  - run_id: r3
    scope_kind: comparison
    module_id: monthly_market_trend
    metric_id: gmv
    table_id: subset_l3_gmv_share_by_site_month
```

同一 `monthly_market_trend` + 不同 `scope_kind` / `grain` = 不同 Scope，**不是**不同 module。

---

## Gate A 澄清流扩展（已拍板）

在现有 `clarifying_questions` / `awaiting_clarification` 上扩展，**不另开 UI**：

| 阶段 | 问题类型 | 示例 |
|------|----------|------|
| 1a 业务 | `clarify_*` | 站点、类目、时间窗、分析目标 |
| 1b 数据 | `rawdata_*` | 缺 shop/item 表时请粘贴文件完整路径；可跳过 |

实现触点：

- `catemate/understanding/schemas.py` — `FILE_PATH` / rawdata 字段
- `app/clarification_editor.py` — 分区展示数据补充题
- 澄清答案 handler — 路径 → ingest → 刷新 catalog

---

## Data Workbook（V2 主交付）

| Sheet / 区块 | 内容 |
|--------------|------|
| **Plan** | 目标、AnalysisPlan、已执行 / blocked 的 run |
| **Data.\<table_id\>** | 各次 module 产出的主表、延伸表、comparison 表 |
| **Gaps** | 缺源、用户跳过、partial 说明 |
| **Confirmation** | 可选，延续 V1 Gate B |

「能完整回答目标」= Plan 中每个子问题有对应 Data sheet，或在 Gaps 中有显式说明。

---

## 业务认知迭代面（V2 演进）

```mermaid
flowchart LR
  A["A · 澄清 + 数据 loop"]
  B["B · 可执行模块目录"]
  C["C · 编排 + Workbook"]
  D["D · Brief / HTML / PPT 消费"]
  A --> B --> C --> D
```

| 面 | V1 | V2 |
|----|----|----|
| **A** | 问站点/类目 | + rawdata 就绪 loop、路径 ingest、Sub-L3 readiness |
| **B** | YAML 说明书 | `source_schema` + Python + pytest |
| **C** | adapter + generic builder | Solve Loop + Scope + multi-scope 表族 → Workbook |
| **D** | default_charts 绑 chart_type | Conclusion Brief + Visual Report Spec + HTML |

---

## 实施路线

| 阶段 | 内容 | 状态 |
|------|------|------|
| **0** | 可执行 data modules + 单测 | ✅ 2 active + 5 draft |
| **1** | `rawdata_catalog` + 三维度源表登记 | ✅ 已落地 |
| **2** | Scope 执行器 + related / concept pack | ✅ 已落地 |
| **3** | Solve Loop + `rawdata_*` 澄清 + 路径 ingest | ✅ 已落地 |
| **4** | Data Workbook 组装（Plan / Data / Gaps） | ✅ 已落地 |
| **4b** | Sub-L3 预计算 / ScopeCache / filter artifacts | ✅ 已落地（v1.2.0） |
| **4c** | multi-scope comparison（subset vs parent） | ✅ 已落地（v1.2.0） |
| **5** | 逐步用 V2 模块替换 V1 YAML 模块 | 🔄 进行中 |
| **6** | Conclusion Brief + HTML Visual Report | ✅ 已落地（v1.2.0） |

---

## 相关文档

| 文档 | 内容 |
|------|------|
| [CHANGELOG.md](../CHANGELOG.md) | 版本记录（当前 v1.2.0） |
| [CATEMATE_V1_DESIGN_OVERVIEW.md](CATEMATE_V1_DESIGN_OVERVIEW.md) | V1 架构 |
| [data_modules/AUTHORING_SPEC.md](../data_modules/AUTHORING_SPEC.md) | 模块写作指示 |
| [PROJECT_LAYOUT.md](PROJECT_LAYOUT.md) | 目录结构 |
| [AI_CORE_INDEX.md](AI_CORE_INDEX.md) | Agent 导航与 LLM 调用清单 |

---

## 修订记录

| 日期 | 说明 |
|------|------|
| 2026-07-27 | **v1.2.0**：核心设计思想置顶；Sub-L3 预计算、multi-scope comparison、Conclusion Brief / HTML 消费层；端到端图与实施路线同步 |
| 2026-07-16 | **v1.1.0**：solve loop 收束为 2 active 模块；新增 Sub-L3 / if_related / output_grain_policy；5 个模块降为 draft |
| 2026-07-15 | 初稿：Scope×Module、三维度 rawdata、澄清 loop、共用 monthly_market_trend、Data Workbook |
