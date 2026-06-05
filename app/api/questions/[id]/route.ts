import { NextRequest, NextResponse } from "next/server";
import { deleteQuestion, getQuestion, updateQuestion } from "@/lib/questions";
import { QuestionInput } from "@/types/question";

export const runtime = "nodejs";

type Params = {
  params: Promise<{
    id: string;
  }>;
};

export async function GET(_request: NextRequest, { params }: Params) {
  const { id } = await params;
  const question = await getQuestion(id);
  if (!question) {
    return NextResponse.json({ error: "Question not found" }, { status: 404 });
  }

  return NextResponse.json(question);
}

export async function PUT(request: NextRequest, { params }: Params) {
  try {
    const { id } = await params;
    const input = (await request.json()) as QuestionInput;
    const question = await updateQuestion(id, input);
    if (!question) {
      return NextResponse.json({ error: "Question not found" }, { status: 404 });
    }

    return NextResponse.json(question);
  } catch (error) {
    return NextResponse.json(
      { error: error instanceof Error ? error.message : "Failed to update question" },
      { status: 400 }
    );
  }
}

export async function DELETE(_request: NextRequest, { params }: Params) {
  const { id } = await params;
  const removed = await deleteQuestion(id);
  if (!removed) {
    return NextResponse.json({ error: "Question not found" }, { status: 404 });
  }

  return NextResponse.json({ ok: true });
}
