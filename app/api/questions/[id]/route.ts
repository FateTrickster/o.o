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
  return proxyJsonNoRequest(`/questions/${encodeURIComponent(id)}`, "Question not found");
}

export async function PUT(request: NextRequest, { params }: Params) {
  const { id } = await params;
  return proxyJson(request, `/questions/${encodeURIComponent(id)}`, "Failed to update question", "PUT");
}

export async function DELETE(_request: NextRequest, { params }: Params) {
  const { id } = await params;
  return proxyJsonNoRequest(`/questions/${encodeURIComponent(id)}`, "Question not found", "DELETE");
}
