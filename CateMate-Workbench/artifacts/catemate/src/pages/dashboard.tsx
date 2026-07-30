import React from "react";
import { useGetRunStats, RunStatus } from "@workspace/api-client-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { StatusBadge } from "@/components/StatusBadge";
import { Link } from "wouter";
import { Button } from "@/components/ui/button";
import { Clock, ArrowRight } from "lucide-react";

export default function Dashboard() {
  const { data: stats, isLoading } = useGetRunStats();

  if (isLoading) {
    return <div className="p-8 text-muted-foreground animate-pulse">Loading dashboard...</div>;
  }

  const total = (stats as any)?.total ?? 0;
  const byStatus = (stats as any)?.byStatus ?? [];
  const recentRuns = (stats as any)?.recentRuns ?? [];

  return (
    <div className="p-8 max-w-6xl mx-auto space-y-8">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Dashboard</h1>
          <p className="text-muted-foreground mt-1">Overview of your category analysis pipeline.</p>
        </div>
        <Button asChild>
          <Link href="/runs/new">New Analysis</Link>
        </Button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card className="bg-card">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">Total Runs</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold">{total}</div>
          </CardContent>
        </Card>

        {byStatus.slice(0, 3).map((s: any) => (
          <Card key={s.status} className="bg-card">
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">
                {s.status.replace(/_/g, " ")}
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-3xl font-bold flex items-center gap-3">
                {s.count}
                <StatusBadge status={s.status} />
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {recentRuns.length > 0 && (
        <div className="space-y-4">
          <h2 className="text-xl font-semibold flex items-center gap-2">
            <Clock className="w-5 h-5 text-muted-foreground" />
            Recent Active Runs
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {recentRuns.slice(0, 3).map((run: any) => (
              <Card key={run.id} className="flex flex-col hover:shadow-md transition-all border-l-4 border-l-primary">
                <CardHeader className="pb-3">
                  <div className="flex justify-between items-start mb-2">
                    <div className="text-xs font-mono text-muted-foreground">{run.caseId}</div>
                    <StatusBadge status={run.status} />
                  </div>
                  <CardTitle className="text-lg line-clamp-2 leading-tight">
                    {run.requirementText}
                  </CardTitle>
                </CardHeader>
                <CardContent className="mt-auto pt-0 pb-4">
                  <Button variant="ghost" className="w-full justify-between group" asChild>
                    <Link href={`/runs/${run.id}`}>
                      Continue Run
                      <ArrowRight className="w-4 h-4 opacity-50 group-hover:opacity-100 group-hover:translate-x-1 transition-all" />
                    </Link>
                  </Button>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      )}

      {total === 0 && (
        <Card className="text-center py-12">
          <CardContent className="space-y-4">
            <p className="text-muted-foreground">No pipeline runs yet. Start your first analysis!</p>
            <Button asChild>
              <Link href="/runs/new">New Analysis</Link>
            </Button>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
