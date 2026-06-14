---
type: spike-ticket
title: "Spike — extend /kb-ingest to support YouTube + podcast URLs"
labels: [spike, kb, ingestion, low-priority]
created: 2026-04-29
status: backlog
blocked_by: []
priority: P3
---

# Spike — /kb-ingest YouTube + podcast URL support

## Why
Extracted from NotebookLM-via-terminal pattern (`knowledge-base/raw/ai-llm/notebooklm-terminal-pattern-2026-04-29.md`). NotebookLM ingests video/audio sources with passage-level citations. We can replicate the *ingestion* slice using yt-dlp + whisper without integrating Google. Existing pgvector RAG handles cited answers downstream.

## Goal
Given a YouTube or podcast URL, `/kb-ingest <url>` produces markdown with timestamps + speaker turns and registers a row in `kb_sources` so existing chunker + embedder pick it up.

## Scope (in)
- URL host detection: youtube.com, youtu.be, common podcast hosts (RSS enclosure URLs, Spotify shareable, Apple Podcasts)
- Branch ingest pipeline:
  - YouTube: `yt-dlp` audio extract -> `whisper` (or whisper.cpp) transcript -> markdown with `[mm:ss]` timestamps
  - Podcast RSS: `yt-dlp` or `requests` -> `.mp3` -> whisper -> markdown
- Markdown frontmatter: `source_url`, `source_type=video|podcast`, `duration`, `speaker_count`, `captured_at`
- Register in `kb_sources` table (existing schema)
- Register chunks for embedding pipeline (existing)

## Scope (out)
- Tenant-facing widget UI for upload (separate ticket)
- Audio overview generation (Google IP — skip)
- Mind maps / flashcards (not on roadmap)
- arXiv ingestion (separate ticket if needed)

## Acceptance
- [ ] `/kb-ingest https://youtube.com/watch?v=...` produces a markdown file in `knowledge-base/raw/<topic>/` with timestamped transcript
- [ ] Row inserted in `kb_sources` with `source_type='video'`
- [ ] Existing `kb-query` returns hits from the new source with citation
- [ ] No regressions on existing URL ingestion path
- [ ] Local-only (no external transcription API calls — whisper.cpp local)

## Files expected to change
- `.claude/skills/kb-ingest/SKILL.md` — add URL-host branching docs + version bump 1.1.0 -> 1.2.0
- `scripts/kb/ingest_yt_url.sh` (NEW) — yt-dlp + whisper wrapper
- `scripts/kb/ingest_podcast_url.sh` (NEW) — RSS/mp3 + whisper wrapper
- `scripts/kb/_transcribe.sh` (NEW) — shared whisper invocation
- `knowledge-base/INDEX.md` — section for video/audio sources

## Constraints
- whisper.cpp local-only (no OpenAI Whisper API — vendor avoidance)
- yt-dlp respects YouTube ToS for personal/research use; do NOT batch-download for resale
- No tenant-scoped ingestion in this spike (admin/eng use only)
- Storage: transcripts text-only in repo; raw audio NOT committed (`.gitignore` enforce)

## Verification
- Pick 1 short YouTube video (3-5 min) + 1 podcast episode (30-60 min)
- Run ingestion, confirm markdown + DB row + query hit
- Time end-to-end -> success metric: <10 min per hour of audio on local

## Risk / unknowns
- whisper.cpp install on WSL2 — may need build step
- yt-dlp updates frequently — pin a known-good version
- Podcast RSS shapes vary — start with one feed (Latent Space or Lex) then generalize

## Effort estimate
M — 1-2 days. yt-dlp + whisper.cpp are off-the-shelf; glue code only.

## Related
- `knowledge-base/raw/ai-llm/notebooklm-terminal-pattern-2026-04-29.md`
- `.claude/skills/kb-ingest/SKILL.md`
- `.claude/skills/kb-compile/SKILL.md`
- `scripts/daily/kb-autopopulate.sh`
- `project_value_prop_framework` memory — onboarding hours-saved framing
