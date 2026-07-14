# CateMate

面向 **Category Analysis** 工作流的本地 AI 辅助分析助手。  
当前 MVP 聚焦：类目分析数据需求确认 → 人工确认 → PPT-ready 数据表生成。

> **Demo 项目：** 个人编写的 AI 工作流演示，非生产系统。  
> 仓库**不包含**真实业务源数据；请用 [`examples/`](examples/) 中的合成数据体验。

中文详细使用说明见 [README_使用说明.md](README_使用说明.md)。

---

## 工作流

```text
需求理解 → 模块选择 → AI 规划 → 数据需求 workbook
    ↓
Streamlit 人工确认
    ↓
Confirmation gate → PPT-ready workbook
```

---

## 快速开始（仅演示数据）

```powershell
pip install -r requirements.txt
copy .env.example .env    # 按需填写 DEEPSEEK_API_KEY（AI 功能）

.\examples\bootstrap_demo_data.ps1
python scripts/run_category_requirement_case.py examples/cases/demo_stationery_sg.yaml
streamlit run app/streamlit_app.py
```

---

## 本地扩展（可选）

若你有自己的 Excel 数据，可放到 `CateMate_rawdata/`（已被 git 忽略），再运行：

```powershell
python scripts/preprocess_raw_data_sources.py
```

私有 case 配置可放在 `config/cases/`（同名文件已在 `.gitignore` 中排除）。

详见 [examples/README.md](examples/README.md)。

---

## 项目结构

```text
catemate/          业务内核（理解、规划、模块选择、PPT-ready 等）
app/               Streamlit 界面
scripts/           命令行入口
config/            模块与数据配置
examples/          可公开的虚构 case + 合成 CSV
docs/              设计文档
```

本地专用（不进公开仓库）：

```text
CateMate_rawdata/        原始 Excel
CateMate_processeddata/  预处理 CSV
outputs/                 运行产物
```

---

## 开源说明

| 可公开 | 不可公开 |
|--------|----------|
| Python 代码、配置模板 | 原始 Excel |
| `examples/` 合成数据 | `CateMate_processeddata/` |
| 设计文档（脱敏后） | `outputs/` 运行结果 |
| `.env.example` | `.env`、API Key |
| 虚构 demo case | 真实业务 case YAML |

---

## License

[MIT](LICENSE) — 个人 demo 项目，按原样提供，无生产级保证。
