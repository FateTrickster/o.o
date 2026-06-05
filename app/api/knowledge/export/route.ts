import { proxyDownload } from "@/lib/backendApi";

export const runtime = "nodejs";

export async function GET() {
  return proxyDownload(
    "/knowledge",
    "ai-literacy-knowledge-base.json",
    "Failed to export knowledge entries"
  );
}
