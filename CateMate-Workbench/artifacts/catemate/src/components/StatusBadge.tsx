import React from "react";
import { Badge } from "@/components/ui/badge";
import { RunStatus } from "@workspace/api-client-react";

export function StatusBadge({ status }: { status: string }) {
  let variant: "default" | "secondary" | "destructive" | "outline" | "success" | "warning" | "info" = "secondary";
  let label = status.replace(/_/g, " ").replace(/\b\w/g, l => l.toUpperCase());

  switch (status) {
    case RunStatus.awaiting_category_confirmation:
    case RunStatus.awaiting_clarification:
    case RunStatus.awaiting_rawdata_clarification:
      variant = "warning";
      break;
    case RunStatus.category_confirmed:
    case RunStatus.clarification_completed:
      variant = "info";
      break;
    case RunStatus.solve_running:
      variant = "info";
      break;
    case RunStatus.data_workbook_generated:
    case RunStatus.brief_generated:
    case RunStatus.visual_spec_generated:
    case RunStatus.html_report_generated:
    case RunStatus.print_report_generated:
      variant = "success";
      break;
    case RunStatus.failed:
      variant = "destructive";
      break;
    default:
      variant = "secondary";
  }

  return <Badge variant={variant}>{label}</Badge>;
}
