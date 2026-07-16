# CateMate 数据模块（新一代）

本目录存放**目录化、可执行**的数据模块。与旧版 `config/data_modules/*.yaml`（v2 扁平说明书）分离。

## 新建模块（推荐流程）

```text
1. 复制 MODULE_INTAKE_TEMPLATE.md → <module_id>_INTAKE.md
2. 填写各节（业务、源列名、指标、延伸表…）
3. 告诉 Agent：「按录入稿生成 <module_id>」
4. Agent 读 AUTHORING_SPEC.md → 生成目录 + 单测
5. pytest tests/data_modules/<module_id>/
```

| 文件 | 用途 |
|------|------|
| [**AUTHORING_SPEC.md**](AUTHORING_SPEC.md) | Agent 写作指示（生成模块时必读） |
| [**MODULE_INTAKE_TEMPLATE.md**](MODULE_INTAKE_TEMPLATE.md) | **用户填写录入稿** |
| [patterns/monthly_metric_trend.md](patterns/monthly_metric_trend.md) | 月度一指标一表 pattern 说明 |
| `<module_id>/source_schema.yaml` | 源列名 + compute/transform 规则 |
| `<module_id>/` | contract、compute.py、transforms.py |
| `<module_id>_review.md` | 人读批注 / 摘要 |

## 当前模块

| module_id | pattern | 批注/录入 |
|-----------|---------|-----------|
| `monthly_market_trend` | `monthly_metric_trend` | `monthly_market_trend_review.md` |
| `top_sku_info` | `custom`（Top N SKU） | `top_sku_info_INTAKE.md` / `top_sku_info_review.md` |

## 架构要点

- **算数写死**：`compute.py` + `transforms.py`  
- **取数在外**：`catemate/scope/` → `ScopedFrame`  
- **画图可改**：`chart_presets`，`binding: soft`

旧版批注 `docs/data_module_review_notes/` 仅对应 v2 YAML。
