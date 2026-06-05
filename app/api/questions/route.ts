import { NextRequest } from "next/server";
import { proxyJson } from "@/lib/backendApi";

export const runtime = "nodejs";

export async function GET(request: NextRequest) {
  return proxyJson(request, "/questions", "Failed to load questions");
}

export async function POST(request: NextRequest) {
  return proxyJson(request, "/questions", "Failed to create question");
}
