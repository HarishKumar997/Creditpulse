import { Frame } from "@/components/Frame";
import { loadQuality, money } from "@/lib/data";

export default function QualityPage() {
  const quality = loadQuality();
  const passed = quality.reconciliation.status === "pass";
  return (
    <Frame disclaimer={quality.disclaimer}>
      <h1>Data quality</h1>
      <p className="lede">
        Batch {quality.batch_id ?? "not published"}. Rejected rows stay in quarantine with a reason.
        They are not dropped silently.
      </p>
      <section className="panel">
        <h2>Reconciliation</h2>
        <p className={passed ? "pass" : "fail"}>
          Status: {quality.reconciliation.status}. Gold due {money(quality.reconciliation.due_amount)},
          gold paid {money(quality.reconciliation.paid_amount)}, {quality.reconciliation.rows} repayment rows.
        </p>
        <table>
          <caption>Rejected rows in the published batch</caption>
          <thead>
            <tr>
              <th scope="col">Reason</th>
              <th scope="col">Rows</th>
            </tr>
          </thead>
          <tbody>
            {quality.rejected_by_reason.map((item) => (
              <tr key={item.reason}>
                <td>{item.reason}</td>
                <td>{item.rows}</td>
              </tr>
            ))}
          </tbody>
        </table>
        {quality.rejected_by_reason.length === 0 ? <p>No reject summary exported yet.</p> : null}
      </section>
    </Frame>
  );
}
