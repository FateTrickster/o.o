import { NextRequest } from "next/server";
import { proxyJson, proxyJsonNoRequest } from "@/lib/backendApi";

export const runtime = "nodejs";

export async function GET() {
  return proxyJsonNoRequest("/drafts", "Failed to load drafts");
}

export async function POST(request: NextRequest) {
  return proxyJson(request, "/drafts/generate", "Failed to generate drafts");
}
