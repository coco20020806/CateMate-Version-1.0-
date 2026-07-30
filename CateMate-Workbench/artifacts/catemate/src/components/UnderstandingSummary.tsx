import React from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible";
import { ChevronDown, AlertTriangle, Lightbulb, Tag } from "lucide-react";

function formatConfidence(confidence: unknown): string | null {
  if (confidence == null || confidence === "") return null;
  if (typeof confidence === "number" && Number.isFinite(confidence)) {
    return `${Math.round(confidence * 100)}%`;
  }
  return String(confidence);
}

interface UnderstandingSummaryProps {
  understanding: {
    site?: string;
    intent?: string;
    timeRange?: string;
    categories?: Array<{ id: string; name: string; level?: string; confidence?: number | string; selected?: boolean }>;
    assumptions?: string[];
    risks?: string[];
    conceptPack?: string[];
  };
}

export function UnderstandingSummary({ understanding }: UnderstandingSummaryProps) {
  const confirmedCats = understanding.categories?.filter(c => c.selected) ?? [];
  const allCats = understanding.categories ?? [];

  return (
    <Card>
      <CardHeader className="py-4 border-b border-border">
        <CardTitle className="text-base font-medium">Understanding Summary</CardTitle>
      </CardHeader>
      <CardContent className="py-4 space-y-4">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
          <div>
            <span className="text-muted-foreground text-xs uppercase block mb-1">Site</span>
            <span className="font-medium">{understanding.site || "—"}</span>
          </div>
          <div>
            <span className="text-muted-foreground text-xs uppercase block mb-1">Intent</span>
            <span className="font-medium">{understanding.intent || "—"}</span>
          </div>
          <div>
            <span className="text-muted-foreground text-xs uppercase block mb-1">Time Range</span>
            <span className="font-medium">{understanding.timeRange || "—"}</span>
          </div>
          <div>
            <span className="text-muted-foreground text-xs uppercase block mb-1">Categories</span>
            <span className="font-medium">{confirmedCats.length > 0 ? confirmedCats.length : allCats.length}</span>
          </div>
        </div>

        {(confirmedCats.length > 0 || allCats.length > 0) && (
          <div>
            <span className="text-muted-foreground text-xs uppercase block mb-2">Confirmed Categories</span>
            <div className="flex flex-wrap gap-2">
              {(confirmedCats.length > 0 ? confirmedCats : allCats).map(c => {
                const conf = formatConfidence(c.confidence);
                return (
                  <Badge key={c.id} variant="secondary">
                    {c.name}
                    {conf && <span className="ml-1 opacity-60">({conf})</span>}
                  </Badge>
                );
              })}
            </div>
          </div>
        )}

        {understanding.assumptions && understanding.assumptions.length > 0 && (
          <Collapsible>
            <CollapsibleTrigger className="flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground transition-colors">
              <Lightbulb className="w-4 h-4" />
              Assumptions ({understanding.assumptions.length})
              <ChevronDown className="w-3 h-3" />
            </CollapsibleTrigger>
            <CollapsibleContent className="mt-2 pl-6 space-y-1">
              {understanding.assumptions.map((a, i) => (
                <p key={i} className="text-sm text-muted-foreground">• {a}</p>
              ))}
            </CollapsibleContent>
          </Collapsible>
        )}

        {understanding.risks && understanding.risks.length > 0 && (
          <Collapsible>
            <CollapsibleTrigger className="flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground transition-colors">
              <AlertTriangle className="w-4 h-4" />
              Risks / Uncertainties ({understanding.risks.length})
              <ChevronDown className="w-3 h-3" />
            </CollapsibleTrigger>
            <CollapsibleContent className="mt-2 pl-6 space-y-1">
              {understanding.risks.map((r, i) => (
                <p key={i} className="text-sm text-muted-foreground">• {r}</p>
              ))}
            </CollapsibleContent>
          </Collapsible>
        )}

        {understanding.conceptPack && understanding.conceptPack.length > 0 && (
          <Collapsible>
            <CollapsibleTrigger className="flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground transition-colors">
              <Tag className="w-4 h-4" />
              Concept Pack ({understanding.conceptPack.length})
              <ChevronDown className="w-3 h-3" />
            </CollapsibleTrigger>
            <CollapsibleContent className="mt-2">
              <div className="flex flex-wrap gap-1.5 pl-6">
                {understanding.conceptPack.map((c, i) => (
                  <Badge key={i} variant="outline" className="bg-primary/5 text-xs">{c}</Badge>
                ))}
              </div>
            </CollapsibleContent>
          </Collapsible>
        )}
      </CardContent>
    </Card>
  );
}
