import json
import re

from groq import APIError, AsyncGroq, RateLimitError

from analyzer_service.prompts.analyzer_prompts import SYSTEM_PROMPT, build_user_prompt
from analyzer_service.schemas import RepoAnalysisResult
from shared.config import settings

_client = AsyncGroq(api_key=settings.GROQ_API_KEY)


_COMMAND_RE = re.compile(r"^\s*((?:python|pytest|pip)\s+[^\r\n]+)", re.MULTILINE)
_PATH_RE = re.compile(
    r"^\s*(?:[|`'\- ]*)?([A-Za-z0-9_./-]+(?:\.py|\.json|\.md|\.toml|\.txt))\s*$",
    re.MULTILINE,
)


def _purpose_for_command(command: str) -> str:
    if "pytest" in command:
        return "Runs the repository test suite."
    if "pip install" in command:
        return "Installs project dependencies."
    if "task1" in command:
        return "Runs the portfolio risk calculator workflow."
    if "task2" in command:
        return "Runs the live market data fetch workflow."
    if "task3" in command:
        return "Runs the AI-powered portfolio explanation workflow."
    if "task4" in command or "crash-story" in command:
        return "Runs the crash scenario story generator workflow."
    if "main.py" in command:
        return "Runs the combined CLI entry point or selected task mode."
    return "Runs a documented repository command."


def _role_for_path(path: str) -> str:
    if path.startswith("tests/"):
        return "Test coverage for the corresponding CLI, core module, or workflow."
    if path.startswith("config/"):
        return "Configuration module used to centralize prompts, thresholds, asset catalogs, or assumptions."
    if path.startswith("core/"):
        return "Core implementation module containing reusable business logic for the CLI workflows."
    if path.startswith("cli/"):
        return "CLI support module for user input or command-line interaction."
    if path.startswith("data/"):
        return "Data file used for sample portfolios, dry-run scenarios, or deterministic demos."
    if path.startswith("task"):
        return "Task-specific CLI entry point documented in the README."
    if path == "main.py":
        return "Combined command-line entry point for the repository."
    return "Documented repository file listed in the README project structure."


def _merge_readme_details(data: dict, readme_content: str | None) -> dict:
    if not readme_content:
        return data

    existing_commands = {
        item.get("command")
        for item in data.get("commands", [])
        if isinstance(item, dict)
    }
    commands = list(data.get("commands", []))
    for command in _COMMAND_RE.findall(readme_content):
        command = command.strip()
        if command not in existing_commands:
            commands.append({
                "command": command,
                "purpose": _purpose_for_command(command),
            })
            existing_commands.add(command)
        if len(commands) >= 20:
            break
    data["commands"] = commands

    existing_modules = {
        item.get("name")
        for item in data.get("key_modules", [])
        if isinstance(item, dict)
    }
    modules = list(data.get("key_modules", []))
    for path in _PATH_RE.findall(readme_content):
        path = path.strip().strip("`")
        if path not in existing_modules:
            modules.append({
                "name": path,
                "role": _role_for_path(path),
            })
            existing_modules.add(path)
        if len(modules) >= 14:
            break
    data["key_modules"] = modules

    return data


async def analyze_with_groq(
    repo_name: str,
    readme_content: str | None,
    folder_tree: str,
    manifest_content: str,
    source_snippets: str,
    readme_found: bool,
) -> RepoAnalysisResult:
    user_prompt = build_user_prompt(
        repo_name=repo_name,
        readme_content=readme_content,
        folder_tree=folder_tree,
        manifest_content=manifest_content,
        source_snippets=source_snippets,
        readme_found=readme_found,
    )

    for attempt in range(3):
        try:
            response = await _client.chat.completions.create(
                model=settings.GROQ_ANALYSIS_MODEL,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0,
                max_tokens=4096,
                response_format={"type": "json_object"},
            )
        except RateLimitError as exc:
            raise ValueError(
                "Groq quota or rate limit was exceeded. Check the Groq API key limits "
                "or use a key with available capacity."
            ) from exc
        except APIError as exc:
            raise ValueError(f"Groq analysis request failed: {exc}") from exc

        raw = response.choices[0].message.content or ""
        try:
            data = json.loads(raw)
            data = _merge_readme_details(data, readme_content)
            data["repo_name"] = repo_name
            data["readme_found"] = readme_found
            return RepoAnalysisResult(**data)
        except (json.JSONDecodeError, Exception):
            if attempt == 2:
                raise ValueError(f"Groq returned invalid JSON after 3 attempts: {raw[:300]}")
