"""
Builds and compiles the LangGraph StateGraph for Phase 1 repo analysis.

Graph topology:

  [START]
     │
     ▼
  clone_and_scan          ← clone repo, extract README / folder tree
     │
     ▼
  run_llm                 ← ChatGroq via LangChain, returns raw JSON text
     │
     ▼
  parse_output            ← validate JSON, Pydantic, enrich from README
     │
     ├── success ─────────────────────────────────────► [END]
     ├── retry (retry_count < 3) ─────────────────────► run_llm
     └── give_up (retry_count ≥ 3) ──► handle_error ──► [END]
"""

from langgraph.graph import END, StateGraph

from analysis.graph.nodes import (
    clone_and_scan,
    handle_error,
    parse_output,
    run_llm,
)
from analysis.graph.state import RepoAnalysisState


# ── Routing logic ──────────────────────────────────────────────────────────

def _route_after_parse(state: RepoAnalysisState) -> str:
    if state.get("analysis_result") is not None:
        return "success"
    if state.get("retry_count", 0) < 3:
        return "retry"
    return "give_up"


# ── Graph assembly ─────────────────────────────────────────────────────────

def _build_graph() -> StateGraph:
    graph = StateGraph(RepoAnalysisState)

    graph.add_node("clone_and_scan", clone_and_scan)
    graph.add_node("run_llm", run_llm)
    graph.add_node("parse_output", parse_output)
    graph.add_node("handle_error", handle_error)

    graph.set_entry_point("clone_and_scan")
    graph.add_edge("clone_and_scan", "run_llm")
    graph.add_edge("run_llm", "parse_output")
    graph.add_conditional_edges(
        "parse_output",
        _route_after_parse,
        {
            "success":  END,
            "retry":    "run_llm",
            "give_up":  "handle_error",
        },
    )
    graph.add_edge("handle_error", END)

    return graph.compile()


# Compiled once at import time — reused for every request
_graph = _build_graph()


# ── Public entry point ─────────────────────────────────────────────────────

async def run_analysis_graph(git_url: str) -> dict:
    """
    Run the full analysis graph for *git_url*.
    Returns the serialised RepoAnalysisResult dict on success.
    Raises ValueError on clone failure or exhausted retries.
    """
    initial_state: RepoAnalysisState = {
        "git_url":          git_url,
        "repo_name":        "",
        "readme_content":   None,
        "readme_found":     False,
        "folder_tree":      "",
        "manifest_content": "",
        "source_snippets":  "",
        "raw_output":       "",
        "analysis_result":  None,
        "retry_count":      0,
        "error":            None,
    }

    final_state = await _graph.ainvoke(initial_state)

    if not final_state.get("analysis_result"):
        raise ValueError(
            final_state.get("error") or "Analysis produced no result"
        )

    return final_state["analysis_result"]
