import tempfile
from dataclasses import dataclass, field
from pathlib import Path

import git

# Directories to skip while walking the tree
_SKIP_DIRS: frozenset[str] = frozenset({
    ".git", "node_modules", "__pycache__", "dist", "build",
    ".next", ".nuxt", "venv", ".venv", ".env", "vendor",
    "target", "out", ".gradle", ".idea", ".vscode",
})

# File extensions that are binary / irrelevant to analysis
_SKIP_EXTENSIONS: frozenset[str] = frozenset({
    ".lock", ".pyc", ".class", ".o", ".so", ".dll", ".exe",
    ".png", ".jpg", ".jpeg", ".gif", ".ico", ".svg",
    ".woff", ".woff2", ".ttf", ".eot", ".pdf",
    ".zip", ".tar", ".gz", ".bin", ".dat",
})

# README filenames (case-insensitive match)
_README_NAMES: frozenset[str] = frozenset({
    "readme.md", "readme.rst", "readme.txt", "readme",
})

# Manifest / config files that reveal the tech stack
_MANIFEST_NAMES: frozenset[str] = frozenset({
    "package.json", "pyproject.toml", "requirements.txt",
    "go.mod", "pom.xml", "cargo.toml", "composer.json",
    "gemfile", "build.gradle", "setup.py", "setup.cfg",
    "dockerfile", "docker-compose.yml",
})

# Source file extensions worth sampling when no README exists
_SOURCE_EXTENSIONS: frozenset[str] = frozenset({
    ".py", ".js", ".ts", ".jsx", ".tsx",
    ".go", ".java", ".rs", ".rb", ".php", ".cs",
})

_README_CHAR_LIMIT = 24_000
_MANIFEST_CHAR_LIMIT = 2_000
_SOURCE_CHAR_LIMIT = 1_500
_MAX_SOURCE_FILES = 5


@dataclass
class RepoContext:
    readme_content: str | None
    folder_tree: str
    manifest_content: str
    source_snippets: str
    readme_found: bool
    repo_name: str = ""


def scan_git_url(url: str) -> RepoContext:
    """Shallow-clone *url* and scan the working tree."""
    with tempfile.TemporaryDirectory() as tmpdir:
        try:
            git.Repo.clone_from(
                url,
                tmpdir,
                depth=1,
                single_branch=True,
                no_tags=True,
            )
        except git.exc.GitCommandError as exc:
            raise ValueError(
                f"Could not clone repository. "
                f"Make sure the URL is public and correct. Detail: {exc}"
            ) from exc

        root = Path(tmpdir)
        # Some repos extract into a single subfolder
        children = [c for c in root.iterdir() if not c.name.startswith(".")]
        if len(children) == 1 and children[0].is_dir():
            root = children[0]

        repo_name = url.rstrip("/").split("/")[-1].removesuffix(".git")
        return _scan_directory(root, repo_name)


# ── Internal helpers ──────────────────────────────────────────────────────


def _scan_directory(root: Path, repo_name: str = "") -> RepoContext:
    readme = _find_readme(root)
    tree = _build_tree(root, max_depth=3)
    manifests = _read_manifests(root)
    # Only sample source files when no README is available (saves tokens)
    snippets = "" if readme else _read_source_snippets(root)

    return RepoContext(
        readme_content=readme,
        folder_tree=tree,
        manifest_content=manifests,
        source_snippets=snippets,
        readme_found=readme is not None,
        repo_name=repo_name,
    )


def _find_readme(root: Path) -> str | None:
    for item in root.iterdir():
        if item.is_file() and item.name.lower() in _README_NAMES:
            return item.read_text(encoding="utf-8", errors="ignore")[:_README_CHAR_LIMIT]
    return None


def _build_tree(root: Path, max_depth: int = 3) -> str:
    lines: list[str] = [f"{root.name}/"]
    _walk_tree(root, prefix="", depth=0, max_depth=max_depth, lines=lines)
    return "\n".join(lines)


def _walk_tree(
    path: Path,
    prefix: str,
    depth: int,
    max_depth: int,
    lines: list[str],
) -> None:
    if depth >= max_depth:
        return

    try:
        all_items = sorted(path.iterdir(), key=lambda x: (x.is_file(), x.name.lower()))
    except PermissionError:
        return

    visible = [
        i for i in all_items
        if not (i.is_dir() and i.name in _SKIP_DIRS)
        and not (i.is_file() and i.suffix.lower() in _SKIP_EXTENSIONS)
    ]

    for idx, item in enumerate(visible):
        is_last = idx == len(visible) - 1
        connector = "└── " if is_last else "├── "
        label = item.name + ("/" if item.is_dir() else "")
        lines.append(f"{prefix}{connector}{label}")

        if item.is_dir():
            extension = "    " if is_last else "│   "
            _walk_tree(item, prefix + extension, depth + 1, max_depth, lines)


def _read_manifests(root: Path) -> str:
    parts: list[str] = []
    for item in root.iterdir():
        if item.is_file() and item.name.lower() in _MANIFEST_NAMES:
            text = item.read_text(encoding="utf-8", errors="ignore")[:_MANIFEST_CHAR_LIMIT]
            parts.append(f"=== {item.name} ===\n{text}")
    return "\n\n".join(parts)


def _read_source_snippets(root: Path) -> str:
    parts: list[str] = []
    count = 0
    for item in sorted(root.iterdir()):
        if (
            item.is_file()
            and item.suffix.lower() in _SOURCE_EXTENSIONS
            and count < _MAX_SOURCE_FILES
        ):
            text = item.read_text(encoding="utf-8", errors="ignore")[:_SOURCE_CHAR_LIMIT]
            parts.append(f"=== {item.name} ===\n{text}")
            count += 1
    return "\n\n".join(parts)
