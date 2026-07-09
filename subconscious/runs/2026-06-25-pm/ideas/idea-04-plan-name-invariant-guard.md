# Idea 04 — Add Plan-Name Invariant Guard to check_project_invariants.py (Check 7)

**Category:** code_health
**Confidence:** HIGH
**Autonomous-executable:** YES (once Check 13 exits 0)

## Proposal
Add Check 7 to check_project_invariants.py: scan backend Python source for plan-name
string literals in gate dicts and ensure retired plan names (foundation, operations)
do not appear.

Currently Check 3 (`retired plan names do not appear in plan-related code`) catches
this partially, but doesn't target the specific pattern of gate dicts that caused
GH #292/#293.

## Gate dict pattern (the real risk)
```python
PLAN_BASELINE_TOKENS = {
    "foundation": 50000,   # retired — this is the bug
    "chatbot": 100000,
    "agent_os": 200000,
}
```

A new developer or a sprint that adds a new plan tier could accidentally introduce
`foundation` or `operations` back into gate dicts without existing Check 3 catching it
(Check 3 looks for imports and usage, not dict literal keys).

## Implementation
```python
RETIRED_PLAN_NAMES = {"foundation", "operations"}
GATE_DICT_PATTERN = re.compile(r'["\'](foundation|operations)["\']:\s')

for path in backend_py_files:
    for line in path.read_text().splitlines():
        if GATE_DICT_PATTERN.search(line):
            failures.append(f"{path}: retired plan name in gate dict")
```

## Dependency
BLOCKED until Check 13 (check_project_invariants.py) exits 0 — i.e., until run 65
fix is delivered. Can't add a new invariant while existing invariants fail; that
would mask the signal.

## Verdict: PARKING LOT
Good idea. Tag as run 68 candidate after run 65 fix lands. AUTONOMOUS-EXECUTABLE.
