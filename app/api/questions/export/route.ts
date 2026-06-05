import { NextResponse } from "next/server";
import { readQuestions } from "@/lib/questions";

export const runtime = "nodejs";

export async function GET() {
  const questions = await readQuestions();
  return new NextResponse(JSON.stringify(questions, null, 2), {
    headers: {
      "Content-Type": "application/json; charset=utf-8",
      "Content-Disposition": "attachment; filename=\"ai-literacy-question-bank.json\""
    }
  });
}
