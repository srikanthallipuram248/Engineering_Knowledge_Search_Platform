"""
LangGraph nodes for the Repo Analyzer pipeline.

Graph flow:
  clone_and_scan → run_llm → parse_output
                                ├── success       → END
                                ├── retry (< 3)   → run_llm
                                └── give up (≥ 3) → handle_error → END
"""

import asyncio
import json
import re

from analyzer_service.graph.state import RepoAnalysisState
from analyzer_service.llm_clients.groq_client import get_llm
from analyzer_service.prompts.analyzer_prompts import build_user_context, get_chat_prompt
from analyzer_service.schemas import RepoAnalysisResult
from analyzer_service.services.repo_analyzer import scan_git_url

# ── README post-processing helpers ────────────────────────────────────────
# Covers Python, JS/TS, Go, Rust, Java, Make, Docker — not just Python CLI

_COMMAND_RE = re.compile(
    r"^\s*((?:python|pytest|pip|npm|yarn|pnpm|npx|node|go\s+run|go\s+test|cargo|"
    r"mvn|gradle|docker|docker-compose|make|\.\/\w+)\s+[^\r\n]+)",
    re.MULTILINE,
)
_PATH_RE = re.compile(
    r"^\s*(?:[|`'\- ]*)?([A-Za-z0-9_./-]+(?:\.py|\.js|\.ts|\.go|\.rs|\.java|"
    r"\.json|\.md|\.toml|\.yaml|\.yml|\.txt))\s*$",
    re.MULTILINE,
)


def _purpose_for_command(cmd: str) -> str:
    c = cmd.lower()
    if any(k in c for k in ("pytest", "test", "spec")):
        return "Runs the test suite."
    if any(k in c for k in ("pip install", "npm install", "yarn", "cargo build")):
        return "Installs project dependencies."
    if "docker" in c:
        return "Builds or runs the Docker container."
    if "make" in c:
        return "Runs a Makefile target."
    if any(k in c for k in ("run", "start", "serve", "dev")):
        return "Starts the application."
    return "Runs a documented project command."


def _role_for_path(path: str) -> str:
    p = path.lower()
    if any(p.startswith(d) for d in ("tests/", "test/", "__tests__/", "spec/")):
        return "Test suite for the corresponding module."
    if any(p.startswith(d) for d in ("config/", "configs/", "settings/")):
        return "Configuration module."
    if any(p.startswith(d) for d in ("src/", "lib/", "core/")):
        return "Core implementation module."
    if p in ("main.py", "main.go", "index.js", "index.ts", "app.py", "server.js"):
        return "Primary entry point."
    if p.endswith(("dockerfile", "docker-compose.yml", "docker-compose.yaml")):
        return "Container build / orchestration definition."
    return "Documented repository file."


def _merge_readme_details(data: dict, readme_content: str | None) -> dict:
    """Enrich LLM output with commands + modules extracted from README via regex."""
    if not readme_content:
        return data

    seen_cmds = {c.get("command") for c in data.get("commands", []) if isinstance(c, dict)}
    commands = list(data.get("commands", []))
    for cmd in _COMMAND_RE.findall(readme_content):
        cmd = cmd.strip()
        if cmd not in seen_cmds:
            commands.append({"command": cmd, "purpose": _purpose_for_command(cmd)})
            seen_cmds.add(cmd)
        if len(commands) >= 20:
            break
    data["commands"] = commands

    seen_mods = {m.get("name") for m in data.get("key_modules", []) if isinstance(m, dict)}
    modules = list(data.get("key_modules", []))
    for path in _PATH_RE.findall(readme_content):
        path = path.strip().strip("`")
        if path not in seen_mods:
            modules.append({"name": path, "role": _role_for_path(path)})
            seen_mods.add(path)
        if len(modules) >= 14:
            break
    data["key_modules"] = modules

    return data


# ── Nodes ──────────────────────────────────────────────────────────────────


async def clone_and_scan(state: RepoAnalysisState) -> dict:
    """Node 1 — Shallow-clone and extract all text context from the repo."""
    context = await asyncio.to_thread(scan_git_url, state["git_url"])
    return {
        "repo_name":        context.repo_name,
        "readme_content":   context.readme_content,
        "readme_found":     context.readme_found,
        "folder_tree":      context.folder_tree,
        "manifest_content": context.manifest_content,
        "source_snippets":  context.source_snippets,
    }


async def run_llm(state: RepoAnalysisState) -> dict:
    """Node 2 — Run the LangChain ChatPromptTemplate | ChatGroq chain."""
    chain = get_chat_prompt() | get_llm()

    user_input = build_user_context(
        repo_name=state["repo_name"],
        readme_content=state["readme_content"],
        folder_tree=state["folder_tree"],
        manifest_content=state["manifest_content"],
        source_snippets=state["source_snippets"],
        readme_found=state["readme_found"],
    )

    response = await chain.ainvoke({"user_input": user_input})
    return {"raw_output": response.content}


def parse_output(state: RepoAnalysisState) -> dict:
    """Node 3 — Parse JSON, enrich via regex, validate with Pydantic."""
    raw = state.get("raw_output", "")

    # Strip markdown fences the LLM sometimes adds despite instructions
    if "```" in raw:
        for part in raw.split("```"):
            stripped = part.strip().lstrip("json").strip()
            if stripped.startswith("{"):
                raw = stripped
                break

    try:
        data = json.loads(raw.strip())
        data = _merge_readme_details(data, state.get("readme_content"))
        data["repo_name"] = state["repo_name"]
        data["readme_found"] = state["readme_found"]
        result = RepoAnalysisResult(**data)
        return {"analysis_result": result.model_dump(), "error": None}
    except Exception as exc:
        attempt = state.get("retry_count", 0) + 1
        return {
            "analysis_result": None,
            "retry_count":     attempt,
            "error":           f"Parse attempt {attempt}: {exc} | raw[:200]: {raw[:200]}",
        }


def handle_error(state: RepoAnalysisState) -> dict:
    """Terminal error node — all retries exhausted."""
    return {
        "error": f"Analysis failed after {state.get('retry_count', 3)} attempts. "
                 f"Last error: {state.get('error', 'Unknown')}"
    }
