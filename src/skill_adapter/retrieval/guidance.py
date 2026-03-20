from typing import Literal

MissingKind = Literal["bge_m3", "reranker"]


def build_missing_model_guidance(kind: MissingKind) -> str:
    if kind == "bge_m3":
        return (
            "Suggestion: switch retrieval_mode to 'bm25_sentence' (or keep 'bm25_bge_m3' after installing dependencies). "
            "Install dependency: pip install FlagEmbedding. "
            "Model cache directory defaults to ~/.cache/huggingface/hub; "
            "set HF_HOME (for example: HF_HOME=E:/models/hf_cache) before starting the service if you want a custom directory."
        )

    return (
        "Suggestion: switch retrieval_mode to 'bm25_bge_m3' or 'bm25_sentence' if reranker is unavailable. "
        "Install dependency: pip install FlagEmbedding. "
        "Reranker cache directory defaults to ~/.cache/huggingface/hub; "
        "set HF_HOME (for example: HF_HOME=E:/models/hf_cache) before starting the service if you want a custom directory."
    )
