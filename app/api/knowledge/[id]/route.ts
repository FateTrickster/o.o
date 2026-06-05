import { NextRequest, NextResponse } from "next/server";
import {
  deleteKnowledgeEntry,
  getKnowledgeEntry,
  updateKnowledgeEntry
} from "@/lib/knowledge";
import { KnowledgeEntryInput } from "@/types/knowledge";

export const runtime = "nodejs";

type Params = {
  params: Promise<{
    id: string;
  }>;
};

export async function GET(_request: NextRequest, { params }: Params) {
  const { id } = await params;
  const entry = await getKnowledgeEntry(id);
  if (!entry) {
    return NextResponse.json({ error: "Knowledge entry not found" }, { status: 404 });
  }

  return NextResponse.json(entry);
}

export async function PUT(request: NextRequest, { params }: Params) {
  try {
    const { id } = await params;
    const input = (await request.json()) as KnowledgeEntryInput;
    const entry = await updateKnowledgeEntry(id, input);
    if (!entry) {
      return NextResponse.json({ error: "Knowledge entry not found" }, { status: 404 });
    }

    return NextResponse.json(entry);
  } catch (error) {
    return NextResponse.json(
      { error: error instanceof Error ? error.message : "Failed to update knowledge entry" },
      { status: 400 }
    );
  }
}

export async function DELETE(_request: NextRequest, { params }: Params) {
  const { id } = await params;
  const removed = await deleteKnowledgeEntry(id);
  if (!removed) {
    return NextResponse.json({ error: "Knowledge entry not found" }, { status: 404 });
  }

  return NextResponse.json({ ok: true });
}
