from typing import List, Optional

from ..config import SkillConfig
from ..models import SkillMetadata
from .base import BaseRetriever
from .hybrid import HybridRetriever
from .rerank_pipeline import RerankPipelineRetriever
from .semantic import (
    BgeM3EmbeddingBackend,
    SemanticRetriever,
    SentenceTransformerEmbeddingBackend,
    build_routing_retrieval_text,
)


def _build_bm25_sentence_retriever(config: SkillConfig) -> BaseRetriever:
    backend = SentenceTransformerEmbeddingBackend(model_name=config.sentence_model_name)
    semantic = SemanticRetriever(backend, backend_name="sentence_transformers")
    return HybridRetriever(
        config=config,
        semantic_retriever=semantic,
        enable_bm25=True,
        enable_semantic=True,
        semantic_backend_name="sentence_transformers",
        retrieval_mode="bm25_sentence",
    )


def _build_bm25_bge_m3_retriever(config: SkillConfig) -> BaseRetriever:
    backend = BgeM3EmbeddingBackend(
        model_name=config.bge_m3_model_name,
        use_fp16=config.bge_m3_use_fp16,
    )
    semantic = SemanticRetriever(
        backend,
        text_builder=build_routing_retrieval_text,
        backend_name="bge_m3",
    )
    return HybridRetriever(
        config=config,
        semantic_retriever=semantic,
        enable_bm25=True,
        enable_semantic=True,
        semantic_backend_name="bge_m3",
        retrieval_mode="bm25_bge_m3",
    )


def build_retriever(config: SkillConfig, skills: Optional[List[SkillMetadata]] = None) -> BaseRetriever:
    _ = skills

    if config.retrieval_mode == "bm25_sentence":
        return _build_bm25_sentence_retriever(config)

    if config.retrieval_mode == "bm25_bge_m3":
        return _build_bm25_bge_m3_retriever(config)

    if config.retrieval_mode == "bge_m3_rerank":
        first_stage = _build_bm25_bge_m3_retriever(config)
        first_stage.enable_bm25 = False
        return RerankPipelineRetriever(
            config=config,
            first_stage=first_stage,
            retrieval_mode="bge_m3_rerank",
        )

    if config.retrieval_mode == "bm25_bge_m3_rerank":
        first_stage = _build_bm25_bge_m3_retriever(config)
        return RerankPipelineRetriever(
            config=config,
            first_stage=first_stage,
            retrieval_mode="bm25_bge_m3_rerank",
        )

    raise ValueError(f"unsupported retrieval_mode: {config.retrieval_mode}")
