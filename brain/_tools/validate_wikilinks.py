#!/usr/bin/env python3
"""Wikilink validation mirroring Obsidian resolution semantics.

Resolves [[links]] by note filename anywhere in the vault, supports path links,
aliases (frontmatter `aliases:`), and ignores heading/block (#) + display (|) parts.
Flags only links that would NOT resolve in Obsidian. Reports unresolved + ambiguous.

Exit 0 = no unresolved links. Exit 1 = unresolved links found.
"""
import re
import sys
from pathlib import Path

VAULT = Path(__file__).resolve().parent.parent
LINK_RE = re.compile(r"\[\[([^\]]+)\]\]")
ALIAS_RE = re.compile(r"^aliases:\s*$")


def md_files():
    return [p for p in VAULT.rglob("*.md") if "_tools" not in p.parts]


def parse_aliases(text):
    """Very small YAML-ish alias parser for the frontmatter block."""
    aliases = []
    if not text.startswith("---"):
        return aliases
    end = text.find("\n---", 3)
    if end == -1:
        return aliases
    fm = text[3:end].splitlines()
    in_aliases = False
    for line in fm:
        if re.match(r"^aliases:\s*\[", line):  # inline list
            inner = line.split("[", 1)[1].rstrip("]")
            aliases += [a.strip().strip('"\'') for a in inner.split(",") if a.strip()]
            continue
        if ALIAS_RE.match(line):
            in_aliases = True
            continue
        if in_aliases:
            m = re.match(r"^\s*-\s*(.+)$", line)
            if m:
                aliases.append(m.group(1).strip().strip('"\''))
            elif line and not line.startswith(" "):
                in_aliases = False
    return aliases


def build_index(files):
    by_base = {}
    by_path = {}
    by_alias = {}
    for p in files:
        rel = p.relative_to(VAULT)
        base = p.stem.lower()
        by_base.setdefault(base, []).append(rel)
        by_path[str(rel.with_suffix("")).lower()] = rel
        by_path[str(rel).lower()] = rel
        try:
            aliases = parse_aliases(p.read_text(encoding="utf-8"))
        except Exception:
            aliases = []
        for a in aliases:
            by_alias.setdefault(a.lower(), []).append(rel)
    return by_base, by_path, by_alias


def normalize(target):
    target = target.split("|", 1)[0]          # drop display text
    target = target.split("#", 1)[0]          # drop heading/block
    return target.strip()


def main():
    files = md_files()
    by_base, by_path, by_alias = build_index(files)
    unresolved, ambiguous = [], []
    total = 0
    for p in files:
        rel = p.relative_to(VAULT)
        text = p.read_text(encoding="utf-8")
        for m in LINK_RE.finditer(text):
            raw = m.group(1)
            tgt = normalize(raw)
            if not tgt:
                continue  # same-file heading link
            total += 1
            key = tgt.lower()
            norm = key[:-3] if key.endswith(".md") else key
            if "/" in tgt:
                if norm in by_path or key in by_path:
                    continue
                unresolved.append((str(rel), raw))
                continue
            if norm in by_base:
                if len(by_base[norm]) > 1:
                    ambiguous.append((str(rel), raw, [str(x) for x in by_base[norm]]))
                continue
            if norm in by_alias:
                if len(by_alias[norm]) > 1:
                    ambiguous.append((str(rel), raw, [str(x) for x in by_alias[norm]]))
                continue
            unresolved.append((str(rel), raw))

    print(f"Scanned {len(files)} notes, {total} wikilinks.")
    if ambiguous:
        print(f"\nAMBIGUOUS ({len(ambiguous)}):")
        for src, raw, tgts in ambiguous:
            print(f"  {src}: [[{raw}]] -> {tgts}")
    if unresolved:
        print(f"\nUNRESOLVED ({len(unresolved)}):")
        for src, raw in unresolved:
            print(f"  {src}: [[{raw}]]")
        return 1
    print("PASS: 0 unresolved wikilinks." + (" (ambiguous are warnings)" if ambiguous else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
