import { Router, type IRouter } from "express";

const PYTHON_API = process.env["PYTHON_API_URL"] || "http://localhost:8100";

const router: IRouter = Router();

// GET /modules
router.get("/modules", async (_req, res): Promise<void> => {
  const resp = await fetch(`${PYTHON_API}/api/modules`);
  const data = await resp.json();
  res.status(resp.status).json(data);
});

export default router;
