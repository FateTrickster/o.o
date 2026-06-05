import { promises as fs } from "fs";
import path from "path";
import { QuestionDraft, QuestionDraftInput } from "@/types/draft";
import { validateQuestionInput } from "@/lib/questions";
import { normalizeFrameworkSelection } from "@/lib/aiLiteracyFramework";

const dataDir = path.join(process.cwd(), "data");
const draftsFile = path.join(dataDir, "drafts.json");

async function ensureStore() {
  await fs.mkdir(dataDir, { recursive: true });

  try {
    await fs.access(draftsFile);
  } catch {
    await fs.writeFile(draftsFile, "[]\n", "utf8");
  }
}

export async function readDrafts(): Promise<QuestionDraft[]> {
  await ensureStore();
  const raw = await fs.readFile(draftsFile, "utf8");
  if (!raw.trim()) {
    return [];
  }

  const parsed = JSON.parse(raw) as QuestionDraft[];
  const { drafts, changed } = ensureDraftMetadata(parsed);
  if (changed) {
    await writeDrafts(drafts);
  }

  return drafts.sort((a, b) => b.updatedAt.localeCompare(a.updatedAt));
}

async function writeDrafts(drafts: QuestionDraft[]) {
  await ensureStore();
  await fs.writeFile(draftsFile, `${JSON.stringify(drafts, null, 2)}\n`, "utf8");
}

function ensureDraftMetadata(drafts: QuestionDraft[]) {
  let changed = false;
  const normalized = drafts.map((draft) => {
    const frameworkSelection = normalizeFrameworkSelection(
      draft.dimension,
      draft.secondaryDimension,
      `${draft.title} ${draft.question} ${draft.scenario} ${draft.subSkill} ${draft.tags?.join(" ")}`
    );

    if (
      draft.dimension === frameworkSelection.dimension &&
      draft.secondaryDimension === frameworkSelection.secondaryDimension
    ) {
      return draft;
    }

    changed = true;
    return {
      ...draft,
      ...frameworkSelection
    };
  });

  return { drafts: normalized, changed };
}

export function validateDraftInput(input: Partial<QuestionDraftInput>) {
  const errors = validateQuestionInput(input);

  if (!Array.isArray(input.sourceKnowledgeIds)) {
    errors.push("sourceKnowledgeIds must be an array");
  }

  if (typeof input.generationRequirement !== "string") {
    errors.push("generationRequirement is required");
  }

  return [...new Set(errors)];
}

export async function createDrafts(inputs: QuestionDraftInput[]) {
  const errors = inputs.flatMap((input, index) =>
    validateDraftInput(input).map((error) => `Draft ${index + 1}: ${error}`)
  );
  if (errors.length > 0) {
    throw new Error(errors.join("; "));
  }

  const drafts = await readDrafts();
  const now = new Date().toISOString();
  const created: QuestionDraft[] = inputs.map((input) => ({
    ...input,
    id: crypto.randomUUID(),
    createdAt: now,
    updatedAt: now
  }));

  await writeDrafts([...created, ...drafts]);
  return created;
}

export async function getDraft(id: string) {
  const drafts = await readDrafts();
  return drafts.find((draft) => draft.id === id) ?? null;
}

export async function updateDraft(id: string, input: QuestionDraftInput) {
  const errors = validateDraftInput(input);
  if (errors.length > 0) {
    throw new Error(errors.join("; "));
  }

  const drafts = await readDrafts();
  const index = drafts.findIndex((draft) => draft.id === id);
  if (index === -1) {
    return null;
  }

  const updated: QuestionDraft = {
    ...drafts[index],
    ...input,
    id,
    updatedAt: new Date().toISOString()
  };

  drafts[index] = updated;
  await writeDrafts(drafts);
  return updated;
}

export async function deleteDraft(id: string) {
  const drafts = await readDrafts();
  const nextDrafts = drafts.filter((draft) => draft.id !== id);
  if (nextDrafts.length === drafts.length) {
    return false;
  }

  await writeDrafts(nextDrafts);
  return true;
}
