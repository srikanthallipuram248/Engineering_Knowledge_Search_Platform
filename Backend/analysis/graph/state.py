from typing import TypedDict


class RepoAnalysisState(TypedDict):
    # ── Input ─────────────────────────────────────────────────────────────
    git_url: str

    # ── After clone_and_scan node ─────────────────────────────────────────
    repo_name: str
    readme_content: str | None
    readme_found: bool
    folder_tree: str
    manifest_content: str
    source_snippets: str

    # ── After run_llm node ────────────────────────────────────────────────
    raw_output: str

    # ── After parse_output node ───────────────────────────────────────────
    analysis_result: dict | None   # validated + serialised RepoAnalysisResult
    retry_count: int               # incremented on each parse failure
    error: str | None
