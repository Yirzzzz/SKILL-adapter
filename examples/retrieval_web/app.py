from pathlib import Path
from typing import Any, Dict, List, Mapping

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import AliasChoices, BaseModel, ConfigDict, Field, model_validator

from skill_adapter import SkillConfig, SkillRuntime

BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parents[1]
DEFAULT_SKILL_DIR = BASE_DIR.parent / "skills"
TEMPLATES_DIR = BASE_DIR / "templates"

MODE_PARAMETER_PROFILE: Dict[str, Dict[str, Any]] = {
    "bm25_sentence": {
        "label": "BM25 + Sentence",
        "required_params": [
            "top_k",
            "bm25_top_k",
            "semantic_top_k",
            "bm25_weight",
            "semantic_weight",
            "activation_threshold",
            "sentence_model_name",
        ],
        "optional_params": [
            "max_active_skills",
            "skill_dir",
        ],
    },
    "bm25_bge_m3": {
        "label": "BM25 + BGE-M3",
        "required_params": [
            "top_k",
            "bm25_top_k",
            "semantic_top_k",
            "bm25_weight",
            "semantic_weight",
            "activation_threshold",
            "bge_m3_model_name",
        ],
        "optional_params": [
            "max_active_skills",
            "skill_dir",
        ],
    },
    "bge_m3_rerank": {
        "label": "BGE-M3 + Rerank",
        "required_params": [
            "top_k",
            "semantic_top_k",
            "rerank_top_k",
            "activation_threshold",
            "bge_m3_model_name",
            "reranker_model_name",
        ],
        "optional_params": [
            "max_active_skills",
            "skill_dir",
        ],
    },
    "bm25_bge_m3_rerank": {
        "label": "BM25 + BGE-M3 + Rerank",
        "required_params": [
            "top_k",
            "bm25_top_k",
            "semantic_top_k",
            "rerank_top_k",
            "bm25_weight",
            "semantic_weight",
            "activation_threshold",
            "bge_m3_model_name",
            "reranker_model_name",
        ],
        "optional_params": [
            "max_active_skills",
            "skill_dir",
        ],
    },
}


class AnalyzeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    query: str = Field(default="", description="User query for retrieval analysis")
    skill_dir: str = Field(default_factory=lambda: str(DEFAULT_SKILL_DIR))
    retrieval_mode: str = Field(default="bm25_sentence")
    top_k: int = 3
    bm25_top_k: int = 5
    semantic_top_k: int = 5
    rerank_top_k: int = 20
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
    sentence_model_name: str = Field(
        default="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
        validation_alias=AliasChoices("sentence_model_name", "embedding_model_name", "embeddingModelName"),
    )
    bge_m3_model_name: str = "BAAI/bge-m3"
    reranker_model_name: str = "BAAI/bge-reranker-v2-m3"
    enable_bm25_retrieval: bool = True
    enable_semantic_retrieval: bool = True

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

        if data.get("enable_bm") is False:
            if "retrieval_mode" not in data and "retrievalMode" not in data:
                data["retrieval_mode"] = "bge_m3_rerank"

        return data


def build_runtime(payload: AnalyzeRequest) -> SkillRuntime:
    config = SkillConfig(
        skill_dirs=[payload.skill_dir],
        retrieval_mode=payload.retrieval_mode,
        top_k=payload.top_k,
        bm25_top_k=payload.bm25_top_k,
        semantic_top_k=payload.semantic_top_k,
        rerank_top_k=payload.rerank_top_k,
        max_active_skills=payload.max_active_skills,
        activation_threshold=payload.activation_threshold,
        bm25_weight=payload.bm25_weight,
        semantic_weight=payload.semantic_weight,
        sentence_model_name=payload.sentence_model_name,
        bge_m3_model_name=payload.bge_m3_model_name,
        reranker_model_name=payload.reranker_model_name,
        debug=True,
    )
    return SkillRuntime(config=config)


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
    default_config = SkillConfig(skill_dirs=[str(DEFAULT_SKILL_DIR)])
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "default_skill_dir": "./examples/skills",
            "default_retrieval_mode": default_config.retrieval_mode,
            "default_embedding_model": default_config.sentence_model_name,
            "default_bge_m3_model": default_config.bge_m3_model_name,
            "default_reranker_model": default_config.reranker_model_name,
            "project_root": str(PROJECT_ROOT),
        },
    )


@app.get("/api/health")
async def health() -> Dict[str, str]:
    return {"status": "ok"}


@app.get("/api/retrieval/modes")
async def retrieval_modes() -> Dict[str, Any]:
    return {
        "default_mode": "bm25_sentence",
        "modes": MODE_PARAMETER_PROFILE,
    }


@app.get("/api/retrieval/modes/{mode}")
async def retrieval_mode_detail(mode: str) -> Dict[str, Any]:
    if mode not in MODE_PARAMETER_PROFILE:
        return {
            "mode": mode,
            "found": False,
            "supported_modes": sorted(MODE_PARAMETER_PROFILE.keys()),
        }
    return {
        "mode": mode,
        "found": True,
        **MODE_PARAMETER_PROFILE[mode],
    }


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
        "mode_profile": MODE_PARAMETER_PROFILE.get(payload.retrieval_mode, {}),
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
