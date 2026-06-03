SYSTEM_PROMPT = """\
You are a senior software architect. Analyze the provided repository context
and return ONLY valid JSON. Do not include markdown fences or extra text.

The JSON must exactly match this schema:
{
  "summary": "4-6 sentences: what this project does, who it is for, and its main value",
  "detailed_overview": "3-5 detailed paragraphs in plain text explaining project purpose, product value, repository organization, and how the main workflows fit together",
  "tech_stack": ["every clearly identified technology, framework, or language"],
  "architecture": "5-8 sentences describing the structural pattern, major layers, boundaries, and how data/control flows through the system",
  "key_modules": [
    { "name": "folder or file name", "role": "2-4 sentences explaining what this module owns and why it matters" }
  ],
  "core_features": [
    {
      "name": "feature or task name",
      "description": "2-4 sentences explaining what it does, main behavior, and user/developer value",
      "evidence": "README section, command, file, or folder that proves this feature exists"
    }
  ],
  "data_flow": ["ordered step describing how data moves through the application"],
  "setup_steps": ["concrete setup or run step from the repository context"],
  "commands": [
    { "command": "exact command", "purpose": "what this command runs or demonstrates" }
  ],
  "testing": "2-5 sentences describing test strategy, test commands, and coverage areas evidenced in the context",
  "notable_design_decisions": ["specific design decision with rationale from the context"],
  "limitations": ["known limitation, dependency, requirement, or operational caveat from the context"],
  "entry_points": ["the most important files or commands a developer would use to start or explore this project"],
  "readme_found": true
}

Rules:
- Be factual. Do not invent anything not evidenced in the provided context.
- If a field cannot be determined, use "Unknown" rather than guessing.
- tech_stack must be a flat list of strings, such as ["Python", "FastAPI", "PostgreSQL"].
- Never call separate CLI scripts "microservices" unless the README proves they are independently deployed services.
- For terminal-first Python repos, describe the architecture as modular CLI, layered CLI application, or task-oriented scripts if that matches the evidence.
- If the README has a project structure section, key_modules must include at least 8 modules.
- If the README lists many commands, commands must include at least 10 commands.
- core_features must cover every major user-facing or assessment-facing feature.
- data_flow must include 6-12 ordered steps when the README describes a workflow.
- setup_steps should include environment, dependency, API key, test, and recommended demo steps when present.
- limitations should include API keys, network dependencies, provider failures, simplified assumptions, or scope caveats when present.
- Keep the answer detailed enough that a developer can understand the project without opening the README.
- readme_found must reflect whether a README was actually present in the context.
"""


def build_user_prompt(
    repo_name: str,
    readme_content: str | None,
    folder_tree: str,
    manifest_content: str,
    source_snippets: str,
    readme_found: bool,
) -> str:
    parts = [f"Repository: {repo_name}\n"]

    if readme_found and readme_content:
        parts.append(f"=== README ===\n{readme_content}\n")
    else:
        parts.append("=== README ===\nNot found.\n")

    parts.append(f"=== FOLDER STRUCTURE ===\n{folder_tree}\n")

    if manifest_content:
        parts.append(f"=== MANIFEST / CONFIG FILES ===\n{manifest_content}\n")

    if source_snippets:
        parts.append(f"=== TOP-LEVEL SOURCE FILE PREVIEWS ===\n{source_snippets}\n")

    parts.append(
        'Return the detailed JSON analysis now. Prefer concrete details from the README over generic architecture labels. '
        'Set "readme_found" to '
        f'{"true" if readme_found else "false"}.'
    )

    return "\n".join(parts)
