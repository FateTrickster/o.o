const defaultMinLength = 500;
const defaultMaxLength = 1200;

function normalizeText(text: string) {
  return text
    .replace(/\r\n/g, "\n")
    .replace(/\r/g, "\n")
    .replace(/[ \t]+/g, " ")
    .replace(/\n{3,}/g, "\n\n")
    .trim();
}

function splitLongSegment(segment: string, maxLength: number) {
  if (segment.length <= maxLength) {
    return [segment];
  }

  const sentences = segment
    .split(/(?<=[。！？!?；;])\s*/)
    .map((item) => item.trim())
    .filter(Boolean);

  const pieces: string[] = [];
  let current = "";

  for (const sentence of sentences.length > 1 ? sentences : [segment]) {
    if (sentence.length > maxLength) {
      if (current) {
        pieces.push(current);
        current = "";
      }
      for (let index = 0; index < sentence.length; index += maxLength) {
        pieces.push(sentence.slice(index, index + maxLength).trim());
      }
      continue;
    }

    const next = current ? `${current}${sentence}` : sentence;
    if (next.length > maxLength && current) {
      pieces.push(current);
      current = sentence;
    } else {
      current = next;
    }
  }

  if (current) {
    pieces.push(current);
  }

  return pieces;
}

function splitBalanced(text: string) {
  const midpoint = Math.ceil(text.length / 2);
  const punctuationIndex = text
    .slice(Math.max(0, midpoint - 120), Math.min(text.length, midpoint + 120))
    .search(/[。！？!?；;]\s*/);

  if (punctuationIndex >= 0) {
    const start = Math.max(0, midpoint - 120);
    const splitAt = start + punctuationIndex + 1;
    return [text.slice(0, splitAt).trim(), text.slice(splitAt).trim()];
  }

  return [text.slice(0, midpoint).trim(), text.slice(midpoint).trim()];
}

export function chunkText(text: string, minLength = defaultMinLength, maxLength = defaultMaxLength) {
  const normalized = normalizeText(text);
  if (!normalized) {
    return [];
  }

  const segments = normalized
    .split(/\n{2,}/)
    .flatMap((paragraph) => splitLongSegment(paragraph.trim(), maxLength))
    .filter(Boolean);

  const chunks: string[] = [];
  let current = "";

  for (const segment of segments) {
    const next = current ? `${current}\n\n${segment}` : segment;
    if (next.length <= maxLength) {
      current = next;
      continue;
    }

    if (current) {
      chunks.push(current);
    }

    current = segment;
  }

  if (current) {
    chunks.push(current);
  }

  const merged: string[] = [];
  for (const chunk of chunks) {
    const previous = merged[merged.length - 1];
    if (previous && previous.length < minLength && previous.length + chunk.length + 2 <= maxLength) {
      merged[merged.length - 1] = `${previous}\n\n${chunk}`;
    } else {
      merged.push(chunk);
    }
  }

  const last = merged[merged.length - 1];
  const previous = merged[merged.length - 2];
  if (merged.length > 1 && last.length < minLength && previous.length + last.length + 2 <= maxLength * 2) {
    const [firstHalf, secondHalf] = splitBalanced(`${previous}\n\n${last}`);
    merged.splice(merged.length - 2, 2, firstHalf, secondHalf);
  }

  return merged;
}
