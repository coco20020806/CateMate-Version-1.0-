# 数据模块写作指示文件（已迁移）

正式指示文件已迁至：

**[`data_modules/AUTHORING_SPEC.md`](../data_modules/AUTHORING_SPEC.md)**

新一代可执行模块目录：**[`data_modules/`](../data_modules/)**

核心模型：**源底表列名**（`source_schema.yaml`）+ **Python 处理规则**（`compute.py` / `transforms.py`）。

旧版 v2 扁平 YAML 仍在 `config/data_modules/`；新模块请在 `data_modules/` 下编写。
