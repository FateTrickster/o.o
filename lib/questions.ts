import { promises as fs } from "fs";
import path from "path";
import {
  aiLiteracyDimensions,
  isValidDimensionPair,
  normalizeFrameworkSelection
} from "@/lib/aiLiteracyFramework";
import {
  DifficultyEstimate,
  Question,
  QuestionFilters,
  QuestionInput,
  QuestionStatus
} from "@/types/question";

const dataDir = path.join(process.cwd(), "data");
const questionsFile = path.join(dataDir, "questions.json");

const statuses: QuestionStatus[] = ["draft", "reviewed", "tested", "retired"];
const difficulties: DifficultyEstimate[] = ["easy", "medium", "hard"];
const itemCodePattern = /^\d{5}$/;

async function ensureStore() {
  await fs.mkdir(dataDir, { recursive: true });

  try {
    await fs.access(questionsFile);
  } catch {
    await fs.writeFile(questionsFile, "[]\n", "utf8");
  }
}

export async function readQuestions(): Promise<Question[]> {
  await ensureStore();
  const raw = await fs.readFile(questionsFile, "utf8");
  if (!raw.trim()) {
    return [];
  }

  const parsed = JSON.parse(raw) as Question[];
  const { questions, changed } = ensureItemCodes(parsed);
  if (changed) {
    await writeQuestions(questions);
  }

  return questions.sort(sortByItemCode);
}

async function writeQuestions(questions: Question[]) {
  await ensureStore();
  await fs.writeFile(questionsFile, `${JSON.stringify(questions, null, 2)}\n`, "utf8");
}

function formatItemCode(value: number) {
  return String(value).padStart(5, "0");
}

function itemCodeNumber(itemCode: string) {
  return itemCodePattern.test(itemCode) ? Number(itemCode) : 0;
}

function sortByItemCode(a: Question, b: Question) {
  const codeDifference = itemCodeNumber(a.itemCode) - itemCodeNumber(b.itemCode);
  if (codeDifference !== 0) {
    return codeDifference;
  }

  return a.createdAt.localeCompare(b.createdAt);
}

function nextItemCode(usedCodes: Set<string>) {
  let next = Math.max(0, ...Array.from(usedCodes, itemCodeNumber)) + 1;
  while (usedCodes.has(formatItemCode(next))) {
    next += 1;
  }

  const itemCode = formatItemCode(next);
  usedCodes.add(itemCode);
  return itemCode;
}

function ensureItemCodes(questions: Question[]) {
  const usedCodes = new Set<string>();
  let changed = false;

  const normalized = questions.map((question) => {
    const frameworkSelection = normalizeFrameworkSelection(
      question.dimension,
      question.secondaryDimension,
      `${question.title} ${question.question} ${question.scenario} ${question.subSkill} ${question.tags?.join(" ")}`
    );
    const normalizedQuestion =
      question.dimension === frameworkSelection.dimension &&
      question.secondaryDimension === frameworkSelection.secondaryDimension
        ? question
        : {
            ...question,
            ...frameworkSelection
          };

    if (normalizedQuestion !== question) {
      changed = true;
    }

    const current = question.itemCode;
    if (current && itemCodePattern.test(current) && !usedCodes.has(current)) {
      usedCodes.add(current);
      return normalizedQuestion;
    }

    changed = true;
    return {
      ...normalizedQuestion,
      itemCode: nextItemCode(usedCodes)
    };
  });

  return { questions: normalized, changed };
}

export function filterQuestions(questions: Question[], filters: QuestionFilters) {
  const search = filters.search?.trim().toLowerCase();
  const tag = filters.tag?.trim().toLowerCase();

  return questions.filter((question) => {
    if (filters.dimension && question.dimension !== filters.dimension) {
      return false;
    }

    if (filters.secondaryDimension && question.secondaryDimension !== filters.secondaryDimension) {
      return false;
    }

    if (filters.status && question.status !== filters.status) {
      return false;
    }

    if (filters.difficulty && question.difficultyEstimate !== filters.difficulty) {
      return false;
    }

    if (tag && !question.tags.some((item) => item.toLowerCase().includes(tag))) {
      return false;
    }

    if (
      search &&
      !`${question.itemCode} ${question.title} ${question.question} ${question.scenario} ${question.dimension} ${question.secondaryDimension} ${question.subSkill}`
        .toLowerCase()
        .includes(search)
    ) {
      return false;
    }

    return true;
  });
}

