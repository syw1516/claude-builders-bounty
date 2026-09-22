# PR Review Agent (Claude Code sub-agent)

A Claude Code sub-agent that reviews a GitHub pull request and posts
a structured, actionable Markdown comment.

## What's in it

- `agents/pr-reviewer.md` — the Claude Code sub-agent definition
  (frontmatter + workflow + safety rules).
- `scripts/review_pr.py` — single-file, stdlib-only Python that pulls
  the PR + diff via the GitHub REST API and renders a structured
  Markdown review. Optional `--post` flag posts the comment back.
- `testcases/test_offline.py` — offline unit tests for the review
  logic (no network needed).

## Use in Claude Code

1. Copy the `agents/` and `scripts/` folders into your project.
2. From Claude Code, invoke the sub-agent:
   ```
   Use the pr-reviewer sub-agent on owner=octocat repo=demo pr_number=123
   ```
   The sub-agent runs `scripts/review_pr.py`, refines the output with
   repo context, and (if you ask) posts it.

## Use standalone

```bash
# dry-run (print review to stdout)
python3 scripts/review_pr.py octocat demo 123

# write to file
python3 scripts/review_pr.py octocat demo 123 review.md

# post as a PR comment (needs GITHUB_TOKEN with repo scope)
export GITHUB_TOKEN=ghp_xxx
python3 scripts/review_pr.py --post octocat demo 123
```

## Review structure

Each review has:

- **Summary** — what the PR does (from the body, or a fallback).
- **Findings** — risky patterns detected in the `+` diff lines,
  deduped and counted:
  - security: dynamic code execution (`eval`/`exec`/`os.system`)
  - security: possible hardcoded credential
  - security: destructive SQL without `WHERE`
  - style: leftover debug output (`console.log` / `print`)
  - style: bare `except:` / empty `catch`
  - style: TypeScript `any` leak
  - performance: unbounded loop
  - follow-up: TODO / FIXME markers
- **Test & CI gaps** — flags missing test files, CI workflows, or
  docs.
- **Suggested follow-ups** — TODOs and style nits to circle back on.

## Safety rules (enforced in the agent, not the script)

- Do not post to a **draft** PR unless explicitly asked.
- Mask secrets in the posted comment.
- For very large diffs, summarize at hunk level instead of pasting.

## Tests

```bash
python3 testcases/test_offline.py
```
