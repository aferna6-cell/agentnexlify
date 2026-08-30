# train/ — reserved, empty by design

Nothing lives here yet, and that is a deliberate state rather than an oversight.

This directory is where examples go once the system has something to learn
*from* examples: few-shot exemplars for an LLM-backed classifier, or worked
cases used to derive a routing rule. Today the offline classifier is a
hand-written heuristic and the LLM classifier is zero-shot, so there is nothing
to train and an empty directory is the honest representation of that.

When it does fill up:

- Files here may be edited freely — this is the split you are allowed to fit to.
- Never copy a case in from `../action-eval-v1.json` or
  `../validation/validation-v1.json`, and never copy one out. Training on a case
  you later measure on is the oldest way to report a number that means nothing.
- A change validated here is not a result until the frozen test split confirms
  it.

See `../README.md` for the full split strategy and `docs/agent-action-eval.md`
for the harness.
