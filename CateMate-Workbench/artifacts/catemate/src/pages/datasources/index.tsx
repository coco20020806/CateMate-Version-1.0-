import React, { useMemo, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { useGetDataSources, useIngestDataSource } from "@workspace/api-client-react";
import {
  AlertTriangle,
  ChevronDown,
  Database,
  FolderOpen,
  GitBranch,
  HardDrive,
  Loader2,
  RefreshCw,
  TableProperties,
  Upload,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { useToast } from "@/hooks/use-toast";
import { cn } from "@/lib/utils";

type DataSourceStatus = "available" | "missing" | "partial" | "raw_only" | "derived_or_folder" | "ingesting" | "error";

type RawdataTreeItem = {
  name: string;
  path: string;
  kind: "file" | "directory";
  fileCount: number;
  folderCount: number;
  totalBytes: number;
  csvFileCount?: number;
  csvFolderCount?: number;
  csvTotalBytes?: number;
  hasCsv?: boolean;
  lastUpdated?: string | null;
  csvLastUpdated?: string | null;
  children?: RawdataTreeItem[];
};

type RawdataTreeGroup = {
  grain: string;
  path: string;
  exists: boolean;
  fileCount: number;
  folderCount: number;
  totalBytes: number;
  csvFileCount?: number;
  csvFolderCount?: number;
  csvTotalBytes?: number;
  hasCsv?: boolean;
  lastUpdated?: string | null;
  csvLastUpdated?: string | null;
  items: RawdataTreeItem[];
};

type DataSourceEntry = {
  id: string;
  grain?: string;
  tableId?: string;
  category?: string;
  type?: string;
  status: DataSourceStatus;
  description?: string;
  expectedColumns?: string[];
  processedTableId?: string;
  processedPath?: string | null;
  path?: string | null;
  rawdataPath?: string | null;
  rawdataExists?: boolean;
  rawdataFileCount?: number;
  rawdataFolderCount?: number;
  rawdataHasCsv?: boolean;
  rawdataCsvFileCount?: number;
  rawdataCsvFolderCount?: number;
  v2SourceRule?: string;
  sourceWorkbookName?: string | null;
  sourceSheet?: string | null;
  rowCount?: number | null;
  columnCount?: number | null;
  lastUpdated?: string | null;
  usedByModules?: string[];
  resolutionMode?: string | null;
  missingReason?: string | null;
};

type DataSourceSummary = {
  available?: number;
  missing?: number;
  partial?: number;
  rawOnly?: number;
  derivedOrFolder?: number;
  processed?: number;
  total?: number;
};

const statusLabels: Record<DataSourceStatus, string> = {
  available: "Available",
  missing: "Missing",
  partial: "Partial",
  raw_only: "Raw only",
  derived_or_folder: "Folder source",
  ingesting: "Ingesting",
  error: "Error",
};

const statusVariants: Record<DataSourceStatus, "success" | "destructive" | "warning" | "info" | "secondary"> = {
  available: "success",
  missing: "destructive",
  partial: "warning",
  raw_only: "info",
  derived_or_folder: "secondary",
  ingesting: "info",
  error: "destructive",
};

function formatNumber(value?: number | null) {
  return typeof value === "number" ? value.toLocaleString() : "-";
}

function formatBytes(value?: number | null) {
  if (!value) return "0 B";
  const units = ["B", "KB", "MB", "GB"];
  let size = value;
  let unitIndex = 0;
  while (size >= 1024 && unitIndex < units.length - 1) {
    size /= 1024;
    unitIndex += 1;
  }
  return `${size.toFixed(size >= 10 || unitIndex === 0 ? 0 : 1)} ${units[unitIndex]}`;
}

function shortPath(path?: string | null) {
  if (!path) return "-";
  const normalized = path.replaceAll("\\", "/");
  const parts = normalized.split("/");
  return parts.length > 3 ? parts.slice(-3).join("/") : normalized;
}

function hasRawdata(group?: RawdataTreeGroup) {
  return Boolean(group?.exists && group.hasCsv);
}

function dataBearingPaths(items: RawdataTreeItem[]): RawdataTreeItem[] {
  const result: RawdataTreeItem[] = [];
  const visit = (item: RawdataTreeItem) => {
    if (item.kind === "directory" && item.hasCsv) {
      const childDirs = (item.children || []).filter(child => child.kind === "directory");
      if (childDirs.length === 0) {
        result.push(item);
      }
    }
    for (const child of item.children || []) {
      visit(child);
    }
  };
  items.forEach(visit);
  return result;
}

function StatCard({
  label,
  value,
  icon: Icon,
}: {
  label: string;
  value: number | string;
  icon: React.ComponentType<{ className?: string }>;
}) {
  return (
    <Card className="bg-card">
      <CardContent className="p-4">
        <div className="flex items-center justify-between gap-3">
          <div>
            <div className="text-sm text-muted-foreground">{label}</div>
            <div className="mt-1 text-2xl font-semibold tabular-nums">{value}</div>
          </div>
          <Icon className="h-5 w-5 text-primary" />
        </div>
      </CardContent>
    </Card>
  );
}

function RawdataGroupCard({ group }: { group: RawdataTreeGroup }) {
  const dataFolders = group.grain === "item" ? dataBearingPaths(group.items) : [];
  const visibleItems = group.grain === "item" ? dataFolders.slice(0, 8) : group.items.slice(0, 8);

  return (
    <Card className="bg-card">
      <CardHeader className="pb-3">
        <div className="flex items-start justify-between gap-3">
          <div>
            <CardTitle className="flex items-center gap-2 text-lg">
              <FolderOpen className="h-5 w-5 text-primary" />
              {group.path}
            </CardTitle>
            <CardDescription className="mt-1">
              {group.grain === "item" ? "item/{L1}/{L2}/{L3}/ CSV folders" : `Recursive CSV check for ${group.grain}`}
            </CardDescription>
          </div>
          <Badge variant={hasRawdata(group) ? "success" : "destructive"}>{hasRawdata(group) ? "Has CSV" : "No CSV"}</Badge>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="grid grid-cols-3 gap-3 text-sm">
          <div>
            <div className="text-muted-foreground">CSV files</div>
            <div className="font-semibold tabular-nums">{formatNumber(group.csvFileCount || 0)}</div>
          </div>
          <div>
            <div className="text-muted-foreground">CSV folders</div>
            <div className="font-semibold tabular-nums">{formatNumber(group.csvFolderCount || 0)}</div>
          </div>
          <div>
            <div className="text-muted-foreground">CSV size</div>
            <div className="font-semibold tabular-nums">{formatBytes(group.csvTotalBytes || 0)}</div>
          </div>
        </div>
        <div className="space-y-2">
          <div className="text-xs font-semibold uppercase text-muted-foreground">
            {group.grain === "item" ? "CSV-bearing L3 folders" : "CSV files / folders"}
          </div>
          {visibleItems.length === 0 ? (
            <div className="rounded-md border border-border bg-muted/30 p-3 text-sm text-muted-foreground">
              No CSV files were found under this folder.
            </div>
          ) : (
            <div className="space-y-2">
              {visibleItems.map(item => (
                <div key={item.path} className="rounded-md border border-border bg-muted/20 p-3">
                  <div className="truncate font-mono text-xs">{item.path}</div>
                  <div className="mt-1 text-xs text-muted-foreground">
                    {formatNumber(item.csvFileCount || 0)} CSV files · {formatBytes(item.csvTotalBytes || 0)}
                  </div>
                </div>
              ))}
              {(group.grain === "item" ? dataFolders.length : group.items.length) > visibleItems.length && (
                <div className="text-xs text-muted-foreground">
                  +{(group.grain === "item" ? dataFolders.length : group.items.length) - visibleItems.length} more
                </div>
              )}
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  );
}

export default function DataSources() {
  const { toast } = useToast();
  const queryClient = useQueryClient();
  const { data: catalog, isLoading, isFetching } = useGetDataSources();
  const ingest = useIngestDataSource();

  const [dialogOpen, setDialogOpen] = useState(false);
  const [openRows, setOpenRows] = useState<Record<string, boolean>>({});
  const [ingestForm, setIngestForm] = useState({ category: "", type: "", path: "" });

  const entries = (((catalog as any)?.entries || []) as DataSourceEntry[]).map(entry => ({
    ...entry,
    grain: entry.grain || entry.category,
    tableId: entry.tableId || entry.type,
  }));
  const summary = ((catalog as any)?.summary || {}) as DataSourceSummary;
  const rawdataRoot = (catalog as any)?.rawdataRoot || "CateMate_rawdata";
  const rawdataGroups = (((catalog as any)?.rawdataTree?.groups || []) as RawdataTreeGroup[]);
  const rawdataByGrain = useMemo(
    () => Object.fromEntries(rawdataGroups.map(group => [group.grain, group])),
    [rawdataGroups],
  ) as Record<string, RawdataTreeGroup | undefined>;

  const refresh = () => {
    queryClient.invalidateQueries({ queryKey: ["/api/datasources"] });
    toast({ title: "Data source status refreshed" });
  };

  const handleFolderAction = (label: string, path: string) => {
    toast({ title: label, description: path });
  };

  const handleIngest = () => {
    if (!ingestForm.category || !ingestForm.type || !ingestForm.path) {
      toast({ title: "All fields required", variant: "destructive" });
      return;
    }
    ingest.mutate(
      { data: ingestForm as any },
      {
        onSuccess: () => {
          toast({ title: "Data source ingested" });
          setDialogOpen(false);
          setIngestForm({ category: "", type: "", path: "" });
          queryClient.invalidateQueries({ queryKey: ["/api/datasources"] });
        },
        onError: () => toast({ title: "Ingest failed", variant: "destructive" }),
      },
    );
  };

  const rawdataFileCount = rawdataGroups.reduce((sum, group) => sum + (group.csvFileCount || 0), 0);
  const rawdataFolderCount = rawdataGroups.reduce((sum, group) => sum + (group.csvFolderCount || 0), 0);
  const itemDataFolders = rawdataByGrain.item ? dataBearingPaths(rawdataByGrain.item.items).length : 0;
  const missingCount = entries.filter(entry => entry.status === "missing" || !entry.rawdataHasCsv).length;

  return (
    <div className="mx-auto max-w-7xl space-y-6 p-8">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Data Sources</h1>
          <p className="mt-1 text-muted-foreground">V2 Solve Loop rawdata structure and catalog readiness.</p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <Button variant="outline" className="gap-2" onClick={refresh} disabled={isFetching}>
            <RefreshCw className={cn("h-4 w-4", isFetching && "animate-spin")} />
            Refresh Status
          </Button>
          <Button
            variant="outline"
            className="gap-2"
            onClick={() => toast({ title: "Preprocess command", description: "scripts/preprocess_raw_data_sources.py" })}
          >
            <TableProperties className="h-4 w-4" />
            Run Preprocess
          </Button>
          <Button variant="outline" className="gap-2" onClick={() => handleFolderAction("Rawdata root", rawdataRoot)}>
            <FolderOpen className="h-4 w-4" />
            Raw Folder
          </Button>
          <Button
            variant="outline"
            className="gap-2"
            onClick={() => handleFolderAction("Processed data folder", "CateMate_processeddata/source_tables")}
          >
            <FolderOpen className="h-4 w-4" />
            Processed Folder
          </Button>
          <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
            <DialogTrigger asChild>
              <Button variant="secondary" className="gap-2">
                <Upload className="h-4 w-4" />
                Ingest Path
              </Button>
            </DialogTrigger>
            <DialogContent>
              <DialogHeader>
                <DialogTitle>Ingest Data Source</DialogTitle>
                <DialogDescription>Use this only when a fixed V2 catalog source needs a new backing file.</DialogDescription>
              </DialogHeader>
              <div className="space-y-4 py-4">
                <div className="space-y-2">
                  <Label>Grain</Label>
                  <Input
                    placeholder="category / shop / item"
                    value={ingestForm.category}
                    onChange={event => setIngestForm(prev => ({ ...prev, category: event.target.value }))}
                  />
                </div>
                <div className="space-y-2">
                  <Label>Table ID</Label>
                  <Input
                    placeholder="item_l3_category_csv"
                    value={ingestForm.type}
                    onChange={event => setIngestForm(prev => ({ ...prev, type: event.target.value }))}
                  />
                </div>
                <div className="space-y-2">
                  <Label>File Path</Label>
                  <Input
                    placeholder="C:\\data\\category_monthly.xlsx"
                    value={ingestForm.path}
                    onChange={event => setIngestForm(prev => ({ ...prev, path: event.target.value }))}
                  />
                </div>
              </div>
              <DialogFooter>
                <Button variant="outline" onClick={() => setDialogOpen(false)}>
                  Cancel
                </Button>
                <Button onClick={handleIngest} disabled={ingest.isPending} className="gap-2">
                  {ingest.isPending && <Loader2 className="h-4 w-4 animate-spin" />}
                  Ingest
                </Button>
              </DialogFooter>
            </DialogContent>
          </Dialog>
        </div>
      </div>

      <div className="rounded-lg border border-border bg-card p-5">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
          <div className="max-w-4xl">
            <div className="flex items-center gap-2 text-lg font-semibold">
              <GitBranch className="h-5 w-5 text-primary" />
              V2 Solve Loop uses rawdata first
            </div>
            <p className="mt-2 text-sm leading-6 text-muted-foreground">
              V2 prioritizes <span className="font-mono text-foreground">{rawdataRoot}/</span>, registered through{" "}
              <span className="font-mono text-foreground">config/rawdata_catalog.yaml</span>, then read by Scope. Category and item runs
              usually require rawdata and should not casually fall back to processed CSV, especially{" "}
              <span className="font-mono text-foreground">monthly_market_trend</span> category/item runs.
            </p>
          </div>
          <Badge variant="outline" className="w-fit">
            Current default chain
          </Badge>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-5">
        <StatCard label="Catalog Sources" value={summary.total || entries.length} icon={Database} />
        <StatCard label="CSV Files" value={formatNumber(rawdataFileCount)} icon={HardDrive} />
        <StatCard label="CSV Folders" value={formatNumber(rawdataFolderCount)} icon={FolderOpen} />
        <StatCard label="Item L3 With CSV" value={formatNumber(itemDataFolders)} icon={GitBranch} />
        <StatCard label="No CSV Found" value={formatNumber(missingCount)} icon={AlertTriangle} />
      </div>

      <div className="grid grid-cols-1 gap-4 xl:grid-cols-3">
        {(["category", "shop", "item"] as const).map(grain => {
          const group = rawdataByGrain[grain] || {
            grain,
            path: `${rawdataRoot}/${grain}`,
            exists: false,
            fileCount: 0,
            folderCount: 0,
            totalBytes: 0,
            csvFileCount: 0,
            csvFolderCount: 0,
            csvTotalBytes: 0,
            hasCsv: false,
            lastUpdated: null,
            items: [],
          };
          return <RawdataGroupCard key={grain} group={group} />;
        })}
      </div>

      <Card className="bg-card">
        <CardHeader className="border-b border-border pb-4">
          <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <CardTitle>V2 Rawdata Catalog</CardTitle>
              <CardDescription>Catalog registration mapped to actual rawdata folders. Last synced {(catalog as any)?.lastSynced || "-"}</CardDescription>
            </div>
            <Badge variant="outline">{entries.length} fixed sources</Badge>
          </div>
        </CardHeader>
        <CardContent className="p-0">
          {isLoading ? (
            <div className="p-8 text-center text-muted-foreground animate-pulse">Loading V2 rawdata catalog...</div>
          ) : entries.length === 0 ? (
            <div className="p-10 text-center text-muted-foreground">No fixed data sources were found in the catalog.</div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Grain</TableHead>
                  <TableHead>Table ID</TableHead>
                  <TableHead>V2 Source Folder</TableHead>
                  <TableHead>Catalog Status</TableHead>
                  <TableHead>Rawdata Availability</TableHead>
                  <TableHead>Used By Modules</TableHead>
                  <TableHead>Notes</TableHead>
                  <TableHead className="w-12" />
                </TableRow>
              </TableHeader>
              <TableBody>
                {entries.map(entry => {
                  const isOpen = Boolean(openRows[entry.id]);
                  const group = entry.grain ? rawdataByGrain[entry.grain] : undefined;
                  const itemFolders = entry.grain === "item" && group ? dataBearingPaths(group.items) : [];
                  return (
                    <React.Fragment key={entry.id}>
                      <TableRow>
                        <TableCell>
                          <Badge variant="outline">{entry.grain}</Badge>
                        </TableCell>
                        <TableCell className="font-mono text-sm">{entry.tableId}</TableCell>
                        <TableCell className="max-w-[230px] truncate font-mono text-xs text-muted-foreground">
                          {entry.rawdataPath || "-"}
                        </TableCell>
                        <TableCell>
                          <Badge variant={statusVariants[entry.status] || "secondary"}>{statusLabels[entry.status] || entry.status}</Badge>
                        </TableCell>
                        <TableCell>
                          <div className="space-y-1">
                            <Badge variant={entry.rawdataHasCsv ? "success" : "destructive"}>
                              {entry.rawdataHasCsv ? "CSV found" : "No CSV"}
                            </Badge>
                            <div className="text-xs text-muted-foreground">
                              {formatNumber(entry.rawdataCsvFileCount || 0)} CSV files · {formatNumber(entry.rawdataCsvFolderCount || 0)} CSV folders
                            </div>
                          </div>
                        </TableCell>
                        <TableCell className="max-w-[240px]">
                          <div className="flex flex-wrap gap-1">
                            {(entry.usedByModules || []).slice(0, 2).map(module => (
                              <Badge key={module} variant="secondary" className="max-w-[180px] truncate">
                                {module}
                              </Badge>
                            ))}
                            {(entry.usedByModules || []).length > 2 && <Badge variant="outline">+{(entry.usedByModules || []).length - 2}</Badge>}
                            {(entry.usedByModules || []).length === 0 && <span className="text-sm text-muted-foreground">-</span>}
                          </div>
                        </TableCell>
                        <TableCell className="max-w-[260px] text-sm text-muted-foreground">
                          {entry.rawdataHasCsv
                            ? entry.grain === "item" && itemFolders.length > 0
                              ? `${itemFolders.length} L3 folders with CSV data`
                              : "CSV exists under this grain folder"
                            : entry.grain === "shop"
                              ? "No CSV under CateMate_rawdata/shop"
                              : entry.missingReason || "Rawdata unavailable"}
                        </TableCell>
                        <TableCell className="text-right">
                          <Button
                            variant="ghost"
                            size="icon"
                            aria-label="Toggle data source details"
                            onClick={() => setOpenRows(prev => ({ ...prev, [entry.id]: !isOpen }))}
                          >
                            <ChevronDown className={cn("h-4 w-4 transition-transform", isOpen && "rotate-180")} />
                          </Button>
                        </TableCell>
                      </TableRow>
                      {isOpen && (
                        <TableRow className="bg-muted/30">
                          <TableCell colSpan={8} className="p-5">
                            <div className="grid gap-5 lg:grid-cols-[1.1fr_1fr_1fr]">
                              <div>
                                <div className="text-xs font-semibold uppercase text-muted-foreground">V2 Source Rule</div>
                                <div className="mt-2 text-sm text-muted-foreground">{entry.v2SourceRule || "-"}</div>
                                {entry.grain === "item" && itemFolders.length > 0 && (
                                  <div className="mt-3 space-y-2">
                                    <div className="text-xs font-semibold uppercase text-muted-foreground">Available L3 folders</div>
                                    {itemFolders.slice(0, 6).map(folder => (
                                      <div key={folder.path} className="rounded-md border border-border bg-background/40 p-2">
                                        <div className="truncate font-mono text-xs">{folder.path}</div>
                                        <div className="mt-1 text-xs text-muted-foreground">{formatNumber(folder.csvFileCount || 0)} CSV files</div>
                                      </div>
                                    ))}
                                  </div>
                                )}
                              </div>
                              <div>
                                <div className="text-xs font-semibold uppercase text-muted-foreground">Expected Columns</div>
                                <div className="mt-2 flex flex-wrap gap-1">
                                  {(entry.expectedColumns || []).map(column => (
                                    <Badge key={column} variant="outline" className="font-mono">
                                      {column}
                                    </Badge>
                                  ))}
                                  {(entry.expectedColumns || []).length === 0 && <span className="text-sm text-muted-foreground">No schema declared.</span>}
                                </div>
                              </div>
                              <div className="space-y-2 text-sm">
                                <div className="text-xs font-semibold uppercase text-muted-foreground">V1 / Preprocess Compatibility</div>
                                <div>Processed CSV: <span className="font-mono text-muted-foreground">{entry.processedPath || "-"}</span></div>
                                <div>Source sheet: <span className="text-muted-foreground">{entry.sourceSheet || "-"}</span></div>
                                <div>Rows: <span className="text-muted-foreground">{formatNumber(entry.rowCount)}</span></div>
                                <div>Columns: <span className="text-muted-foreground">{formatNumber(entry.columnCount)}</span></div>
                                <div className="pt-2 text-muted-foreground">{entry.missingReason || "Ready for V2 rawdata use."}</div>
                              </div>
                            </div>
                          </TableCell>
                        </TableRow>
                      )}
                    </React.Fragment>
                  );
                })}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
