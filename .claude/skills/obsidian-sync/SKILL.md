---
name: obsidian-sync
description: Sync wiki articles to an Obsidian vault with wikilinks and frontmatter in a one-way sync that never modifies source wiki files. Use when user says 'obsidian-sync', 'sync to obsidian', 'sync wiki to vault', 'obsidian vault sync', or asks about obsidian sync.
version: 1.0.0
origin: claude
user-invocable: true
triggers:
- obsidian-sync
- sync to obsidian
- sync wiki to vault
- obsidian vault sync
effort: low
---

# obsidian-sync

Two modes:

1. **Direct Vault Mode** (recommended for editing skills/rules/memory). Point Obsidian at
   the repo root directly — `File → Open folder as vault → /home/aidan/agentnexlify`.
   Obsidian reads `.md` files natively; no sync script needed. Edits hit git-tracked files.
   Use for `.claude/skills/**`, `.claude/rules/**`, `memory/**`, `plans/**`, `specs/**`,
   `audits/**`, `docs/**`, `knowledge-base/raw/**`. Add `.obsidian/` to `.gitignore` if not
   already there.

2. **Wiki Sync Mode** (this skill's automation). Copy wiki articles from
   `knowledge-base/wiki/` to a separate Obsidian vault with Obsidian-specific transforms:
   YAML frontmatter with `aliases` and `cssclass`, `[[Title]]` wikilinks instead of
   `[[slug]]`, category subfolders, and a generated Map of Content (MOC). One-way sync —
   wiki is canonical, Obsidian copy is read-friendly. Use for sharing wiki with a reader
   who isn't on this machine, or keeping a standalone knowledge vault.

Most engineering workflows want Mode 1 (zero setup, edits live-sync via filesystem).
Mode 2 below is for the wiki-sharing case.

## Usage

```
/obsidian-sync /path/to/vault                # full sync (all articles)
/obsidian-sync /path/to/vault --incremental  # only articles newer than last sync
```

Also callable as a flag when ingesting:
```
/wiki https://example.com --obsidian /path/to/vault
```

## When to Use
- Creating a read-friendly copy of the wiki for use in Obsidian
- Setting up the Obsidian vault with the latest wiki articles
- Incremental sync after new articles have been added to the wiki

## When NOT to Use
- Editing wiki content (edit the wiki directly, then sync)
- Two-way sync (this is one-way only, wiki is canonical)
- Querying the knowledge base (use kb-query instead)

---

## Workflow

### Step 1: Validate Vault Path

Check that the provided path exists on disk.

Look for a `.obsidian/` directory inside it. If found, proceed. If not found, output:
```
Warning: {path} does not appear to be an Obsidian vault (.obsidian/ not found).
Proceed anyway? [y/N]
```
Wait for confirmation. If the user says no (or this is running headless/unattended), abort.

Read `knowledge-base/INDEX.md` to confirm the wiki has articles. If INDEX.md is missing or
empty, abort with:
```
Error: knowledge-base/INDEX.md not found or empty. Run /kb-compile or /wiki first.
```

### Step 2: Create Folder Structure

Create the following directories inside the vault (use `mkdir -p`; skip if already exist):

```
{vault}/Claudeopedia/
{vault}/Claudeopedia/competitors/
{vault}/Claudeopedia/ai-llm/
{vault}/Claudeopedia/small-biz-saas/
{vault}/Claudeopedia/verticals/
{vault}/Claudeopedia/technical/
{vault}/Claudeopedia/regulations/
{vault}/Claudeopedia/growth/
{vault}/Claudeopedia/general/
{vault}/Claudeopedia/_outputs/
{vault}/Claudeopedia/_meta/
```

Use Bash to create these:
```bash
for d in competitors ai-llm small-biz-saas verticals technical regulations growth general _outputs _meta; do
  mkdir -p "{vault}/Claudeopedia/$d"
done
```

### Step 3: Build Slug-to-Title Map

Read `knowledge-base/INDEX.md`. Parse all article entries to build a mapping of:
```
{slug} → {title}
```

Article entries in INDEX.md have the form:
```markdown
- [{title}](wiki/{category}/{slug}.md) — {summary}
```

Build a Python dict or equivalent in memory:
```python
slug_to_title = {
    "competitors/gohighlevel": "GoHighLevel",
    "technical/prompt-caching": "Prompt Caching — Cost and Latency Patterns",
    ...
}
```
Also build the reverse: `title_to_slug`. This will be used for cross-reference conversion.

### Step 4: Determine Sync Scope

**Full sync** (default, no `--incremental`):
- Process every `.md` file in `knowledge-base/wiki/` (recursively, excluding `_outputs/`).

**Incremental sync** (`--incremental` flag):
- Read `knowledge-base/.obsidian-sync-state.json` if it exists. Extract `last_sync` ISO
  timestamp.
- For each article, read the frontmatter `updated` date. Only include articles where
  `updated >= last_sync date`.
- If `.obsidian-sync-state.json` doesn't exist, fall back to full sync and log a warning.

Track counters: `new`, `updated`, `unchanged`, `skipped`.

### Step 5: Convert and Write Each Article

For each article in scope, perform all conversions in memory before writing. Never modify
the source file.

#### 5a. Read Source Article

Read the file from `knowledge-base/wiki/{category}/{slug}.md`.

Parse the YAML frontmatter (between the first `---` delimiters). Extract body (everything
after the second `---`).

#### 5b. Transform Frontmatter

Build an Obsidian-compatible YAML frontmatter block. Preserve all existing fields and add:

```yaml
---
title: "{same title}"
category: {same category}
tags:           # as YAML list, not inline array
  - tag1
  - tag2
sources:
  - "raw/category/source.md"
created: YYYY-MM-DD
updated: YYYY-MM-DD
challenged: YYYY-MM-DD   # only if present in source
summary: "{same summary}"
slug: "{category}/{slug}"  # added for mapping back to source
aliases:                   # NEW: for Obsidian autocomplete
  - "{short title without subtitle after —}"
  - "{slug without category prefix}"
cssclass: claudeopedia     # NEW: for optional custom CSS in Obsidian
---
```

**Aliases generation rules:**
- If the title contains ` — ` (em-dash with spaces), add the part before ` — ` as an alias.
  Example: "Prompt Caching — Cost and Latency Patterns" → alias "Prompt Caching"
- Always add the slug (without category prefix) as an alias.
  Example: slug `technical/prompt-caching` → alias "prompt-caching"
- Do not add duplicate aliases (check case-insensitively).
- Do not add the full title as an alias (Obsidian already uses the filename as the primary name).

#### 5c. Convert Cross-References

In the article body, find all `[[slug]]` patterns and replace them with `[[Title]]` using
the slug-to-title map built in Step 3.

```python
import re

def convert_wikilinks(body, slug_to_title):
    def replace(m):
        slug = m.group(1).strip()
        # Try exact match first, then with category prefix removed
        title = slug_to_title.get(slug) or slug_to_title.get(slug.split('/')[-1])
        if title:
            # Sanitize title for Obsidian filename compatibility
            safe_title = title.replace('/', '—').replace(':', ' —')
            return f'[[{safe_title}]]'
        return m.group(0)  # Keep original if no match found
    return re.sub(r'\[\[([^\]]+)\]\]', replace, body)
```

Slugs that don't match any article in the map are kept as-is. Obsidian will show them as
unresolved links, which is correct behavior.

#### 5d. Determine Output Filename

Obsidian convention is filename = title, not slug.

```python
def title_to_filename(title):
    # Replace characters that are invalid in filenames
    safe = title.replace('/', '—').replace(':', ' —').replace('?', '').replace('*', '')
    return safe.strip() + '.md'
```

Output path: `{vault}/Claudeopedia/{category}/{title_to_filename(title)}`

#### 5e. Write Output File

Assemble: transformed frontmatter + body with converted wikilinks.

Write to the output path. If the file already exists and content is identical (compare
checksums), mark as `unchanged` and skip writing to avoid touching Obsidian's modification
timestamps unnecessarily.

### Step 6: Generate Map of Content (MOC)

Create `{vault}/Claudeopedia/Claudeopedia MOC.md`:

```markdown
---
title: Claudeopedia — Map of Content
tags:
  - MOC
  - claudeopedia
created: YYYY-MM-DD
updated: YYYY-MM-DD
cssclass: claudeopedia-moc
---

# Claudeopedia

Personal knowledge base for AgentNexLiFy. {N} articles across {M} categories.
Last synced: YYYY-MM-DD HH:MM UTC.

## By Category

### Competitors ({count})
- [[{Article Title}]]
- [[{Article Title}]]

### AI & LLM ({count})
- [[{Article Title}]]

### Small Business SaaS ({count})
- [[{Article Title}]]

### Verticals ({count})
- [[{Article Title}]]

### Technical ({count})
- [[{Article Title}]]

### Regulations ({count})
- [[{Article Title}]]

### Growth ({count})
- [[{Article Title}]]

### General ({count})
- [[{Article Title}]]

## Recent (Last 30 Days)

{Articles sorted by updated date, newest first, limited to 30 days window}
- [[{Article Title}]] — {updated date}

## Most Connected

{Articles with the most [[wikilink]] references from other articles, sorted descending}
- [[{Article Title}]] — referenced by {N} other articles
```

Sort articles within each category section alphabetically by title.

For "Most Connected": scan all article bodies in `knowledge-base/wiki/` for `[[slug]]`
references. Count how many articles reference each slug. Show the top 10.

### Step 7: Write Sync State

Save sync metadata to two locations:

**In vault** (for Obsidian users):
`{vault}/Claudeopedia/_meta/sync-state.json`

**In repo** (for incremental sync):
`knowledge-base/.obsidian-sync-state.json`

Both files contain:
```json
{
  "last_sync": "YYYY-MM-DDTHH:MM:SSZ",
  "articles_synced": 42,
  "articles_new": 3,
  "articles_updated": 2,
  "articles_unchanged": 37,
  "vault_path": "/path/to/vault",
  "source_path": "/home/aidan/agentnexlify/knowledge-base",
  "schema_version": 1
}
```

Note: `knowledge-base/.obsidian-sync-state.json` is gitignored (contains local vault path).
If it's not already in `.gitignore`, add it:
```bash
echo "knowledge-base/.obsidian-sync-state.json" >> /home/aidan/agentnexlify/.gitignore
```

### Step 8: Report

Output a summary:

```
Obsidian sync → {vault_path}/Claudeopedia/
  Articles synced:   42
    New:             3
    Updated:         2
    Unchanged:       37
  MOC regenerated:   Claudeopedia MOC.md
  Wikilinks converted: 156 (12 unresolved — kept as slugs)
  Sync state saved to: knowledge-base/.obsidian-sync-state.json
```

If any articles had unresolved wikilinks (slugs with no title match), list them:
```
  Unresolved wikilinks:
    [[claude-api-patterns]] — referenced in 3 articles (article does not exist yet)
    [[model-routing]] — referenced in 1 article
```
This is informational — not an error.

---

## Design Decisions

- **One-way sync, wiki is canonical.** If you edit a note in Obsidian, those edits are
  overwritten on next sync. This avoids merge conflicts entirely. The Obsidian copy is a
  reading interface, not an editing environment. Edit in the wiki; read in Obsidian.

- **Title-based filenames in Obsidian.** Obsidian users expect `Note Title.md`, not
  `category/slug.md`. The original slug is preserved in frontmatter (`slug:` field) so the
  mapping back to source is always recoverable.

- **Aliases.** Obsidian's link autocomplete and backlinks use filenames. Aliases let you
  reference articles by short name or slug in Obsidian's `[[` autocomplete. This is
  especially useful for articles with long descriptive titles.

- **`cssclass: claudeopedia`.** Allows targeting all Claudeopedia notes in a custom
  `obsidian.css` snippet. Not required; purely cosmetic.

- **MOC file.** Obsidian's graph view clusters notes by connections. Without a central MOC
  that links to everything, the graph appears as disconnected islands. The MOC pulls all
  Claudeopedia notes into one connected component.

- **Incremental mode.** For large knowledge bases (100+ articles), full sync on every `/wiki`
  call is slow. `--incremental` makes it practical to sync after every new article.

- **Gitignored sync state.** `.obsidian-sync-state.json` contains the local vault path,
  which is machine-specific and should never be committed.

- **Never touch `_outputs/`.** The `_outputs/` directory in `knowledge-base/wiki/` contains
  synthesis reports from `/last30days`, not articles. These are synced to
  `{vault}/Claudeopedia/_outputs/` unchanged (no frontmatter transformation needed).

---

## Error Handling

| Condition | Behavior |
|-----------|----------|
| Vault path doesn't exist | Abort with error |
| `.obsidian/` not found | Prompt for confirmation (abort headless) |
| Article has no frontmatter | Log warning, copy file unchanged |
| Wikilink slug has no title match | Keep `[[slug]]` as-is, log as unresolved |
| Write permission denied on vault | Abort with error, show which path failed |
| `knowledge-base/.obsidian-sync-state.json` missing + `--incremental` | Fall back to full sync, log warning |
