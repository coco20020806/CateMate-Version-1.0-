# CateMate

> 面向 **Category Analysis** 的 AI 辅助工作流 Demo — 把自然语言需求，转成可确认、可追溯、可生成 PPT-ready 数据的分析流水线。

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.10%2B-blue)](requirements.txt)
[![Streamlit](https://img.shields.io/badge/UI-Streamlit-FF4B4B)](app/streamlit_app.py)

**个人 AI Demo 项目，非生产系统。** 仓库不含真实业务数据，请用 [`examples/`](examples/) 合成数据体验。

中文操作说明 → [README_使用说明.md](README_使用说明.md) · 完整设计文档 → [docs/CATEMATE_V1_DESIGN_OVERVIEW.md](docs/CATEMATE_V1_DESIGN_OVERVIEW.md)

---

## 架构设计

CateMate 的目标不是让 AI 直接「编一份报告」，而是把业务需求翻译成**可审查的数据准备流程**，在人工确认通过后再输出 PPT-ready 数据包。

### 三大设计原则

| 原则 | 说明 |
|------|------|
| **先理解，再生成** | 自然语言需求先结构化为站点、类目、分析意图、假设与待澄清问题 |
| **模块化，不自由发挥** | 从预定义 data module 目录中选择能力，而非让 AI 即兴设计图表 |
| **人工确认门禁** | 缺数、类目映射、关键假设未确认前，禁止生成 PPT-ready 输出 |

### 端到端流水线

```mermaid
flowchart LR
  NL[自然语言需求] --> U[需求理解]
  U --> MS[数据模块选择]
  MS --> P[确定性规划]
  P --> WB[确认 Workbook]
  WB --> G{Confirmation Gate}
  G -->|通过| PPT[PPT-ready Workbook]
  PPT --> HTML[HTML 图表预览]

  U -.->|待澄清| CL[人工澄清]
  CL --> U
  WB -.->|待确认| CF[Streamlit 人工确认]
  CF --> G
```

### 分层架构

```mermaid
flowchart TB
  subgraph ui [交互层]
    ST[Streamlit Dashboard]
    CE[确认 / 澄清编辑器]
  end

  subgraph ai [AI 认知层]
    CC[Case Config 生成]
    UG[需求理解 Generator]
    SEL[模块选择 Selector]
  end

  subgraph plan [规划层 · 确定性]
    AD[Module Selection Adapter]
    PS[Planning Spec]
  end

  subgraph data [数据层]
    RAW[(CateMate_rawdata<br/>原始 Excel)]
    PROC[(CateMate_processeddata<br/>Processed CSV)]
    MOD[config/data_modules<br/>业务问题模块]
  end

  subgraph out [输出层]
    WB[数据需求 / 确认 Workbook]
    GATE[Confirmation Gate]
    PR[PPT-ready + HTML Preview]
  end

  ST --> CC & UG & SEL
  CE --> WB
  UG --> SEL --> AD --> PS --> WB
  MOD --> SEL & AD
  PROC --> SEL & PR
  RAW -.预处理.-> PROC
  WB --> GATE --> PR
```

| 层级 | 职责 | 代码目录 |
|------|------|----------|
| **需求理解层** | 提取站点、类目、分析目标、假设与澄清问题 | `catemate/understanding/` |
| **模块选择层** | 从 data module 目录匹配业务问题（selected / optional / rejected） | `catemate/module_selection/` |
| **规划层** | 将选中模块转为 chart intent、指标、维度、排序规则 | `catemate/planning/` |
| **确认 Workbook** | 可审计的人工审查载体：类目映射、数据需求、图表规格 | `catemate/modules/` |
| **Confirmation Gate** | 阻断缺数 / 未确认映射 / 未完成确认项 | `catemate/core/confirmation_gate.py` |
| **PPT-ready 输出** | 结构化图表数据包 + 血缘说明 + HTML 预览 | `catemate/ppt_ready/` |

### 两道人工门禁

```mermaid
flowchart TB
  subgraph gateA [Gate A · 需求澄清]
    Q[系统生成澄清问题]
    H1[人工回答 / 跳过]
    M[批量合并理解结果]
  end

  subgraph gateB [Gate B · 数据确认]
    W[确认 Workbook]
    H2[人工确认 / 舍弃各项]
    C[Confirmation Gate 检查]
  end

  Q --> H1 --> M
  W --> H2 --> C
  C -->|全部已确认或不需要| OK[允许生成 PPT-ready]
  C -->|存在阻塞项| BLOCK[拒绝生成]
```

### 数据与模块：两层分工

```mermaid
flowchart LR
  subgraph assets [数据资产层]
    M[processed_manifest.yaml]
    T[source_tables/*.csv]
    L[sph_category_tree_lookup.csv]
  end

  subgraph business [业务问题层]
    D1[dashboard_history_market_trend]
    D2[dashboard_price_tier_distribution]
    D3[rm_monthly_category_performance]
    D4[...]
  end

  RAW[原始 Excel] -->|preprocess| assets
  business -->|引用| assets
  business -->|驱动| PLAN[规划 & 图表生成]
```

- **数据资产层**（`CateMate_processeddata/`）：AI 优先读取的 processed CSV + manifest，避免反复打开大型 Excel
- **业务问题层**（`config/data_modules/*.yaml`）：每个模块描述「能回答什么业务问题、用哪些表、能生成什么图」

### 业务知识的三处迭代面

流程骨架（Streamlit、manifest、两道 gate、PPT-ready）相对稳定；**业务认知**主要在以下三处持续迭代：

```mermaid
flowchart LR
  A["A · 澄清策略<br/>问什么 / 假设什么"]
  B["B · 模块目录<br/>能分析什么"]
  C["C · 规划映射<br/>模块如何变成图表"]
  A --> B --> C
```

| 迭代面 | 工作流步骤 | 配置载体 |
|--------|------------|----------|
| **A** 澄清策略 | 需求理解 | understanding prompt / schema |
| **B** 模块目录 | 模块选择 | `config/data_modules/*.yaml` |
| **C** 规划映射 | 确定性规划 | `module_selection_adapter` + 模块规则 |

---

## 快速开始

```powershell
pip install -r requirements.txt
copy .env.example .env          # AI 功能需填写 DEEPSEEK_API_KEY

.\examples\bootstrap_demo_data.ps1
python scripts/run_category_requirement_case.py examples/cases/demo_stationery_sg.yaml
streamlit run app/streamlit_app.py
```

一键完整链路（需 API Key）：

```powershell
python scripts/run_natural_language_requirement_pipeline.py --planning-mode module_selection
```

---

## 项目结构

```text
catemate/
  understanding/       需求理解层
  module_selection/    模块选择层
  planning/            规划层
  ppt_ready/           PPT-ready 生成
  core/                确认门禁、路径
app/                   Streamlit 总控台
config/
  data_modules/        业务问题模块（YAML）
  processed_data_sources.yaml
scripts/               CLI 入口
examples/              虚构 demo case + 合成数据
docs/                  设计文档
```

本地专用（不进公开仓库）：`CateMate_rawdata/` · `CateMate_processeddata/` · `outputs/`

---

## 相关文档

| 文档 | 内容 |
|------|------|
| [CATEMATE_V1_DESIGN_OVERVIEW.md](docs/CATEMATE_V1_DESIGN_OVERVIEW.md) | V1 完整架构与设计原则 |
| [data_module_catalog.md](docs/data_module_catalog.md) | 数据模块业务说明 |
| [AI_CORE_INDEX.md](docs/AI_CORE_INDEX.md) | Agent 开发导航索引 |
| [examples/README.md](examples/README.md) | 演示数据使用说明 |

---

## License

[MIT](LICENSE) — 个人 demo 项目，按原样提供，无生产级保证。
