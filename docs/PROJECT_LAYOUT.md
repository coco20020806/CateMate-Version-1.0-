# CateMate 项目目录结构

更新时间：2026-07-15

本文档描述本地工作区的**推荐目录约定**。带 🔒 的目录已被 `.gitignore` 排除，不会进入公开 GitHub。

---

## 顶层一览

```text
CateMate/
├── app/                      # Streamlit 交互层
├── catemate/                 # 核心业务代码（Agent 流水线）
├── config/                   # 流水线配置（case、v2 模块、预处理规则）
├── data_modules/             # 新一代可执行数据模块（v3）
├── docs/                     # 设计文档与架构说明
├── examples/                 # 可公开的虚构 demo 数据
├── scripts/                  # CLI 入口脚本
├── tests/                    # 单测（含 data_modules 测试）
│
├── CateMate_rawdata/    🔒   # 原始 Excel（公司下载）
├── CateMate_processeddata/ 🔒 # 预处理 CSV（AI 读取层）
├── outputs/             🔒   # 流水线运行产物
├── _local/              🔒   # 本机私有笔记 / PPT / 草稿
│
├── README.md                 # GitHub 首页（含架构图）
├── README_使用说明.md
├── requirements.txt
├── .env.example
└── LICENSE
```

---

## 代码层

### `app/` — 交互层

| 文件 | 作用 |
|------|------|
| `streamlit_app.py` / `streamlit_dashboard.py` | V1 总控台入口 |
| `confirmation_editor.py` | 确认 Workbook 编辑 |
| `clarification_editor.py` | 需求澄清编辑 |
| `pipeline_runtime.py` | 读取 manifest、驱动流水线状态 |

### `catemate/` — Agent 内核

```text
catemate/
  understanding/       需求理解层（Gate A 澄清）
  module_selection/    数据模块选择层
  planning/            确定性规划层
  case_generation/     Case config 生成
  modules/             确认 Workbook 构建
  ppt_ready/           PPT-ready + HTML 预览
  pipeline/            Manifest 与 run 编排
  core/                路径、确认门禁
  data/                源数据扫描、类目树
  ai/                  LLM 客户端
  schemas/             Pydantic 结构定义
  config/              Case config 加载
```

### `scripts/` — 命令行入口

常用脚本：

| 脚本 | 用途 |
|------|------|
| `run_natural_language_requirement_pipeline.py` | 一键完整链路 |
| `run_category_requirement_case.py` | 从 case YAML 生成需求 Workbook |
| `preprocess_raw_data_sources.py` | Raw Excel → processed CSV |
| `build_ppt_ready_from_confirmed_workbook.py` | 确认后生成 PPT-ready |
| `check_confirmation_gate.py` | 确认门禁检查 |

---

## 配置层

### `config/`

```text
config/
  cases/                  真实业务 case（🔒 具体 yaml 被 gitignore）
  data_modules/           v2 扁平模块 YAML（当前流水线使用）
  modules/                分析模块配置
  processed_data_sources.yaml   Raw → processed 抽取规则
```

### `data_modules/` — v3 可执行模块（新）

与 `config/data_modules/` 并存，面向**目录化、可测试**的模块实现：

```text
data_modules/
  AUTHORING_SPEC.md           模块写作规范
  monthly_market_trend/         示例模块（contract + compute.py）
  monthly_market_trend_review.md
```

| 代际 | 位置 | 特点 |
|------|------|------|
| **v2** | `config/data_modules/*.yaml` | 扁平 YAML，当前主链路 module selection 使用 |
| **v3** | `data_modules/<id>/` | 目录化 + Python compute + pytest |

### `examples/` — 公开演示

```text
examples/
  cases/demo_stationery_sg.yaml
  processed_data/             合成 CSV + manifest
  bootstrap_demo_data.ps1       复制到 CateMate_processeddata/
```

---

## 数据层 🔒

### `CateMate_rawdata/`

放置从内部看板下载的 **原始 Excel**。不进 Git。

### `CateMate_processeddata/`

由预处理脚本生成的 **processed CSV**，AI 运行时优先读取：

```text
CateMate_processeddata/
  sph_category_tree_lookup.csv
  source_tables/
    rm_raw_data.csv
    dashboard_history.csv
    ...
  processed_manifest.yaml       数据血缘 manifest
```

生成命令：

```powershell
python scripts/preprocess_raw_data_sources.py
```

无真实 Excel 时，用演示数据：

```powershell
.\examples\bootstrap_demo_data.ps1
```

---

## 产出层 🔒

### `outputs/`

所有流水线产物，按 run 隔离：

```text
outputs/
  runs/<case_id>_<timestamp>/    单次 run 的全套 JSON / xlsx / html
  _legacy/                        历史归档
  _cleanup_inventory.json         清理盘点（脚本生成）
  README.md
```

> 旧版根目录 `runs/` 已废弃，统一使用 `outputs/runs/`。

---

## 本机私有区 🔒

### `_local/`

仅本机使用的材料，不进 Git：

```text
_local/
  notes/              产品构想、个人笔记
  private_assets/     参考 PPT、截图
  README.md
```

---

## 已清理的遗留目录

| 原目录 | 处理 |
|--------|------|
| `example/` | 已删除；PPT 移至 `_local/private_assets/` |
| `processed/` | 已删除；与 `CateMate_processeddata/` 重复 |
| `runs/`（根目录） | 已删除；空目录，现用 `outputs/runs/` |
| `CateMate_新产品构想.md`（根目录） | 已移至 `_local/notes/` |

---

## 测试

```text
tests/
  data_modules/monthly_market_trend/test_compute.py
  fixtures/data_modules/...
```

```powershell
pytest tests/data_modules/
```

---

## 相关文档

- 架构设计：[CATEMATE_V1_DESIGN_OVERVIEW.md](CATEMATE_V1_DESIGN_OVERVIEW.md)
- Agent 导航：[AI_CORE_INDEX.md](AI_CORE_INDEX.md)
- 开源清单：[OPEN_SOURCE_CHECKLIST.md](OPEN_SOURCE_CHECKLIST.md)
- v3 模块规范：[../data_modules/AUTHORING_SPEC.md](../data_modules/AUTHORING_SPEC.md)
