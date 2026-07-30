# CateMate 分析工作台

A guided analytics workbench for category analysts — turning natural-language analysis requests into auditable Data Workbooks, visual reports, and shareable deliverables via a step-gated pipeline.

## Run & Operate

- `pnpm --filter @workspace/catemate run dev` — frontend (port varies, BASE_PATH `/`)
- `pnpm --filter @workspace/api-server run dev` — API server (port 8080, path `/api`)
- `pnpm run typecheck` — full typecheck across all packages
- `pnpm run build` — typecheck + build all packages
- `pnpm --filter @workspace/api-spec run codegen` — regenerate API hooks and Zod schemas from the OpenAPI spec
- `pnpm --filter @workspace/db run push` — push DB schema changes (dev only)
- Required env: `DATABASE_URL` — Postgres connection string, `SESSION_SECRET`

## Stack

- pnpm workspaces, Node.js 24, TypeScript 5.9
- Frontend: React 18 + Vite 7, TailwindCSS, shadcn/ui, Wouter, TanStack Query, Framer Motion
- API: Express 5 (artifacts/api-server)
- DB: PostgreSQL + Drizzle ORM
- Validation: Zod (zod/v4), drizzle-zod
- API codegen: Orval (from OpenAPI spec in lib/api-spec/openapi.yaml)
- Build: esbuild (CJS bundle)

## Where things live

- `lib/api-spec/openapi.yaml` — single source of truth for all API contracts
- `lib/db/src/schema/` — DB schema: runs.ts, settings.ts, datasources.ts
- `lib/api-client-react/src/generated/` — generated React Query hooks
- `lib/api-zod/src/generated/` — generated Zod validation schemas
- `artifacts/catemate/src/pages/` — frontend pages (dashboard, runs, datasources, settings, modules)
- `artifacts/catemate/src/components/` — shared components (StatusBadge, layout/Shell)
- `artifacts/api-server/src/routes/` — API routes: runs.ts, settings.ts, datasources.ts, modules.ts

## Architecture decisions

- **OpenAPI-first**: All endpoints defined in `lib/api-spec/openapi.yaml` before any code. Codegen produces hooks + Zod schemas.
- **Gate-driven UI**: Frontend respects `RunStatus` enum strictly — each status maps to exactly one next action. No gate-skipping.
- **Mock-first backend**: Routes simulate the full pipeline flow (solve loop, blueprint, gaps, deliverables) with realistic mock data until the real Python agent is integrated.
- **DB stores all run state as JSONB**: understanding_json, blueprint_json, gaps_json, etc. are JSONB columns to flexibly store agent-produced nested objects without schema churn.
- **Gaps as first-class UI citizen**: Prominently surfaced after workbook generation with severity badges before the download button.

## Product

- **Dashboard**: Run stats by status, recent active runs, New Analysis CTA
- **Run Wizard** (`/runs/:runId`): Step-gated (A0 category confirm → clarification → solve → workbook), persistent header with step progress bar
- **Deliverables Hub** (`/runs/:runId/deliver`): Workbook, Brief, Visual Spec (Gate C edit), HTML Report, Print Report
- **Data Sources** (`/datasources`): Catalog registry with availability status, missing-source alerts, ingest form
- **Settings** (`/settings`): AI provider, model, pipeline defaults
- **Module Catalog** (`/modules`): Active/draft module cards with metrics and output tables

## User preferences

_Populate as you build — explicit user instructions worth remembering across sessions._

## Gotchas

- OpenAPI `integer` types cause `zod.int()` errors with the workspace Zod version — use `number` type instead.
- Orval body schema names must be entity-shaped (NoteInput not CreateNoteBody) to avoid TS2308 collisions.
- `pnpm run dev` at workspace root has no script — always target specific packages with `--filter`.
- Do not hardcode ports; services read `PORT` env from workflow config.

## Pointers

- See the `pnpm-workspace` skill for workspace structure, TypeScript setup, and package details
- See `lib/api-spec/openapi.yaml` for the full API contract
