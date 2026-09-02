# Transition record — 2026-09-02

**M8 COMPLETE → restore mandatory green CI → close demo-role security gap → M9 planner.**

## Done

1. **M8 formal completion** — canonical six-suite PASS @ runtime SHA `962da79b`; evidence commit `ac80a1bd`.
2. **#748 MERGED** — input preservation + OAuth state TTL 60m + evidence.
3. **#747 MERGED** — brace-expansion + frontend/demo audits + stale-test retargets + key-vault 100% gate. PR Validation SUCCESS on `a9d54243`.
4. **#749 MERGED** — central `DemoRoleBlockMiddleware` for GH #669. PR Validation SUCCESS on `4ceaaa5a`.
5. **#669 allowlist audit** — PASS (`audits/artifacts/gh-669-allowlist-audit-2026-09-02.md`). Issue close blocked for this integration (403); owner paste closure checklist.

## Blocked / in flight

6. **Branch protection on `main`** — private-repo rulesets require GitHub Pro. See `audits/artifacts/branch-protection-blocker-2026-09-02.md`. Do not make the repo public.
7. **Auto-log bot** — converting from direct `main` pushes to docs PRs.

## Next

8. **M9 START** — `planning/milestone-9-persistent-planner-kickoff.md`
9. M9.1 typed workflow/state contract (no real tools)
10. M9.2 persistence + deterministic engine
11. M9.3 frozen planner eval, then LLM plans
