export type Summary = {
  schema_version: string;
  disclaimer: string;
  as_of_date?: string | null;
  generated_at?: string | null;
  batch_id?: string | null;
  loans: number;
  customers: number;
  outstanding_balance_proxy: string | null;
  repayment_completion_rate: string | null;
  delinquency_rate: string | null;
  accepted: number;
  rejected: number;
  duplicates: number;
  buckets: { id: string; label: string; loans: number }[];
  products: {
    product_code: string;
    loans: number;
    outstanding_balance_proxy: string | null;
    delinquent_loans: number;
  }[];
};

export type Quality = {
  schema_version: string;
  disclaimer: string;
  batch_id?: string | null;
  generated_at?: string | null;
  rejected_by_reason: { reason: string; rows: number }[];
  reconciliation: {
    status: string;
    due_amount: string | null;
    paid_amount: string | null;
    rows: number;
  };
};

export type RunRow = {
  run_id: string;
  batch_id: string;
  status: string;
  started_at: string;
  finished_at: string | null;
  rows_read: number;
  rows_accepted: number;
  rows_rejected: number;
  rows_duplicate: number;
  error_summary: string | null;
  step: string | null;
};

export type Runs = {
  schema_version: string;
  disclaimer: string;
  runs: RunRow[];
};

export type PortfolioRow = {
  report_date: string;
  product_code: string;
  repayment_count: number;
  loan_count: number;
  due_amount: string | null;
  paid_amount: string | null;
  repayment_completion_rate: string | null;
  delinquent_event_count: number;
};

export type Portfolio = {
  schema_version: string;
  disclaimer: string;
  rows: PortfolioRow[];
};
