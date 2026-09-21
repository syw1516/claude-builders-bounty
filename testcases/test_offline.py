#!/usr/bin/env python3
"""Offline tests for the review logic (no network needed)."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "scripts"))
import importlib.util
spec = importlib.util.spec_from_file_location("review_pr", os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "scripts", "review_pr.py"))
rp = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rp)

pr = {
    "title": "Add user login",
    "body": "Adds a login page with bcrypt hashing.",
    "html_url": "https://github.com/x/y/pull/1",
    "draft": False,
    "additions": 120,
    "deletions": 5,
    "base": {"ref": "main"},
    "head": {"ref": "feat/login"},
}
files = [
    {"filename": "app/login/page.tsx", "patch": "+ import { hash } from 'bcrypt'\n+ const token = process.env.SECRET\n+ const x = eval(input)\n+ console.log('debug')\n+ TODO: handle CSRF\n"},
    {"filename": "app/api/login/route.ts", "patch": "+ DROP TABLE users\n"},
    {"filename": "tests/login.test.tsx", "patch": "+ expect(1).toBe(1)\n"},
]
review = rp.build_review(pr, files)
print(review)
print("---")
assert "security: dynamic code execution" in review
assert "security: possible hardcoded credential" in review
assert "style: leftover debug output" in review
assert "security: destructive SQL without WHERE" in review
assert "No test files changed" not in review   # 因为有 tests/ 目录
print("offline tests passed")