export function validateQuestionInput(input: Partial<QuestionInput>): string[] {
  const errors: string[] = [];

  const requiredText: Array<keyof QuestionInput> = [
    "title",
    "question",
    "scenario",
    "explanation",
    "dimension",
    "secondaryDimension",
    "subSkill",
    "sourceReference"
  ];

  for (const field of requiredText) {
    const value = input[field];
    if (typeof value !== "string" || !value.trim()) {
      errors.push(`${field} is required`);
    }
  }

  if (!Array.isArray(input.options) || input.options.length < 2) {
    errors.push("options must contain at least two choices");
  } else {
    const optionIds = new Set<string>();
    for (const option of input.options) {
      if (!option.id?.trim() || !option.text?.trim()) {
        errors.push("each option needs an id and text");
        break;
      }
      optionIds.add(option.id);
    }

    if (!input.correctAnswer || !optionIds.has(input.correctAnswer)) {
      errors.push("correctAnswer must match an option id");
    }
  }

  if (!input.cognitiveLevel) {
    errors.push("cognitiveLevel is required");
  }

  if (input.dimension && !aiLiteracyDimensions.some((dimension) => dimension === input.dimension)) {
    errors.push("dimension must be one of the UACE framework dimensions");
  }

  if (
    input.dimension &&
    input.secondaryDimension &&
    !isValidDimensionPair(input.dimension, input.secondaryDimension)
  ) {
    errors.push("secondaryDimension must belong to the selected dimension");
  }

  if (!input.difficultyEstimate || !difficulties.includes(input.difficultyEstimate)) {
    errors.push("difficultyEstimate must be easy, medium, or hard");
  }

  if (!input.status || !statuses.includes(input.status)) {
    errors.push("status must be draft, reviewed, tested, or retired");
  }

  if (!Array.isArray(input.tags)) {
    errors.push("tags must be an array");
  }

  return [...new Set(errors)];
}

export async function getQuestion(id: string) {
  const questions = await readQuestions();
  return questions.find((question) => question.id === id) ?? null;
}

export async function createQuestion(input: QuestionInput) {
  const errors = validateQuestionInput(input);
  if (errors.length > 0) {
    throw new Error(errors.join("; "));
  }

  const questions = await readQuestions();
  const usedCodes = new Set(questions.map((question) => question.itemCode));
  const now = new Date().toISOString();
  const question: Question = {
    ...input,
    id: crypto.randomUUID(),
    itemCode: nextItemCode(usedCodes),
    createdAt: now,
    updatedAt: now
  };

  await writeQuestions([question, ...questions]);
  return question;
}

export async function updateQuestion(id: string, input: QuestionInput) {
  const errors = validateQuestionInput(input);
  if (errors.length > 0) {
    throw new Error(errors.join("; "));
  }

  const questions = await readQuestions();
  const index = questions.findIndex((question) => question.id === id);
  if (index === -1) {
    return null;
  }

  const updated: Question = {
    ...questions[index],
    ...input,
    id,
    itemCode: questions[index].itemCode,
    updatedAt: new Date().toISOString()
  };

  questions[index] = updated;
  await writeQuestions(questions);
  return updated;
}

export async function deleteQuestion(id: string) {
  const questions = await readQuestions();
  const nextQuestions = questions.filter((question) => question.id !== id);
  if (nextQuestions.length === questions.length) {
    return false;
  }

  await writeQuestions(nextQuestions);
  return true;
}

export async function importQuestions(imported: Question[]) {
  if (!Array.isArray(imported)) {
    throw new Error("JSON payload must be an array of questions");
  }

  const existing = await readQuestions();
  const byId = new Map(existing.map((question) => [question.id, question]));
  const usedCodes = new Map(existing.map((question) => [question.itemCode, question.id]));
  const now = new Date().toISOString();

  for (const question of imported) {
    const id = question.id || crypto.randomUUID();
    const existingQuestion = byId.get(id);
    const incomingCode = question.itemCode;
    const conflictingId = incomingCode ? usedCodes.get(incomingCode) : undefined;
    const itemCode =
      incomingCode &&
      itemCodePattern.test(incomingCode) &&
      (!conflictingId || conflictingId === id)
        ? incomingCode
        : existingQuestion && (!incomingCode || !itemCodePattern.test(incomingCode))
          ? existingQuestion.itemCode
        : nextItemCode(new Set(usedCodes.keys()));

    const candidate: Question = {
      ...question,
      id,
      itemCode,
      ...normalizeFrameworkSelection(
        question.dimension,
        question.secondaryDimension,
        `${question.title} ${question.question} ${question.scenario} ${question.subSkill} ${question.tags?.join(" ")}`
      ),
      createdAt: question.createdAt || now,
      updatedAt: now
    };

    const input = {
      title: candidate.title,
      question: candidate.question,
      scenario: candidate.scenario,
      options: candidate.options,
      correctAnswer: candidate.correctAnswer,
      explanation: candidate.explanation,
      dimension: candidate.dimension,
      secondaryDimension: candidate.secondaryDimension || "未分类",
      subSkill: candidate.subSkill,
      cognitiveLevel: candidate.cognitiveLevel,
      difficultyEstimate: candidate.difficultyEstimate,
      tags: candidate.tags,
      sourceReference: candidate.sourceReference,
      status: candidate.status
    };
    const errors = validateQuestionInput(input);
    if (errors.length > 0) {
      throw new Error(`Question "${candidate.title || candidate.id}" is invalid: ${errors.join("; ")}`);
    }

    if (existingQuestion) {
      usedCodes.delete(existingQuestion.itemCode);
    }
    usedCodes.set(candidate.itemCode, candidate.id);
    byId.set(candidate.id, candidate);
  }

  const merged = Array.from(byId.values()).sort(sortByItemCode);
  await writeQuestions(merged);

  return {
    imported: imported.length,
    total: merged.length
  };
}
