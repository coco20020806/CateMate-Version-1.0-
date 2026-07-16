# 数据模块录入稿（请填写）

> **用法**：复制本文件为 `data_modules/<module_id>_INTAKE.md`，填写下列各节（删除「填写说明」）。  
> 填好后告诉 Agent：「按录入稿生成模块」。  
> Agent 依据：`AUTHORING_SPEC.md` + 本录入稿。

- **录入稿路径**：（例：`data_modules/price_tier_share_INTAKE.md`）
- **填表人**：
- **填写日期**：

---

## §1 模块身份

| 字段 | 填写 |
|------|------|
| `module_id`（英文 snake_case） | |
| `module_name`（中文名） | |
| `module_type`（如 market_trend / share / listing） | |
| `status` | active / draft |
| 替代的旧 v2 模块（无则留空） | |

---

## §2 业务说明

### 2.1 一句话描述

（这个模块算什么、为谁服务）

### 2.2 典型能回答的问题

- 
- 

### 2.3 明确不回答的问题

- 
- 

### 2.4 决策支持场景（可选）

- 

---

## §3 实现模式

选择一种（Agent 据此选代码骨架）：

- [ ] **`monthly_metric_trend`** — 月度、站点×月份、每次一个指标、三延伸表（参考 `monthly_market_trend`）
- [ ] **`custom`** — 与上不同，须在 §7 写清规则

### 3.1 主表粒度（`monthly_metric_trend` 默认 site×month）

| 项 | 填写（默认可不改） |
|----|-------------------|
| group_by 列名 | `grass_region`, `grass_month` |
| 时间列 | `grass_month`；或 `grass_date`（自动归月） |

---

## §4 源底表列名（Excel / CSV 表头）

### 4.1 必需列（缺则报错）

| column | 含义 | dtype |
|--------|------|-------|
| | | string / float / ... |

### 4.2 二选一必需（无则删本节）

说明：

| column | 含义 |
|--------|------|
| | |

### 4.3 软期望列（缺不阻塞，输出 metadata 标记）

| column | 含义 |
|--------|------|
| | |

---

## §5 指标定义（每次调用只选一个 `metric_id`）

每行一个指标；主表命名默认：`{metric_id}_by_site_month`（可改）。

| metric_id | 显示名 | 源列（sum/derive） | value_column | 聚合 | 派生公式（derive 时填） | null 规则 |
|-----------|--------|-------------------|--------------|------|-------------------------|-----------|
| gmv | | gmv_usd | gmv_usd | sum | | |
| orders | | orders | orders | sum | | |
| aov | | gmv_usd + orders | aov | derived | sum(gmv)/sum(orders) | orders=0→空 |

（按需增删行；非 trend 类模块可改为你的指标表）

---

## §6 延伸表（每 active 指标产出哪些）

**`monthly_metric_trend` 默认勾选（可取消某项）：**

- [ ] `{metric_id}_latest_month_by_site` — 最新月各站
- [ ] `{metric_id}_latest_month_pct_by_site` — 最新月各站占比
- [ ] `{metric_id}_mom_by_site_month` — 各站逐月环比

**自定义延伸（`custom` 或额外需求）：**

| output_table_id | 来源表 | transform 类型 | 说明 |
|-----------------|--------|----------------|------|
| | | | |

---

## §7 自定义算数规则（仅 `custom` 模式必填）

### 7.1 compute 逻辑（自然语言或伪代码）

### 7.2 transform 逻辑

---

## §8 数据源绑定（可选，给 V2 编排 / Scope）

支持的 grain（维度）：

- [ ] category
- [ ] shop
- [ ] item

| grain | 默认 table_id | 候选表 | 备注 |
|-------|---------------|--------|------|
| category | | | |
| shop | | | |
| item | | | |

> 取数、filter 由外部 Scope 完成；此处只登记「模块常与哪些底表配合」。

---

## §9 Scope / 调用约定

| 项 | 填写 |
|----|------|
| 每次调用必填参数 | 例：`metric_id` |
| Scope 由外部完成（是/否） | 默认：是 |
| 同一模块多次 Run 场景 | 例：不同 metric、不同对照 Scope |

---

## §10 Planning（模块选中提示）

### 10.1 建议命中（explicit_triggers）

- 
- 

### 10.2 建议避免（avoid_when）

- 
- 

---

## §11 画图预设（软参考，可后改）

每个 preset：`preset_id`、绑定的 `output_table_id`、建议图型（trend/bar/…）

| preset_id | metric_id | output_table_id | suggested_chart_type |
|-----------|-----------|-----------------|----------------------|
| | | | |

---

## §12 单测样例（可选，Agent 可自拟）

描述一组最小输入数据预期结果，或指定业务场景：

（例：VN 某类目 2 个月 2 个站，gmv 聚合值 …）

---

## §13 其他备注

（自由补充）

---

## Agent 生成清单（填完后由 Agent 勾选）

- [ ] `data_modules/<module_id>/source_schema.yaml`
- [ ] `data_modules/<module_id>/contract.yaml`
- [ ] `data_modules/<module_id>/compute.py`
- [ ] `data_modules/<module_id>/transforms.py`
- [ ] `data_modules/<module_id>/__init__.py`
- [ ] `data_modules/<module_id>_review.md`
- [ ] `tests/data_modules/<module_id>/test_compute.py`
- [ ] `tests/fixtures/data_modules/<module_id>/sample_scoped.csv`
- [ ] `pytest` 通过
