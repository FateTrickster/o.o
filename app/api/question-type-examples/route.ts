import { NextRequest } from "next/server";
import { proxyJson } from "@/lib/backendApi";

export const runtime = "nodejs";

export async function GET(request: NextRequest) {
  return proxyJson(request, "/question-type-examples", "Failed to load question type examples");
}
