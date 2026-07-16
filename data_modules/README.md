# CateMate 数据模块（新一代）

本目录存放**目录化、可执行**的数据模块。与旧版 `config/data_modules/*.yaml`（v2 扁平说明书）分离。

## Active 与 Draft

**Active module 是 V2 solve loop 的唯一能力边界。** 仅 `contract.yaml` 中 `status: active` 的模块会进入：

- 蓝图 LLM 的 `module_catalog`
- `plan_composer` / `catalog_checker` / `execution` 链路

| 状态 | module_id | 说明 |
|------|-----------|------|
| **active** | `monthly_market_trend` | 月度 GMV / Orders / AOV 趋势 |
| **active** | `top_sku_info` | Top SKU 排名（item 粒度） |
| draft | `daily_cncb_performance` | 保留实现；solve loop 未启用 |
| draft | `price_tier_distribution` | 同上 |
| draft | `top_shop` | 同上 |
| draft | `top_listing` | 同上 |
| draft | `keywords` | 同上 |

加载入口：[`catemate/planning/context_loader.py`](../catemate/planning/context_loader.py) 的 `load_v2_data_module_contracts(active_only=True)`（默认仅 active）。

校验：`python scripts/validate_v3_data_modules.py`

## 新建模块（推荐流程）

```text
1. 复制 MODULE_INTAKE_TEMPLATE.md → <module_id>_INTAKE.md
2. 填写各节（业务、源列名、指标、延伸表…）
3. 告诉 Agent：「按录入稿生成 <module_id>」
4. Agent 读 AUTHORING_SPEC.md → 生成目录 + 单测
5. pytest tests/data_modules/<module_id>/
6. 评审通过后将 contract.yaml 的 status 改为 active
```

| 文件 | 用途 |
|------|------|
| [**AUTHORING_SPEC.md**](AUTHORING_SPEC.md) | Agent 写作指示（生成模块时必读） |
| [**MODULE_INTAKE_TEMPLATE.md**](MODULE_INTAKE_TEMPLATE.md) | **用户填写录入稿** |
| [patterns/monthly_metric_trend.md](patterns/monthly_metric_trend.md) | 月度一指标一表 pattern 说明 |
| `<module_id>/source_schema.yaml` | 源列名 + compute/transform 规则 |
| `<module_id>/` | contract、compute.py、transforms.py |
| `<module_id>_review.md` | 人读批注 / 摘要 |

## 架构要点

- **算数写死**：`compute.py` + `transforms.py`  
- **取数在外**：`catemate/scope/` → `ScopedFrame`  
- **画图可改**：`chart_presets`，`binding: soft`

旧版批注 `docs/data_module_review_notes/` 仅对应 v2 YAML。
