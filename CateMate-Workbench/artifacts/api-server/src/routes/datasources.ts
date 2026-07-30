import { Router, type IRouter } from "express";
import { IngestDataSourceBody } from "@workspace/api-zod";

const PYTHON_API = process.env["PYTHON_API_URL"] || "http://localhost:8100";

const router: IRouter = Router();

// GET /datasources
router.get("/datasources", async (_req, res): Promise<void> => {
  const resp = await fetch(`${PYTHON_API}/api/datasources`);
  const data = await resp.json();
  res.status(resp.status).json(data);
});

// POST /datasources/ingest
router.post("/datasources/ingest", async (req, res): Promise<void> => {
  const parsed = IngestDataSourceBody.safeParse(req.body);
  if (!parsed.success) {
    res.status(400).json({ error: parsed.error.message });
    return;
  }
  const resp = await fetch(`${PYTHON_API}/api/datasources/ingest`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(parsed.data),
  });
  const data = await resp.json();
  res.status(resp.status).json(data);
});

export default router;
