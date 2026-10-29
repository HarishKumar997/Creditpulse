import { readFileSync } from "fs";
import path from "path";

import type { Portfolio, PortfolioRow, Quality, Runs, Summary } from "./types";

const DISCLAIMER =
  "Synthetic demonstration data only. CreditPulse does not make lending decisions and is not a credit bureau.";

function readJson<T>(name: string): T | null {
  try {
    const raw = readFileSync(path.join(process.cwd(), "data", name), "utf8");
    return JSON.parse(raw) as T;
  } catch {
    return null;
  }
}

export function loadSummary(): Summary {
  return (
    readJson<Summary>("summary.json") ?? {
      schema_version: "1",
      disclaimer: DISCLAIMER,
      loans: 0,
      customers: 0,
      outstanding_balance_proxy: null,
      repayment_completion_rate: null,
      delinquency_rate: null,
      accepted: 0,
      rejected: 0,
      duplicates: 0,
      buckets: [],
      products: [],
    }
  );
}

export function loadQuality(): Quality {
  return (
    readJson<Quality>("quality.json") ?? {
      schema_version: "1",
      disclaimer: DISCLAIMER,
      rejected_by_reason: [],
      reconciliation: { status: "missing", due_amount: null, paid_amount: null, rows: 0 },
    }
  );
}

export function loadRuns(): Runs {
  return readJson<Runs>("runs.json") ?? { schema_version: "1", disclaimer: DISCLAIMER, runs: [] };
}

export function loadPortfolio(): Portfolio {
  return (
    readJson<Portfolio>("portfolio_daily.json") ?? {
      schema_version: "1",
      disclaimer: DISCLAIMER,
      rows: [],
    }
  );
}

export function isIsoDate(value: string): boolean {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(value)) return false;
  const [year, month, day] = value.split("-").map(Number);
  const parsed = new Date(Date.UTC(year, month - 1, day));
  return (
    parsed.getUTCFullYear() === year &&
    parsed.getUTCMonth() === month - 1 &&
    parsed.getUTCDate() === day
  );
}

export function filterPortfolio(
  rows: PortfolioRow[],
  from: string | null,
  to: string | null,
): { rows: PortfolioRow[]; error: string | null } {
  if (!from || !to) {
    return { rows: [], error: "from and to are required (YYYY-MM-DD)." };
  }
  if (!isIsoDate(from)) return { rows: [], error: "from must be YYYY-MM-DD." };
  if (!isIsoDate(to)) return { rows: [], error: "to must be YYYY-MM-DD." };
  if (from > to) return { rows: [], error: "from must be on or before to." };
  return {
    rows: rows.filter((row) => row.report_date >= from && row.report_date <= to),
    error: null,
  };
}

export function money(value: string | null | undefined): string {
  if (value == null || value === "") return "—";
  const amount = Number(value);
  if (Number.isNaN(amount)) return "—";
  return new Intl.NumberFormat("en-US", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(amount);
}

export function percent(value: string | null | undefined): string {
  if (value == null || value === "") return "n/a";
  const rate = Number(value);
  if (Number.isNaN(rate)) return "n/a";
  return `${(rate * 100).toFixed(1)}%`;
}
