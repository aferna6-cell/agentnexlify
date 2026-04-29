---
paths:
  - "**/*.pdf"
---

# PDF Handling — pdftotext over Read

## Rule
For PDF files, use `pdftotext <file> -` (stdout) via Bash. Use `Read` only when the user explicitly asks to analyze images, charts, or layout inside the document.

## Why
- `Read` on a PDF rasterizes pages into the context window — burns tokens on visual rendering when text is what matters
- `pdftotext` extracts plain text only — typical 80-95% token reduction for text-heavy docs (contracts, invoices, statements, RFPs)
- AgentNexLiFy ingests tenant onboarding docs (menus, price lists, policies). Text extraction is what the wiki + KB pipeline needs

## When to use Read instead
- User asks to analyze a chart, diagram, or image inside the PDF
- Document is layout-sensitive (form fields with positional meaning)
- Scanned PDF with no embedded text layer (need OCR, not text extraction — flag to user)

## Pattern
```bash
pdftotext path/to/doc.pdf - | head -200       # quick read
pdftotext -layout path/to/doc.pdf -            # preserve column layout
pdftotext -f 1 -l 5 path/to/doc.pdf -          # pages 1-5 only
```

## Vision RAG cross-ref
If we ever ship the steal-list Vision RAG item (multimodal tenant ingest — menus, photos, before/after), that flow uses Read intentionally. This rule applies to plain document ingestion only.

## Cross-refs
- `rules/vision-3x.md` — when high-res image input is the right call
- `rules/kb-first.md` — KB ingestion pipeline target
- `.claude/skills/kb-ingest/SKILL.md` — invoke this rule when source is a PDF
