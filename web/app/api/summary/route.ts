import { loadSummary } from "@/lib/data";

export function GET() {
  return Response.json(loadSummary());
}
