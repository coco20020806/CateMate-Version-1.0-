# Case 配置说明

## 公开仓库

请使用 **`examples/cases/`** 下的虚构示例 case，例如：

```powershell
python scripts/run_category_requirement_case.py examples/cases/demo_stationery_sg.yaml
```

## 本地真实 case

可将公司内部 case 的 YAML 放在本目录，例如：

- `pet_healthcare_vn.yaml`
- `hkcb_collectible.yaml`

这些文件已在 `.gitignore` 中排除，**不会**被 `git add` 进公开仓库。

命名约定：私有 case 可使用 `*_private.yaml` 或 `*_internal.yaml` 后缀，同样会被忽略。
