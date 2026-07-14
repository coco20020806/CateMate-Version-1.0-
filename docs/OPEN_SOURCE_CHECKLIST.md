# CateMate 开源上传清单

在将仓库推送到 **公开 GitHub** 之前，按本清单逐项核对。原则：**只公开框架与虚构示例；真实源数据、运行产物、内部 case 永远留在本地。**

---

## 一、必须排除（已在 `.gitignore` 中配置）

以下路径**不应**出现在 `git ls-files` 输出中：

| 路径 | 原因 |
|------|------|
| `CateMate_rawdata/**`（除 `.gitkeep`、`README.md`） | 公司内部下载的原始 Excel |
| `CateMate_processeddata/**`（除 `.gitkeep`、`README.md`） | 由真实数据衍生的 CSV，含 GMV/订单等指标 |
| `outputs/**`（除 `.gitkeep`、`README.md`） | 流水线产物：workbook、manifest、HTML 预览 |
| `logs/` | 运行日志，可能含路径与 case 信息 |
| `runs/` | 临时运行目录 |
| `.env` | API Key 等密钥 |
| `config/cases/pet_healthcare_vn.yaml` | 真实业务 case（越南畜牧 / Pet Healthcare） |
| `config/cases/hkcb_collectible.yaml` | 真实业务 case（HKCB Collectible） |
| `config/cases/*_private.yaml` | 自定义私有 case 命名约定 |
| `config/cases/*_internal.yaml` | 自定义内部 case 命名约定 |
| `docs/example_case_vn_livestock_pet_healthcare.md` | 真实案例工作流文档 |
| `docs/example_case_hkcb_collectible_workflow.md` | 真实案例工作流文档 |
| `CateMate_新产品构想.md` | 未发布产品构想，建议不公开 |

### 当前仓库中应被忽略的实例子目录

若你本地已有这些目录，它们会被整体忽略，**不会**进公开仓：

```text
outputs/runs/                          # 含 a4_paper_market_trend_* 等真实 run
outputs/_legacy/                       # 历史孤儿产物
CateMate_rawdata/*.xlsx                # 所有源 Excel
CateMate_processeddata/source_tables/  # 全部 processed CSV
CateMate_processeddata/sph_category_tree_lookup.csv
CateMate_processeddata/processed_manifest.yaml  # 含本机绝对路径与真实文件名
```

---

## 二、可以公开（应出现在公开仓库中）

| 路径 | 说明 |
|------|------|
| `catemate/` | 核心业务代码 |
| `app/` | Streamlit 前端 |
| `scripts/` | CLI 脚本 |
| `config/data_modules/` | 数据模块配置（无业务数字） |
| `config/processed_data_sources.yaml` | 抽取规则（仅字段名与 sheet 名） |
| `config/modules/` | 模块配置 |
| `docs/`（除第一节排除项） | 设计与架构文档 |
| `examples/` | **虚构** case + 合成 CSV |
| `tests/` | 测试（若有） |
| `requirements.txt` | 依赖 |
| `.env.example` | 环境变量模板（无真实 Key） |
| `README.md` | 开源说明 |
| `README_使用说明.md` | 中文使用说明（建议后续弱化内部案例引用） |

---

## 三、上传前命令检查

在项目根目录执行：

```powershell
# 1. 查看将被跟踪的文件（确认无 rawdata / outputs / processeddata）
git init   # 若尚未初始化
git status
git add -n .   # dry-run，预览将加入暂存区的文件

# 2. 正式 add 后再次确认
git add .
git status

# 3. 列出已暂存文件，人工扫一眼
git diff --cached --name-only
```

**红线：** 若列表中出现 `.xlsx`、`.csv`（`examples/` 下除外）、`outputs/` 下任意文件、`CateMate_rawdata/` 下任意 Excel，立即 `git reset` 并检查 `.gitignore`。

```powershell
# 若误加了机密文件（尚未 push）
git reset HEAD <file>
# 若已 commit 但未 push，删除最后一次提交并修正
git reset --soft HEAD~1
```

---

## 四、文档与代码中的脱敏建议

公开前建议人工扫一遍（`.gitignore` 无法覆盖已提交的文档正文）：

1. **`docs/PROJECT_STATUS.md`、`docs/AI_CORE_INDEX.md`**  
   文中引用了 `livestock_healthcare_vn`、`pet_healthcare_vn` 等真实 run 文件名 — 可改为指向 `examples/cases/demo_stationery_sg.yaml`，或标注「内部样例，文件未随仓库发布」。

2. **`docs/ai_planning_layer_design.md` 等**  
   命令示例中的 `config/cases/pet_healthcare_vn.yaml` 可改为 `examples/cases/demo_stationery_sg.yaml`。

3. **代码注释**  
   搜索 `中农`、`HKCB`、`越南`、`VN Pet` 等内部关键词，确认无硬编码机密。

4. **`processed_manifest.yaml`**  
   真实 manifest 含 Windows 绝对路径与真实 workbook 文件名，必须整文件忽略（已配置）。

---

## 五、推荐仓库结构策略

```text
公开 GitHub 仓库
├── 代码 + 配置模板 + examples/ 合成数据
└── README 说明：真实数据放本地 CateMate_rawdata/

本地 / 公司私有（不进公开仓）
├── CateMate_rawdata/
├── CateMate_processeddata/
├── outputs/
└── config/cases/<真实 case>.yaml
```

可选：公司内网再建一个 **private fork**，同步代码的同时保留真实数据目录（仍建议数据目录用 `.gitignore`，通过网盘或内部对象存储分发 Excel）。

---

## 六、合规与 License

- [ ] 已确认公司允许将 **代码**（非数据）以开源协议发布  
- [ ] 已选择 License（如 MIT / Apache-2.0）并添加 `LICENSE` 文件  
- [ ] README 中声明：**本仓库不含任何真实业务数据**  
- [ ] 贡献指南中注明：PR 不得包含真实 CSV/Excel/case 配置  

---

## 七、首次 Push 流程（摘要）

```powershell
git init
git add .
git status                    # 最后一遍人工检查
git commit -m "Initial open-source release: framework and demo data only"
git branch -M main
git remote add origin https://github.com/<you>/CateMate.git
git push -u origin main
```

推送后，在 GitHub 网页上打开仓库，确认 **没有** `.xlsx` 和大体积 `outputs/` 文件。

---

## 八、快速自检表

| 检查项 | 通过 |
|--------|------|
| `git diff --cached --name-only` 无 `CateMate_rawdata/*.xlsx` | ☐ |
| 无 `CateMate_processeddata/*.csv`（`examples/` 除外） | ☐ |
| 无 `outputs/runs/` 或 `outputs/*.xlsx` | ☐ |
| 无 `.env`（仅有 `.env.example`） | ☐ |
| 无 `pet_healthcare_vn.yaml` / `hkcb_collectible.yaml` | ☐ |
| `examples/bootstrap_demo_data.ps1` 可在干净环境跑通 | ☐ |
| 已获公司开源许可 | ☐ |
