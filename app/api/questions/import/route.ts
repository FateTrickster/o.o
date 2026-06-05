import { NextRequest, NextResponse } from "next/server";
import { importQuestions } from "@/lib/questions";
import { Question } from "@/types/question";

export const runtime = "nodejs";

export async function GET(request: NextRequest) {
  return NextResponse.redirect(new URL("/", request.url));
}

export async function POST(request: NextRequest) {
  try {
    const questions = (await request.json()) as Question[];
    const result = await importQuestions(questions);
    return NextResponse.json(result);
  } catch (error) {
    return NextResponse.json(
      { error: error instanceof Error ? error.message : "Failed to import questions" },
      { status: 400 }
    );
  }
}
