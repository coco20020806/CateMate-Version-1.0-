import { Router, type IRouter } from "express";
import healthRouter from "./health";
import runsRouter from "./runs";
import settingsRouter from "./settings";
import dataSourcesRouter from "./datasources";
import modulesRouter from "./modules";
import filesRouter from "./files";

const router: IRouter = Router();

router.use(healthRouter);
router.use(runsRouter);
router.use(settingsRouter);
router.use(dataSourcesRouter);
router.use(modulesRouter);
router.use(filesRouter);

export default router;
