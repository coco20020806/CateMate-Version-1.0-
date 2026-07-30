import { Router, type IRouter } from "express";

const PYTHON_API = process.env["PYTHON_API_URL"] || "http://localhost:8100";

const router: IRouter = Router();

// Proxy file downloads to the Python API which serves from outputs/
// Express 5 / path-to-regexp v8 requires a named wildcard parameter.
router.get("/files/*filePath", async (req, res): Promise<void> => {
  const filePath = String(req.params.filePath || "").replace(/^\//, "");
  const resp = await fetch(`${PYTHON_API}/api/files/${filePath}`);
  if (!resp.ok) {
    res.status(resp.status).json({ error: "File not found" });
    return;
  }
  const contentType = resp.headers.get("content-type") || "application/octet-stream";
  res.setHeader("Content-Type", contentType);
  const disposition = resp.headers.get("content-disposition");
  if (disposition) res.setHeader("Content-Disposition", disposition);

  const buffer = Buffer.from(await resp.arrayBuffer());
  res.send(buffer);
});

// Proxy task polling
router.get("/tasks/:taskId", async (req, res): Promise<void> => {
  const resp = await fetch(`${PYTHON_API}/api/tasks/${req.params.taskId}`);
  const data = await resp.json();
  res.status(resp.status).json(data);
});

export default router;
