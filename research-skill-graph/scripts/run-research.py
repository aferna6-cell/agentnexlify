#!/usr/bin/env python3
"""
Research Skill Graph engine.

Picks the next pending question from research-queue.md (or one passed via
--question), assembles methodology + lenses into a system prompt, calls the
Anthropic API, parses the structured response into project output files,
and updates the log + knowledge base. Open-questions auto-append to the
queue so the system iterates itself.
"""

import argparse
import datetime as dt
import os
import pathlib
import re
import subprocess
import sys
from typing import Optional

try:
    from anthropic import Anthropic
except ImportError:
    sys.exit("missing dependency: pip install -r scripts/requirements.txt")

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None


ROOT = pathlib.Path(__file__).resolve().parent.parent
INDEX = ROOT / "index.md"
METHODOLOGY = ROOT / "methodology"
LENSES = ROOT / "lenses"
PROJECTS = ROOT / "projects"
LOG = ROOT / "research-log.md"
QUEUE = ROOT / "research-queue.md"
CONCEPTS = ROOT / "knowledge" / "concepts.md"
DATA_POINTS = ROOT / "knowledge" / "data-points.md"

DEFAULT_MODEL = os.environ.get("RESEARCH_MODEL", "claude-sonnet-4-6")
MAX_TOKENS = int(os.environ.get("RESEARCH_MAX_TOKENS", "32000"))
MAX_RETRIES = int(os.environ.get("RESEARCH_MAX_RETRIES", "5"))
QUEUE_PENDING_CAP = int(os.environ.get("RESEARCH_QUEUE_CAP", "50"))
AUTO_ITERATED_MARKER = "<!-- open-questions from completed projects land below this line -->"


def atomic_write(path: pathlib.Path, content: str) -> None:
    """Write content to path via temp file + rename for crash-safety."""
    tmp = path.with_suffix(path.suffix + f".tmp.{os.getpid()}")
    tmp.write_text(content)
    os.replace(tmp, path)


def atomic_append(path: pathlib.Path, content: str) -> None:
    existing = path.read_text() if path.exists() else ""
    atomic_write(path, existing + content)


def count_pending(text: str) -> int:
    in_fence = False
    count = 0
    for line in text.splitlines():
        if line.lstrip().startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        if re.match(r"^- \[ \]\s", line):
            count += 1
    return count


def load_env() -> None:
    if load_dotenv is None:
        return
    for candidate in [
        ROOT.parent / "backend" / ".env",
        ROOT.parent / ".env",
        pathlib.Path.home() / ".env",
    ]:
        if candidate.exists():
            load_dotenv(candidate, override=False)


def slugify(text: str, max_len: int = 50) -> str:
    text = text.lower().strip()
    text = re.sub(r"\(depth:[^)]*\)", "", text)
    text = re.sub(r"[^a-z0-9]+", "-", text).strip("-")
    return text[:max_len] or "untitled"


def parse_depth(question: str) -> str:
    match = re.search(r"\(depth:(quick|standard|deep)\)", question)
    return match.group(1) if match else "standard"


def strip_metadata(question: str) -> str:
    return re.sub(r"\s*\(depth:[^)]*\)\s*", "", question).strip()


def pick_queue_item() -> Optional[tuple[int, str]]:
    if not QUEUE.exists():
        return None
    in_fence = False
    for i, line in enumerate(QUEUE.read_text().splitlines()):
        if line.lstrip().startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        m = re.match(r"^- \[ \]\s*(.+)$", line)
        if m:
            return i, m.group(1).strip()
    return None


def mark_queue_done(line_index: int) -> None:
    lines = QUEUE.read_text().splitlines()
    lines[line_index] = lines[line_index].replace("- [ ]", "- [x]", 1)
    atomic_write(QUEUE, "\n".join(lines) + "\n")


