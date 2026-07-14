# CateMate_rawdata（本地专用，勿提交 Git）

此目录用于存放**公司内部下载的原始 Excel**，属于机密数据，已被 `.gitignore` 排除，不会进入公开仓库。

## 本地准备

1. 将业务方提供的 SPH / 品类看板等 Excel 放入本目录。
2. 文件名需与 `config/processed_data_sources.yaml` 中的 `source_workbook_keywords` 能匹配上。
3. 运行预处理脚本生成 processed 层：

```powershell
python scripts/preprocess_raw_data_sources.py `
  --raw-data-dir CateMate_rawdata `
  --processed-data-dir CateMate_processeddata
```

## 仅想体验框架、没有真实数据？

使用仓库自带的合成示例数据：

```powershell
.\examples\bootstrap_demo_data.ps1
```

详见 [examples/README.md](../examples/README.md)。
