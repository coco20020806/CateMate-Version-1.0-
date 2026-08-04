import React, { useState } from "react";
import { useParams, Link } from "wouter";
import {
  useGetRun,
  getGetRunQueryKey,
  getGetBlueprintQueryKey,
  getGetGapsQueryKey,
  RunStatus,
  useConfirmCategories,
  useSubmitClarification,
  useGetBlueprint,
  useGetGaps,
  useTriggerSolve,
} from "@workspace/api-client-react";
import { useQueryClient } from "@tanstack/react-query";
import { StatusBadge } from "@/components/StatusBadge";
import { UnderstandingSummary } from "@/components/UnderstandingSummary";
import { SolveProgressPanel } from "@/components/SolveProgress";
import { Card, CardContent, CardHeader, CardTitle, CardDescription, CardFooter } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { AlertCircle, CheckCircle2, ChevronRight, Download, FileSpreadsheet, Loader2, Play, SkipForward, FolderOpen } from "lucide-react";
import { useToast } from "@/hooks/use-toast";

function formatConfidence(confidence: unknown): string | null {
  if (confidence == null || confidence === "") return null;
  if (typeof confidence === "number" && Number.isFinite(confidence)) {
    return `${Math.round(confidence * 100)}%`;
  }
  return String(confidence);
}

const POST_CATEGORY_DONE_STATUSES = new Set([
  RunStatus.awaiting_clarification,
  RunStatus.awaiting_rawdata_clarification,
  RunStatus.clarification_completed,
  RunStatus.solve_running,
  RunStatus.failed,
  RunStatus.data_workbook_generated,
]);

