#!/usr/bin/env python3
"""Smoke-test skill trigger fixtures without calling an LLM."""

import argparse
import json
import re
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ROOTS = (
    "skills/canonical",
    ".claude/skills",
    ".codex/skills",
    ".agents/skills",
    "skills/generated",
)
CANONICAL_ROOT = "skills/canonical"
DEFAULT_EVAL_DIR = "skills/evals"

STOPWORDS = {
    "about",
    "after",
    "again",
    "before",
    "build",
    "change",
    "changes",
    "check",
    "code",
    "current",
    "diff",
    "does",
    "edit",
    "editing",
    "file",
    "files",
    "find",
    "for",
    "from",
    "into",
    "main",
    "new",
    "one",
    "please",
    "run",
    "test",
    "tests",
    "the",
    "this",
    "use",
    "uses",
    "when",
    "with",
}
SHORT_KEEPERS = {"api", "ci", "db", "pr", "qa", "ui", "xss"}


def clean_scalar(value):
    value = value.strip()
    if not value:
        return ""
    if value[0] in {"'", '"'} and value[-1:] == value[0]:
        return value[1:-1]
    return value


def parse_inline_list(value):
    inner = value.strip()[1:-1].strip()
    if not inner:
        return []
    return [clean_scalar(part.strip()) for part in inner.split(",") if part.strip()]


def parse_frontmatter(path):
    text = path.read_text(encoding="utf-8", errors="replace")
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}

    frontmatter = []
    for line in lines[1:]:
        if line.strip() == "---":
            break
        frontmatter.append(line)

    data = {}
    current_key = None
    for raw_line in frontmatter:
        stripped = raw_line.strip()
        if not stripped or stripped.startswith("#"):
            continue

        if raw_line[:1].isspace():
            if current_key and stripped.startswith("- "):
                data.setdefault(current_key, [])
                if isinstance(data[current_key], list):
                    data[current_key].append(clean_scalar(stripped[2:]))
            continue

        if ":" not in raw_line:
            current_key = None
            continue

        key, value = raw_line.split(":", 1)
        key = key.strip()
        value = value.strip()
        current_key = key
        if not value:
            data[key] = []
        elif value.startswith("[") and value.endswith("]"):
            data[key] = parse_inline_list(value)
        else:
            data[key] = clean_scalar(value)

    return data


def normalize_phrase(value):
    return re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()


def tokenize(value):
    tokens = set()
    for token in re.findall(r"[a-z0-9]+", value.lower()):
        if (len(token) >= 3 or token in SHORT_KEEPERS) and token not in STOPWORDS:
            tokens.add(token)
    return tokens


def relative_display(path):
    return path.relative_to(REPO_ROOT).as_posix()


def load_skills(roots):
    records_by_name = {}
    for root in roots:
        root_path = REPO_ROOT / root
        if not root_path.exists():
            continue
        for path in sorted(root_path.rglob("SKILL.md")):
            meta = parse_frontmatter(path)
            name = clean_scalar(str(meta.get("name") or path.parent.name))
            key = name.lower()
            triggers = meta.get("triggers") or []
            if isinstance(triggers, str):
                triggers = [triggers]
            description = clean_scalar(str(meta.get("description") or ""))
            record = {
                "name": name,
                "path": path,
                "relative_path": relative_display(path),
                "root": root,
                "description": description,
                "triggers": [clean_scalar(str(item)) for item in triggers],
                "text": path.read_text(encoding="utf-8", errors="replace"),
            }
            records_by_name.setdefault(key, []).append(record)

    resolved = {}
    preferred_duplicates = []
    failures = []
    for key, records in sorted(records_by_name.items()):
        if len(records) == 1:
            resolved[key] = records[0]
            continue

        canonical_records = [record for record in records if record["root"] == CANONICAL_ROOT]
        if len(canonical_records) > 1:
            paths = ", ".join(record["relative_path"] for record in canonical_records)
            failures.append(
                f"skill '{records[0]['name']}' has multiple canonical definitions: {paths}"
            )
            continue

        if not canonical_records:
            paths = ", ".join(record["relative_path"] for record in records)
            failures.append(
                f"skill '{records[0]['name']}' is duplicated without a canonical source: {paths}"
            )
            continue

        canonical = canonical_records[0]
        drift_paths = [
            record["relative_path"]
            for record in records
            if record is not canonical and record["text"] != canonical["text"]
        ]
        if drift_paths:
            failures.append(
                f"skill '{canonical['name']}' drifts from canonical copy "
                f"{canonical['relative_path']}: {', '.join(drift_paths)}"
            )
            continue

        preferred_duplicates.append(
            f"{canonical['name']}: {', '.join(record['relative_path'] for record in records)}"
        )
        resolved[key] = canonical

    return resolved, preferred_duplicates, failures


