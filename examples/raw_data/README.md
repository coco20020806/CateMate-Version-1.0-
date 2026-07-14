# 示例原始数据（虚构）

本目录**不**包含真实 Excel 文件。开源仓库只提供说明；真实业务 Excel 请放在项目根目录的 `CateMate_rawdata/`（已被 git 忽略）。

若你只有合成 processed 数据、没有原始 Excel，可直接运行：

```powershell
.\examples\bootstrap_demo_data.ps1
```

然后用 `examples/cases/demo_stationery_sg.yaml` 跑通流水线。

若你有真实 Excel，放入 `CateMate_rawdata/` 后执行：

```powershell
python scripts/preprocess_raw_data_sources.py
```
