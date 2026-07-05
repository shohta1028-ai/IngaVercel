// backend/app/ingestion/edinet_client.py の EdinetDocumentSummary に対応するTS型定義

export interface EdinetDocumentSummary {
  doc_id: string;
  filer_name: string;
  sec_code?: string | null;
  doc_description?: string | null;
  period_end?: string | null;
  submit_date_time?: string | null;
}
