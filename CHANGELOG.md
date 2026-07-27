# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [1.2.0] - 2026-07-27

### Added

- Sub-L3 subset precompute, ScopeCache, and auditable filter artifacts (`subset_precompute.py`, `scope_cache.py`, `sub_l3_artifacts.py`)
- Multi-scope AnalysisPlan binding: `subset` / `parent_l3` / `comparison` / `standard` in `plan_composer.py`
- Deterministic subset-vs-parent share tables (`comparison_compute.py`, `comparison_runner.py`, `derived_tables.py`)
- `solve_loop_readiness.py` to finalize category mapping and Concept Pack before Solve Loop
- Conclusion Brief consumption layer (`catemate/conclusion_brief/` + `scripts/build_conclusion_brief_from_data_workbook.py`)
- HTML Visual Report layer (`catemate/html_report/`, `app/visual_report_editor.py` + `scripts/build_html_report_from_data_workbook.py`)
- Tests and scripts for comparison, subset precompute, readiness, Brief, and HTML report

### Changed

- Solve Loop registers subset-scope artifacts on the pipeline manifest and reuses cached item frames
- Data Workbook / Streamlit dashboard expose Brief and Visual Report as optional post-workbook steps
- Documentation: README, V2 design overview, AI_CORE_INDEX, and PROJECT_LAYOUT updated for v1.2.0 architecture and LLM boundaries

### Docs

- Core Data Agent design philosophy (flexibility vs correctness via modular Scope × Module) placed at the front of README and V2 overview

## [1.1.0] - 2026-07-16

### Added

- Sub-L3 detection and `RelatedConceptPack` generation in the understanding layer (`sub_l3_detector.py`, `concept_pack_generator.py`)
- `if_related` item-title relevance filtering in `catemate/scope/related.py`, wired through `scope/executor.py`
- Global output grain policy (`config/output_grain_policy.yaml`, `catemate/core/output_policy.py`) — monthly output by default; daily modules forbidden in solve loop
- `catemate/orchestration/module_registry.py` and `scripts/validate_v3_data_modules.py` to enforce the active-module boundary
- Tests for related filtering, if_related e2e pipeline, and output grain policy

### Changed

- `data_modules/`: only `monthly_market_trend` and `top_sku_info` are `status: active`; the other five modules are `status: draft` (code + tests retained, excluded from solve loop)
- Orchestration chain (blueprint, plan composer, catalog checker, execution) loads **active modules only** via `load_v2_data_module_contracts(active_only=True)`
- `config/analysis_playbook.md` rewritten for the 2-module capability boundary with separate L3 vs L3-subset analysis paths
- Category confirmation gate triggers concept pack generation when Sub-L3 qualifiers are detected

### Fixed

- Documentation drift: README and design docs no longer present draft modules as executable solve-loop capabilities

## [1.0.0] - 2026-07-14

### Added

- V2 Solve Loop pipeline (`catemate/orchestration/`, `catemate/scope/`, `catemate/execution/`)
- Seven executable `data_modules/` with `compute.py` and pytest coverage
- `rawdata_catalog.yaml`, `analysis_playbook.md`, Data Workbook assembly
- Streamlit dashboard defaulting to `v2_solve_loop`
- Synthetic demo data under `examples/`
- GitHub README with architecture diagrams and project layout docs
