import React, { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription, CardFooter } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible";
import { ChevronDown, Eye, EyeOff, CheckCircle2 } from "lucide-react";

interface VisualSpecSection {
  id: string;
  title: string;
  visible: boolean;
  chartType?: string;
  notes?: string;
  sub_question?: string;
  narrative?: string;
  status?: string;
}

interface VisualSpecEditorProps {
  sections: VisualSpecSection[];
  specStatus: string;
  dataGaps?: string[];
  onConfirm: (sections: VisualSpecSection[]) => void;
  isConfirming?: boolean;
}

export function VisualSpecEditor({ sections: initialSections, specStatus, dataGaps, onConfirm, isConfirming }: VisualSpecEditorProps) {
  const [sections, setSections] = useState(initialSections);
  const isConfirmed = specStatus === "confirmed";

  const toggleVisibility = (id: string) => {
    setSections(prev => prev.map(s => s.id === id ? { ...s, visible: !s.visible } : s));
  };

  const updateTitle = (id: string, title: string) => {
    setSections(prev => prev.map(s => s.id === id ? { ...s, title } : s));
  };

  return (
    <Card>
      <CardHeader className="border-b border-border">
        <div className="flex items-center justify-between">
          <div>
            <CardTitle className="text-lg">Gate C: Visual Report Spec</CardTitle>
            <CardDescription>Review and confirm the report structure before rendering.</CardDescription>
          </div>
          <Badge variant={isConfirmed ? "success" : "warning"}>
            {isConfirmed ? "Confirmed" : "Draft"}
          </Badge>
        </div>
      </CardHeader>
      <CardContent className="pt-4 space-y-3">
        {sections.map((section, idx) => (
          <Collapsible key={section.id} defaultOpen={section.visible}>
            <div className="border border-border rounded-md">
              <CollapsibleTrigger className="w-full flex items-center justify-between p-3 hover:bg-muted/50 transition-colors">
                <div className="flex items-center gap-3">
                  <span className="text-sm font-mono text-muted-foreground w-6">{idx + 1}</span>
                  {section.visible ? (
                    <Eye className="w-4 h-4 text-primary" />
                  ) : (
                    <EyeOff className="w-4 h-4 text-muted-foreground" />
                  )}
                  <span className="font-medium text-sm">{section.title}</span>
                  {section.chartType && (
                    <Badge variant="outline" className="text-xs">{section.chartType}</Badge>
                  )}
                </div>
                <ChevronDown className="w-4 h-4 text-muted-foreground" />
              </CollapsibleTrigger>
              <CollapsibleContent className="px-3 pb-3 pt-1 border-t border-border space-y-3">
                <div className="flex items-center gap-4">
                  <div className="flex items-center gap-2">
                    <Switch
                      checked={section.visible}
                      onCheckedChange={() => toggleVisibility(section.id)}
                      disabled={isConfirmed}
                    />
                    <Label className="text-sm">Visible</Label>
                  </div>
                </div>
                <div className="space-y-1">
                  <Label className="text-xs">Title</Label>
                  <Input
                    value={section.title}
                    onChange={e => updateTitle(section.id, e.target.value)}
                    disabled={isConfirmed}
                    className="h-8 text-sm"
                  />
                </div>
                {section.notes && (
                  <p className="text-xs text-muted-foreground">{section.notes}</p>
                )}
              </CollapsibleContent>
            </div>
          </Collapsible>
        ))}

        {dataGaps && dataGaps.length > 0 && (
          <div className="pt-4 border-t border-border">
            <h4 className="text-sm font-medium mb-2">Data Gaps</h4>
            {dataGaps.map((gap, i) => (
              <p key={i} className="text-sm text-muted-foreground">• {gap}</p>
            ))}
          </div>
        )}
      </CardContent>
      {!isConfirmed && (
        <CardFooter className="border-t border-border pt-4 justify-end">
          <Button
            onClick={() => onConfirm(sections)}
            disabled={isConfirming}
            className="gap-2"
          >
            <CheckCircle2 className="w-4 h-4" />
            {isConfirming ? "Confirming..." : "Confirm Spec"}
          </Button>
        </CardFooter>
      )}
    </Card>
  );
}
