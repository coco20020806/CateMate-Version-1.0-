# CateMate 使用说明

CateMate 是一个面向 Category Analysis 工作流的本地分析助手。当前 MVP 聚焦“类目分析数据需求确认 + PPT-ready 数据表生成”。

第一版不会直接生成正式报告或 PPT，而是完成以下闭环：

```text
源数据
  ↓
生成数据需求/确认 workbook
  ↓
Streamlit 人工确认
  ↓
confirmation gate 检查
  ↓
生成 PPT-ready workbook
```

## 当前已完成能力

1. 读取 `CateMate_rawdata` 中的 SPH Excel 源数据。
2. 预处理 `SPH类目树`，生成可查找的类目树表。
3. 生成数据需求/确认 workbook。
4. 在 Streamlit 中人工确认或舍弃确认项。
5. 检查确认项是否全部为 `已确认` 或 `不需要`。
6. 在确认通过后生成 PPT-ready workbook。

## 当前暂不支持

- 直接生成正式 PPT。
- HTML preview。
- 对外交付脱敏。
- 价格段分布分析。
- 关键词搜索量 YoY。
- 气泡图专用数据表 `yoy_bubble_data`。
- DeepSeek / Pydantic AI / LlamaIndex 工作流接入。

## 项目目录

```text
CateMate/
  app/                     Streamlit 前端入口
  catemate/                业务内核代码
    core/                  确认门禁、读写确认记录、路径等基础能力
    data/                  数据扫描与类目树预处理
    modules/               可复用业务模块
    schemas/               结构定义
    services/              外部服务预留
  config/modules/          分析模块配置
  CateMate_rawdata/        原始下载数据
  CateMate_processeddata/  预处理后的数据
  outputs/                 生成的 workbook
  docs/                    产品、流程与设计文档
  scripts/                 命令行脚本
```

## 运行方式

### 1. 生成数据需求/确认 workbook

```powershell
python scripts/run_category_requirement_demo.py
```

生成结果会放在 `outputs/`。

### 2. 打开 Streamlit V1 总控台

```powershell
streamlit run app/streamlit_dashboard.py
```

（`app/streamlit_app.py` 为兼容入口，行为相同。）

在页面中可完成整条 V1 链路：生成 workbook → 查看理解与选模块 → 编辑确认项 → 生成 PPT-ready。

### 3. 命令行检查 confirmation gate

检查最新确认 workbook：

```powershell
python scripts/check_confirmation_gate.py
```

检查指定 workbook：

```powershell
python scripts/check_confirmation_gate.py outputs/your_confirmed_workbook.xlsx
```

### 4. 生成 PPT-ready workbook

```powershell
python scripts/build_ppt_ready_workbook.py outputs/your_confirmed_workbook.xlsx
```

生成结果会放在 `outputs/`。

当前 PPT-ready workbook 包含：

- `ppt_data_catalog`
- `data_notes`
- `site_performance_l2`
- `l3_distribution`
- `monthly_trend_by_site`

### 5. 生成第二案例：VN Pet Healthcare PPT-ready workbook

```powershell
python scripts/build_pet_healthcare_ppt_ready_workbook.py
```

生成结果会放在 `outputs/`。

当前第二案例输出：

- `ppt_data_catalog`
- `data_notes`
- `vn_pet_health_trend`
- `vn_pet_health_price_tier`
- `vn_pet_health_avg_price`
- `vn_pet_health_top_listing`

## 关键规则

- 数字计算由 Python 数据工具完成，模型不能编造数字。
- PPT-ready workbook 必须在 confirmation gate 通过后才能生成。
- 用户补充数据后，状态应先为 `已补充`，Agent 复检通过后才能变为 `已确认`。
- 类目映射由系统列出候选，用户选择确认；系统不能自动声称前台类目等同于后台类目。
- PPT-ready workbook 是内部数据包，不做对外交付脱敏。

## 关键设计文档

- `docs/example_case_hkcb_collectible_workflow.md`：HKCB Collectible 样例流程记录。
- `docs/example_case_vn_livestock_pet_healthcare.md`：越南畜牧 / Pet Healthcare 样例流程记录。
- `docs/category_analysis_data_requirement_module.md`：类目分析数据需求模块说明。
- `docs/ppt_ready_workbook_design.md`：PPT-ready workbook 设计说明。
- `docs/cursor_prompt_streamlit_confirmation_ui.md`：交给 Cursor 实现确认页面的提示词。
- `docs/PROJECT_STATUS.md`：当前工程状态与后续路线。
