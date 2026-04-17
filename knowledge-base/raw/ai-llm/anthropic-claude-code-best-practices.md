---
source_url: https://www.anthropic.com/engineering/claude-code-best-practices
fetched_at: 2026-04-17T22:04:19Z
category: ai-llm
title: Best Practices for Claude Code - Claude Code Docs
---

# Best Practices for Claude Code - Claude Code Docs

## Getting started

## Core concepts

## Use Claude Code

## Platforms and integrations

Provide specific context in your prompts

Claude Code is an agentic coding environment. Unlike a chatbot that answers questions and waits, Claude Code can read your files, run commands, make changes, and autonomously work through problems while you watch, redirect, or step away entirely.

This changes how you work. Instead of writing code yourself and asking Claude to review it, you describe what you want and Claude figures out how to build it. Claude explores, plans, and implements.

But this autonomy still comes with a learning curve. Claude works within certain constraints you need to understand.

This guide covers patterns that have proven effective across Anthropic’s internal teams and for engineers using Claude Code across various codebases, languages, and environments. For how the agentic loop works under the hood, see How Claude Code works.

##

Most best practices are based on one constraint: Claude’s context window fills up fast, and performance degrades as it fills.

Claude’s context window holds your entire conversation, including every message, every file Claude reads, and every command output. However, this can fill up fast. A single debugging session or codebase exploration might generate and consume tens of thousands of tokens.

This matters since LLM performance degrades as context fills. When the context window is getting full, Claude may start “forgetting” earlier instructions or making more mistakes. The context window is the most important resource to manage. To see how a session fills up in practice, watch an interactive walkthrough of what loads at startup and what each file read costs. Track context usage continuously with a custom status line, and see Reduce token usage for strategies on reducing token usage.

##

##

Include tests, screenshots, or expected outputs so Claude can check itself. This is the single highest-leverage thing you can do.

Claude performs dramatically better when it can verify its own work, like run tests, compare screenshots, and validate outputs.

Without clear success criteria, it might produce something that looks right but actually doesn’t work. You become the only feedback loop, and every mistake requires your attention.

Provide verification criteria”implement a function that validates email addresses""write a validateEmail function. example test cases: user@example.com is true, invalid is false, user@.com is false. run the tests after implementing”

Verify UI changes visually”make the dashboard look better""[paste screenshot] implement this design. take a screenshot of the result and compare it to the original. list differences and fix them”

Address root causes, not symptoms”the build is failing""the build fails with this error: [paste error]. fix it and verify the build succeeds. address the root cause, don’t suppress the error”

UI changes can be verified using the Claude in Chrome extension. It opens new tabs in your browser, tests the UI, and iterates until the code works.

Your verification can also be a test suite, a linter, or a Bash command that checks output. Invest in making your verification rock-solid.

##

##

Separate research and planning from implementation to avoid solving the wrong problem.

Letting Claude jump straight to coding can produce code that solves the wrong problem. Use Plan Mode to separate exploration from execution.

The recommended workflow has four phases:

Enter Plan Mode. Claude reads files and answers questions without making changes.

read /src/auth and understand how we handle sessions and login.

also look at how we manage environment variables for secrets.

Ask Claude to create a detailed implementation plan.

I want to add Google OAuth. What files need to change?

Press Ctrl+G to open the plan in your text editor for direct editing before Claude proceeds.

Switch back to Normal Mode and let Claude code, verifying against its plan.

implement the OAuth flow from your plan. write tests for the

callback handler, run the test suite and fix any failures.

Ask Claude to commit with a descriptive message and create a PR.

commit with a descriptive message and open a PR

Plan Mode is useful, but also adds overhead.For tasks where the scope is clear and the fix is small (like fixing a typo, adding a log line, or renaming a variable) ask Claude to do it directly.Planning is most useful when you’re uncertain about the approach, when the change modifies multiple files, or when you’re unfamiliar with the code being modified. If you could describe the diff in one sentence, skip the plan.

##

##

Provide specific context in your prompts

The more precise your instructions, the fewer corrections you’ll need.

Claude can infer intent, but it can’t read your mind. Reference specific files, mention constraints, and point to example patterns.

Scope the task. Specify which file, what scenario, and testing preferences.”add tests for foo.py""write a test for foo.py covering the edge case where the user is logged out. avoid mocks.”

Point to sources. Direct Claude to the source that can answer a question.”why does ExecutionFactory have such a weird api?""look through ExecutionFactory’s git history and summarize how its api came to be”

Reference existing patterns. Point Claude to patterns in your codebase.”add a calendar widget""look at how existing widgets are implemented on the home page to understand the patterns. HotDogWidget.php is a good example. follow the pattern to implement a new calendar widget that lets the user select a month and paginate forwards/backwards to pick a year. build from scratch without libraries other than the ones already used in the codebase.”

Describe the symptom. Provide the symptom, the likely location, and what “fixed” looks like.”fix the login bug""users report that login fails after session timeout. check the auth flow in src/auth/, especially token refresh. write a failing test that reproduces the issue, then fix it”

