import { NextRequest, NextResponse } from "next/server";
import { deleteDraft, getDraft, updateDraft } from "@/lib/drafts";
import { QuestionDraftInput } from "@/types/draft";

export const runtime = "nodejs";

type Params = {
  params: Promise<{
    id: string;
  }>;
};

export async function GET(_request: NextRequest, { params }: Params) {
  const { id } = await params;
  const draft = await getDraft(id);
  if (!draft) {
    return NextResponse.json({ error: "Draft not found" }, { status: 404 });
  }

  return NextResponse.json(draft);
}

export async function PUT(request: NextRequest, { params }: Params) {
  try {
    const { id } = await params;
    const input = (await request.json()) as QuestionDraftInput;
    const draft = await updateDraft(id, input);
    if (!draft) {
      return NextResponse.json({ error: "Draft not found" }, { status: 404 });
    }

    return NextResponse.json(draft);
  } catch (error) {
    return NextResponse.json(
      { error: error instanceof Error ? error.message : "Failed to update draft" },
      { status: 400 }
    );
  }
}

export async function DELETE(_request: NextRequest, { params }: Params) {
  const { id } = await params;
  const removed = await deleteDraft(id);
  if (!removed) {
    return NextResponse.json({ error: "Draft not found" }, { status: 404 });
  }

  return NextResponse.json({ ok: true });
}
