import { Router, type IRouter } from "express";
import {
  CreateRunBody,
  GetRunParams,
  GetUnderstandingParams,
  GetBlueprintParams,
  GetGapsParams,
  ConfirmCategoriesBody,
  ConfirmCategoriesParams,
  SubmitClarificationBody,
  SubmitClarificationParams,
  TriggerSolveParams,
  GetBriefParams,
  GenerateBriefParams,
  GetVisualSpecParams,
  GenerateVisualSpecParams,
  GenerateHtmlReportParams,
  GeneratePrintReportParams,
  GetDeliverablesParams,
  ConfirmVisualSpecBody,
  ConfirmVisualSpecParams,
  ListRunsQueryParams,
} from "@workspace/api-zod";

const PYTHON_API = process.env["PYTHON_API_URL"] || "http://localhost:8100";

async function proxyGet(path: string) {
  const resp = await fetch(`${PYTHON_API}${path}`);
  const data = await resp.json();
  return { status: resp.status, data };
}

async function proxyPost(path: string, body?: unknown) {
  const resp = await fetch(`${PYTHON_API}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });
  const data = await resp.json();
  return { status: resp.status, data };
}

async function proxyPut(path: string, body: unknown) {
  const resp = await fetch(`${PYTHON_API}${path}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  const data = await resp.json();
  return { status: resp.status, data };
}

const router: IRouter = Router();

// GET /runs
router.get("/runs", async (req, res): Promise<void> => {
  const params = ListRunsQueryParams.safeParse(req.query);
  const qs = new URLSearchParams();
  if (params.success && params.data.status) qs.set("status", params.data.status);
  if (params.success && params.data.q) qs.set("q", params.data.q);
  const qsStr = qs.toString();
  const { status, data } = await proxyGet(`/api/runs${qsStr ? `?${qsStr}` : ""}`);
  res.status(status).json(data);
});

// POST /runs
router.post("/runs", async (req, res): Promise<void> => {
  const parsed = CreateRunBody.safeParse(req.body);
  if (!parsed.success) {
    res.status(400).json({ error: parsed.error.message });
    return;
  }
  const { status, data } = await proxyPost("/api/runs", parsed.data);
  res.status(status).json(data);
});

// GET /runs/stats/summary
router.get("/runs/stats/summary", async (_req, res): Promise<void> => {
  const { status, data } = await proxyGet("/api/runs/stats/summary");
  res.status(status).json(data);
});

// GET /runs/:runId
router.get("/runs/:runId", async (req, res): Promise<void> => {
  const params = GetRunParams.safeParse(req.params);
  if (!params.success) { res.status(400).json({ error: params.error.message }); return; }
  const { status, data } = await proxyGet(`/api/runs/${params.data.runId}`);
  res.status(status).json(data);
});

// GET /runs/:runId/understanding
router.get("/runs/:runId/understanding", async (req, res): Promise<void> => {
  const params = GetUnderstandingParams.safeParse(req.params);
  if (!params.success) { res.status(400).json({ error: params.error.message }); return; }
  const { status, data } = await proxyGet(`/api/runs/${params.data.runId}/understanding`);
  res.status(status).json(data);
});

// GET /runs/:runId/blueprint
router.get("/runs/:runId/blueprint", async (req, res): Promise<void> => {
  const params = GetBlueprintParams.safeParse(req.params);
  if (!params.success) { res.status(400).json({ error: params.error.message }); return; }
  const { status, data } = await proxyGet(`/api/runs/${params.data.runId}/blueprint`);
  res.status(status).json(data);
});

// GET /runs/:runId/gaps
router.get("/runs/:runId/gaps", async (req, res): Promise<void> => {
  const params = GetGapsParams.safeParse(req.params);
  if (!params.success) { res.status(400).json({ error: params.error.message }); return; }
  const { status, data } = await proxyGet(`/api/runs/${params.data.runId}/gaps`);
  res.status(status).json(data);
});

// POST /runs/:runId/gates/category
router.post("/runs/:runId/gates/category", async (req, res): Promise<void> => {
  const params = ConfirmCategoriesParams.safeParse(req.params);
  const body = ConfirmCategoriesBody.safeParse(req.body);
  if (!params.success || !body.success) { res.status(400).json({ error: "Invalid request" }); return; }
  const { status, data } = await proxyPost(`/api/runs/${params.data.runId}/gates/category`, body.data);
  res.status(status).json(data);
});

// POST /runs/:runId/gates/clarification
router.post("/runs/:runId/gates/clarification", async (req, res): Promise<void> => {
  const params = SubmitClarificationParams.safeParse(req.params);
  const body = SubmitClarificationBody.safeParse(req.body);
  if (!params.success || !body.success) { res.status(400).json({ error: "Invalid request" }); return; }
  const { status, data } = await proxyPost(`/api/runs/${params.data.runId}/gates/clarification`, body.data);
  res.status(status).json(data);
});

// POST /runs/:runId/gates/visual-spec
router.post("/runs/:runId/gates/visual-spec", async (req, res): Promise<void> => {
  const params = ConfirmVisualSpecParams.safeParse(req.params);
  const body = ConfirmVisualSpecBody.safeParse(req.body);
  if (!params.success || !body.success) { res.status(400).json({ error: "Invalid request" }); return; }
  const { status, data } = await proxyPost(`/api/runs/${params.data.runId}/gates/visual-spec`, body.data);
  res.status(status).json(data);
});

// POST /runs/:runId/solve
router.post("/runs/:runId/solve", async (req, res): Promise<void> => {
  const params = TriggerSolveParams.safeParse(req.params);
  if (!params.success) { res.status(400).json({ error: "Invalid request" }); return; }
  const { status, data } = await proxyPost(`/api/runs/${params.data.runId}/solve`);
  res.status(status).json(data);
});

// GET /runs/:runId/brief
router.get("/runs/:runId/brief", async (req, res): Promise<void> => {
  const params = GetBriefParams.safeParse(req.params);
  if (!params.success) { res.status(400).json({ error: "Invalid request" }); return; }
  const { status, data } = await proxyGet(`/api/runs/${params.data.runId}/brief`);
  res.status(status).json(data);
});

// POST /runs/:runId/brief
router.post("/runs/:runId/brief", async (req, res): Promise<void> => {
  const params = GenerateBriefParams.safeParse(req.params);
  if (!params.success) { res.status(400).json({ error: "Invalid request" }); return; }
  const { status, data } = await proxyPost(`/api/runs/${params.data.runId}/brief`);
  res.status(status).json(data);
});

// GET /runs/:runId/visual-spec
router.get("/runs/:runId/visual-spec", async (req, res): Promise<void> => {
  const params = GetVisualSpecParams.safeParse(req.params);
  if (!params.success) { res.status(400).json({ error: "Invalid request" }); return; }
  const { status, data } = await proxyGet(`/api/runs/${params.data.runId}/visual-spec`);
  res.status(status).json(data);
});

// POST /runs/:runId/visual-spec
router.post("/runs/:runId/visual-spec", async (req, res): Promise<void> => {
  const params = GenerateVisualSpecParams.safeParse(req.params);
  if (!params.success) { res.status(400).json({ error: "Invalid request" }); return; }
  const { status, data } = await proxyPost(`/api/runs/${params.data.runId}/visual-spec`);
  res.status(status).json(data);
});

// POST /runs/:runId/html-report
router.post("/runs/:runId/html-report", async (req, res): Promise<void> => {
  const params = GenerateHtmlReportParams.safeParse(req.params);
  if (!params.success) { res.status(400).json({ error: "Invalid request" }); return; }
  const { status, data } = await proxyPost(`/api/runs/${params.data.runId}/html-report`);
  res.status(status).json(data);
});

// POST /runs/:runId/print-report
router.post("/runs/:runId/print-report", async (req, res): Promise<void> => {
  const params = GeneratePrintReportParams.safeParse(req.params);
  if (!params.success) { res.status(400).json({ error: "Invalid request" }); return; }
  const { status, data } = await proxyPost(`/api/runs/${params.data.runId}/print-report`);
  res.status(status).json(data);
});

// GET /runs/:runId/deliverables
router.get("/runs/:runId/deliverables", async (req, res): Promise<void> => {
  const params = GetDeliverablesParams.safeParse(req.params);
  if (!params.success) { res.status(400).json({ error: "Invalid request" }); return; }
  const { status, data } = await proxyGet(`/api/runs/${params.data.runId}/deliverables`);
  res.status(status).json(data);
});

export default router;
