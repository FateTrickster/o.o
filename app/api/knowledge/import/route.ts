import { NextRequest, NextResponse } from "next/server";
import { createKnowledgeEntries } from "@/lib/knowledge";
import { KnowledgeEntryInput } from "@/types/knowledge";

export const runtime = "nodejs";

export async function POST(request: NextRequest) {
  try {
    const entries = (await request.json()) as KnowledgeEntryInput[];
    const result = await createKnowledgeEntries(entries);
    return NextResponse.json(result);
  } catch (error) {
    return NextResponse.json(
      { error: error instanceof Error ? error.message : "Failed to import knowledge entries" },
      { status: 400 }
    );
  }
}
