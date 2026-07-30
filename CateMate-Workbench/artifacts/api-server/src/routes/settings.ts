import { Router, type IRouter } from "express";
import { UpdateSettingsBody } from "@workspace/api-zod";

const PYTHON_API = process.env["PYTHON_API_URL"] || "http://localhost:8100";

const router: IRouter = Router();

// GET /settings
router.get("/settings", async (_req, res): Promise<void> => {
  const resp = await fetch(`${PYTHON_API}/api/settings`);
  const data = await resp.json();
  res.status(resp.status).json(data);
});

// PUT /settings
router.put("/settings", async (req, res): Promise<void> => {
  const parsed = UpdateSettingsBody.safeParse(req.body);
  if (!parsed.success) {
    res.status(400).json({ error: parsed.error.message });
    return;
  }
  const resp = await fetch(`${PYTHON_API}/api/settings`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(parsed.data),
  });
  const data = await resp.json();
  res.status(resp.status).json(data);
});

export default router;
