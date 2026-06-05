import { NextRequest } from "next/server";
import { proxyJsonNoRequest } from "@/lib/backendApi";

export const runtime = "nodejs";

type Params = {
  params: Promise<{
    id: string;
  }>;
};

export async function POST(_request: NextRequest, { params }: Params) {
  const { id } = await params;
  return proxyJsonNoRequest(`/drafts/${encodeURIComponent(id)}/accept`, "Failed to accept draft", "POST");
}
