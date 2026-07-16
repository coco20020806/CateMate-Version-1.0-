# CateMate 项目目录结构

更新时间：2026-07-16

本文档描述本地工作区的**推荐目录约定**。带 🔒 的目录已被 `.gitignore` 排除，不会进入公开 GitHub。

---

## 顶层一览

```text
CateMate/
├── app/                          # Streamlit 交互层
├── catemate/                     # Agent 内核（V1 + V2）
├── config/                       # 流水线配置
├── data_modules/                 # V2 可执行数据模块
├── docs/                         # 设计文档
├── examples/                     # 公开 demo 数据
├── scripts/                      # CLI 入口
├── tests/                        # 单测
│
├── CateMate_rawdata/        🔒   # 原始 Excel（category/shop/item）
├── CateMate_processeddata/  🔒   # 预处理 CSV
├── outputs/                 🔒   # 流水线产物
├── _local/                  🔒   # 本机私有笔记 / PPT
│
├── README.md                     # GitHub 首页
├── requirements.txt
└── LICENSE
```

---

## 代码层

### `app/` — 交互层

| 文件 | 作用 |
|------|------|
| `streamlit_dashboard.py` | 总控台；默认 `v2_solve_loop` |
| `category_confirmation_editor.py` | Gate A0：类目定位确认 |
| `clarification_editor.py` | Gate A1/A2：业务澄清 + rawdata 路径澄清 |
| `confirmation_editor.py` | V1 Gate B：确认 Workbook 编辑 |
| `pipeline_runtime.py` | 子进程调用 CLI |

### `catemate/` — Agent 内核

```text
catemate/
  understanding/       需求理解、类目确认、concept pack、Sub-L3 检测
  case_generation/     自然语言 → Case Config
  orchestration/       V2 意图编排 + Solve Loop（blueprint / plan / verify）
  scope/               V2 取数层（loader / filters / related → ScopedFrame）
  execution/           V2 执行层（遍历 AnalysisPlan → module compute）
  modules/             Workbook 组装（含 data_workbook.py）
  pipeline/            runner.py、v2_runner.py、manifest.py
  module_selection/    V1 数据模块选择
  planning/            V1 确定性 / AI 规划
  ppt_ready/           HTML / PPT-ready（含 build_from_data_workbook.py）
  data/                rawdata catalog、ingest、loader、类目树
  core/                路径、确认门禁
  ai/                  LLM 客户端
  schemas/             Pydantic 结构定义
```

### V1 vs V2 代码分工

| 链路 | 关键包 | 主交付物 |
|------|--------|----------|
| **V2（默认）** | `orchestration/` + `scope/` + `execution/` + `data_modules/` | `data_workbook_*.xlsx` |
| **V1（兼容）** | `module_selection/` + `planning/` + `config/data_modules/` | 确认 Workbook → PPT-ready |

---

## 配置层

### `config/`

```text
config/
  rawdata_catalog.yaml          # V2：源表登记（grain / status）
  analysis_playbook.md          # V2：报告蓝图章节顺序
  processed_data_sources.yaml   # Raw Excel → processed CSV
  data_modules/                 # V1 扁平模块 YAML
  cases/                        # 本地 case（yaml 🔒）
  modules/                      # 分析模块配置
```

### `data_modules/` — V2 可执行模块

```text
data_modules/
  AUTHORING_SPEC.md             模块写作规范
  MODULE_INTAKE_TEMPLATE.md     用户录入模板
  patterns/                     可复用 pattern 说明
  monthly_market_trend/         试点：月度一指标一表
  daily_cncb_performance/
  price_tier_distribution/
  top_shop/
  top_listing/
  top_sku_info/
  keywords/
```

| 代际 | 位置 | 特点 |
|------|------|------|
| **V1 YAML** | `config/data_modules/*.yaml` | 扁平说明书，module_selection 使用 |
| **V2 可执行** | `data_modules/<id>/` | `source_schema` + `compute.py` + pytest |

---

## 数据层 🔒

### `CateMate_rawdata/`

```text
CateMate_rawdata/
  category/          类目维度 Excel
  shop/              店铺维度（用户补充）
  item/              商品维度 / L3 文件夹 CSV
  category_tree_en.json
```

登记在 `config/rawdata_catalog.yaml`，缺表时通过澄清流贴路径 → `scripts/ingest_rawdata_from_path.py`。

### `CateMate_processeddata/`

```text
CateMate_processeddata/
  sph_category_tree_lookup.csv
  source_tables/*.csv
  processed_manifest.yaml
```

---

## 产出层 🔒

```text
outputs/
  runs/<case_id>_<timestamp>/
    pipeline_manifest_*.json
    requirement_understanding_*.json
    report_blueprint_*.json       # V2
    analysis_plan_*.json          # V2
    solve_verdict_*.json          # V2
    data_workbook_*.xlsx          # V2 主交付
    planning_spec_*.json          # V1
    ppt_ready_workbook_*.xlsx     # V1
  _legacy/
```

---

## 关键脚本

| 脚本 | 用途 |
|------|------|
| `run_natural_language_requirement_pipeline.py` | 主入口（支持 v2_solve_loop / module_selection） |
| `verify_v2_solve_loop.py` | V2 solve loop 离线验证 |
| `run_scope_and_compute.py` | Scope + compute 独立运行 |
| `ingest_rawdata_from_path.py` | 用户贴路径 → rawdata 入库 |
| `build_data_workbook.py` | Data Workbook 构建 |
| `preprocess_raw_data_sources.py` | Raw → processed |

---

## 测试

```text
tests/
  data_modules/           各 module compute 单测
  catemate/orchestration/ solve loop 单测
  catemate/scope/         取数 / related 单测
  fixtures/
```

```powershell
pytest tests/
```

---

## 相关文档

- V2 设计：[CATEMATE_V2_DESIGN_OVERVIEW.md](CATEMATE_V2_DESIGN_OVERVIEW.md)
- V1 设计：[CATEMATE_V1_DESIGN_OVERVIEW.md](CATEMATE_V1_DESIGN_OVERVIEW.md)
- Agent 导航：[AI_CORE_INDEX.md](AI_CORE_INDEX.md)
- 模块规范：[../data_modules/AUTHORING_SPEC.md](../data_modules/AUTHORING_SPEC.md)
