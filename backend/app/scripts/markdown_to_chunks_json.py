#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
将 Markdown 文档按标题层级解析，并输出可追溯的 JSON 块。

规则：
1. 标题层级仅依据 # 的数量判断，支持 # 到 ######。
2. 每个标题之后、下一个任意级别标题之前的正文，作为一个 section。
3. section 内按约 500 个非空白字符切块，不跨越标题边界。
4. 每个块保留：chunk_id、book_name、source_file、section_id、
   chunk_index、heading_path、content。
5. # 与 ##、## 与 ### 等标题之间存在正文时，会归属于前一个标题。
6. 首个标题之前的正文默认保留为 heading_path=[]；
   可使用 --skip-preamble 跳过。

示例：
    python markdown_to_chunks_json.py "人工智能导论.md"
    python markdown_to_chunks_json.py "教材目录" -r -o output_json
    python markdown_to_chunks_json.py "人工智能导论.md" --book-name "人工智能导论（通识版）"
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


HEADING_RE = re.compile(r"^\s*(#{1,6})\s+(.+?)\s*$")
FENCE_RE = re.compile(r"^\s*(`{3,}|~{3,})")


@dataclass
class Section:
    section_id: str
    heading_path: list[dict[str, object]]
    content: str


def read_text(path: Path) -> tuple[str, str]:
    """兼容常见中文文本编码。"""
    for encoding in ("utf-8-sig", "utf-8", "gb18030"):
        try:
            return path.read_text(encoding=encoding), encoding
        except UnicodeDecodeError:
            continue
    raise UnicodeError(f"无法识别文件编码：{path}")


def normalize_text(text: str) -> str:
    """清理行尾空白，并将连续空行压缩为一个空行。"""
    lines = [line.rstrip() for line in text.splitlines()]
    output: list[str] = []
    previous_blank = False

    for line in lines:
        blank = not line.strip()
        if blank and previous_blank:
            continue
        output.append(line)
        previous_blank = blank

    return "\n".join(output).strip()


def parse_markdown_sections(
    text: str,
    *,
    keep_preamble: bool = True,
) -> list[Section]:
    """按标题边界解析 section，正文归属于最近出现的标题。"""
    heading_stack: dict[int, str] = {}
    current_lines: list[str] = []
    sections: list[Section] = []
    section_counter = 0
    inside_fence = False
    fence_char = ""
    fence_len = 0

    def current_path() -> list[dict[str, object]]:
        return [
            {"level": level, "title": heading_stack[level]}
            for level in sorted(heading_stack)
        ]

    def flush_section() -> None:
        nonlocal section_counter, current_lines
        content = normalize_text("\n".join(current_lines))
        current_lines = []

        if not content:
            return

        path = current_path()
        if not path and not keep_preamble:
            return

        section_counter += 1
        sections.append(
            Section(
                section_id=f"section_{section_counter:06d}",
                heading_path=path,
                content=content,
            )
        )

    for raw_line in text.splitlines():
        fence_match = FENCE_RE.match(raw_line)

        if inside_fence:
            current_lines.append(raw_line)
            if fence_match:
                fence = fence_match.group(1)
                if fence[0] == fence_char and len(fence) >= fence_len:
                    inside_fence = False
                    fence_char = ""
                    fence_len = 0
            continue

        if fence_match:
            fence = fence_match.group(1)
            inside_fence = True
            fence_char = fence[0]
            fence_len = len(fence)
            current_lines.append(raw_line)
            continue

        heading_match = HEADING_RE.match(raw_line)
        if heading_match:
            flush_section()

            level = len(heading_match.group(1))
            title = heading_match.group(2).strip()

            # 新标题出现时，清除同级及其全部下级标题。
            for old_level in list(heading_stack):
                if old_level >= level:
                    del heading_stack[old_level]

            heading_stack[level] = title
            continue

        current_lines.append(raw_line)

    flush_section()
    return sections


def visible_char_count(text: str) -> int:
    """按“字”统计：忽略空格、换行和制表符。"""
    return len(re.sub(r"\s+", "", text))


def hard_split(text: str, max_chars: int) -> list[str]:
    """对单个超长片段强制切分，同时尽量保留原始空白。"""
    chunks: list[str] = []
    buffer: list[str] = []
    count = 0

    for char in text:
        if not char.isspace():
            count += 1
        buffer.append(char)

        if count >= max_chars:
            piece = "".join(buffer).strip()
            if piece:
                chunks.append(piece)
            buffer = []
            count = 0

    tail = "".join(buffer).strip()
    if tail:
        chunks.append(tail)

    return chunks


def split_into_units(text: str) -> list[str]:
    """优先按自然段，再按中文句末标点拆分，保留标点。"""
    units: list[str] = []
    paragraphs = re.split(r"\n\s*\n", text.strip())
    sentence_re = re.compile(r"(?<=[。！？!?；;])")

    for paragraph in paragraphs:
        paragraph = paragraph.strip()
        if not paragraph:
            continue

        sentences = [
            item.strip()
            for item in sentence_re.split(paragraph)
            if item.strip()
        ]
        units.extend(sentences or [paragraph])

    return units


