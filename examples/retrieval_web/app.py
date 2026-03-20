from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Mapping

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import AliasChoices, BaseModel, ConfigDict, Field, model_validator

from skill_adapter import SkillConfig, SkillRuntime
from skill_adapter.retrieval.hybrid import HybridRetriever
from skill_adapter.retrieval.semantic import SentenceTransformerEmbeddingBackend
from skill_adapter.routing import SkillRouter

BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parents[1]
DEFAULT_SKILL_DIR = BASE_DIR.parent / "skills"
TEMPLATES_DIR = BASE_DIR / "templates"


class AnalyzeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    query: str = Field(default="", description="User query for retrieval analysis")
    skill_dir: str = Field(default_factory=lambda: str(DEFAULT_SKILL_DIR))
    top_k: int = 3
    bm25_top_k: int = 5
    semantic_top_k: int = 5
    max_active_skills: int = 1
    activation_threshold: float = 0.35
    bm25_weight: float = Field(
        default=0.5,
        validation_alias=AliasChoices("bm25_weight", "bm25Weight", "bm_weight", "bmWeight"),
    )
    semantic_weight: float = Field(
        default=0.5,
        validation_alias=AliasChoices("semantic_weight", "semanticWeight"),
    )
    embedding_model_name: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    enable_bm25_retrieval: bool = Field(
        default=True,
        validation_alias=AliasChoices(
            "enable_bm25_retrieval",
            "enableBm25Retrieval",
            "enable_bm25",
            "enable_bm",
            "enableBM",
        ),
    )
    enable_semantic_retrieval: bool = Field(
        default=True,
        validation_alias=AliasChoices(
            "enable_semantic_retrieval",
            "enableSemanticRetrieval",
            "enable_semantic",
            "enableSemantic",
        ),
    )

    @model_validator(mode="before")
    @classmethod
    def _apply_legacy_weight_aliases(cls, value: Any) -> Any:
        if not isinstance(value, Mapping):
            return value

        data = dict(value)
        if "weight" in data:
            weight_value = data["weight"]
            if isinstance(weight_value, Mapping):
                if "bm25_weight" not in data and "bm25" in weight_value:
                    data["bm25_weight"] = weight_value["bm25"]
                if "semantic_weight" not in data and "semantic" in weight_value:
                    data["semantic_weight"] = weight_value["semantic"]
            else:
                if "bm25_weight" not in data:
                    data["bm25_weight"] = weight_value
                if "semantic_weight" not in data:
                    data["semantic_weight"] = weight_value
        return data


@lru_cache(maxsize=4)
def get_embedding_backend(model_name: str) -> SentenceTransformerEmbeddingBackend:
    return SentenceTransformerEmbeddingBackend(model_name=model_name)


def build_runtime(payload: AnalyzeRequest) -> SkillRuntime:
    config = SkillConfig(
        skill_dirs=[payload.skill_dir],
        top_k=payload.top_k,
        bm25_top_k=payload.bm25_top_k,
        semantic_top_k=payload.semantic_top_k,
        max_active_skills=payload.max_active_skills,
        activation_threshold=payload.activation_threshold,
        bm25_weight=payload.bm25_weight,
        semantic_weight=payload.semantic_weight,
        embedding_model_name=payload.embedding_model_name,
        enable_bm25_retrieval=payload.enable_bm25_retrieval,
        enable_semantic_retrieval=payload.enable_semantic_retrieval,
        debug=True,
    )
    runtime = SkillRuntime(config=config)
    runtime.router = SkillRouter(
        config=config,
        retriever=HybridRetriever(
            config=config,
            embedding_backend=get_embedding_backend(config.embedding_model_name),
        ),
    )
    return runtime


def selected_skill_details(runtime: SkillRuntime, selected_skills: List[Dict[str, Any]]) -> List[Dict[str, str]]:
    items: List[Dict[str, str]] = []
    for selected in selected_skills:
        metadata = runtime.registry.get(selected["skill"])
        items.append(
            {
                "skill": metadata.skill_id,
                "name": metadata.name,
                "description": metadata.description,
                "path": metadata.path,
                "retrieval_text": metadata.retrieval_text,
                "content": Path(metadata.path).read_text(encoding="utf-8"),
            }
        )
    return items


def available_skills(runtime: SkillRuntime) -> List[Dict[str, str]]:
    items: List[Dict[str, str]] = []
    for metadata in runtime.registry.list_metadata():
        items.append(
            {
                "skill": metadata.skill_id,
                "name": metadata.name,
                "description": metadata.description,
                "path": metadata.path,
                "retrieval_text": metadata.retrieval_text,
            }
        )
    return items


app = FastAPI(title="Skill Retrieval Visualizer")
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


@app.get("/", response_class=HTMLResponse)
async def index(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "default_skill_dir": "./examples/skills",
            "default_embedding_model": "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
            "project_root": str(PROJECT_ROOT),
        },
    )


@app.get("/api/health")
async def health() -> Dict[str, str]:
    return {"status": "ok"}


@app.post("/api/analyze")
async def analyze(payload: AnalyzeRequest) -> Dict[str, Any]:
    runtime = build_runtime(payload)
    selection = runtime.route(payload.query, debug=True)
    prepared = runtime.prepare(
        query=payload.query,
        payload={"messages": [{"role": "user", "content": payload.query}]},
        mode="messages",
        debug=True,
    )

    return {
        "query": payload.query,
        "config": payload.model_dump(),
        "selection": {
            "selected_skills": selection.selected_skills,
            "candidates": selection.candidates,
            "reason": selection.reason,
            "fallback": selection.fallback,
        },
        "prepared": {
            "payload": prepared.payload,
            "trace": prepared.trace,
        },
        "selected_skill_details": selected_skill_details(runtime, selection.selected_skills),
        "available_skills": available_skills(runtime),
        "registry_errors": runtime.registry.build_errors,
    }
