# Cursor Prompt: Streamlit Confirmation UI

请在当前 CateMate 项目中实现一个 Streamlit 页面，用于“数据需求/确认 workbook”的人工确认闭环。不要实现 PPT-ready workbook 生成器，这部分暂时搁置。

## 项目背景

CateMate 是面向 Category Analysis 的本地分析助手。当前 MVP 的流程是：

1. 生成数据需求/确认 workbook。
2. 用户检查 workbook 中的 `确认记录` sheet。
3. 用户把每个确认项标记为 `已确认` 或 `不需要`，或在补充数据后标记为 `已补充`。
4. Agent 复检补充数据，复检通过后才能转为 `已确认`。
5. 只有所有确认项都是 `已确认` 或 `不需要`，后续才允许生成 PPT-ready workbook。

## 现有代码

请优先复用现有模块，不要在 Streamlit 页面里重复写业务规则。

相关文件：

- `app/streamlit_app.py`
- `scripts/run_category_requirement_demo.py`
- `scripts/check_confirmation_gate.py`
- `catemate/core/confirmation_gate.py`
- `catemate/core/confirmation_reader.py`
- `catemate/modules/category_analysis_data_requirement.py`
- `outputs/category_analysis_data_requirement_*.xlsx`

确认状态规则：

- 允许进入后续生成的状态：`已确认`、`不需要`
- 阻塞状态：`待确认`、`待补充`、`已补充`、`阻塞`
- 用户补充数据后只能先标记为 `已补充`
- Agent 复检通过后才可以转为 `已确认`

## 本次开发目标

实现 Streamlit 页面中的确认交互，页面应支持：

1. 选择或自动加载 `outputs/` 中最新的 `category_analysis_data_requirement_*.xlsx`。
2. 读取 workbook 的 `确认记录` sheet。
3. 展示确认项列表，至少包含：
   - 确认项
   - 建议值
   - 当前状态
   - 原因
   - 是否阻止 PPT-ready 生成
4. 对每一行提供状态选择控件，可选状态：
   - `待确认`
   - `待补充`
   - `已补充`
   - `已确认`
   - `不需要`
   - `阻塞`
5. 用户修改状态后，可以保存回原 workbook，或者另存为一份带时间戳的新 workbook。优先建议另存，避免覆盖原始确认记录。
6. 点击“检查确认状态”按钮后，调用现有 `evaluate_confirmation_gate` 逻辑，展示：
   - 是否可以进入 PPT-ready workbook
   - 阻塞项数量
   - 阻塞项清单
   - 给用户的下一步建议
7. 如果所有状态都是 `已确认` 或 `不需要`，页面只显示“可以进入 PPT-ready workbook 生成步骤”，不要实际生成 PPT-ready workbook。

## UI 要求

- 第一版用户是产品经理/策略分析师，不要暴露过多技术细节。
- 页面应简洁，优先完成工作流，不需要复杂视觉设计。
- 不要做营销式首页。
- 主页面直接进入确认工作台。
- 可以使用 `st.data_editor` 做可编辑表格。
- 状态字段建议使用下拉选择。
- 对阻塞项使用清晰提示，例如 `st.warning`。
- 对已全部通过使用 `st.success`。

## 代码要求

- 保持代码简洁，方便后续继续扩展。
- 不要把确认规则写死在页面中，尽量复用 `catemate.core.confirmation_gate`。
- 如需新增函数，优先放在合适的业务模块里，不要全部塞进 `streamlit_app.py`。
- 不要实现 DeepSeek、Pydantic AI、LlamaIndex workflow。
- 不要实现 PPT-ready workbook 生成。
- 不要读取或修改 `CateMate_rawdata` 中的源数据文件。

## 建议实现方式

1. 在 `catemate/core/confirmation_reader.py` 中增加一个可返回表格行的函数，或在 Streamlit 中把 `read_confirmation_items` 结果转为 DataFrame。
2. 新增一个保存确认记录的函数，例如：
   - 输入：原 workbook 路径、更新后的确认记录 DataFrame、输出路径
   - 行为：复制 workbook，更新 `确认记录` sheet 中对应行的状态和阻止标记
   - 输出：新 workbook 路径
3. 在 `app/streamlit_app.py` 中实现页面：
   - 加载 workbook
   - 展示 editable confirmation table
   - 保存确认结果
   - 运行 gate check

## 完成标准

完成后应能做到：

1. 运行 `streamlit run app/streamlit_app.py`。
2. 页面自动找到最新确认 workbook。
3. 用户可以编辑确认状态。
4. 用户可以保存为新的确认 workbook。
5. 页面可以判断是否通过 confirmation gate。
6. 页面不会生成 PPT-ready workbook，只提示是否可以进入下一步。
