# Requirement Understanding Layer 设计（v1）

更新时间：2026-07-09

## 为什么需要这一层

在 module selection / AI planning 之前，用户自然语言需求往往不完整、口径含糊、类目尚未定位。  
若直接进入 planning，容易过早绑定 data module 或生成过重 workbook。

Requirement Understanding Layer 专门负责：

```text
自然语言需求
→ RequirementUnderstandingSpec
→ 澄清 gate（clarifying_questions 逐条回答/跳过）
→ ready_for_module_selection
→ 后续 module selection / case config / planning
```

本层**不**选择 data module，**不**生成 `RequirementPlanningSpec`，**不**生成 workbook。

## 核心原则：默认推进，谨慎追问，澄清 gate 必经

1. 需求大体与类目/市场/商品/卖家/关键词/价格段相关 → 积极理解并揣测。
2. 像成熟分析师一样补全 `analysis_intents`、站点、类目方向。
3. `clarifying_questions` 少而关键（通常 0–3 条）；**只要列出，用户必须逐条「回答」或「跳过」后才能进入 module selection**（manifest 状态 `awaiting_clarification` → `clarification_completed`）。
4. 细节若可从原文推断，优先写入 `assumptions`，不要生成琐碎澄清问题。
5. 只有两类情况在 readiness 层硬阻塞（`exit_code=1`）：
   - `out_of_scope`：明显无关（写邮件、写代码、闲聊）
   - `needs_minimum_context`：相关但完全无分析对象线索

## RequirementUnderstandingSpec 核心字段

| 字段 | 含义 |
|------|------|
| `status` | `ready_for_module_selection` / `needs_minimum_context` / `out_of_scope` |
| `original_request` | 用户原始需求 |
| `conversation_summary` | 系统对需求的理解摘要 |
| `understood` | 结构化理解：站点、类目、分析意图、交付、口径 |
| `assumptions` | 主动假设（可需用户确认） |
| `uncertainties` | 不确定点（默认不阻塞） |
| `clarifying_questions` | 澄清问题（列出则必经澄清 gate） |
| `user_answers` | 用户对澄清问题的回答或跳过记录 |
| `readiness` | 是否可进入 module selection |

### `understood.analysis_intents`

用于表达分析方向，**不是** data module id：

- `market_trend` — 大盘/月度趋势
- `daily_performance` — 日度/CNCB/渗透
- `price_tier` — 价格段结构
- `top_listing` — Top Listing 样本
- `top_shop` — Top Shop 榜单
- `keywords` — 关键词热词
- `category_mapping` — 类目定位/映射
- `site_comparison` — 站点对比
- `price_reference` — 价格水平/均价参考
- `unknown`

## blocking vs non-blocking

| 类型 | `blocks_module_selection` | 示例 |
|------|---------------------------|------|
| non-blocking | `false`（默认） | 平均价格口径、时间范围、是否要关键词/价格段 |
| blocking | `true`（极少） | 用户说「先不要继续」「等我确认」 |
| readiness 兜底 | 确定性规则 | 即使模型误标 blocking，readiness 也会降级 |

实现：`catemate/understanding/readiness.py` → `normalize_understanding_readiness()`

## 与其他层的关系

```text
RequirementUnderstandingSpec     ← 本层（需求理解）
        ↓
CategoryAnalysisCaseConfig     ← case config 层（结构化需求草稿）
        ↓
RequirementPlanningSpec        ← planning 层（选 module、提议图表）
        ↓
确认 workbook → PPT-ready → HTML preview
```

v1 本层已接入 `module_selection` 主流水线；存在 `clarifying_questions` 时会在澄清 gate 暂停。

## 代码入口

| 组件 | 路径 |
|------|------|
| Schema | `catemate/understanding/schemas.py` |
| Prompt | `catemate/understanding/prompt_builder.py` |
| Generator | `catemate/understanding/generator.py` |
| Clarification gate | `catemate/understanding/clarification.py` |
| Updater | `catemate/understanding/updater.py` |
| Readiness | `catemate/understanding/readiness.py` |
| Pipeline 续跑 | `catemate/pipeline/runner.py` → `run_pipeline_continue_from_manifest` |
| Streamlit 澄清 UI | `app/clarification_editor.py` |
| CLI 生成 | `scripts/run_requirement_understanding.py` |
| CLI 更新 | `scripts/update_requirement_understanding.py` |
| 规则测试 | `scripts/validate_understanding_readiness.py` |
| 澄清 gate 测试 | `scripts/validate_clarification_gate.py` |

## 示例：HKCB Collectible

**输入（节选）**：收集 H&C / Hobby & Collectibles 类目市场资讯；L1 总览、Collectible L2 站点占比、价格段、关键词、Action Figures / Movies & Anime…

**期望理解**：

- `status`: `ready_for_module_selection`
- `target_category_text` / `inferred_category` 含 Hobby / Collectible / Action Figures
- `analysis_intents`: `market_trend`, `price_tier`, `keywords`, `category_mapping`, `site_comparison`
- `assumptions` 含类目映射/口径待确认
- 不因细节不清阻塞

## 示例：VN Pet Healthcare

**输入**：

```text
中农类目需求…越南畜牧相关的类目数据，大盘类目趋势，平均价格、top listing等。
关键词可参考：催肥增重、增蛋、催奶…
最后实际定位出来是在pet healthcare
```

**期望理解**：

- `status`: `ready_for_module_selection`
- `target_sites`: `["VN"]`
- `inferred_category`: Pet Healthcare
- `analysis_intents`: `market_trend`, `top_listing`, `price_reference`, `category_mapping`
- 平均价格口径 → `assumptions` 或 non-blocking question

**用户补充**：

```text
平均价格先用 Top Listing 样本价格，关键词和价格段也都先带上。
```

**期望更新**：

- 仍 `ready_for_module_selection`
- `metric_definitions` 或 `assumptions` 体现 Top Listing 样本价
- `analysis_intents` 含 `keywords`, `price_tier`
- `user_answers` 有记录

## 验证

```bash
python -m py_compile catemate/understanding/*.py scripts/run_requirement_understanding.py scripts/update_requirement_understanding.py
python scripts/validate_understanding_readiness.py
```

AI 实跑（需配置 `CATEMATE_AI_PROVIDER`）：

```bash
python scripts/run_requirement_understanding.py --request-file path/to/request.txt
python scripts/update_requirement_understanding.py --understanding-spec outputs/xxx.json --answer-text "..."
```