def load_eval_entries(eval_dir):
    entries = []
    eval_path = REPO_ROOT / eval_dir
    if not eval_path.exists():
        return entries

    for path in sorted(eval_path.rglob("*.json")):
        with path.open(encoding="utf-8") as handle:
            data = json.load(handle)
        if isinstance(data, dict) and "skills" in data:
            candidates = data["skills"]
        elif isinstance(data, list):
            candidates = data
        else:
            candidates = [data]

        for item in candidates:
            if not isinstance(item, dict):
                raise ValueError(f"{path}: expected object entries")
            name = item.get("name")
            positives = item.get("positive") or item.get("positives") or []
            negatives = item.get("negative") or item.get("negatives") or []
            entries.append(
                {
                    "file": path,
                    "name": str(name or "").strip(),
                    "positive": list(positives),
                    "negative": list(negatives),
                }
            )
    return entries


def skill_signal(skill):
    source_parts = [skill["name"], skill["description"]]
    source_parts.extend(skill["triggers"])
    source = "\n".join(source_parts)
    tokens = tokenize(source)
    phrases = {normalize_phrase(skill["name"])}
    phrases.add(normalize_phrase(skill["name"].replace("-", " ")))
    for trigger in skill["triggers"]:
        phrase = normalize_phrase(trigger)
        if phrase:
            phrases.add(phrase)
    phrases.discard("")
    return tokens, phrases


def evaluate_prompt(prompt, skill, min_positive_overlap, max_negative_overlap):
    skill_tokens, skill_phrases = skill_signal(skill)
    prompt_norm = normalize_phrase(prompt)
    prompt_tokens = tokenize(prompt)
    exact = sorted(phrase for phrase in skill_phrases if phrase and phrase in prompt_norm)
    overlap = sorted(prompt_tokens & skill_tokens)
    positive_ok = bool(exact) or len(overlap) >= min_positive_overlap
    negative_ok = not exact and len(overlap) < max_negative_overlap
    return {
        "exact": exact,
        "overlap": overlap,
        "positive_ok": positive_ok,
        "negative_ok": negative_ok,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Run deterministic smoke evals for Agent Nexlify skill triggers."
    )
    parser.add_argument("--eval-dir", default=DEFAULT_EVAL_DIR)
    parser.add_argument("--roots", nargs="*", default=list(DEFAULT_ROOTS))
    parser.add_argument("--allow-missing", action="store_true")
    parser.add_argument("--min-positive-overlap", type=int, default=1)
    parser.add_argument("--max-negative-overlap", type=int, default=3)
    args = parser.parse_args(argv)

    skills, preferred_duplicates, duplicate_failures = load_skills(args.roots)
    entries = load_eval_entries(args.eval_dir)
    failures = list(duplicate_failures)
    skipped = []
    total_positive = 0
    total_negative = 0

    if not entries:
        failures.append(f"No eval fixtures found under {args.eval_dir}")

    for entry in entries:
        name = entry["name"]
        if not name:
            failures.append(f"{entry['file']}: missing skill name")
            continue
        if not entry["positive"] or not entry["negative"]:
            failures.append(f"{entry['file']}: requires positive and negative prompts")
            continue

        skill = skills.get(name.lower())
        if not skill:
            message = f"{entry['file']}: skill '{name}' not found in configured roots"
            if args.allow_missing:
                skipped.append(message)
                continue
            failures.append(message)
            continue

        for prompt in entry["positive"]:
            total_positive += 1
            result = evaluate_prompt(
                str(prompt), skill, args.min_positive_overlap, args.max_negative_overlap
            )
            if not result["positive_ok"]:
                failures.append(
                    f"{entry['file']}: positive prompt missed '{name}': {prompt!r}"
                )

        for prompt in entry["negative"]:
            total_negative += 1
            result = evaluate_prompt(
                str(prompt), skill, args.min_positive_overlap, args.max_negative_overlap
            )
            if not result["negative_ok"]:
                detail = ", ".join(result["exact"] or result["overlap"])
                failures.append(
                    f"{entry['file']}: negative prompt collides with '{name}' "
                    f"({detail}): {prompt!r}"
                )

    print("Skill trigger smoke eval")
    print(f"  skills indexed: {len(skills)}")
    print(f"  fixtures: {len(entries)}")
    print(f"  positive prompts checked: {total_positive}")
    print(f"  negative prompts checked: {total_negative}")
    if preferred_duplicates:
        print(f"  canonical duplicates resolved: {len(preferred_duplicates)}")
        for item in preferred_duplicates:
            print(f"    DUP {item}")
    if skipped:
        print(f"  skipped missing skills: {len(skipped)}")
        for item in skipped:
            print(f"    SKIP {item}")

    if failures:
        print("  result: FAIL")
        for failure in failures:
            print(f"    FAIL {failure}")
        return 1

    print("  result: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
