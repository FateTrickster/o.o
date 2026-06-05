import { NextRequest, NextResponse } from "next/server";
import { createQuestion, filterQuestions, readQuestions } from "@/lib/questions";
import { DifficultyEstimate, QuestionInput, QuestionStatus } from "@/types/question";

export const runtime = "nodejs";

export async function GET(request: NextRequest) {
  const { searchParams } = request.nextUrl;
  const questions = await readQuestions();
  const filtered = filterQuestions(questions, {
    dimension: searchParams.get("dimension") || undefined,
    secondaryDimension: searchParams.get("secondaryDimension") || undefined,
    status: (searchParams.get("status") || "") as QuestionStatus | "",
    difficulty: (searchParams.get("difficulty") || "") as DifficultyEstimate | "",
    tag: searchParams.get("tag") || undefined,
    search: searchParams.get("search") || undefined
  });

  return NextResponse.json(filtered);
}

export async function POST(request: NextRequest) {
  try {
    const input = (await request.json()) as QuestionInput;
    const question = await createQuestion(input);
    return NextResponse.json(question, { status: 201 });
  } catch (error) {
    return NextResponse.json(
      { error: error instanceof Error ? error.message : "Failed to create question" },
      { status: 400 }
    );
  }
}
