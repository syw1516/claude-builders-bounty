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

# ---- 第二轮回归测试（has_tests 假阳性 / doc-gap 扩展名 / env 边界 / patch null） ----

# has_tests 假阳性：文件名恰好含 "test" 子串但不是测试文件，应报"缺少测试"
for name in ("app/latest.ts", "app/api/testify.py", "src/contest.js"):
    r = rp.build_review(pr, [{"filename": name, "patch": "+ x = 1\n"}])
    assert "No test files changed" in r, f"{name} should be flagged as missing tests"

# 但真正的测试文件仍应被识别（后缀与目录两种写法）
for name in ("tests/login.test.tsx", "src/__tests__/app.spec.js", "test/util.test.py"):
    r = rp.build_review(pr, [{"filename": name, "patch": "+ expect(1).toBe(1)\n"}])
    assert "No test files changed" not in r, f"{name} should count as a test file"

# doc-gap 扩展名对齐：纯 .tsx 源码 PR 应报"无文档更新"（旧列表漏 .tsx）
r = rp.build_review(pr, [{"filename": "app/login/page.tsx", "patch": "+ const a = 1\n"}])
assert "No documentation updated" in r, "tsx-only PR should trigger doc gap"

# doc-gap 排除测试文件：纯 .test.tsx PR 不应报"无文档更新"
r = rp.build_review(pr, [{"filename": "app/login/page.test.tsx", "patch": "+ expect(1).toBe(1)\n"}])
assert "No documentation updated" not in r, "test-only PR should not trigger doc gap"

# env 读取边界：process.env['X']（不带点）也不该误报
r = rp.build_review(pr, [{"filename": "app/c.js", "patch": "+ const token = process.env['TOKEN']\n"}])
assert "security: possible hardcoded credential" not in r, "process.env['X'] is an env read"

# patch 键缺失或为 null（二进制文件）不应崩溃
rp.build_review(pr, [{"filename": "assets/logo.png"}])
rp.build_review(pr, [{"filename": "assets/logo.png", "patch": None}])

print("round-2 regression tests (has_tests/doc-gap/env-boundary/patch-null) passed")
