# CateMate 自然语言 → Case Config 草稿设计（v1）

更新时间：2026-07-08

## 目标

新增一个轻量模块，把用户自然语言需求转换为 `CategoryAnalysisCaseConfig` 草稿，并保存为 YAML，供后续 planning/workbook 流程继续使用。

链路：

```text
用户自然语言需求
  ↓
AI 生成 CategoryAnalysisCaseConfig JSON
  ↓
Pydantic 校验
  ↓
保存为 YAML
  ↓
（可选）一键串联：planning spec → 数据需求/确认 workbook
  或继续用独立脚本分步执行
```

## 为什么先生成草稿

1. 用户需求通常不完整，先沉淀为可审阅配置更安全。
2. 避免让 AI 直接写 Excel，保持“AI 负责结构化，Python 负责确定性执行”。
3. 便于产品经理先复核类目、站点、关键词和确认事项，再进入规划与数据生成。

## 输入与输出

### 输入

- 自然语言需求文本（`--request-text` 或 `--request-file`）
- 参考 case config（`config/cases/*.yaml` 摘要）
- 参考数据模块（`config/data_modules/*.yaml` 摘要）

### 输出

- 经过 `CategoryAnalysisCaseConfig.model_validate(...)` 校验通过的 YAML
- 默认路径：
  - `outputs/generated_case_config_<case_id>_<timestamp>.yaml`

若使用一键链路脚本，还会额外产出同 timestamp 的：

- `outputs/planning_spec_<case_id>_<timestamp>.json`
- `outputs/category_analysis_data_requirement_from_planning_<case_id>_<timestamp>.xlsx`

## 默认 AI Provider

遵循现有 `AISettings.from_env()`：

- 默认 provider：`openai_compatible`
- 默认 base_url：`http://127.0.0.1:8080/v1`
- 默认 model：`gpt-5.5`
- DeepSeek 可通过环境变量切换

## 代码入口

- `catemate/case_generation/prompt_builder.py`
- `catemate/case_generation/generator.py`
- `catemate/case_generation/context_loader.py`（request / reference helpers）
- `scripts/run_natural_language_to_case_config.py`（只生成 case config 草稿）
- `scripts/run_natural_language_requirement_pipeline.py`（一键串联到确认 workbook）

独立脚本仍然可用；一键脚本只是串联器，每一步产物都会单独保存，方便产品经理复核。

## 使用示例

只生成 case config：

```bash
python scripts/run_natural_language_to_case_config.py \
  --request-text "中农类目需求🙏 有空帮忙看就可以~~ 越南畜牧相关的类目数据，大盘类目趋势，平均价格、top listing等。关键词可参考：催肥增重、增蛋、催奶、鱼用益生菌、驱虫、呼吸道问题、解暑等畜牧品类。先定位所在类目（和之前一样），最后实际定位出来是在pet healthcare"
```

自然语言一键到确认 workbook：

```bash
python scripts/run_natural_language_requirement_pipeline.py \
  --request-text "……同上……"
```

可用 `--stop-after-case-config` / `--stop-after-planning` 提前停止。

## 当前限制

- 草稿 / 规划不做自动确认；确认仍走 Streamlit + confirmation gate。
- 一键脚本不替代三个独立脚本。
- 不让 AI 直接写 Excel / PPT-ready workbook。
- 不读取大型 raw Excel。
- 不做复杂自动修复（若 schema 校验失败会直接报错）。
