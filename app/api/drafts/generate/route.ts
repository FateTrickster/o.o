import { NextRequest, NextResponse } from "next/server";
import { createDrafts } from "@/lib/drafts";
import { generateDraftQuestions } from "@/lib/llm/generator";
import { getKnowledgeEntry } from "@/lib/knowledge";
import { DraftGenerationRequest, QuestionDraftInput } from "@/types/draft";
import { KnowledgeEntry } from "@/types/knowledge";

export const runtime = "nodejs";

function isKnowledgeEntry(entry: KnowledgeEntry | null): entry is KnowledgeEntry {
  return entry !== null;
}

function cleanList(value: unknown) {
  return Array.isArray(value)
    ? value.map((item) => String(item).trim()).filter(Boolean)
    : [];
}

function buildGenerationRequirement(body: DraftGenerationRequest) {
  const parts = [body.requirement?.trim()].filter(Boolean);
  const dimensions = cleanList(body.targetDimensions);
  const secondaryDimensions = cleanList(body.targetSecondaryDimensions);
  const tags = cleanList(body.targetTags);

  if (dimensions.length > 0) {
    parts.push(`目标一级维度：${dimensions.join("、")}`);
  }

  if (secondaryDimensions.length > 0) {
    parts.push(`目标二级维度：${secondaryDimensions.join("、")}`);
  }

  if (tags.length > 0) {
    parts.push(`目标知识点标签：${tags.join("、")}`);
  }

  return parts.join("\n");
}

export async function POST(request: NextRequest) {
  try {
    const body = (await request.json()) as DraftGenerationRequest;
    if (!Array.isArray(body.knowledgeIds) || body.knowledgeIds.length === 0) {
      return NextResponse.json({ error: "请选择至少一个知识条目" }, { status: 400 });
    }

    const knowledgeEntries = (
      await Promise.all(body.knowledgeIds.map((id) => getKnowledgeEntry(id)))
    ).filter(isKnowledgeEntry);

    if (knowledgeEntries.length === 0) {
      return NextResponse.json({ error: "未找到可用知识条目" }, { status: 400 });
    }

    const generated = await generateDraftQuestions({
      knowledgeEntries,
      requirement: body.requirement,
      targetDimensions: cleanList(body.targetDimensions),
      targetSecondaryDimensions: cleanList(body.targetSecondaryDimensions),
      targetTags: cleanList(body.targetTags),
      count: 3
    });

    const generationRequirement = buildGenerationRequirement(body);
    const inputs: QuestionDraftInput[] = generated.map((question) => ({
      ...question,
      sourceKnowledgeIds: body.knowledgeIds,
      generationRequirement
    }));

    const drafts = await createDrafts(inputs);
    return NextResponse.json(drafts, { status: 201 });
  } catch (error) {
    return NextResponse.json(
      { error: error instanceof Error ? error.message : "Failed to generate drafts" },
      { status: 400 }
    );
  }
}
