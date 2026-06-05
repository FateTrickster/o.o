import { NextRequest } from "next/server";
import { proxyJson } from "@/lib/backendApi";

export const runtime = "nodejs";

export async function GET(request: NextRequest) {
  return proxyJson(request, "/knowledge", "Failed to load knowledge entries");
}

export async function POST(request: NextRequest) {
  return proxyJson(request, "/knowledge", "Failed to create knowledge entry");
}
