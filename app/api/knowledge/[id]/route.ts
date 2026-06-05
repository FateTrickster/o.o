import { NextRequest } from "next/server";
import { proxyJson, proxyJsonNoRequest } from "@/lib/backendApi";

export const runtime = "nodejs";

type Params = {
  params: Promise<{
    id: string;
  }>;
};

export async function GET(_request: NextRequest, { params }: Params) {
  const { id } = await params;
  return proxyJsonNoRequest(`/knowledge/${encodeURIComponent(id)}`, "Knowledge entry not found");
}

export async function PUT(request: NextRequest, { params }: Params) {
  const { id } = await params;
  return proxyJson(request, `/knowledge/${encodeURIComponent(id)}`, "Failed to update knowledge entry", "PUT");
}

export async function DELETE(_request: NextRequest, { params }: Params) {
  const { id } = await params;
  return proxyJsonNoRequest(`/knowledge/${encodeURIComponent(id)}`, "Knowledge entry not found", "DELETE");
}
