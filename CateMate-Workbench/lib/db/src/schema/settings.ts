import { pgTable, text, timestamp, jsonb, real } from "drizzle-orm/pg-core";
import { createInsertSchema } from "drizzle-zod";
import { z } from "zod/v4";

export const settingsTable = pgTable("settings", {
  id: text("id").primaryKey().default("default"),
  provider: text("provider").notNull().default("deepseek"),
  model: text("model").notNull().default("deepseek-chat"),
  baseUrl: text("base_url").notNull().default("https://api.deepseek.com/v1"),
  defaultPlanningMode: text("default_planning_mode").notNull().default("v2_solve_loop"),
  temperature: real("temperature"),
  maxTokens: real("max_tokens"),
  enabledModules: jsonb("enabled_modules").$type<string[]>(),
  defaultTimeGranularity: text("default_time_granularity").notNull().default("month"),
  updatedAt: timestamp("updated_at", { withTimezone: true }).notNull().defaultNow().$onUpdate(() => new Date()),
});

export const insertSettingsSchema = createInsertSchema(settingsTable);
export type InsertSettings = z.infer<typeof insertSettingsSchema>;
export type Settings = typeof settingsTable.$inferSelect;
