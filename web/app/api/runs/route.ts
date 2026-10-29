import { loadRuns } from "@/lib/data";

export function GET() {
  return Response.json(loadRuns());
}
