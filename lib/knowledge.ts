import { promises as fs } from "fs";
import path from "path";
import { KnowledgeEntry, KnowledgeEntryInput, KnowledgeFilters } from "@/types/knowledge";

const dataDir = path.join(process.cwd(), "data");
const knowledgeFile = path.join(dataDir, "knowledge.json");

async function ensureStore() {
  await fs.mkdir(dataDir, { recursive: true });

  try {
    await fs.access(knowledgeFile);
  } catch {
    await fs.writeFile(knowledgeFile, "[]\n", "utf8");
  }
}

export async function readKnowledgeEntries(): Promise<KnowledgeEntry[]> {
  await ensureStore();
  const raw = await fs.readFile(knowledgeFile, "utf8");
  if (!raw.trim()) {
    return [];
  }

  const parsed = JSON.parse(raw) as KnowledgeEntry[];
  return parsed.sort((a, b) => b.updatedAt.localeCompare(a.updatedAt));
}

async function writeKnowledgeEntries(entries: KnowledgeEntry[]) {
  await ensureStore();
  await fs.writeFile(knowledgeFile, `${JSON.stringify(entries, null, 2)}\n`, "utf8");
}

export function filterKnowledgeEntries(entries: KnowledgeEntry[], filters: KnowledgeFilters) {
  const search = filters.search?.trim().toLowerCase();
  const tag = filters.tag?.trim().toLowerCase();

  return entries.filter((entry) => {
    if (filters.sourceType && entry.sourceType !== filters.sourceType) {
      return false;
    }

    if (tag && !entry.tags.some((item) => item.toLowerCase().includes(tag))) {
      return false;
    }

    if (
      search &&
      !`${entry.title} ${entry.content} ${entry.sourceFileName}`
        .toLowerCase()
        .includes(search)
    ) {
      return false;
    }

    return true;
  });
}

export function validateKnowledgeEntryInput(input: Partial<KnowledgeEntryInput>) {
  const errors: string[] = [];
  const requiredFields: Array<keyof KnowledgeEntryInput> = [
    "title",
    "content",
    "sourceFileName",
    "sourceType"
  ];

  for (const field of requiredFields) {
    const value = input[field];
    if (typeof value !== "string" || !value.trim()) {
      errors.push(`${field} is required`);
    }
  }

  if (!Array.isArray(input.tags)) {
    errors.push("tags must be an array");
  }

  return [...new Set(errors)];
}

export async function getKnowledgeEntry(id: string) {
  const entries = await readKnowledgeEntries();
  return entries.find((entry) => entry.id === id) ?? null;
}

export async function createKnowledgeEntry(input: KnowledgeEntryInput) {
  const errors = validateKnowledgeEntryInput(input);
  if (errors.length > 0) {
    throw new Error(errors.join("; "));
  }

  const entries = await readKnowledgeEntries();
  const now = new Date().toISOString();
  const entry: KnowledgeEntry = {
    ...input,
    id: crypto.randomUUID(),
    createdAt: now,
    updatedAt: now
  };

  await writeKnowledgeEntries([entry, ...entries]);
  return entry;
}

export async function createKnowledgeEntries(inputs: KnowledgeEntryInput[]) {
  if (!Array.isArray(inputs)) {
    throw new Error("JSON payload must be an array of knowledge entries");
  }

  const errors = inputs.flatMap((input, index) =>
    validateKnowledgeEntryInput(input).map((error) => `Entry ${index + 1}: ${error}`)
  );
  if (errors.length > 0) {
    throw new Error(errors.join("; "));
  }

  const entries = await readKnowledgeEntries();
  const now = new Date().toISOString();
  const created = inputs.map((input) => ({
    ...input,
    id: crypto.randomUUID(),
    createdAt: now,
    updatedAt: now
  }));

  await writeKnowledgeEntries([...created, ...entries]);

  return {
    imported: created.length,
    total: created.length + entries.length
  };
}

export async function updateKnowledgeEntry(id: string, input: KnowledgeEntryInput) {
  const errors = validateKnowledgeEntryInput(input);
  if (errors.length > 0) {
    throw new Error(errors.join("; "));
  }

  const entries = await readKnowledgeEntries();
  const index = entries.findIndex((entry) => entry.id === id);
  if (index === -1) {
    return null;
  }

  const updated: KnowledgeEntry = {
    ...entries[index],
    ...input,
    id,
    updatedAt: new Date().toISOString()
  };

  entries[index] = updated;
  await writeKnowledgeEntries(entries);
  return updated;
}

export async function deleteKnowledgeEntry(id: string) {
  const entries = await readKnowledgeEntries();
  const nextEntries = entries.filter((entry) => entry.id !== id);
  if (nextEntries.length === entries.length) {
    return false;
  }

  await writeKnowledgeEntries(nextEntries);
  return true;
}
