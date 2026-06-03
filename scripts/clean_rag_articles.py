#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parent


NOISE_LINE_PATTERNS = [
    r"^>?\s*原文地址[:：]",
    r"^>?\s*原文链接[:：]",
    r"^>?\s*转载[:：]",
    r"^>?\s*来源[:：]",
    r"^>?\s*作者[:：]",
    r"^>?\s*编辑[:：]",
    r"^>?\s*责任编辑[:：]",
    r"^>?\s*审核[:：]",
    r"^>?\s*声明[:：]",
    r"^>?\s*本文仅供",
    r"^>?\s*仅供医疗卫生",
    r"^>?\s*仅供参考",
    r"^>?\s*点击蓝字",
    r"^>?\s*关注我们",
    r"^>?\s*欢迎关注",
    r"^>?\s*扫码",
    r"^>?\s*公众号",
    r"^>?\s*广告",
    r"^>?\s*推广",
    r"^>?\s*加群",
    r"^>?\s*入群",
    r"^>?\s*阅读原文",
    r"^>?\s*请点击",
    r"^>?\s*点击阅读",
    r"^>?\s*转发",
    r"^>?\s*分享",
    r"^>?\s*点赞",
    r"^>?\s*留言",
]

NOISE_SUBSTRINGS = [
    "data:image/svg+xml",
    "Lucide",
    ".__page_content__",
    "pay_subscribe_notice",
    "__bottom-bar__",
    "blockquote.source",
    "text_content",
    "picture_content",
    "mmbiz.qpic.cn",
]

KEEP_IF_CONTAINS = [
    "病例",
    "结果",
    "结论",
    "方法",
    "目的",
    "背景",
    "讨论",
]

BUTTON_WORDS = {"阅读", "赞", "分享", "推荐", "留言"}


@dataclass
class CleanStats:
    total_files: int = 0
    written_files: int = 0
    removed_lines: int = 0
    removed_by_dir: dict[str, int] | None = None
    written_by_dir: dict[str, int] | None = None

    def __post_init__(self) -> None:
        if self.removed_by_dir is None:
            self.removed_by_dir = {}
        if self.written_by_dir is None:
            self.written_by_dir = {}


def normalize_title_preamble(text: str) -> str:
    lines = text.splitlines()
    if not lines:
        return text

    first = lines[0]
    cut_patterns = [
        r"\s+\\?\*\s*\{.*$",
        r"\s+body\s*\{.*$",
        r"\s+\.?__page_content__\s*\{.*$",
        r"\s+\.title\s*\{.*$",
        r"\s+\.?__meta__\s*\{.*$",
        r"\s+blockquote\.source\s*\{.*$",
        r"\s+\.text_content\s*\{.*$",
    ]
    for pattern in cut_patterns:
        m = re.search(pattern, first)
        if m:
            first = first[: m.start()].rstrip()
            break
    css_markers = [
        ".__page_content__ {",
        ".title {",
        ".__meta__ {",
        "blockquote.source {",
        ".text_content {",
        "body { font-family:",
        "* { margin: 0; padding: 0; outline: 0; }",
    ]
    for marker in css_markers:
        idx = first.find(marker)
        if idx != -1:
            first = first[:idx].rstrip()
            break
    lines[0] = first.strip()
    return "\n".join(lines)


def is_noise_line(line: str) -> bool:
    stripped = line.strip()
    if not stripped:
        return False

    if stripped.startswith("![](data:image/svg+xml"):
        return True
    if any(token in stripped for token in NOISE_SUBSTRINGS):
        return True

    for pattern in NOISE_LINE_PATTERNS:
        if re.search(pattern, stripped, flags=re.IGNORECASE):
            return True

    if stripped in BUTTON_WORDS:
        return True

    if stripped.startswith("**点击蓝字") or stripped == "｜关注我们":
        return True

    if stripped.startswith("原创 ") or stripped.startswith("原创："):
        return True

    if stripped.startswith("本文旨在") and "医疗" in stripped:
        return True

    short_promotional = (
        len(stripped) <= 80
        and any(word in stripped for word in ["关注", "扫码", "转发", "加群", "入群", "留言", "点击蓝字", "阅读原文"])
    )
    if short_promotional and not any(word in stripped for word in KEEP_IF_CONTAINS):
        return True

    if len(stripped) >= 400 and any(word in stripped for word in ["阅读", "赞", "分享", "留言", "推荐"]):
        return True

    if stripped.startswith("![](") and any(word in stripped for word in ["mmbiz", "svg", "png", "jpg"]):
        return True

    return False


