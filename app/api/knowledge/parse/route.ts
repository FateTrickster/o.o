import { NextRequest, NextResponse } from "next/server";
import { chunkText } from "@/lib/chunkText";

export const runtime = "nodejs";

const supportedTypes = new Set(["pdf", "docx", "txt", "md", "json"]);

function extensionFromName(fileName: string) {
  return fileName.split(".").pop()?.toLowerCase() ?? "";
}

function jsonToText(raw: string) {
  const parsed = JSON.parse(raw) as unknown;
  if (Array.isArray(parsed)) {
    return parsed
      .map((item) => {
        if (item && typeof item === "object") {
          const record = item as Record<string, unknown>;
          return [record.title, record.content, record.text, record.description]
            .filter((value) => typeof value === "string" && value.trim())
            .join("\n\n");
        }
        return String(item);
      })
      .filter(Boolean)
      .join("\n\n");
  }

  if (parsed && typeof parsed === "object") {
    const record = parsed as Record<string, unknown>;
    const text = [record.title, record.content, record.text, record.description]
      .filter((value) => typeof value === "string" && value.trim())
      .join("\n\n");
    return text || JSON.stringify(parsed, null, 2);
  }

  return String(parsed);
}

async function extractText(file: File, sourceType: string) {
  const buffer = Buffer.from(await file.arrayBuffer());

  if (sourceType === "pdf") {
    const { PDFParse } = await import("pdf-parse");
    const parser = new PDFParse({ data: buffer });
    try {
      const result = await parser.getText();
      return result.text;
    } finally {
      await parser.destroy();
    }
  }

  if (sourceType === "docx") {
    const mammoth = await import("mammoth");
    const result = await mammoth.extractRawText({ buffer });
    return result.value;
  }

  const raw = buffer.toString("utf8");
  if (sourceType === "json") {
    return jsonToText(raw);
  }

  return raw;
}

export async function POST(request: NextRequest) {
  try {
    const formData = await request.formData();
    const file = formData.get("file");

    if (!(file instanceof File)) {
      return NextResponse.json({ error: "file is required" }, { status: 400 });
    }

    const sourceFileName = file.name;
    const sourceType = extensionFromName(sourceFileName);
    if (!supportedTypes.has(sourceType)) {
      return NextResponse.json(
        { error: "Only PDF, DOCX, TXT, MD, and JSON files are supported" },
        { status: 400 }
      );
    }

    const text = await extractText(file, sourceType);
    const chunks = chunkText(text).map((content, index) => ({
      title: `${sourceFileName} #${index + 1}`,
      content,
      sourceFileName,
      sourceType,
      tags: []
    }));

    return NextResponse.json({
      sourceFileName,
      sourceType,
      textLength: text.length,
      chunks
    });
  } catch (error) {
    return NextResponse.json(
      { error: error instanceof Error ? error.message : "Failed to parse file" },
      { status: 400 }
    );
  }
}
