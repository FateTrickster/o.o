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
  return proxyJsonNoRequest(`/drafts/${encodeURIComponent(id)}`, "Draft not found");
}

export async function PUT(request: NextRequest, { params }: Params) {
  const { id } = await params;
  return proxyJson(request, `/drafts/${encodeURIComponent(id)}`, "Failed to update draft", "PUT");
}

export async function DELETE(_request: NextRequest, { params }: Params) {
  const { id } = await params;
  return proxyJsonNoRequest(`/drafts/${encodeURIComponent(id)}`, "Draft not found", "DELETE");
}
