from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from analyzer_service.graph.builder import run_analysis_graph
from analyzer_service.schemas import RepoAnalysisResult

router = APIRouter()


class AnalyzeRequest(BaseModel):
    git_url: str


@router.post("/repo", response_model=RepoAnalysisResult)
async def analyze_repo(body: AnalyzeRequest):
    """
    Clone *git_url* (shallow), run the LangGraph analysis pipeline,
    and return a structured architecture summary.
    """
    try:
        result = await run_analysis_graph(body.git_url)
        return RepoAnalysisResult(**result)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {exc}")
