# Examples — 开源演示数据

`examples/` 目录中的内容**可以安全提交到公开 GitHub**，全部为虚构业务场景与合成数字。

## 目录结构

```text
examples/
  cases/                    虚构 case 配置（YAML）
  processed_data/           合成 processed CSV + manifest
  raw_data/                 说明：真实 Excel 放本地 CateMate_rawdata/
  bootstrap_demo_data.ps1   一键复制合成数据到本地运行目录
```

## 快速体验（无需公司源数据）

```powershell
# 1. 安装依赖
pip install -r requirements.txt

# 2. 复制合成 processed 数据
.\examples\bootstrap_demo_data.ps1

# 3. 用虚构 case 生成需求 workbook
python scripts/run_category_requirement_case.py examples/cases/demo_stationery_sg.yaml

# 4. （可选）启动 Streamlit
streamlit run app/streamlit_app.py
```

## 与本地机密数据的关系

| 路径 | 是否进 Git | 说明 |
|------|-----------|------|
| `examples/` | ✅ 是 | 虚构示例，可公开 |
| `CateMate_rawdata/` | ❌ 否 | 公司 Excel |
| `CateMate_processeddata/` | ❌ 否 | 由真实数据预处理得到 |
| `outputs/` | ❌ 否 | 运行产物，可能含真实 case 信息 |
| `config/cases/pet_healthcare_vn.yaml` 等 | ❌ 否 | 真实业务 case，已在 .gitignore |

上传 GitHub 前请阅读 [docs/OPEN_SOURCE_CHECKLIST.md](../docs/OPEN_SOURCE_CHECKLIST.md)。
