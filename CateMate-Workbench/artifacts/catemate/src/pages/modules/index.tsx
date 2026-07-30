import React from "react";
import { useListModules } from "@workspace/api-client-react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { BoxSelect } from "lucide-react";

export default function Modules() {
  const { data: modules, isLoading } = useListModules();

  return (
    <div className="p-8 max-w-6xl mx-auto space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Module Catalog</h1>
        <p className="text-muted-foreground mt-1">Analytical building blocks used by the planner.</p>
      </div>

      {isLoading ? (
        <div className="text-muted-foreground animate-pulse">Loading modules...</div>
      ) : !modules || (modules as any[]).length === 0 ? (
        <Card className="text-center py-12">
          <CardContent className="text-muted-foreground">No modules found.</CardContent>
        </Card>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {(modules as any[]).map((mod: any) => (
            <Card key={mod.id} className="flex flex-col">
              <CardHeader className="pb-3">
                <div className="flex justify-between items-start mb-2">
                  <BoxSelect className="w-5 h-5 text-primary" />
                  <Badge variant={mod.status === "active" ? "success" : "secondary"}>{mod.status}</Badge>
                </div>
                <CardTitle className="text-lg">{mod.name}</CardTitle>
                <CardDescription className="line-clamp-2">{mod.description}</CardDescription>
              </CardHeader>
              <CardContent className="mt-auto space-y-4 pt-0">
                <div>
                  <div className="text-xs font-semibold text-muted-foreground mb-1 uppercase tracking-wider">Metrics</div>
                  <div className="flex flex-wrap gap-1">
                    {mod.metrics?.map((m: string) => (
                      <Badge key={m} variant="outline" className="bg-background">{m}</Badge>
                    ))}
                  </div>
                </div>
                <div>
                  <div className="text-xs font-semibold text-muted-foreground mb-1 uppercase tracking-wider">Output Tables</div>
                  <div className="text-xs font-mono text-primary/80">{mod.outputTables?.join(", ")}</div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
