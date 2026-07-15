# CateMate 数据模块（新一代）

本目录存放**目录化、可执行**的数据模块。与旧版 `config/data_modules/*.yaml`（v2 扁平说明书）分离；后续模块均在此重写。

## 目录说明

| 路径 | 用途 |
|------|------|
| `AUTHORING_SPEC.md` | **写作指示** — 源列名 + 处理规则模型 |
| `<module_id>/source_schema.yaml` | **源底表列名** + compute/transform 规则 |
| `<module_id>/` | contract、compute.py、transforms.py 等 |
| `<module_id>_review.md` | 人读批注稿 |

## 当前模块

| module_id | 状态 | 批注稿 |
|-----------|------|--------|
| `monthly_market_trend` | 首版已写 | `monthly_market_trend_review.md` |

## 工作流

```text
1. 在 <module_id>_review.md 用自然语言批注
2. Agent 读 AUTHORING_SPEC.md + 批注稿 → 更新 <module_id>/ 下正式资产
3. 跑单测：pytest tests/data_modules/<module_id>/
```

旧版批注目录 `docs/data_module_review_notes/` 仅对应 v2 YAML；新模块批注放在本目录同级 `*_review.md`。
