## PR Review

**PR:** feat(agent): claude-review PR agent CLI + Action (Opire #4 $150) (https://github.com/claude-builders-bounty/claude-builders-bounty/pull/4250)
**Branch:** `feat/claude-review-agent-4` → `main`  ·  ready  ·  +435 / +0 lines, 5 files

### Summary
## Summary
Implements Opire bounty **#4 ($150)**: `claude-review` agent that reviews a GitHub PR and emits structured Markdown.

### Findings
- **security: possible hardcoded credential** × 5
- **style: leftover debug output** × 3
- **security: dynamic code execution** × 2
- **security: destructive SQL without WHERE** × 2

### Test & CI gaps
- No test files changed in this PR — add a unit or integration test for the new behaviour.
- No CI workflow changed — verify the new code path is covered by existing CI.

### Suggested follow-ups
- style: leftover debug output