def append_auto_iterated(questions: list[str], cap: int = QUEUE_PENDING_CAP) -> int:
    if not questions:
        return 0
    text = QUEUE.read_text()
    pending = count_pending(text)
    slots = max(0, cap - pending)
    if slots == 0:
        print(
            f"queue at cap ({cap} pending) — skipping {len(questions)} new questions. "
            f"Prune queue or raise RESEARCH_QUEUE_CAP to resume auto-iteration.",
            file=sys.stderr,
        )
        return 0
    if AUTO_ITERATED_MARKER not in text:
        text += f"\n\n{AUTO_ITERATED_MARKER}\n"
    accepted = [q.strip() for q in questions[:slots] if q.strip()]
    new_lines = [f"- [ ] {q}" for q in accepted]
    if len(questions) > slots:
        print(f"queue cap: kept {len(accepted)} of {len(questions)} new questions (cap={cap})")
    text = text.rstrip() + "\n" + "\n".join(new_lines) + "\n"
    atomic_write(QUEUE, text)
    return len(accepted)


def read_all(path: pathlib.Path, glob: str = "*.md") -> str:
    parts = []
    for f in sorted(path.glob(glob)):
        parts.append(f"## FILE: {f.relative_to(ROOT)}\n\n{f.read_text()}")
    return "\n\n---\n\n".join(parts)


def build_system_prompt() -> str:
    return (
        "You are the Research Skill Graph engine. Execute the instructions in "
        "index.md exactly. Use only the methodology and lens files provided "
        "below as your operating procedure. Produce the final response in the "
        "strict output format specified at the bottom of index.md — the "
        "===MARKERS=== are non-negotiable because downstream automation parses "
        "them.\n\n"
        f"=== INDEX ===\n{INDEX.read_text()}\n\n"
        f"=== METHODOLOGY ===\n{read_all(METHODOLOGY)}\n\n"
        f"=== LENSES ===\n{read_all(LENSES)}\n"
    )


def load_prior_context() -> str:
    bits = []
    if LOG.exists():
        bits.append(f"=== RESEARCH LOG (prior projects) ===\n{LOG.read_text()[:6000]}")
    if CONCEPTS.exists():
        bits.append(f"=== CONCEPTS ===\n{CONCEPTS.read_text()[:4000]}")
    if DATA_POINTS.exists():
        bits.append(f"=== DATA POINTS ===\n{DATA_POINTS.read_text()[:4000]}")
    return "\n\n".join(bits)


def call_claude(question: str, depth: str, model: str) -> str:
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        sys.exit("ANTHROPIC_API_KEY not set (checked env and backend/.env)")
    client = Anthropic(api_key=api_key, max_retries=MAX_RETRIES)
    system = build_system_prompt()
    prior = load_prior_context()
    user = (
        f"Research question: {question}\n"
        f"Research depth: {depth} (see research-frameworks.md)\n"
        f"Today's date: {dt.date.today().isoformat()}\n\n"
        f"Follow the execution instructions in index.md. Run every applicable "
        f"lens, document contradictions honestly, and finish with the strict "
        f"===SECTION=== output format.\n\n"
        f"{prior}"
    )
    resp = client.messages.create(
        model=model,
        max_tokens=MAX_TOKENS,
        system=system,
        messages=[{"role": "user", "content": user}],
    )
    return "".join(block.text for block in resp.content if block.type == "text")


def parse_sections(text: str) -> dict[str, str]:
    markers = [
        "EXECUTIVE_SUMMARY",
        "DEEP_DIVE",
        "KEY_PLAYERS",
        "OPEN_QUESTIONS",
        "NEW_CONCEPTS",
        "NEW_DATA_POINTS",
    ]
    sections = {m: "" for m in markers}
    for m in markers:
        pattern = rf"===\s*{m}\s*===\s*\n(.*?)(?=(?:\n===\s*(?:{'|'.join(markers)})\s*===)|\Z)"
        match = re.search(pattern, text, flags=re.DOTALL)
        if match:
            sections[m] = match.group(1).strip()
    return sections


def write_project(slug: str, question: str, depth: str, model: str, sections: dict[str, str], raw: str) -> pathlib.Path:
    folder = PROJECTS / slug
    if folder.exists():
        slug = f"{slug}-{dt.datetime.now().strftime('%H%M%S')}"
        folder = PROJECTS / slug
    folder.mkdir(parents=True, exist_ok=True)

    meta = (
        f"# {question}\n\n"
        f"**Depth:** {depth}  |  **Model:** {model}  |  **Date:** {dt.date.today().isoformat()}\n\n"
    )

    (folder / "executive-summary.md").write_text(meta + sections.get("EXECUTIVE_SUMMARY", "(missing)"))
    (folder / "deep-dive.md").write_text(meta + sections.get("DEEP_DIVE", "(missing)"))
    (folder / "key-players.md").write_text(meta + sections.get("KEY_PLAYERS", "(missing)"))
    (folder / "open-questions.md").write_text(meta + sections.get("OPEN_QUESTIONS", "(missing)"))
    (folder / "_raw-response.md").write_text(raw)
    return folder