def clean_markdown(text: str) -> tuple[str, int]:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = normalize_title_preamble(text)

    cleaned_lines: list[str] = []
    removed = 0
    blank_run = 0
    skip_related = False
    for line in text.splitlines():
        stripped = line.strip()

        if skip_related:
            if stripped:
                removed += 1
            continue

        if stripped in {"往期热文", "相关推荐", "相关内容", "相关阅读", "更多推荐", "延伸阅读"}:
            skip_related = True
            removed += 1
            continue

        if is_noise_line(line):
            removed += 1
            continue

        stripped = line.rstrip()
        if not stripped:
            blank_run += 1
            if blank_run > 2:
                removed += 1
                continue
            cleaned_lines.append("")
            continue

        if re.fullmatch(r"[=\-]{3,}", stripped):
            removed += 1
            continue

        blank_run = 0
        cleaned_lines.append(stripped)

    non_empty = [line for line in cleaned_lines if line.strip()]
    if len(non_empty) >= 2 and non_empty[0] == non_empty[1]:
        removed += 1
        seen_first = False
        deduped: list[str] = []
        for line in cleaned_lines:
            if line.strip() == non_empty[0]:
                if not seen_first:
                    deduped.append(line)
                    seen_first = True
                else:
                    continue
            else:
                deduped.append(line)
        cleaned_lines = deduped

    cleaned = "\n".join(cleaned_lines).strip()
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    cleaned += "\n"
    return cleaned, removed


def output_path_for(src: Path) -> Path:
    rel_parts = src.relative_to(ROOT).parts
    if not rel_parts:
        raise ValueError(f"cannot derive output path for {src}")

    if len(rel_parts) == 1:
        return ROOT / "_clean" / rel_parts[0]

    top = rel_parts[0]
    top_dir = ROOT / f"{top}_clean"
    return top_dir.joinpath(*rel_parts[1:])


def source_group_for(src: Path) -> str:
    rel_parts = src.relative_to(ROOT).parts
    if not rel_parts:
        return "."
    if len(rel_parts) == 1:
        return "<root>"
    return rel_parts[0]


def iter_source_files() -> list[Path]:
    paths: list[Path] = []
    for path in ROOT.rglob("*.md"):
        if any(part.endswith("_clean") for part in path.parts):
            continue
        if "docs" in path.parts:
            continue
        if path.parts[0] == "wechat-mp-monitor":
            continue
        if path.name == "skills.md":
            continue
        if path.name.startswith("README"):
            continue
        paths.append(path)
    return sorted(paths)


def main() -> int:
    parser = argparse.ArgumentParser(description="Clean markdown files for RAG ingestion.")
    parser.add_argument("--dry-run", action="store_true", help="Print stats without writing files.")
    parser.add_argument("--limit", type=int, default=0, help="Process only the first N files.")
    parser.add_argument("--report", action="store_true", help="Print per-directory summary at the end.")
    parser.add_argument("--include-root", action="append", default=[], help="Extra top-level directory names to include.")
    parser.add_argument("--include-root-file", action="append", default=[], help="Extra files in the root directory to include.")
    args = parser.parse_args()

    files = iter_source_files()
    requested_root_files = {Path(name).name for name in args.include_root_file}
    if requested_root_files:
        files = [p for p in files if p.parent == ROOT and p.name in requested_root_files]
    if args.include_root_file:
        files = [p for p in files if p.parent != ROOT or p.name in requested_root_files]
    if args.include_root:
        include_roots = set(args.include_root)
        files = [p for p in files if source_group_for(p) in include_roots]
    if args.limit and args.limit > 0:
        files = files[: args.limit]

    stats = CleanStats(total_files=len(files))

    for src in files:
        raw = src.read_text(encoding="utf-8", errors="ignore")
        cleaned, removed = clean_markdown(raw)
        stats.removed_lines += removed

        dst = output_path_for(src)
        if not args.dry_run:
            dst.parent.mkdir(parents=True, exist_ok=True)
            dst.write_text(cleaned, encoding="utf-8")
        stats.written_files += 1
        group = source_group_for(src)
        stats.removed_by_dir[group] = stats.removed_by_dir.get(group, 0) + removed
        stats.written_by_dir[group] = stats.written_by_dir.get(group, 0) + 1
        print(f"[clean] {src.relative_to(ROOT)} -> {dst.relative_to(ROOT)} removed_lines={removed}")

    print(
        f"[done] files={stats.total_files} written={stats.written_files} "
        f"removed_lines={stats.removed_lines}"
    )
    if args.report:
        print("[report] by_dir")
        for group in sorted(stats.written_by_dir):
            print(
                f"  - {group}: files={stats.written_by_dir[group]} "
                f"removed_lines={stats.removed_by_dir[group]}"
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
