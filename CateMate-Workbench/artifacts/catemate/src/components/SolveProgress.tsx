import React from "react";
import { Card, CardContent } from "@/components/ui/card";
import { CheckCircle2, Circle, Loader2 } from "lucide-react";

const PHASES = [
  { id: "blueprint", label: "Blueprint", description: "Generating analysis blueprint" },
  { id: "plan", label: "Plan", description: "Composing execution plan" },
  { id: "catalog", label: "Catalog", description: "Checking module catalog" },
  { id: "execute", label: "Execute", description: "Running data queries" },
  { id: "verify", label: "Verify", description: "Validating results" },
  { id: "done", label: "Done", description: "Workbook ready" },
];

interface SolveProgressProps {
  phase: string;
  completedPhases?: string[];
  percentComplete?: number;
  message?: string;
}

export function SolveProgressPanel({ phase, completedPhases = [], percentComplete = 0, message }: SolveProgressProps) {
  const currentIdx = PHASES.findIndex(p => p.id === phase);

  return (
    <Card>
      <CardContent className="py-8">
        <div className="flex flex-col items-center space-y-6">
          {phase !== "done" && (
            <Loader2 className="w-10 h-10 text-primary animate-spin" />
          )}
          <div className="text-center space-y-1">
            <h3 className="text-lg font-semibold">
              {phase === "done" ? "Data Workbook Generated" : "Generating Data Workbook..."}
            </h3>
            {message && <p className="text-sm text-muted-foreground">{message}</p>}
            <p className="text-sm font-mono text-muted-foreground">{percentComplete}% complete</p>
          </div>

          <div className="w-full max-w-lg">
            <div className="flex items-center justify-between">
              {PHASES.map((p, i) => {
                const isCompleted = completedPhases.includes(p.id) || i < currentIdx;
                const isCurrent = p.id === phase && phase !== "done";
                const isDone = p.id === "done" && phase === "done";

                return (
                  <React.Fragment key={p.id}>
                    <div className="flex flex-col items-center gap-1">
                      <div className={`w-8 h-8 rounded-full flex items-center justify-center border-2 transition-colors ${
                        isCompleted || isDone
                          ? "bg-primary border-primary text-primary-foreground"
                          : isCurrent
                          ? "border-primary text-primary bg-primary/10"
                          : "border-muted text-muted-foreground"
                      }`}>
                        {isCompleted || isDone ? (
                          <CheckCircle2 className="w-5 h-5" />
                        ) : isCurrent ? (
                          <Loader2 className="w-4 h-4 animate-spin" />
                        ) : (
                          <Circle className="w-4 h-4" />
                        )}
                      </div>
                      <span className="text-[10px] font-medium text-muted-foreground uppercase tracking-wider">
                        {p.label}
                      </span>
                    </div>
                    {i < PHASES.length - 1 && (
                      <div className={`flex-1 h-[2px] mx-1 mt-[-16px] ${
                        isCompleted ? "bg-primary" : "bg-muted"
                      }`} />
                    )}
                  </React.Fragment>
                );
              })}
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
