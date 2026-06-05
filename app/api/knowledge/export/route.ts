import { NextResponse } from "next/server";
import { readKnowledgeEntries } from "@/lib/knowledge";

export const runtime = "nodejs";

export async function GET() {
  const entries = await readKnowledgeEntries();
  return new NextResponse(JSON.stringify(entries, null, 2), {
    headers: {
      "Content-Type": "application/json; charset=utf-8",
      "Content-Disposition": "attachment; filename=\"ai-literacy-knowledge-base.json\""
    }
  });
}
