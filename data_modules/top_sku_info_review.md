# top_sku_info 批注稿

- **正式模块**：`data_modules/top_sku_info/`
- **录入稿**：`data_modules/top_sku_info_INTAKE.md`（fei.kong，2026-07-15）
- **写作指示**：`data_modules/AUTHORING_SPEC.md`
- **替代**：`dashboard_top_listing`、`data_modules/top_listing`

---

## 模块摘要

| 项 | 约定 |
|----|------|
| 数据源 | item 文件夹 `item_l3_category_csv` |
| 切片 | `grass_region` × `grass_month` |
| 排序 | `orders` / `gmv_usd`，竞争排名 |
| 默认产出 | `sort_by=both` + top 5/10/20 → 最多 6 张表 |
| 降级 | `both` 仅一列指标 → 自动用可用列 |

---

## 输出表

| table_id | 说明 |
|----------|------|
| `top_sku_by_orders_top{N}` | 按 orders 降序 Top N |
| `top_sku_by_gmv_top{N}` | 按 gmv_usd 降序 Top N |

无延伸 transform。

---

## 验收

```bash
pytest tests/data_modules/top_sku_info/
```

**【批注区】**
