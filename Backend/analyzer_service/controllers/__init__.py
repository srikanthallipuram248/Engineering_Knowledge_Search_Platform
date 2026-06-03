from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, HttpUrl

from analyzer_service.llm_clients.groq_client import analyze_with_groq
from analyzer_service.schemas import RepoAnalysisResult
from analyzer_service.services.repo_analyzer import scan_git_url

router = APIRouter()


class AnalyzeRequest(BaseModel):
    git_url: str


@router.post("/repo", response_model=RepoAnalysisResult)
async def analyze_repo(body: AnalyzeRequest):
    """
    Clone *git_url* (shallow), scan the repo, and return a structured
    architecture summary powered by Groq.
    """
    try:
        context = scan_git_url(body.git_url)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to clone repository: {exc}")

    try:
        result = await analyze_with_groq(
            repo_name=context.repo_name,
            readme_content=context.readme_content,
            folder_tree=context.folder_tree,
            manifest_content=context.manifest_content,
            source_snippets=context.source_snippets,
            readme_found=context.readme_found,
        )
    except ValueError as exc:
        raise HTTPException(status_code=502, detail=str(exc))

    return result
