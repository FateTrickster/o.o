import { NextRequest, NextResponse } from "next/server";
import { createQuestion } from "@/lib/questions";
import { deleteDraft, getDraft } from "@/lib/drafts";

export const runtime = "nodejs";

type Params = {
  params: Promise<{
    id: string;
  }>;
};

export async function POST(_request: NextRequest, { params }: Params) {
  try {
    const { id } = await params;
    const draft = await getDraft(id);
    if (!draft) {
      return NextResponse.json({ error: "Draft not found" }, { status: 404 });
    }

    const question = await createQuestion({
      title: draft.title,
      question: draft.question,
      scenario: draft.scenario,
      options: draft.options,
      correctAnswer: draft.correctAnswer,
      explanation: draft.explanation,
      dimension: draft.dimension,
      secondaryDimension: draft.secondaryDimension,
      subSkill: draft.subSkill,
      cognitiveLevel: draft.cognitiveLevel,
      difficultyEstimate: draft.difficultyEstimate,
      tags: draft.tags,
      sourceReference: draft.sourceReference,
      status: draft.status
    });

    await deleteDraft(id);
    return NextResponse.json(question, { status: 201 });
  } catch (error) {
    return NextResponse.json(
      { error: error instanceof Error ? error.message : "Failed to accept draft" },
      { status: 400 }
    );
  }
}
