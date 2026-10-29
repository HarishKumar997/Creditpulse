import { Frame } from "@/components/Frame";
import { filterPortfolio, loadPortfolio, money, percent } from "@/lib/data";

export default async function PortfolioPage({
  searchParams,
}: {
  searchParams: Promise<{ from?: string; to?: string }>;
}) {
  const params = await searchParams;
  const portfolio = loadPortfolio();
  const dates = portfolio.rows.map((row) => row.report_date).sort();
  const from = params.from ?? dates[0] ?? "";
  const to = params.to ?? dates[dates.length - 1] ?? "";
  const filtered =
    params.from || params.to || dates.length
      ? filterPortfolio(portfolio.rows, from || null, to || null)
      : { rows: [], error: "No daily aggregates have been exported yet." };

  return (
    <Frame disclaimer={portfolio.disclaimer}>
      <h1>Daily activity</h1>
      <p className="lede">
        One row per event date and product. This is payment flow, not the delinquency stock.
      </p>
      <form method="get" action="/portfolio">
        <label htmlFor="from">
          From
          <input id="from" name="from" type="date" defaultValue={from} required />
        </label>
        <label htmlFor="to">
          To
          <input id="to" name="to" type="date" defaultValue={to} required />
        </label>
        <button type="submit">Apply</button>
      </form>
      {filtered.error ? (
        <p className="alert" role="alert">
          {filtered.error}
        </p>
      ) : (
        <div className="panel">
          <table>
            <caption>Synthetic repayment activity</caption>
            <thead>
              <tr>
                <th scope="col">Date</th>
                <th scope="col">Product</th>
                <th scope="col">Repayments</th>
                <th scope="col">Due</th>
                <th scope="col">Paid</th>
                <th scope="col">Completion</th>
                <th scope="col">Unpaid events</th>
              </tr>
            </thead>
            <tbody>
              {filtered.rows.map((row) => (
                <tr key={`${row.report_date}-${row.product_code}`}>
                  <td>{row.report_date}</td>
                  <td>{row.product_code}</td>
                  <td>{row.repayment_count}</td>
                  <td>{money(row.due_amount)}</td>
                  <td>{money(row.paid_amount)}</td>
                  <td>{percent(row.repayment_completion_rate)}</td>
                  <td>{row.delinquent_event_count}</td>
                </tr>
              ))}
            </tbody>
          </table>
          {filtered.rows.length === 0 ? <p>No rows in this range.</p> : null}
        </div>
      )}
    </Frame>
  );
}
