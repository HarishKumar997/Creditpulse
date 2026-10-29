import { Frame } from "@/components/Frame";
import { loadSummary, money, percent } from "@/lib/data";

export default function HomePage() {
  const summary = loadSummary();
  const maxBucket = Math.max(1, ...summary.buckets.map((bucket) => bucket.loans));
  return (
    <Frame disclaimer={summary.disclaimer}>
      <h1>Portfolio snapshot</h1>
      <p className="lede">
        Aggregates as of {summary.as_of_date ?? "the latest batch"}. Amounts are synthetic units.
        Delinquency is calculated from unpaid events, not from the source loan status.
      </p>
      <section className="grid" aria-label="Portfolio totals">
        <article className="card">
          <span>Outstanding proxy</span>
          <strong>{money(summary.outstanding_balance_proxy)}</strong>
        </article>
        <article className="card">
          <span>Repayment completion</span>
          <strong>{percent(summary.repayment_completion_rate)}</strong>
        </article>
        <article className="card">
          <span>Delinquency rate</span>
          <strong>{percent(summary.delinquency_rate)}</strong>
        </article>
        <article className="card">
          <span>Rows accepted / rejected / extra copies</span>
          <strong>
            {summary.accepted} / {summary.rejected} / {summary.duplicates}
          </strong>
        </article>
      </section>
      <section className="panel">
        <h2>Delinquency buckets</h2>
        <p className="lede">{summary.loans} loans, {summary.customers} current customers.</p>
        {summary.buckets.length === 0 ? (
          <p>No snapshot yet. Run the local pipeline, then refresh.</p>
        ) : (
          <div className="bars">
            {summary.buckets.map((bucket) => (
              <div className="bar-row" key={bucket.id}>
                <span>{bucket.label}</span>
                <div className="track" aria-hidden="true">
                  <div className="fill" style={{ width: `${(bucket.loans / maxBucket) * 100}%` }} />
                </div>
                <strong>{bucket.loans}</strong>
              </div>
            ))}
          </div>
        )}
        <table>
          <caption>Loans by product</caption>
          <thead>
            <tr>
              <th scope="col">Product</th>
              <th scope="col">Loans</th>
              <th scope="col">Outstanding proxy</th>
              <th scope="col">Delinquent loans</th>
            </tr>
          </thead>
          <tbody>
            {summary.products.map((product) => (
              <tr key={product.product_code}>
                <td>{product.product_code}</td>
                <td>{product.loans}</td>
                <td>{money(product.outstanding_balance_proxy)}</td>
                <td>{product.delinquent_loans}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
    </Frame>
  );
}
