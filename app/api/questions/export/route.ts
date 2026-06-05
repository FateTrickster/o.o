import { proxyDownload } from "@/lib/backendApi";

export const runtime = "nodejs";

export async function GET() {
  return proxyDownload(
    "/questions",
    "ai-literacy-question-bank.json",
    "Failed to export questions"
  );
}
