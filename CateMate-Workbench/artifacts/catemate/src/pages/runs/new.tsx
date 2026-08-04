import React from "react";
import { useCreateRun, PlanningMode } from "@workspace/api-client-react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription, CardFooter } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import { useLocation } from "wouter";
import { Play, Loader2 } from "lucide-react";
import { useToast } from "@/hooks/use-toast";
import { Label } from "@/components/ui/label";

export default function NewAnalysis() {
  const [, setLocation] = useLocation();
  const { toast } = useToast();
  const createRun = useCreateRun();

  const [requirementText, setRequirementText] = React.useState("");
  const [planningMode, setPlanningMode] = React.useState<string>("v2_solve_loop");

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (requirementText.length < 10) {
      toast({ title: "Requirement too short", description: "Please provide more detail.", variant: "destructive" });
      return;
    }

    createRun.mutate(
      { data: { requirementText, planningMode: planningMode as PlanningMode } },
      {
        onSuccess: (data: any) => {
          if (data?.taskId) {
            toast({ title: "Pipeline started", description: "Check Run History for progress." });
            setLocation("/runs");
          } else if (data?.id) {
            toast({ title: "Analysis started", description: `Case ${data.caseId} created.` });
            setLocation(`/runs/${data.id}`);
          }
        },
        onError: () => {
          toast({ title: "Pipeline submitted", description: "Check Run History for results." });
          setLocation("/runs");
        },
      },
    );
  };

  const samplePrompts = [
    "VN Pet Healthcare 类目的月度趋势分析，包括 GMV、订单量、客单价。",
    "分析 Amazon US Wireless Earbuds 品类 Top 5 品牌市场份额。",
    "Give me a category overview of skincare products, focusing on organic ingredients.",
  ];

  return (
    <div className="p-8 max-w-3xl mx-auto space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">New Analysis</h1>
        <p className="text-muted-foreground mt-1">Start a new category analysis pipeline.</p>
      </div>

      <form onSubmit={handleSubmit}>
        <Card className="bg-card">
          <CardHeader>
            <CardTitle>Requirement Definition</CardTitle>
            <CardDescription>Describe what you want to analyze. Supports Chinese and English.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">
            <div className="space-y-2">
              <Label htmlFor="requirement">Analysis Request</Label>
              <Textarea
                id="requirement"
                value={requirementText}
                onChange={e => setRequirementText(e.target.value)}
                placeholder="e.g. 分析 VN Pet Healthcare 类目月度趋势..."
                className="min-h-[160px] text-base resize-y"
              />
              <div className="flex gap-2 flex-wrap pt-2">
                {samplePrompts.map((prompt, i) => (
                  <Badge key={i} variant="outline" className="cursor-pointer hover:bg-muted" onClick={() => setRequirementText(prompt)}>
                    {prompt.substring(0, 35)}...
                  </Badge>
                ))}
              </div>
            </div>

            <div className="space-y-2">
              <Label>Planning Mode</Label>
              <select
                className="flex h-10 w-full md:w-1/2 rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                value={planningMode}
                onChange={e => setPlanningMode(e.target.value)}
              >
                <option value="v2_solve_loop">V2 Solve Loop (Default)</option>
                <option value="module_selection">Module Selection (V1)</option>
                <option value="ai_direct">AI Direct</option>
              </select>
            </div>
          </CardContent>
          <CardFooter className="bg-muted/30 pt-6 border-t border-border flex justify-end">
            <Button type="submit" disabled={createRun.isPending} className="gap-2" size="lg">
              {createRun.isPending ? <Loader2 className="w-4 h-4 animate-spin" /> : <Play className="w-4 h-4" />}
              {createRun.isPending ? "Starting..." : "Start Analysis Pipeline"}
            </Button>
          </CardFooter>
        </Card>
      </form>
    </div>
  );
}
