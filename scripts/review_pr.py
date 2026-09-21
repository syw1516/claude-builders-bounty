#!/usr/bin/env python3
"""PR reviewer: read a GitHub PR, produce a structured Markdown review.

Usage:
    python3 review_pr.py <owner> <repo> <pr_number> [output_file]

Reads the PR's diff, changed files, and issue body via the GitHub API
(no auth required for public repos; set GITHUB_TOKEN for private or
higher rate limits). Writes a structured Markdown review to stdout or
to output_file.

The review includes:
  - Summary of what the PR does
  - Categorised findings (bugs, style, security, performance, tests)
  - Test-gap analysis
  - Suggested follow-ups

If run with --post <owner> <repo> <pr_number>, it also posts the
review as a comment on the PR via the GitHub API (requires
GITHUB_TOKEN with repo scope).
"""
import json
import os
import re
import subprocess
import sys
import urllib.request
import urllib.parse

API = "https://api.github.com"
TOKEN = os.environ.get("GITHUB_TOKEN", "")


def headers():
    h = {"Accept": "application/vnd.github+json", "User-Agent": "pr-review-agent/1.0"}
    if TOKEN:
        h["Authorization"] = f"Bearer {TOKEN}"
    return h


def get_json(url):
    req = urllib.request.Request(url, headers=headers())
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode())


def post_comment(owner, repo, pr_number, body):
    url = f"{API}/repos/{owner}/{repo}/issues/{pr_number}/comments"
    data = json.dumps({"body": body}).encode()
    req = urllib.request.Request(url, data=data, headers=headers(), method="POST")
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode())


def fetch_pr(owner, repo, number):
    return get_json(f"{API}/repos/{owner}/{repo}/pulls/{number}")


def fetch_files(owner, repo, number, per_page=100):
    files = []
    page = 1
    while True:
        url = (f"{API}/repos/{owner}/{repo}/pulls/{number}/files"
               f"?per_page={per_page}&page={page}")
        data = get_json(url)
        files.extend(data)
        if len(data) < per_page:
            break
        page += 1
    return files


def categorize_line(line):
    """Classify a diff line into a review concern if it looks risky."""
    low = line.lower()
    findings = []
    if any(k in low for k in ("eval(", "exec(", "subprocess.call(", "os.system(")):
        findings.append("security: dynamic code execution")
    is_env_read = any(k in low for k in ("process.env.", "os.environ", "os.getenv("))
    if any(k in low for k in ("password", "secret", "api_key", "token")) and "=" in low and not is_env_read:
        findings.append("security: possible hardcoded credential")
    if "except:" in low or "catch (e)" in low:
        findings.append("style: bare except / empty catch swallows errors")
    if any(k in low for k in ("console.log(", "print(")):
        findings.append("style: leftover debug output")
    if any(k in low for k in ("while (true", "for (;;)", "while true")):
        findings.append("performance: unbounded loop")
    if any(k in low for k in ("drop table", "truncate", "delete from")) and " where" not in low:
        findings.append("security: destructive SQL without WHERE")
    if "as any" in low:
        findings.append("style: TypeScript any leak")
    if "fixme" in low or "todo" in low:
        findings.append("follow-up: TODO/FIXME marker")
    return findings


def build_review(pr, files):
    """Return a structured Markdown review string."""
    title = pr.get("title", "")
    body = pr.get("body") or ""
    base = pr.get("base", {}).get("ref", "")
    head = pr.get("head", {}).get("ref", "")
    diff = ""
    for f in files:
        diff += f.get("patch", "") + "\n"

    findings = []
    for line in diff.splitlines():
        if line.startswith("+") and not line.startswith("+++"):
            for tag in categorize_line(line):
                findings.append(tag)

    # De-dup and count
    seen = {}
    for f in findings:
        seen[f] = seen.get(f, 0) + 1

    has_tests = any(f["filename"].endswith((".test.ts", ".test.tsx", ".test.js",
                    ".spec.ts", ".spec.tsx", ".spec.js")) or
                    "test" in f["filename"].lower() or
                    "tests/" in f["filename"] for f in files)
    has_ci = any(f["filename"].startswith(".github/workflows/") for f in files)
    has_docs = any(f["filename"].lower().endswith((".md", ".rst")) for f in files)

    lines = []
    lines.append("## PR Review")
    lines.append("")
    lines.append(f"**PR:** {title} ({pr.get('html_url','')})")
    lines.append(f"**Branch:** `{head}` → `{base}`  ·  "
                 f"{'draft' if pr.get('draft') else 'ready'}  ·  "
                 f"{pr.get('additions',0):+} / {pr.get('deletions',0):+} lines, "
                 f"{len(files)} files")
    lines.append("")

    lines.append("### Summary")
    if body:
        first_para = body.strip().split("\n\n")[0][:300]
        lines.append(first_para or "(no description)")
    else:
        lines.append(f"Adds/modifies {len(files)} file(s) on `{head}`.")
    lines.append("")

    lines.append("### Findings")
    if seen:
        for tag, count in sorted(seen.items(), key=lambda x: -x[1]):
            lines.append(f"- **{tag}** × {count}")
    else:
        lines.append("- No risky patterns detected in the diff.")
    lines.append("")

    lines.append("### Test & CI gaps")
    gaps = []
    if not has_tests:
        gaps.append("No test files changed in this PR — add a unit or integration test for the new behaviour.")
    if not has_ci:
        gaps.append("No CI workflow changed — verify the new code path is covered by existing CI.")
    if not has_docs and any(
        f["filename"].endswith((".py", ".ts", ".js"))
        and not f["filename"].endswith((".test.ts", ".test.tsx", ".test.js", ".spec.ts", ".spec.tsx", ".spec.js"))
        for f in files
    ):
        gaps.append("No documentation updated — consider a short doc note for public-facing changes.")
    if gaps:
        lines.extend(f"- {g}" for g in gaps)
    else:
        lines.append("- Tests, CI, and docs all touched. No obvious gap.")
    lines.append("")

    lines.append("### Suggested follow-ups")
    followups = [f for f in seen if "follow-up" in f or "style" in f]
    if followups:
        lines.extend(f"- {f}" for f in followups)
    else:
        lines.append("- None.")
    lines.append("")

    return "\n".join(lines)


def main():
    args = sys.argv[1:]
    post = False
    if "--post" in args:
        post = True
        args = [a for a in args if a != "--post"]

    if len(args) < 3:
        print(f"usage: {sys.argv[0]} [{{--post}}] <owner> <repo> <pr_number> [output_file]")
        sys.exit(1)

    owner, repo, number = args[0], args[1], args[2]
    out = args[3] if len(args) > 3 else None

    pr = fetch_pr(owner, repo, number)
    files = fetch_files(owner, repo, number)
    review = build_review(pr, files)

    if post:
        url = post_comment(owner, repo, number, review)
        print(f"Posted review: {url['html_url']}")
    elif out:
        with open(out, "w") as f:
            f.write(review + "\n")
        print(f"Wrote {out}")
    else:
        print(review)


if __name__ == "__main__":
    main()
