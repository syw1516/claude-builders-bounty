# n8n + Claude — automated weekly dev summary

Drop-in n8n workflow that:

1. Runs every Monday 09:00 (configurable)
2. Pulls the last week's commits from a GitHub repo
3. Asks Claude to turn them into a concise leadership update
4. Posts the summary as a comment on a pinned "Weekly Dev Summary" GitHub issue
5. (Optional) pings a Slack channel

## Setup (5 steps)

1. **Import the workflow** — in n8n, *Import from JSON* → pick
   `workflow.json`.
2. **Set env vars** — copy `.env.example` to `.env` and fill in:
   - `ANTHROPIC_API_KEY`
   - `GITHUB_TOKEN` (fine-grained, `Contents: read` on the source repo,
     `Issues: write` on the report repo)
   - `WEEKLY_SUMMARY_REPO_URL` → GitHub API URL for the repo you want to
     summarize
   - `GITHUB_REPORT_URL` → full URL of the issue you want to post into
     (e.g. `.../issues/42/comments`)
   - `SLACK_CHANNEL` → optional
3. **Connect credentials** — n8n asks for `httpHeaderAuth` for the
   commit-fetch node and Slack credentials for the notify node.
4. **Adjust the prompt** — the "Build Claude prompt" node contains the
   system prompt. Edit it to match your team's voice.
5. **Test run** — hit *Execute Workflow* once, check that the GitHub
   issue gets a comment.

## Tuning

- **Different cadence** — change the schedule trigger (daily, bi-weekly,
  on a tag, etc.).
- **Different model** — swap `claude-sonnet-4-5-20250929` in the
  "Call Claude API" node.
- **Different output** — point "Post to GitHub issue" at a different
  URL (Matrix bridge, email, etc.). The Claude response is plain
  Markdown; any Markdown renderer works.
- **Longer history** — bump `per_page=100` to `per_page=200` or add a
  second HTTP node that paginates.

## Error handling

The workflow is intentionally minimal. For production you'd want:

- `onError: "continueRegularRun"` on the HTTP nodes so one bad week
  doesn't kill the schedule
- An `If` node that skips the post when `resp.content` is empty
- A retry node for the Claude API call (transient 429s)
- A dead-letter Slack notification on any failure

The template ships without those so it's readable.

## Cost

One weekly run = 1 Claude call (~2k tokens in, ~1k out). Trivial cost.
If you run it daily the math is still small; the Claude API pricing
page has the exact per-token rates.
