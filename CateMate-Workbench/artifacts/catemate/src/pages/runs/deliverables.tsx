import React, { useState } from "react";
import { useParams } from "wouter";
import {
  useGetRun,
  getGetRunQueryKey,
  getGetBriefQueryKey,
  getGetVisualSpecQueryKey,
  useGetDeliverables,
  useGenerateBrief,
  useGenerateVisualSpec,
  useGetVisualSpec,
  useConfirmVisualSpec,
  useGenerateHtmlReport,
  useGeneratePrintReport,
  useGetBrief,
} from "@workspace/api-client-react";
import { useQueryClient } from "@tanstack/react-query";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { FileText, Download, LayoutTemplate, Printer, FileSpreadsheet, ExternalLink, Loader2, CheckCircle2 } from "lucide-react";
import { StatusBadge } from "@/components/StatusBadge";
import { VisualSpecEditor } from "@/components/VisualSpecEditor";
import { useToast } from "@/hooks/use-toast";

export default function DeliverablesHub() {
  const { runId } = useParams();
  const queryClient = useQueryClient();
  const { toast } = useToast();

  const { data: run } = useGetRun(runId!);
  const { data: deliverables, refetch: refetchDeliverables } = useGetDeliverables(runId!);
  const { data: brief } = useGetBrief(runId!, {
    query: {
      queryKey: getGetBriefQueryKey(runId!),
      enabled: !!deliverables?.brief?.status && deliverables.brief.status === "ready",
    },
  });
  const { data: visualSpec, refetch: refetchSpec } = useGetVisualSpec(runId!, {
    query: {
      queryKey: getGetVisualSpecQueryKey(runId!),
      retry: false,
    },
  });

  const generateBrief = useGenerateBrief();
  const generateVisualSpec = useGenerateVisualSpec();
  const confirmVisualSpec = useConfirmVisualSpec();
  const generateHtmlReport = useGenerateHtmlReport();
  const generatePrintReport = useGeneratePrintReport();

  const [showBrief, setShowBrief] = useState(false);

  const invalidateAll = () => {
    queryClient.invalidateQueries({ queryKey: getGetRunQueryKey(runId!) });
    refetchDeliverables();
  };

  const handleGenerateBrief = () => {
    generateBrief.mutate({ runId: runId! }, {
      onSuccess: () => { toast({ title: "Brief generation started" }); invalidateAll(); },
      onError: () => toast({ title: "Failed to generate brief", variant: "destructive" }),
    });
  };

  const handleGenerateVisualSpec = () => {
    generateVisualSpec.mutate({ runId: runId! }, {
      onSuccess: () => { toast({ title: "Visual Spec generation started" }); setTimeout(() => refetchSpec(), 2000); },
      onError: () => toast({ title: "Failed to generate visual spec", variant: "destructive" }),
    });
  };

  const handleConfirmSpec = (sections: any[]) => {
    confirmVisualSpec.mutate(
      { runId: runId!, data: { sections } },
      {
        onSuccess: () => { toast({ title: "Visual Spec confirmed" }); refetchSpec(); invalidateAll(); },
        onError: () => toast({ title: "Failed to confirm spec", variant: "destructive" }),
      },
    );
  };

  const handleGenerateHtmlReport = () => {
    generateHtmlReport.mutate({ runId: runId! }, {
      onSuccess: () => { toast({ title: "HTML report generation started" }); invalidateAll(); },
    });
  };

  const handleGeneratePrintReport = () => {
    generatePrintReport.mutate({ runId: runId! }, {
      onSuccess: () => { toast({ title: "Print report generation started" }); invalidateAll(); },
    });
  };

  const del = (deliverables as any) || {};
  const specStatus = (visualSpec as any)?.spec_status || (visualSpec as any)?.specStatus || "none";
  const isSpecConfirmed = specStatus === "confirmed";

  return (
    <div className="p-8 max-w-5xl mx-auto space-y-6">
      <div className="flex items-center justify-between mb-8 pb-4 border-b border-border">
        <div>
          <h1 className="text-3xl font-bold tracking-tight mb-2">Deliverables Hub</h1>
          <div className="flex items-center gap-3">
            <span className="font-mono text-muted-foreground">{run?.caseId}</span>
            <span className="text-muted-foreground">•</span>
            <span className="text-sm truncate max-w-md">{run?.requirementText}</span>
          </div>
        </div>
        {run && <StatusBadge status={run.status} />}
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Workbook */}
        <Card className="flex flex-col">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <FileSpreadsheet className="w-5 h-5 text-primary" />
              Data Workbook
            </CardTitle>
            <CardDescription>Raw data, intermediate tables, and catalog subsets.</CardDescription>
          </CardHeader>
          <CardContent className="mt-auto">
            <div className="flex items-center justify-between">
              <DeliverableStatus status={del.workbook?.status} />
              {del.workbook?.downloadUrl && (
                <Button variant="outline" size="sm" className="gap-2" asChild>
                  <a href={del.workbook.downloadUrl} download>
                    <Download className="w-4 h-4" /> Download .xlsx
                  </a>
                </Button>
              )}
            </div>
          </CardContent>
        </Card>

        {/* Brief */}
        <Card className="flex flex-col">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <FileText className="w-5 h-5 text-primary" />
              Conclusion Brief
            </CardTitle>
            <CardDescription>Markdown executive summary with key findings.</CardDescription>
          </CardHeader>
          <CardContent className="mt-auto space-y-3">
            <div className="flex items-center justify-between">
              <DeliverableStatus status={del.brief?.status} />
              <div className="flex gap-2">
                {del.brief?.status !== "ready" && (
                  <Button variant="outline" size="sm" className="gap-2" onClick={handleGenerateBrief} disabled={generateBrief.isPending}>
                    {generateBrief.isPending && <Loader2 className="w-3 h-3 animate-spin" />}
                    Generate Brief
                  </Button>
                )}
                {del.brief?.status === "ready" && (
                  <Button variant="outline" size="sm" onClick={() => setShowBrief(!showBrief)}>
                    {showBrief ? "Hide" : "View"} Brief
                  </Button>
                )}
              </div>
            </div>
            {showBrief && brief && (
              <div className="prose prose-sm dark:prose-invert max-w-none border border-border rounded-md p-4 bg-muted/30 max-h-96 overflow-y-auto">
                <pre className="whitespace-pre-wrap text-sm font-sans">{(brief as any).markdown}</pre>
              </div>
            )}
          </CardContent>
        </Card>

        {/* HTML Report */}
        <Card className="flex flex-col">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <LayoutTemplate className="w-5 h-5 text-primary" />
              Visual HTML Report
            </CardTitle>
            <CardDescription>Interactive web report with Plotly charts.</CardDescription>
          </CardHeader>
          <CardContent className="mt-auto space-y-3">
            <div className="flex items-center justify-between">
              <DeliverableStatus status={del.htmlReport?.status} />
              <div className="flex gap-2">
                {isSpecConfirmed && del.htmlReport?.status !== "ready" && (
                  <Button size="sm" className="gap-2" onClick={handleGenerateHtmlReport} disabled={generateHtmlReport.isPending}>
                    {generateHtmlReport.isPending && <Loader2 className="w-3 h-3 animate-spin" />}
                    Render Report
                  </Button>
                )}
                {!isSpecConfirmed && del.htmlReport?.status !== "ready" && (
                  <span className="text-xs text-muted-foreground">Confirm Visual Spec first</span>
                )}
                {del.htmlReport?.downloadUrl && (
                  <Button size="sm" variant="outline" className="gap-2" asChild>
                    <a href={del.htmlReport.downloadUrl} target="_blank" rel="noopener noreferrer">
                      <ExternalLink className="w-3 h-3" /> Open
                    </a>
                  </Button>
                )}
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Print Report */}
        <Card className="flex flex-col">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Printer className="w-5 h-5 text-primary" />
              Print Report (Fuzzy Numbers)
            </CardTitle>
            <CardDescription>A4 landscape HTML for printing/PDF export. Numbers are obfuscated.</CardDescription>
          </CardHeader>
          <CardContent className="mt-auto space-y-3">
            <div className="flex items-center justify-between">
              <DeliverableStatus status={del.printReport?.status} />
              <div className="flex gap-2">
                {isSpecConfirmed && del.printReport?.status !== "ready" && (
                  <Button size="sm" variant="outline" className="gap-2" onClick={handleGeneratePrintReport} disabled={generatePrintReport.isPending}>
                    {generatePrintReport.isPending && <Loader2 className="w-3 h-3 animate-spin" />}
                    Generate Print
                  </Button>
                )}
                {del.printReport?.downloadUrl && (
                  <Button size="sm" variant="outline" className="gap-2" asChild>
                    <a href={del.printReport.downloadUrl} target="_blank" rel="noopener noreferrer">
                      <ExternalLink className="w-3 h-3" /> Open
                    </a>
                  </Button>
                )}
              </div>
            </div>
            {del.printReport?.status === "ready" && (
              <p className="text-xs text-muted-foreground">Ctrl+P / Command+P to save as PDF (A4 landscape recommended).</p>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Visual Spec Editor (Gate C) */}
      <div className="pt-4">
        {!visualSpec && (
          <Card>
            <CardContent className="py-6 text-center space-y-3">
              <p className="text-muted-foreground">No Visual Report Spec yet.</p>
              <Button onClick={handleGenerateVisualSpec} disabled={generateVisualSpec.isPending} className="gap-2">
                {generateVisualSpec.isPending && <Loader2 className="w-3 h-3 animate-spin" />}
                Generate Visual Report Spec
              </Button>
            </CardContent>
          </Card>
        )}

        {visualSpec && (
          <VisualSpecEditor
            sections={(visualSpec as any).sections || []}
            specStatus={specStatus}
            dataGaps={(visualSpec as any).data_gaps || (visualSpec as any).dataGaps}
            onConfirm={handleConfirmSpec}
            isConfirming={confirmVisualSpec.isPending}
          />
        )}
      </div>
    </div>
  );
}

function DeliverableStatus({ status }: { status?: string }) {
  if (status === "ready") {
    return (
      <span className="text-sm text-emerald-600 font-medium flex items-center gap-2">
        <CheckCircle2 className="w-4 h-4" /> Ready
      </span>
    );
  }
  if (status === "generating") {
    return (
      <span className="text-sm text-blue-500 font-medium flex items-center gap-2">
        <Loader2 className="w-4 h-4 animate-spin" /> Generating...
      </span>
    );
  }
  if (status === "failed") {
    return <span className="text-sm text-destructive font-medium">Failed</span>;
  }
  return (
    <span className="text-sm text-muted-foreground flex items-center gap-2">
      <span className="w-2 h-2 rounded-full bg-muted" /> Not Started
    </span>
  );
}
