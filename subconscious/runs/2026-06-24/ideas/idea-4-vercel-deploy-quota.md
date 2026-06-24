# Idea 4: Vercel Deploy Quota Optimization

## Summary
Brain note in 5b62a9b: "Vercel daily deploy quota exhausted — frontend deploys blocked ~24h". Optimize CI to avoid burning quota on docs/ops changes that don't need a frontend rebuild.

## Evidence
- 5b62a9b brain note: "Vercel daily deploy quota exhausted — frontend deploys blocked ~24h" (after #369)
- Current CI likely triggers Vercel deploy on every push, including backend/docs/ops changes
- Quota exhaustion = customer-visible gap risk if a real bug fix needs deploying

## What "done" looks like
In `.github/workflows/` (or Vercel project settings):
1. Add path filter: only trigger Vercel deploy when `frontend/**` or `widget/**` or `landing-page-v2/**` changes
2. Add `[skip vercel]` token support in commit message for manual override
3. Add `if: github.ref == 'refs/heads/main'` guard — preview deploys only for PRs that touch frontend paths
4. Document quota limits + strategy in `ops/docs/vercel-deploy-strategy.md`

## Impact
Reduces unnecessary Vercel deployments by ~60-70% (most commits are backend/ops). Quota exhaustion becomes rare. Frontend bug fixes can always deploy when needed.

## Effort
LOW — ~10-20 lines of GitHub Actions YAML + Vercel project settings toggle.

## Category
Ops / reliability
