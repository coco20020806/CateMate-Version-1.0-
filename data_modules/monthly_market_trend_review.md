# monthly_market_trend 批注稿

- **正式模块**：`data_modules/monthly_market_trend/`
- **写作指示**：`data_modules/AUTHORING_SPEC.md`
- **最后同步**：2026-07-15

> 结构对齐模块内文件；在 **【批注区】** 写意见，Agent 同步到 YAML / Python。

---

## 待修改清单

| 状态 | 修改摘要 |
|------|----------|
| 已落地 | 一指标一主表；每指标 3 张延伸表（2026-07-15 批注） |

---

## `source_schema.yaml`

### `source_columns`

| 类别 | 约定 |
|------|------|
| 必需 | `grass_region` |
| 时间二选一 | `grass_month` / `grass_date`（仅 date 时归月） |
| 软期望 | L1/L2/L3 类目列；缺则不阻塞，metadata 标记 |
| 指标源列 | 由当次 `metric_id` 决定：gmv→`gmv_usd`；orders→`orders`；aov→`gmv_usd`+`orders` |

**【批注区】**

---

### `compute_rules`

- 每次调用 `metric_id` 取 **gmv | orders | aov 之一**
- 主表形态：**一指标一表**，grain = `grass_region × grass_month`
  - `gmv_by_site_month` → 列 `gmv_usd`
  - `orders_by_site_month` → 列 `orders`
  - `aov_by_site_month` → 列 `aov`

**【批注区】**

---

### `transform_rules`

对**当次 active 指标**产出 3 张延伸表：

| 后缀 | 含义 |
|------|------|
| `_latest_month_by_site` | 最新月各站 |
| `_latest_month_pct_by_site` | 最新月各站占比 |
| `_mom_by_site_month` | 各站逐月环比（site×month） |

**【批注区】**

---

## `contract.yaml`

- `compute_params.metric_id`：必填
- `outputs` / `chart_presets` 登记三指标全部表名（每次运行只产出其中一组）

**【批注区】**

---

## `compute.py` / `transforms.py`

与 `source_schema.yaml` 同步；不在此重复。

**【批注区】**

---

## 验收

```bash
pytest tests/data_modules/monthly_market_trend/
```

**【批注区】**
