// backend/app/ingestion/models.py の IRDataPoint に対応するTS型定義

export type IRDataPointKind = "financial" | "nonfinancial";

export interface IRDataSource {
  document_name: string;
  excerpt?: string | null;
}

export interface IRDataPoint {
  label: string;
  kind: IRDataPointKind;
  value?: number | null;
  unit?: string | null;
  period?: string | null;
  source: IRDataSource;
}
