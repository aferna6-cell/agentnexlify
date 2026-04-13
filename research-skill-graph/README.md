# Research Skill Graph

Multi-lens research engine for AgentNexLiFy. Auto-populates from a question queue, auto-iterates by feeding open-questions back into the queue. Every research project passes through 6 lenses (technical, economic, historical, geopolitical, contrarian, first-principles) and produces 4 output files plus compounding knowledge.

Based on the skill-graph pattern: a folder of interconnected markdown nodes where `[[wikilinks]]` connect methodology, lenses, and knowledge into a reusable research department.

## Structure

```
research-skill-graph/
├── index.md                      command center (read first every run)
├── research-log.md               running log of completed projects
├── research-queue.md             pending questions (checkbox list)
├── methodology/
│   ├── research-frameworks.md    how to approach question types
│   ├── source-evaluation.md      5-tier trust system
│   ├── synthesis-rules.md        combine without flattening
│   └── contradiction-protocol.md what to do when sources disagree
├── lenses/
│   ├── technical.md              what the numbers say
│   ├── economic.md               follow the money
│   ├── historical.md             what patterns repeat
│   ├── geopolitical.md           global power dynamics
│   ├── contrarian.md             stress-test the consensus
│   └── first-principles.md       rebuild from fundamentals
├── projects/                     one folder per research topic
├── sources/
│   └── source-template.md        per-source notes template
├── knowledge/
│   ├── concepts.md               accumulated definitions
│   └── data-points.md            accumulated hard numbers
└── scripts/
    ├── run-research.py           engine (calls Claude API)
    ├── run-research.sh           cron wrapper
    ├── auto-iterate.py           queue management
    └── requirements.txt
```

## Usage

### One-off run
```bash
cd research-skill-graph
python scripts/run-research.py                  # pick next pending question
python scripts/run-research.py --question "..."  # ad-hoc
```

### Auto-populating via cron
```bash
# add to crontab (runs every 6 hours)
0 */6 * * * /home/aidan/agentnexlify/research-skill-graph/scripts/run-research.sh >> /tmp/research.log 2>&1
```

### Seed the queue
Append to `research-queue.md`:
```
- [ ] your research question
```

### Auto-iteration
Each completed project's `open-questions.md` items get appended to `research-queue.md` automatically. The queue grows itself — prune manually if it drifts.

## Requirements

- Python 3.11+
- `ANTHROPIC_API_KEY` in env (read from `../backend/.env` by default)
- `anthropic` package (`pip install -r scripts/requirements.txt`)

## Output per run

For research question `Q`:
```
projects/{slug}/
├── executive-summary.md   500-word synthesis
├── deep-dive.md           full analysis per lens with contradictions
├── key-players.md         people/orgs/countries that matter
└── open-questions.md      still-unknowns (auto-appended to queue)
```

Plus appends to `research-log.md`, `knowledge/concepts.md`, `knowledge/data-points.md`.

## Model

Default: `claude-sonnet-4-6`. Override via `--model` or `RESEARCH_MODEL` env.

## Design principles

- 20 files, 6 folders, zero abstractions
- Markdown only — no DB, no API, no framework
- Every lens must rethink the question, not just add information
- Contradictions between lenses are features — that tension is where insight lives
- Knowledge compounds across projects