def append_log(slug: str, question: str, depth: str, model: str, exec_summary: str) -> None:
    first_lines = "\n".join(line for line in exec_summary.splitlines() if line.strip())[:400]
    entry = (
        f"\n## {dt.date.today().isoformat()} — {slug}\n\n"
        f"**Question:** {question}\n"
        f"**Depth:** {depth}\n"
        f"**Folder:** [[projects/{slug}]]\n"
        f"**Model:** {model}\n\n"
        f"### Headline\n{first_lines}\n\n---\n"
    )
    atomic_append(LOG, entry)


def append_concepts(text: str, slug: str) -> None:
    if not text.strip():
        return
    stamped = f"\n<!-- from projects/{slug} on {dt.date.today().isoformat()} -->\n{text.strip()}\n"
    atomic_append(CONCEPTS, stamped)


def append_data_points(text: str, slug: str) -> None:
    if not text.strip():
        return
    stamped = f"\n<!-- from projects/{slug} on {dt.date.today().isoformat()} -->\n{text.strip()}\n"
    atomic_append(DATA_POINTS, stamped)


def extract_open_questions(text: str) -> list[str]:
    return [m.group(1).strip() for m in re.finditer(r"^- \[ \]\s*(.+)$", text, flags=re.MULTILINE)]


def git_commit(slug: str) -> None:
    repo = str(ROOT.parent)
    try:
        subprocess.run(["git", "-C", repo, "add", "research-skill-graph"], check=True)
        subprocess.run(
            [
                "git",
                "-C",
                repo,
                "commit",
                "-m",
                f"research: {slug}",
                "-m",
                "auto-generated research run",
            ],
            check=True,
        )
    except subprocess.CalledProcessError as e:
        print(f"git commit skipped (nothing to commit or hook failure): {e}", file=sys.stderr)


def run(question: Optional[str], model: str, auto_commit: bool) -> int:
    queue_line = None
    if question is None:
        picked = pick_queue_item()
        if picked is None:
            print("queue empty — nothing to research")
            return 0
        queue_line, question = picked
        print(f"picked from queue (line {queue_line}): {question}")

    depth = parse_depth(question)
    clean_q = strip_metadata(question)
    slug = slugify(clean_q)
    print(f"slug={slug} depth={depth} model={model}")

    raw = call_claude(clean_q, depth, model)
    sections = parse_sections(raw)

    folder = write_project(slug, clean_q, depth, model, sections, raw)

    parse_ok = bool(sections.get("EXECUTIVE_SUMMARY") and sections.get("DEEP_DIVE"))
    if not parse_ok:
        print(
            f"WARNING: response missing required ===EXECUTIVE_SUMMARY=== or "
            f"===DEEP_DIVE=== markers. Raw response saved to {folder}/"
            f"_raw-response.md. Queue item NOT marked done so it retries.",
            file=sys.stderr,
        )
        return 2

    append_log(slug, clean_q, depth, model, sections.get("EXECUTIVE_SUMMARY", ""))
    append_concepts(sections.get("NEW_CONCEPTS", ""), slug)
    append_data_points(sections.get("NEW_DATA_POINTS", ""), slug)

    new_questions = extract_open_questions(sections.get("OPEN_QUESTIONS", ""))
    append_auto_iterated(new_questions)
    print(f"wrote {folder}")
    print(f"appended {len(new_questions)} new questions to queue")

    if queue_line is not None:
        mark_queue_done(queue_line)

    if auto_commit:
        git_commit(slug)

    return 0


def main() -> int:
    load_env()
    p = argparse.ArgumentParser()
    p.add_argument("--question", help="ad-hoc question (skips queue)")
    p.add_argument("--model", default=DEFAULT_MODEL)
    p.add_argument("--auto-commit", action="store_true", help="git commit after successful run")
    args = p.parse_args()
    try:
        return run(args.question, args.model, args.auto_commit)
    except Exception as e:
        print(f"run failed: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
