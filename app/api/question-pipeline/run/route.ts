import { NextRequest } from "next/server";
import { proxyJson } from "@/lib/backendApi";

export const runtime = "nodejs";

export async function POST(request: NextRequest) {
  return proxyJson(request, "/question-pipeline/run", "Failed to run question pipeline");
}
