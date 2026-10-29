import { filterPortfolio, loadPortfolio } from "@/lib/data";

export function GET(request: Request) {
  const url = new URL(request.url);
  const result = filterPortfolio(
    loadPortfolio().rows,
    url.searchParams.get("from"),
    url.searchParams.get("to"),
  );
  if (result.error) {
    return Response.json({ schema_version: "1", error: result.error }, { status: 400 });
  }
  return Response.json({ schema_version: "1", rows: result.rows });
}
