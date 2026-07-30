import { pgTable, text, timestamp, jsonb } from "drizzle-orm/pg-core";
import { createInsertSchema } from "drizzle-zod";
import { z } from "zod/v4";

export const runsTable = pgTable("runs", {
  id: text("id").primaryKey(),
  caseId: text("case_id").notNull(),
  status: text("status").notNull().default("awaiting_category_confirmation"),
  planningMode: text("planning_mode").notNull().default("v2_solve_loop"),
  requirementText: text("requirement_text").notNull(),
  site: text("site"),
  category: text("category"),
  errorMessage: text("error_message"),
  understandingJson: jsonb("understanding_json"),
  clarifyingQuestionsJson: jsonb("clarifying_questions_json"),
  deliverablesJson: jsonb("deliverables_json"),
  solveProgressJson: jsonb("solve_progress_json"),
  blueprintJson: jsonb("blueprint_json"),
  gapsJson: jsonb("gaps_json"),
  briefJson: jsonb("brief_json"),
  visualSpecJson: jsonb("visual_spec_json"),
  createdAt: timestamp("created_at", { withTimezone: true }).notNull().defaultNow(),
  updatedAt: timestamp("updated_at", { withTimezone: true }).notNull().defaultNow().$onUpdate(() => new Date()),
});

export const insertRunSchema = createInsertSchema(runsTable).omit({ createdAt: true, updatedAt: true });
export type InsertRun = z.infer<typeof insertRunSchema>;
export type Run = typeof runsTable.$inferSelect;
