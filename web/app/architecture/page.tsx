import { Frame } from "@/components/Frame";

const DISCLAIMER =
  "Synthetic demonstration data only. CreditPulse does not make lending decisions and is not a credit bureau.";

const STEPS = [
  ["Land", "Seeded CSV for customers, accounts, loans, and customer events. Repayments come from a small local JSON API."],
  ["Bronze", "Each batch is kept as Parquet with a batch id, source name, and ingestion time."],
  ["Silver", "PySpark deduplicates on the business key. The newest source timestamp wins. Invalid rows go to quarantine."],
  ["Staging", "PostgreSQL upserts accepted rows. A rerun does not insert a second repayment."],
  ["Gold", "dbt builds the dimensions, the repayment fact, the loan snapshot, and the daily aggregate, then tests them."],
  ["Publish", "The watermark and the run audit commit together. The site reads the exported aggregates only."],
];

export default function ArchitecturePage() {
  return (
    <Frame disclaimer={DISCLAIMER}>
      <h1>How the local platform fits together</h1>
      <p className="lede">
        PostgreSQL is the local warehouse. Databricks is an optional later path and is not required
        to run this demo. The page you are reading never starts Spark.
      </p>
      <ol className="steps">
        {STEPS.map(([title, copy], index) => (
          <li key={title}>
            <span className="num">{index + 1}</span>
            <div>
              <h2>{title}</h2>
              <p>{copy}</p>
            </div>
          </li>
        ))}
      </ol>
    </Frame>
  );
}