export default function RunDetail() {
  const { runId } = useParams();
  const queryClient = useQueryClient();
  const { toast } = useToast();

  const [selectedCats, setSelectedCats] = useState<string[]>([]);
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [feedback, setFeedback] = useState("");
  const [continuingAfterCategory, setContinuingAfterCategory] = useState(false);

  const { data: run, isLoading: runLoading } = useGetRun(runId!, {
    query: {
      queryKey: getGetRunQueryKey(runId!),
      refetchInterval: (query: any) => {
        const d = query.state?.data;
        if (d?.status === RunStatus.solve_running) return 3000;
        // Keep polling while post-category continue is in flight.
        if (continuingAfterCategory) return 2500;
        return false;
      },
    },
  });

  React.useEffect(() => {
    if (!continuingAfterCategory || !run) return;
    if (POST_CATEGORY_DONE_STATUSES.has(run.status as any)) {
      setContinuingAfterCategory(false);
    }
  }, [continuingAfterCategory, run?.status]);

  const { data: blueprint } = useGetBlueprint(runId!, {
    query: {
      queryKey: getGetBlueprintQueryKey(runId!),
      enabled: !!run && (
        run.status === RunStatus.data_workbook_generated ||
        run.status === RunStatus.brief_generated ||
        run.status === RunStatus.html_report_generated ||
        run.status === RunStatus.print_report_generated
      ),
    },
  });

  const { data: gaps } = useGetGaps(runId!, {
    query: {
      queryKey: getGetGapsQueryKey(runId!),
      enabled: !!run && run.status === RunStatus.data_workbook_generated,
    },
  });

  const confirmCats = useConfirmCategories();
  const triggerSolve = useTriggerSolve();
  const submitClarification = useSubmitClarification();

  if (runLoading) {
    return <div className="p-8 text-muted-foreground animate-pulse">Loading run detail...</div>;
  }

  if (!run) return <div className="p-8 text-destructive">Run not found.</div>;

  const understanding = run.understanding as any;
  const clarifyingQuestions = (run.clarifyingQuestions ?? []) as any[];

  const invalidateRun = () => queryClient.invalidateQueries({ queryKey: getGetRunQueryKey(runId!) });

  const continueAfterCategory = (opts?: { toastTitle?: string }) => {
    setContinuingAfterCategory(true);
    triggerSolve.mutate(
      { runId: runId! },
      {
        onSuccess: () => {
          toast({ title: opts?.toastTitle || "Continuing pipeline…" });
          invalidateRun();
        },
        onError: () => {
          setContinuingAfterCategory(false);
          toast({ title: "Continue failed", variant: "destructive" });
        },
      },
    );
  };

  const handleConfirmCats = () => {
    if (selectedCats.length === 0) {
      toast({ title: "Select categories", description: "You must select at least one category.", variant: "destructive" });
      return;
    }
    confirmCats.mutate(
      { runId: runId!, data: { confirmedCategoryIds: selectedCats, feedback: feedback || undefined } as any },
      {
        onSuccess: () => {
          toast({ title: "Categories confirmed" });
          invalidateRun();
          // Align with Streamlit: auto-continue after category gate.
          continueAfterCategory({ toastTitle: "Continuing to clarification…" });
        },
      },
    );
  };

  const handleSubmitClarification = () => {
    const formatted = Object.entries(answers).map(([id, ans]) => ({
      questionId: id,
      answer: ans || null,
      skipped: !ans,
    }));
    submitClarification.mutate(
      { runId: runId!, data: { answers: formatted } },
      { onSuccess: () => { toast({ title: "Answers submitted" }); invalidateRun(); } },
    );
  };

  const handleSkipQuestion = (qid: string) => {
    setAnswers(prev => ({ ...prev, [qid]: "" }));
    submitClarification.mutate(
      { runId: runId!, data: { answers: [{ questionId: qid, skipped: true }] } },
      { onSuccess: () => { toast({ title: "Question skipped" }); invalidateRun(); } },
    );
  };

  const handleTriggerSolve = () => {
    triggerSolve.mutate(
      { runId: runId! },
      { onSuccess: () => { toast({ title: "Solve loop started" }); invalidateRun(); } },
    );
  };

  const isContinuing = continuingAfterCategory || triggerSolve.isPending;

  // Step progress
  const steps = ["A0", "Clarify", "Solve", "Workbook", "Deliver"];
  let currentStep = 0;
  const s = run.status;
  if (s === RunStatus.awaiting_category_confirmation) currentStep = 0;
  else if (s === RunStatus.awaiting_clarification || s === RunStatus.awaiting_rawdata_clarification || s === RunStatus.category_confirmed) currentStep = 1;
  else if (s === RunStatus.clarification_completed || s === RunStatus.solve_running) currentStep = 2;
  else if (s === RunStatus.data_workbook_generated) currentStep = 3;
  else if (s.includes("generated")) currentStep = 4;

  // Separate clarification question types
  const businessQuestions = clarifyingQuestions.filter((q: any) => q.questionCategory !== "rawdata" && !q.skipped && !q.answer);
  const rawdataQuestions = clarifyingQuestions.filter((q: any) => q.questionCategory === "rawdata" && !q.skipped && !q.answer);
  const answeredQuestions = clarifyingQuestions.filter((q: any) => q.skipped || q.answer);

  return (
    <div className="flex flex-col h-full bg-background text-foreground">
      {/* Sticky header */}
      <div className="border-b border-border bg-card p-4 shrink-0 flex items-center justify-between z-10 sticky top-0">
        <div className="flex flex-col gap-1">
          <div className="flex items-center gap-3">
            <span className="font-mono text-sm text-muted-foreground">{run.caseId}</span>
            <StatusBadge status={run.status} />
            {gaps && (gaps as any[]).length > 0 && (
              <Badge variant="destructive" className="ml-2 bg-destructive/20 text-destructive-foreground border border-destructive/50">
                {(gaps as any[]).length} Gaps
              </Badge>
            )}
          </div>
          <h2 className="text-lg font-semibold truncate max-w-2xl">{run.requirementText}</h2>
          <div className="flex gap-4 text-xs text-muted-foreground">
            <span>Mode: <span className="font-mono">{run.planningMode}</span></span>
            {(run as any).manifestPath && <span className="font-mono truncate max-w-md">{(run as any).manifestPath}</span>}
          </div>
        </div>

        <div className="flex items-center gap-2">
          {steps.map((step, i) => (
            <React.Fragment key={step}>
              <div className={`flex flex-col items-center gap-1 ${i <= currentStep ? "text-primary" : "text-muted-foreground"}`}>
                <div className={`w-8 h-8 rounded-full flex items-center justify-center border-2 text-xs font-bold transition-colors ${
                  i < currentStep ? "bg-primary border-primary text-primary-foreground" :
                  i === currentStep ? "border-primary text-primary bg-primary/10" :
                  "border-muted bg-transparent"
                }`}>
                  {i < currentStep ? <CheckCircle2 className="w-5 h-5" /> : i + 1}
                </div>
                <span className="text-[10px] font-medium uppercase tracking-wider">{step}</span>
              </div>
              {i < steps.length - 1 && (
                <div className={`w-8 h-[2px] mt-[-16px] ${i < currentStep ? "bg-primary" : "bg-muted"}`} />
              )}
            </React.Fragment>
          ))}
        </div>
      </div>

      <div className="p-8 max-w-5xl mx-auto w-full space-y-8 pb-20">

        {/* Gate A0: Category Confirmation */}
        {run.status === RunStatus.awaiting_category_confirmation && understanding && (
          <Card className="border-primary/50 shadow-md">
            <CardHeader className="bg-primary/5 border-b border-primary/10">
              <CardTitle className="flex items-center gap-2">Gate A0: Category Confirmation</CardTitle>
              <CardDescription>Confirm the target categories to proceed.</CardDescription>
            </CardHeader>
            <CardContent className="pt-6 space-y-6">
              <div className="grid grid-cols-2 gap-4 text-sm bg-muted/30 p-4 rounded-md border border-border">
                <div><span className="text-muted-foreground block mb-1">Site</span><span className="font-medium">{understanding.site}</span></div>
                <div><span className="text-muted-foreground block mb-1">Intent</span><span className="font-medium">{understanding.intent}</span></div>
                <div><span className="text-muted-foreground block mb-1">Time Range</span><span className="font-medium">{understanding.timeRange}</span></div>
              </div>

              <div>
                <h4 className="font-medium mb-3">Candidate Categories</h4>
                <div className="space-y-3">
                  {understanding.categories?.map((cat: any) => (
                    <div key={cat.id} className={`flex items-start space-x-3 p-3 rounded-md border transition-colors ${selectedCats.includes(cat.id) ? "border-primary bg-primary/5" : "border-border bg-card"}`}>
                      <Checkbox
                        id={cat.id}
                        checked={selectedCats.includes(cat.id)}
                        onCheckedChange={c => setSelectedCats(prev => c ? [...prev, cat.id] : prev.filter(id => id !== cat.id))}
                      />
                      <div className="grid gap-1.5 leading-none">
                        <Label htmlFor={cat.id} className="font-medium text-base cursor-pointer">{cat.name}</Label>
                        <p className="text-sm text-muted-foreground">
                          {cat.level && `Level: ${cat.level} • `}
                          {formatConfidence(cat.confidence) != null && `Confidence: ${formatConfidence(cat.confidence)}`}
                          {cat.positioning && ` • ${cat.positioning}`}
                        </p>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              <div className="space-y-2">
                <Label className="text-sm">Feedback (optional)</Label>
                <Input
                  placeholder="e.g. Should be Pet Accessories > Bowls & Feeders, not Pet Food."
                  value={feedback}
                  onChange={e => setFeedback(e.target.value)}
                />
              </div>
            </CardContent>
            <CardFooter className="justify-end border-t border-border pt-4 pb-4 bg-muted/10">
              <Button onClick={handleConfirmCats} disabled={confirmCats.isPending}>
                {confirmCats.isPending ? "Confirming..." : "Confirm & Proceed"}
              </Button>
            </CardFooter>
          </Card>
        )}

        {/* Understanding summary (shown after A0) */}
        {run.status !== RunStatus.awaiting_category_confirmation && understanding && (
          <UnderstandingSummary understanding={understanding} />
        )}

        {/* category_confirmed: continue into clarification (Streamlit dual-path) */}
        {run.status === RunStatus.category_confirmed && (
          <Card className="bg-primary/5 border-primary/20 text-center py-8">
            <CardContent className="space-y-4">
              <div className="w-16 h-16 mx-auto bg-primary/20 rounded-full flex items-center justify-center">
                {isContinuing ? (
                  <Loader2 className="w-8 h-8 text-primary animate-spin" />
                ) : (
                  <CheckCircle2 className="w-8 h-8 text-primary" />
                )}
              </div>
              <div>
                <h3 className="text-xl font-semibold mb-2">Categories Confirmed</h3>
                <p className="text-muted-foreground max-w-md mx-auto">
                  {isContinuing
                    ? "Pipeline is continuing toward clarification…"
                    : "Continue the pipeline to generate / enter clarification questions."}
                </p>
              </div>
              <Button
                size="lg"
                className="mt-4"
                onClick={() => continueAfterCategory()}
                disabled={isContinuing}
              >
                {isContinuing ? (
                  <>
                    <Loader2 className="w-4 h-4 mr-2 animate-spin" /> Continuing…
                  </>
                ) : (
                  <>
                    <Play className="w-4 h-4 mr-2" /> 继续进入澄清
                  </>
                )}
              </Button>
            </CardContent>
          </Card>
        )}

        {/* Clarification */}
        {(run.status === RunStatus.awaiting_clarification || run.status === RunStatus.awaiting_rawdata_clarification) && (
          <Card className="border-amber-500/50">
            <CardHeader className="bg-amber-500/5 border-b border-amber-500/10">
              <CardTitle className="flex items-center gap-2">
                <AlertCircle className="text-amber-500 h-5 w-5" />
                Awaiting Clarification
              </CardTitle>
              <CardDescription>
                {businessQuestions.length > 0 && `${businessQuestions.length} business questions`}
                {businessQuestions.length > 0 && rawdataQuestions.length > 0 && " + "}
                {rawdataQuestions.length > 0 && `${rawdataQuestions.length} data source questions`}
              </CardDescription>
            </CardHeader>
            <CardContent className="pt-6 space-y-6">
              {businessQuestions.length > 0 && (
                <div className="space-y-4">
                  <h4 className="font-medium text-sm uppercase tracking-wider text-muted-foreground">Business Clarification</h4>
                  {businessQuestions.map((q: any) => (
                    <div key={q.id} className="border border-border rounded-md p-4 space-y-2">
                      <Label className="text-base font-medium">{q.question}</Label>
                      {q.reason && <p className="text-sm text-muted-foreground">{q.reason}</p>}
                      {q.defaultAssumption && <p className="text-xs text-muted-foreground">Default: {q.defaultAssumption}</p>}
                      <div className="flex gap-2">
                        <Input
                          placeholder="Your answer..."
                          value={answers[q.id] || ""}
                          onChange={e => setAnswers(prev => ({ ...prev, [q.id]: e.target.value }))}
                          className="flex-1"
                        />
                        <Button variant="ghost" size="sm" onClick={() => handleSkipQuestion(q.id)}>
                          <SkipForward className="w-4 h-4 mr-1" /> Skip
                        </Button>
                      </div>
                    </div>
                  ))}
                </div>
              )}

              {rawdataQuestions.length > 0 && (
                <div className="space-y-4">
                  <h4 className="font-medium text-sm uppercase tracking-wider text-muted-foreground">
                    <FolderOpen className="w-4 h-4 inline mr-1" />
                    Data Source Path Required
                  </h4>
                  {rawdataQuestions.map((q: any) => (
                    <div key={q.id} className="border border-border rounded-md p-4 space-y-2 bg-amber-500/5">
                      <Label className="text-base font-medium">{q.question}</Label>
                      {q.reason && <p className="text-sm text-muted-foreground">{q.reason}</p>}
                      <Input
                        placeholder="e.g. C:\\data\\shop_sales.xlsx"
                        value={answers[q.id] || ""}
                        onChange={e => setAnswers(prev => ({ ...prev, [q.id]: e.target.value }))}
                      />
                      <div className="flex gap-2">
                        <Button variant="ghost" size="sm" onClick={() => handleSkipQuestion(q.id)}>
                          <SkipForward className="w-4 h-4 mr-1" /> Skip (use default)
                        </Button>
                      </div>
                    </div>
                  ))}
                </div>
              )}

              {answeredQuestions.length > 0 && (
                <div className="border-t border-border pt-4">
                  <h4 className="font-medium text-sm text-muted-foreground mb-2">Already Answered ({answeredQuestions.length})</h4>
                  {answeredQuestions.map((q: any) => (
                    <div key={q.id} className="text-sm text-muted-foreground py-1">
                      <span className="font-medium">{q.question}</span>:{" "}
                      {q.skipped ? <span className="italic">Skipped</span> : q.answer}
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
            <CardFooter className="justify-end border-t border-border pt-4 pb-4">
              <Button onClick={handleSubmitClarification} disabled={submitClarification.isPending}>
                Submit Answers
              </Button>
            </CardFooter>
          </Card>
        )}

        {/* Ready to solve */}
        {run.status === RunStatus.clarification_completed && (
          <Card className="bg-primary/5 border-primary/20 text-center py-8">
            <CardContent className="space-y-4">
              <div className="w-16 h-16 mx-auto bg-primary/20 rounded-full flex items-center justify-center">
                <CheckCircle2 className="w-8 h-8 text-primary" />
              </div>
              <div>
                <h3 className="text-xl font-semibold mb-2">Ready to Generate Plan & Workbook</h3>
                <p className="text-muted-foreground max-w-md mx-auto">
                  All requirements are clear. The AI will now generate the blueprint, execute queries, and build the Data Workbook.
                </p>
              </div>
              <Button size="lg" className="mt-4" onClick={handleTriggerSolve} disabled={triggerSolve.isPending}>
                <Play className="w-4 h-4 mr-2" /> Start Solve Loop
              </Button>
            </CardContent>
          </Card>
        )}

        {/* Solve running */}
        {run.status === RunStatus.solve_running && run.solveProgress && (
          <SolveProgressPanel
            phase={(run.solveProgress as any).phase || "blueprint"}
            completedPhases={(run.solveProgress as any).completedPhases || []}
            percentComplete={(run.solveProgress as any).percentComplete || 0}
            message={(run.solveProgress as any).message}
          />
        )}

        {/* Gaps */}
        {run.status === RunStatus.data_workbook_generated && gaps && (gaps as any[]).length > 0 && (
          <Card className="border-destructive/30">
            <CardHeader className="bg-destructive/5 border-b border-destructive/10 pb-4">
              <CardTitle className="text-destructive flex items-center gap-2 text-lg">
                <AlertCircle className="w-5 h-5" />
                Data Gaps Detected ({(gaps as any[]).length})
              </CardTitle>
              <CardDescription>These issues may affect report accuracy.</CardDescription>
            </CardHeader>
            <CardContent className="p-0">
              <div className="divide-y divide-border">
                {(gaps as any[]).map((gap: any) => (
                  <div key={gap.id} className="p-4 flex items-start gap-4">
                    <Badge variant={gap.severity === "high" ? "destructive" : gap.severity === "medium" ? "warning" : "secondary"} className="mt-0.5">
                      {gap.severity?.toUpperCase()}
                    </Badge>
                    <div className="flex-1 space-y-1">
                      <p className="font-medium leading-none">{gap.description}</p>
                      <div className="flex gap-4 text-xs text-muted-foreground">
                        <span>Type: <span className="font-mono">{gap.type}</span></span>
                        {gap.affectedModule && <span>Module: {gap.affectedModule}</span>}
                      </div>
                      {gap.suggestion && (
                        <p className="text-sm bg-muted p-2 rounded-md mt-2 inline-block">
                          <span className="font-semibold">Suggestion:</span> {gap.suggestion}
                        </p>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        )}

        {/* Blueprint + Workbook ready */}
        {run.status === RunStatus.data_workbook_generated && blueprint && (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <Card className="md:col-span-2">
              <CardHeader className="pb-4">
                <CardTitle className="text-lg">Report Blueprint</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-6">
                  {(blueprint as any).chapters?.map((ch: any, idx: number) => (
                    <div key={ch.id} className="relative pl-6 border-l border-border pb-2 last:pb-0">
                      <div className="absolute w-3 h-3 bg-primary rounded-full -left-[6.5px] top-1.5 ring-4 ring-background" />
                      <h4 className="font-semibold text-base mb-2">Chapter {idx + 1}: {ch.title}</h4>
                      <div className="flex flex-wrap gap-2 mb-2">
                        {ch.modules?.map((m: string) => <Badge key={m} variant="secondary" className="bg-secondary/50">{m}</Badge>)}
                      </div>
                      {ch.metrics && (
                        <div className="text-xs text-muted-foreground">Metrics: {ch.metrics.join(", ")}</div>
                      )}
                      {ch.scopeKind && (
                        <div className="text-xs text-muted-foreground">Scope: <span className="font-mono">{ch.scopeKind}</span></div>
                      )}
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>

            <Card className="bg-emerald-500/5 border-emerald-500/20">
              <CardHeader>
                <CardTitle className="flex items-center gap-2 text-emerald-600">
                  <FileSpreadsheet className="w-5 h-5" />
                  Data Workbook
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <p className="text-sm text-muted-foreground">Data tables have been successfully generated.</p>
                {run.deliverables?.workbook?.downloadUrl && (
                  <Button className="w-full gap-2 bg-emerald-600 text-white hover:bg-emerald-700" asChild>
                    <a href={run.deliverables.workbook.downloadUrl} download>
                      <Download className="w-4 h-4" /> Download .xlsx
                    </a>
                  </Button>
                )}
                <div className="pt-6 border-t border-border mt-6">
                  <p className="text-sm mb-3">Ready to create final deliverables?</p>
                  <Button variant="outline" className="w-full gap-2" asChild>
                    <Link href={`/runs/${run.id}/deliver`}>
                      Go to Deliverables Hub <ChevronRight className="w-4 h-4" />
                    </Link>
                  </Button>
                </div>
              </CardContent>
            </Card>
          </div>
        )}
      </div>
    </div>
  );
}
