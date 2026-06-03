from langchain_core.prompts import ChatPromptTemplate

# ── System prompt ──────────────────────────────────────────────────────────

SYSTEM_PROMPT = """\
You are a senior software architect. Analyze the provided repository context \
and return ONLY valid JSON. Do not include markdown fences or extra text.

The JSON must exactly match this schema:
{
  "summary": "4-6 sentences: what this project does, who it is for, and its main value",
  "detailed_overview": "3-5 detailed paragraphs explaining project purpose, product value, repository organisation, and how the main workflows fit together",
  "tech_stack": ["every clearly identified technology, framework, language, or runtime"],
  "architecture": "5-8 sentences describing the structural pattern, major layers, boundaries, and how data/control flows through the system",
  "key_modules": [
    { "name": "folder or file name", "role": "2-4 sentences explaining what this module owns and why it matters" }
  ],
  "core_features": [
    {
      "name": "feature name",
      "description": "2-4 sentences explaining what it does and its value to users or developers",
      "evidence": "README section, file, folder, or command that proves this feature exists"
    }
  ],
  "data_flow": ["ordered step describing how data moves through the application"],
  "setup_steps": ["concrete install, configure, or run step from the repository context"],
  "commands": [
    { "command": "exact command string", "purpose": "what this command does" }
  ],
  "testing": "2-5 sentences describing test strategy, commands, and coverage areas evidenced in the context. Use 'Unknown' if no test information is present.",
  "notable_design_decisions": ["specific design decision with rationale evidenced in the context"],
  "limitations": ["known limitation, dependency, requirement, or operational caveat from the context"],
  "entry_points": ["the most important files or commands a developer would use to start or explore this project"],
  "readme_found": true or false
}

Rules:
- Be factual. Do not invent anything not evidenced in the provided context.
- If a string field cannot be determined, use "Unknown". If a list field cannot be determined, use [].
- tech_stack must be a flat list of strings, e.g. ["Python", "FastAPI", "PostgreSQL"].
- Describe architecture accurately for the actual project type: web API, CLI tool, frontend SPA, library, microservices, data pipeline, etc. Do not apply web-service patterns to CLI tools or vice versa.
- key_modules should cover the 6-10 most important folders or files evidenced in the repo.
- core_features must cover every major user-facing or developer-facing feature visible in the context.
- Set readme_found to true ONLY if a README file was actually present in the provided context.
- Keep the analysis detailed enough that a developer can understand the project without opening the README.
"""


def get_chat_prompt() -> ChatPromptTemplate:
    """Return a LangChain ChatPromptTemplate for the repo analysis chain."""
    return ChatPromptTemplate.from_messages([
        ("system", SYSTEM_PROMPT),
        ("human", "{user_input}"),
    ])


def build_user_context(
    repo_name: str,
    readme_content: str | None,
    folder_tree: str,
    manifest_content: str,
    source_snippets: str,
    readme_found: bool,
) -> str:
    """Assemble all repo context into the human message string."""
    parts = [f"Repository: {repo_name}\n"]

    if readme_found and readme_content:
        parts.append(f"=== README ===\n{readme_content}\n")
    else:
        parts.append("=== README ===\nNot found — infer from folder structure and manifest files.\n")

    parts.append(f"=== FOLDER STRUCTURE ===\n{folder_tree}\n")

    if manifest_content:
        parts.append(f"=== MANIFEST / CONFIG FILES ===\n{manifest_content}\n")

    if source_snippets:
        parts.append(f"=== TOP-LEVEL SOURCE FILE PREVIEWS ===\n{source_snippets}\n")

    parts.append(
        "Return the detailed JSON analysis now. "
        "Prefer concrete details from the provided context over generic labels. "
        f'Set "readme_found" to {"true" if readme_found else "false"}.'
    )

    return "\n".join(parts)
