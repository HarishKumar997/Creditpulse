import { Frame } from "@/components/Frame";
import { loadRuns } from "@/lib/data";

export default function RunsPage() {
  const payload = loadRuns();
  return (
    <Frame disclaimer={payload.disclaimer}>
      <h1>Pipeline runs</h1>
      <p className="lede">
        The watermark moves only after a run is marked success. A failed attempt stays in this list.
      </p>
      <div className="panel">
        <table>
          <caption>Recent batch attempts</caption>
          <thead>
            <tr>
              <th scope="col">Status</th>
              <th scope="col">Batch</th>
              <th scope="col">Started</th>
              <th scope="col">Read</th>
              <th scope="col">Accepted</th>
              <th scope="col">Rejected</th>
              <th scope="col">Duplicates</th>
              <th scope="col">Note</th>
            </tr>
          </thead>
          <tbody>
            {payload.runs.map((run) => (
              <tr key={run.run_id}>
                <td className={run.status === "success" ? "pass" : "fail"}>{run.status}</td>
                <td>{run.batch_id}</td>
                <td>{run.started_at}</td>
                <td>{run.rows_read}</td>
                <td>{run.rows_accepted}</td>
                <td>{run.rows_rejected}</td>
                <td>{run.rows_duplicate}</td>
                <td>{run.error_summary ?? ""}</td>
              </tr>
            ))}
          </tbody>
        </table>
        {payload.runs.length === 0 ? <p>No runs exported yet.</p> : null}
      </div>
    </Frame>
  );
}
