import { pgTable, text, timestamp, real } from "drizzle-orm/pg-core";
import { createInsertSchema } from "drizzle-zod";
import { z } from "zod/v4";

export const dataSourcesTable = pgTable("data_sources", {
  id: text("id").primaryKey(),
  category: text("category").notNull(),
  type: text("type").notNull(), // category | shop | item
  status: text("status").notNull().default("available"),
  path: text("path"),
  rowCount: real("row_count"),
  lastUpdated: timestamp("last_updated", { withTimezone: true }),
  createdAt: timestamp("created_at", { withTimezone: true }).notNull().defaultNow(),
});

export const insertDataSourceSchema = createInsertSchema(dataSourcesTable).omit({ createdAt: true });
export type InsertDataSource = z.infer<typeof insertDataSourceSchema>;
export type DataSource = typeof dataSourcesTable.$inferSelect;
