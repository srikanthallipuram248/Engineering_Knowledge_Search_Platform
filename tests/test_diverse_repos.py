"""
Smoke-tests Phase 1 (repo analysis) against diverse public GitHub repos.
Requires the backend running at localhost:5000.

Run:
    cd tests
    python test_diverse_repos.py
"""

import asyncio
import json
import sys
import httpx

API_URL = "http://localhost:5000/api/v1/analyze/repo"
TIMEOUT  = 180  # seconds — shallow clone can take ~30s on slow connections

REPOS = [
    # (label,           url,                                          expect_readme)
    ("Python library",  "https://github.com/psf/requests",           True),
    ("Python web fw",   "https://github.com/pallets/flask",          True),
    ("JS/Node HTTP",    "https://github.com/axios/axios",            True),
    ("Go web fw",       "https://github.com/gin-gonic/gin",          True),
    ("React tooling",   "https://github.com/vitejs/vite",            True),
    ("Rust CLI",        "https://github.com/BurntSushi/ripgrep",     True),
]


async def test_repo(client: httpx.AsyncClient, label: str, url: str, expect_readme: bool) -> bool:
    print(f"\n{'─'*60}")
    print(f"  {label}")
    print(f"  {url}")

    try:
        resp = await client.post(API_URL, json={"git_url": url}, timeout=TIMEOUT)
    except httpx.TimeoutException:
        print("  ✗  TIMEOUT")
        return False

    if resp.status_code != 200:
        print(f"  ✗  HTTP {resp.status_code}: {resp.text[:300]}")
        return False

    data = resp.json()

    readme_ok  = data.get("readme_found") == expect_readme
    has_tech   = len(data.get("tech_stack", [])) > 0
    has_summ   = len(data.get("summary", "")) > 20
    has_arch   = len(data.get("architecture", "")) > 20
    has_mods   = len(data.get("key_modules", [])) > 0

    status = "✓" if all([readme_ok, has_tech, has_summ, has_arch, has_mods]) else "⚠"

    print(f"  {status}  readme_found={data.get('readme_found')}  "
          f"tech_stack={data.get('tech_stack', [])[:4]}...")
    print(f"     summary : {data.get('summary','')[:120]}...")
    print(f"     arch    : {data.get('architecture','')[:120]}...")
    print(f"     modules : {[m['name'] for m in data.get('key_modules',[])[:4]]}")

    if not readme_ok:
        print(f"  ⚠  readme_found mismatch (got {data.get('readme_found')}, expected {expect_readme})")

    return all([has_tech, has_summ, has_arch, has_mods])


async def main() -> None:
    passed = 0
    failed = 0

    async with httpx.AsyncClient() as client:
        # Quick health check first
        try:
            hc = await client.get("http://localhost:5000/health", timeout=5)
            print(f"Backend health: {hc.json()}")
        except Exception:
            print("✗  Backend is not running at localhost:5000 — start it first.")
            sys.exit(1)

        for label, url, expect_readme in REPOS:
            ok = await test_repo(client, label, url, expect_readme)
            if ok:
                passed += 1
            else:
                failed += 1

    print(f"\n{'='*60}")
    print(f"  Results: {passed} passed  {failed} failed  ({len(REPOS)} total)")
    print(f"{'='*60}\n")
    sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    asyncio.run(main())