def split_text(text: str, max_chars: int = 500) -> list[str]:
    """按不超过 max_chars 个非空白字符切块，优先保持句子完整。"""
    if max_chars <= 0:
        raise ValueError("max_chars 必须大于 0。")

    units = split_into_units(text)
    chunks: list[str] = []
    current: list[str] = []
    current_count = 0

    def flush_current() -> None:
        nonlocal current, current_count
        if current:
            chunk = "\n".join(current).strip()
            if chunk:
                chunks.append(chunk)
        current = []
        current_count = 0

    for unit in units:
        unit_count = visible_char_count(unit)

        if unit_count > max_chars:
            flush_current()
            chunks.extend(hard_split(unit, max_chars))
            continue

        if current and current_count + unit_count > max_chars:
            flush_current()

        current.append(unit)
        current_count += unit_count

    flush_current()
    return chunks


def infer_book_name(path: Path) -> str:
    """默认使用文件名作为书名，并去掉末尾常见的重复文件编号。"""
    name = path.stem.strip()
    name = re.sub(r"\s*\(\d+\)\s*$", "", name)
    return name.strip() or path.stem


def safe_id_prefix(book_name: str) -> str:
    """生成适合 chunk_id 的稳定前缀。"""
    prefix = re.sub(r"[^\w\u4e00-\u9fff]+", "", book_name, flags=re.UNICODE)
    return prefix[:30] or "book"


def build_chunks(
    source: Path,
    *,
    book_name: str | None = None,
    max_chars: int = 500,
    keep_preamble: bool = True,
) -> list[dict[str, object]]:
    text, _encoding = read_text(source)
    sections = parse_markdown_sections(text, keep_preamble=keep_preamble)

    resolved_book_name = book_name or infer_book_name(source)
    id_prefix = safe_id_prefix(resolved_book_name)

    result: list[dict[str, object]] = []
    global_chunk_counter = 0

    for section in sections:
        section_chunks = split_text(section.content, max_chars=max_chars)

        for chunk_index, content in enumerate(section_chunks, start=1):
            global_chunk_counter += 1
            result.append(
                {
                    "chunk_id": f"{id_prefix}_{global_chunk_counter:06d}",
                    "book_name": resolved_book_name,
                    "source_file": source.name,
                    "section_id": section.section_id,
                    "chunk_index": chunk_index,
                    "heading_path": section.heading_path,
                    "content": content,
                }
            )

    return result


def collect_markdown_files(input_path: Path, recursive: bool) -> list[Path]:
    if input_path.is_file():
        if input_path.suffix.lower() != ".md":
            raise ValueError(f"输入文件不是 Markdown：{input_path}")
        return [input_path.resolve()]

    if input_path.is_dir():
        iterator: Iterable[Path]
        iterator = input_path.rglob("*.md") if recursive else input_path.glob("*.md")
        return sorted(
            (path.resolve() for path in iterator if path.is_file()),
            key=lambda item: str(item).lower(),
        )

    raise FileNotFoundError(f"输入路径不存在：{input_path}")


def write_json(data: list[dict[str, object]], destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    # Path.write_text(newline=...) 需要 Python 3.10+，改用 open() 以兼容 3.8。
    with destination.open("w", encoding="utf-8", newline="\n") as file:
        json.dump(data, file, ensure_ascii=False, indent=2)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="将 Markdown 按标题路径和约 500 字切分为可追溯 JSON。"
    )
    parser.add_argument(
        "input",
        help="单个 .md 文件或包含 Markdown 文件的目录。",
    )
    parser.add_argument(
        "-o",
        "--output",
        default="chunked_json",
        help=(
            "输出目录；处理单文件时也可指定以 .json 结尾的输出文件。"
            "默认：chunked_json"
        ),
    )
    parser.add_argument(
        "-r",
        "--recursive",
        action="store_true",
        help="输入为目录时，递归处理子目录。",
    )
    parser.add_argument(
        "--max-chars",
        type=int,
        default=500,
        help="每块最多包含的非空白字符数，默认 500。",
    )
    parser.add_argument(
        "--book-name",
        help="手动指定书名。仅处理单个 Markdown 文件时可用。",
    )
    parser.add_argument(
        "--skip-preamble",
        action="store_true",
        help="跳过首个标题之前的正文。",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()

    try:
        input_path = Path(args.input).expanduser().resolve()
        files = collect_markdown_files(input_path, args.recursive)

        if not files:
            print("未找到 Markdown 文件。", file=sys.stderr)
            return 1

        if args.book_name and len(files) != 1:
            print("--book-name 只能用于单个 Markdown 文件。", file=sys.stderr)
            return 1

        output_arg = Path(args.output).expanduser()
        single_json_output = len(files) == 1 and output_arg.suffix.lower() == ".json"

        total_chunks = 0

        for source in files:
            chunks = build_chunks(
                source,
                book_name=args.book_name,
                max_chars=args.max_chars,
                keep_preamble=not args.skip_preamble,
            )

            if single_json_output:
                destination = output_arg.resolve()
            else:
                output_dir = output_arg.resolve()
                destination = output_dir / f"{source.stem}.chunks.json"

            write_json(chunks, destination)
            total_chunks += len(chunks)

            print(
                f"[完成] {source.name} -> {destination} | "
                f"生成 {len(chunks)} 个块"
            )

        print(f"处理结束：{len(files)} 个文件，共 {total_chunks} 个块。")
        return 0

    except Exception as exc:
        print(f"处理失败：{exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
