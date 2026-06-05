import { NextResponse } from "next/server";
import { readDrafts } from "@/lib/drafts";

export const runtime = "nodejs";

export async function GET() {
  const drafts = await readDrafts();
  return NextResponse.json(drafts);
}

export async function POST() {
  return NextResponse.json({ error: "Use /api/drafts/generate to create drafts" }, { status: 405 });
}
