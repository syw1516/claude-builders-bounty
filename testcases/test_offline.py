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
    {"filename": "app/login/page.tsx", "patch": "+ import { hash } from 'bcrypt'\n+ const token = process.env.SECRET\n+ password = \"hunter2\"\n+ const x = eval(input)\n+ console.log('debug')\n+ TODO: handle CSRF\n"},
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

# ---- 回归测试（凭据检测假阳性修复 + 补覆盖） ----

# 环境变量读取不应被误判为硬编码凭据
files_env = [
    {"filename": "app/config.py", "patch": "+ token = os.environ['API_TOKEN']\n"},
    {"filename": "app/config2.js", "patch": "+ const secret = process.env.SECRET\n"},
    {"filename": "app/config3.py", "patch": "+ api_key = os.getenv('KEY')\n"},
]
review_env = rp.build_review(pr, files_env)
assert "security: possible hardcoded credential" not in review_env, "env var reads should not be flagged"

# 真正硬编码的凭据仍应被抓到
files_hardcoded = [
    {"filename": "app/bad.py", "patch": "+ password = \"hunter2\"\n"},
]
review_bad = rp.build_review(pr, files_hardcoded)
assert "security: possible hardcoded credential" in review_bad

# TypeScript any 泄漏规则要有测试覆盖
files_any = [
    {"filename": "app/types.ts", "patch": "+ const x = value as any\n"},
]
review_any = rp.build_review(pr, files_any)
assert "style: TypeScript any leak" in review_any

# 无限循环规则要有测试覆盖
files_loop = [
    {"filename": "app/loop.js", "patch": "+ while (true) { run(); }\n"},
]
review_loop = rp.build_review(pr, files_loop)
assert "performance: unbounded loop" in review_loop

print("regression tests for env-var false positive + any-leak + loop passed")
