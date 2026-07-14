# CateMate_processeddata（本地专用，勿提交 Git）

此目录是 AI 优先读取的 **processed CSV 数据层**，由 `CateMate_rawdata` 预处理生成，包含真实业务指标，已被 `.gitignore` 排除。

## 生成方式

```powershell
python scripts/preprocess_raw_data_sources.py
```

## 无真实源数据时

运行示例引导脚本，将 `examples/processed_data/` 中的合成数据复制到本目录：

```powershell
.\examples\bootstrap_demo_data.ps1
```
