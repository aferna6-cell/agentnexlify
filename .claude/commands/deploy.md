Run the full pre-deploy validation pipeline and prepare for deployment.

## Step 1: Create Checkpoint

Write checkpoint to `.claude/agent-comms/checkpoint.md`:
- Deploy reason
- Current branch
- Last commit hash

## Step 2: Run Parallel Validation

Spawn these agents in **parallel**:

**qa-tester agent:**
- "Run full validation: dangerous imports, bare excepts, secrets scan, frontend build check, backend import check, schema consistency. Write results to .claude/agent-comms/qa-tester-output.md"

**devops agent:**
- "Run deploy readiness check: .env safety, environment variables, CORS configuration, migration numbering. Write results to .claude/agent-comms/devops-output.md"

## Step 3: Compile Results

Read both output files. Create a deploy report:

### Deploy Readiness Report

**Status: READY / NOT READY**

**QA Results:**
- [list of checks and pass/fail]

**DevOps Results:**
- [list of checks and pass/fail]

**Blockers (must fix before deploy):**
- [any critical issues]

**Warnings (non-blocking):**
- [any warnings]

**Manual Steps Required:**
- [any migrations to run, env vars to set, etc.]

## Step 4: Fix Blockers

If there are blockers, fix them automatically if safe (bare excepts, missing error handling). For anything risky, list it and ask the developer.

## Step 5: Final Gate

After fixes, re-run the qa-tester to verify blockers are resolved.

## Step 6: Clean Up

Clean up .claude/agent-comms/. Do NOT commit or push — the developer decides when to push.

Report: deploy readiness status, what was fixed, what still needs manual attention.
