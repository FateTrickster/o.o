import { proxyJsonNoRequest } from "@/lib/backendApi";

export const runtime = "nodejs";

export async function GET() {
  return proxyJsonNoRequest("/generation-jobs", "Failed to load generation jobs");
}
