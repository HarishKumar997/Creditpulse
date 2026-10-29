import { loadQuality } from "@/lib/data";

export function GET() {
  return Response.json(loadQuality());
}
