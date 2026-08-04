import React, { useState } from "react";
import { useListRuns, RunStatus } from "@workspace/api-client-react";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { StatusBadge } from "@/components/StatusBadge";
import { Link } from "wouter";
import { Button } from "@/components/ui/button";
import { Search, ChevronRight } from "lucide-react";
import { Badge } from "@/components/ui/badge";

const STATUS_FILTERS = [
  { label: "All", value: "" },
  { label: "Awaiting", value: RunStatus.awaiting_category_confirmation },
  { label: "Solving", value: RunStatus.solve_running },
  { label: "Workbook Ready", value: RunStatus.data_workbook_generated },
  { label: "Failed", value: RunStatus.failed },
];

export default function RunHistory() {
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("");

  const { data: runs, isLoading } = useListRuns(
    { q: search || undefined, status: statusFilter || undefined } as any,
  );

  return (
    <div className="p-8 max-w-6xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Run History</h1>
          <p className="text-muted-foreground mt-1">All analysis pipeline executions.</p>
        </div>
      </div>

      <Card className="bg-card">
        <div className="p-4 border-b border-border flex items-center gap-4">
          <div className="relative flex-1 max-w-md">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
            <Input
              placeholder="Search by case ID or keyword..."
              value={search}
              onChange={e => setSearch(e.target.value)}
              className="pl-9"
            />
          </div>
          <div className="flex gap-2">
            {STATUS_FILTERS.map(f => (
              <Badge
                key={f.value}
                variant={statusFilter === f.value ? "default" : "outline"}
                className="cursor-pointer"
                onClick={() => setStatusFilter(f.value)}
              >
                {f.label}
              </Badge>
            ))}
          </div>
        </div>
        <CardContent className="p-0">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Case ID</TableHead>
                <TableHead>Requirement</TableHead>
                <TableHead>Mode</TableHead>
                <TableHead>Status</TableHead>
                <TableHead className="text-right">Action</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {isLoading ? (
                <TableRow>
                  <TableCell colSpan={5} className="h-24 text-center text-muted-foreground">Loading runs...</TableCell>
                </TableRow>
              ) : !runs || (runs as any[]).length === 0 ? (
                <TableRow>
                  <TableCell colSpan={5} className="h-24 text-center text-muted-foreground">No runs found.</TableCell>
                </TableRow>
              ) : (
                (runs as any[]).map((run: any) => (
                  <TableRow key={run.id} className="group">
                    <TableCell className="font-mono text-xs">{run.caseId}</TableCell>
                    <TableCell className="max-w-md truncate font-medium">{run.requirementText}</TableCell>
                    <TableCell className="font-mono text-xs text-muted-foreground">{run.planningMode}</TableCell>
                    <TableCell><StatusBadge status={run.status} /></TableCell>
                    <TableCell className="text-right">
                      <Button variant="ghost" size="sm" asChild className="opacity-0 group-hover:opacity-100 transition-opacity">
                        <Link href={`/runs/${run.id}`}>
                          View <ChevronRight className="w-4 h-4 ml-1" />
                        </Link>
                      </Button>
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  );
}
