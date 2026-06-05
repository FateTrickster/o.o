import { NextRequest, NextResponse } from "next/server";
import {
  createKnowledgeEntry,
  filterKnowledgeEntries,
  readKnowledgeEntries
} from "@/lib/knowledge";
import { KnowledgeEntryInput } from "@/types/knowledge";

export const runtime = "nodejs";

export async function GET(request: NextRequest) {
  const { searchParams } = request.nextUrl;
  const entries = await readKnowledgeEntries();
  const filtered = filterKnowledgeEntries(entries, {
    sourceType: searchParams.get("sourceType") || undefined,
    tag: searchParams.get("tag") || undefined,
    search: searchParams.get("search") || undefined
  });

  return NextResponse.json(filtered);
}

export async function POST(request: NextRequest) {
  try {
    const input = (await request.json()) as KnowledgeEntryInput;
    const entry = await createKnowledgeEntry(input);
    return NextResponse.json(entry, { status: 201 });
  } catch (error) {
    return NextResponse.json(
      { error: error instanceof Error ? error.message : "Failed to create knowledge entry" },
      { status: 400 }
    );
  }
}
