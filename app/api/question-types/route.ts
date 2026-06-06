import { proxyJsonNoRequest } from "@/lib/backendApi";

export const runtime = "nodejs";

export async function GET() {
  return proxyJsonNoRequest("/question-types", "Failed to load question types");
}
