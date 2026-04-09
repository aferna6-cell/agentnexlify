---
paths:
  - "**/*"
---

# Claude Code Security Hardening

Based on "You installed Claude Code and never once looked at the security settings" (2026-04-09). Applied at Level 1 + Level 2 equivalent.

## Threat Model
By default Claude Code has full access to the host machine. Attack vectors:
- **Prompt injection** via malicious CLAUDE.md in cloned repos
- **MCP hijack** via malicious `.mcp.json` in untrusted projects
- **Credential read** on `~/.ssh`, `~/.aws`, `.env`, etc.
- **Data exfiltration** via `curl`, `wget`, `nc`, `socat`
- **Persistence** via `~/.bashrc`, `~/.zshrc` edits
- **Lateral movement** via `ssh`, `scp`, `sudo`

Average credential leak costs $8k-$50k, detected in 197 days on average.

## Controls Applied

### Level 1 — permissions.deny (ACTIVE)
Blocks Read/Edit on credential paths + sensitive dotfiles. Blocks exfil commands outright (`nc`, `socat`, `telnet`). See `~/.claude/settings.json` and `.claude/settings.json`.

**Denied reads:**
- `~/.ssh/**`, `~/.gnupg/**`, `~/.aws/**`, `~/.azure/**`, `~/.kube/**`, `~/.gcp/**`
- `~/.config/gcloud/**`, `~/.config/gh/**`, `~/.docker/config.json`
- `~/.npmrc`, `~/.pypirc`, `~/.netrc`, `~/.git-credentials`
- `**/.env`, `**/.env.*`, `**/*.pem`, `**/*.key`, `**/id_rsa`, `**/id_ed25519`
- `**/credentials.json`, `**/service-account*.json`

**Denied edits:**
- `~/.ssh/**`, `~/.aws/**`, `~/.gnupg/**`
- `~/.bashrc`, `~/.zshrc`, `~/.bash_profile`, `~/.profile`, `~/.zprofile`, `~/.zlogin`
- `/etc/**`

**Denied bash commands:**
- `nc`, `ncat`, `socat`, `telnet` — raw network
- `bash -i`, `sh -i` — interactive reverse shell

### Level 1 — permissions.ask (ACTIVE)
Prompts user for confirmation on potentially exfil/destructive commands:
- `curl`, `wget` — HTTP fetches (may exfiltrate)
- `ssh`, `scp`, `rsync` — remote transfer
- `git push` (global only, project allows — pre-push hook gates it)
- `npm publish`, `pip install` — supply chain
- `sudo`, `chmod`, `chown` — privilege/ownership change

### Level 1 — MCP trust
- Global: `enableAllProjectMcpServers: false` — untrusted repos DO NOT auto-load `.mcp.json`
- Project (agentnexlify): `enableAllProjectMcpServers: true` — trusted, own MCP config
- When cloning new repo, `.mcp.json` will require explicit approval

### Level 1 — Sandbox (CONFIGURED, NOT ENABLED)
Sandbox config in `~/.claude/settings.json` and `.claude/settings.json`:
```json
"sandbox": {
  "enabled": false,
  "failIfUnavailable": false,
  "filesystem": {
    "denyRead": ["**/.env", "**/*.pem", ...]
  }
}
```

**Why disabled:** Sandbox requires `bubblewrap` + `socat` on Linux. Not yet installed on this host.

**To activate:**
```bash
sudo apt-get install bubblewrap socat
```
Then flip `sandbox.enabled` to `true` in `~/.claude/settings.json` OR run `/sandbox` in Claude Code (auto-allow mode).

Once enabled:
- Deny rules apply at OS level (Seatbelt on Mac, bubblewrap on Linux)
- Bash commands can't bypass rules
- Sub-processes spawned by Claude also restricted
- 84% fewer confirmation popups per Anthropic data

### Level 2 — Trail of Bits (PARTIAL)
Trail of Bits publishes a Claude Code security config at `github.com/trailofbits/claude-code-config`. Their plugin:
```bash
claude plugin marketplace add trailofbits/skills
/trailofbits:config
```

**Not yet installed.** Their config adds:
- Security skills (vulnerability patterns, auditor checklists)
- Workflow hooks (plan → execute → verify gate)
- CLAUDE.md template (no speculative code, justify every dep)

**Action:** Install when convenient — their config is additive, won't conflict with ours.

### Level 3 — Devcontainer (NOT APPLIED)
Full host isolation via `trailofbits/claude-code-devcontainer`. Runs Claude in a container with zero host access. Recommended for:
- Working on untrusted cloned repos
- Client code on personal machine
- One-shot repo investigations

**Action:** Use ad-hoc when cloning untrusted repos:
```bash
npm install -g @devcontainers/cli
git clone https://github.com/trailofbits/claude-code-devcontainer ~/.claude-devcontainer
~/.claude-devcontainer/install.sh self-install
# Then for any untrusted repo:
cd /path/to/untrusted-repo
devc .
devc shell
claude
```

## Monthly Maintenance
```bash
claude update  # patch known vulnerabilities
```
Run first of every month. Pre-2.0.65 Claude Code versions had two unpatched critical vulns.

## What This Does NOT Protect Against
- Committed secrets already in git history (use `git-secrets` + BFG)
- Secrets logged to stdout/files before deny rules block reading them
- Malicious MCP from a server already marked as trusted
- Attacks via allowed commands (`git`, `npm`) being subverted
- Prompt injection that convinces user to manually run commands
- Sandbox escape via kernel vulnerabilities (Linux bubblewrap)

## Verification
After deploy:
```bash
# JSON valid
jq -e . ~/.claude/settings.json /home/aidan/agentnexlify/.claude/settings.json

# Deny list present
jq -r '.permissions.deny[]' /home/aidan/agentnexlify/.claude/settings.json

# Test deny works (should be blocked):
# Try reading ~/.ssh/id_rsa — Claude should refuse at permission layer
```

## Pointers
- Article: https://twitter.com (original post by @trailofbits-style security guide)
- Trail of Bits: https://github.com/trailofbits/claude-code-config
- Devcontainer: https://github.com/trailofbits/claude-code-devcontainer
- Local: `.claude/rules/claude-code-security.md` (this file)
