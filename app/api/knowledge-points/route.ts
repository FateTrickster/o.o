import { NextRequest } from "next/server";
import { proxyJson } from "@/lib/backendApi";

export const runtime = "nodejs";

export async function GET(request: NextRequest) {
  return proxyJson(request, "/knowledge-points", "Failed to load knowledge points");
}