Vague prompts can be useful when you’re exploring and can afford to course-correct. A prompt like "what would you improve in this file?" can surface things you wouldn’t have thought to ask about.

##

Use @ to reference files, paste screenshots/images, or pipe data directly.

You can provide rich data to Claude in several ways:

Reference files with @ instead of describing where code lives. Claude reads the file before responding.

Paste images directly. Copy/paste or drag and drop images into the prompt.

Give URLs for documentation and API references. Use /permissions to allowlist frequently-used domains.

Pipe in data by running cat error.log | claude to send file contents directly.

Let Claude fetch what it needs. Tell Claude to pull context itself using Bash commands, MCP tools, or by reading files.

##

##

A few setup steps make Claude Code significantly more effective across all your sessions. For a full overview of extension features and when to use each one, see Extend Claude Code.

##

Run /init to generate a starter CLAUDE.md file based on your current project structure, then refine over time.

CLAUDE.md is a special file that Claude reads at the start of every conversation. Include Bash commands, code style, and workflow rules. This gives Claude persistent context it can’t infer from code alone.

The /init command analyzes your codebase to detect build systems, test frameworks, and code patterns, giving you a solid foundation to refine.

There’s no required format for CLAUDE.md files, but keep it short and human-readable. For example:

- Use ES modules (import/export) syntax, not CommonJS (require)

- Destructure imports when possible (eg. import { foo } from 'bar')

- Be sure to typecheck when you're done making a series of code changes

- Prefer running single tests, and not the whole test suite, for performance

CLAUDE.md is loaded every session, so only include things that apply broadly. For domain knowledge or workflows that are only relevant sometimes, use skills instead. Claude loads them on demand without bloating every conversation.

Keep it concise. For each line, ask: “Would removing this cause Claude to make mistakes?” If not, cut it. Bloated CLAUDE.md files cause Claude to ignore your actual instructions!

Bash commands Claude can’t guessAnything Claude can figure out by reading code

Code style rules that differ from defaultsStandard language conventions Claude already knows

Testing instructions and preferred test runnersDetailed API documentation (link to docs instead)

Repository etiquette (branch naming, PR conventions)Information that changes frequently

Architectural decisions specific to your projectLong explanations or tutorials

Developer environment quirks (required env vars)File-by-file descriptions of the codebase

Common gotchas or non-obvious behaviorsSelf-evident practices like “write clean code”

If Claude keeps doing something you don’t want despite having a rule against it, the file is probably too long and the rule is getting lost. If Claude asks you questions that are answered in CLAUDE.md, the phrasing might be ambiguous. Treat CLAUDE.md like code: review it when things go wrong, prune it regularly, and test changes by observing whether Claude’s behavior actually shifts.

You can tune instructions by adding emphasis (e.g., “IMPORTANT” or “YOU MUST”) to improve adherence. Check CLAUDE.md into git so your team can contribute. The file compounds in value over time.

CLAUDE.md files can import additional files using @path/to/import syntax:

See @README.md for project overview and @package.json for available npm commands.

- Git workflow: @docs/git-instructions.md

- Personal overrides: @~/.claude/my-project-instructions.md

You can place CLAUDE.md files in several locations:

Home folder (~/.claude/CLAUDE.md): applies to all Claude sessions

Project root (./CLAUDE.md): check into git to share with your team

Project root (./CLAUDE.local.md): personal project-specific notes; add this file to your .gitignore so it isn’t shared with your team

Parent directories: useful for monorepos where both root/CLAUDE.md and root/foo/CLAUDE.md are pulled in automatically

Child directories: Claude pulls in child CLAUDE.md files on demand when working with files in those directories

##

Use auto mode to let a classifier handle approvals, /permissions to allowlist specific commands, or /sandbox for OS-level isolation. Each reduces interruptions while keeping you in control.

By default, Claude Code requests permission for actions that might modify your system: file writes, Bash commands, MCP tools, etc. This is safe but tedious. After the tenth approval you’re not really reviewing anymore, you’re just clicking through. There are three ways to reduce these interruptions:

Auto mode: a separate classifier model reviews commands and blocks only what looks risky: scope escalation, unknown infrastructure, or hostile-content-driven actions. Best when you trust the general direction of a task but don’t want to click through every step

Permission allowlists: permit specific tools you know are safe, like npm run lint or git commit

Sandboxing: enable OS-level isolation that restricts filesystem and network access, allowing Claude to work more freely within defined boundaries

Read more about permission modes, permission rules, and sandboxing.

##

Tell Claude Code to use CLI tools like gh, aws, gcloud, and sentry-cli when interacting with external services.

CLI tools are the most context-efficient way to interact with external services. If you use GitHub, install the gh CLI. Claude knows how to use it for creating issues, opening pull requests, and reading comments. Without gh, Claude can still use the GitHub API, but unauthenticated requests often hit rate limits.

Claude is also effective at learning CLI tools it doesn’t already know. Try prompts like Use 'foo-cli-tool --help' to learn about foo tool, then use it to solve A, B, C.



[truncated]
