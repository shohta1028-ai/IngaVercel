// backend/app/api/template_library.py の型に対応するTS型定義

import type { FinancialCausalDAG } from "../types/dag";

export interface TemplateLibraryListItem {
  industry_id: string;
  industry_label: string;
  cached: boolean;
  summary?: string | null;
}

export interface TemplateLibraryEntry {
  industry_id: string;
  industry_label: string;
  summary: string;
  dag: FinancialCausalDAG;
}
