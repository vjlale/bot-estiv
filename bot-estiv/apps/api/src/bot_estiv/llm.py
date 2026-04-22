"""Factory para modelos LLM — stack 100% Gemini.

- Texto / razonamiento: gemini-3.1-flash-lite-preview (económico + smart)
- Embeddings RAG: gemini-embedding-001 a 768 dims (barato + suficiente)
"""
from __future__ import annotations

from functools import lru_cache

from langchain_core.embeddings import Embeddings
from langchain_core.language_models.chat_models import BaseChatModel

from .config import settings


@lru_cache(maxsize=4)
def get_chat_model(
    model: str | None = None,
    temperature: float = 0.4,
) -> BaseChatModel:
    """Devuelve un ChatModel de LangChain (Gemini) listo para usar en agentes."""
    from langchain_google_genai import ChatGoogleGenerativeAI

    return ChatGoogleGenerativeAI(
        model=model or settings.gemini_model,
        temperature=temperature,
        google_api_key=settings.google_api_key,
    )


class _GeminiEmbeddings(Embeddings):
    """Wrapper sobre google-genai con output_dimensionality configurable.

    Implementa la interfaz `Embeddings` de LangChain para que sea drop-in
    en cualquier código que ya use embed_documents / embed_query.
    """

    def __init__(self, model: str, dim: int, api_key: str) -> None:
        from google import genai

        self._client = genai.Client(api_key=api_key)
        self._model = model
        self._dim = dim

    def _embed(self, texts: list[str], task_type: str) -> list[list[float]]:
        from google.genai import types

        result = self._client.models.embed_content(
            model=self._model,
            contents=texts,
            config=types.EmbedContentConfig(
                task_type=task_type,
                output_dimensionality=self._dim,
            ),
        )
        return [list(e.values) for e in result.embeddings]

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return self._embed(texts, task_type="RETRIEVAL_DOCUMENT")

    def embed_query(self, text: str) -> list[float]:
        return self._embed([text], task_type="RETRIEVAL_QUERY")[0]


@lru_cache(maxsize=1)
def get_embeddings() -> Embeddings:
    """Embeddings Gemini para RAG con la dimensión configurada (default 768)."""
    return _GeminiEmbeddings(
        model=settings.gemini_embedding_model,
        dim=settings.gemini_embedding_dim,
        api_key=settings.google_api_key,
    )
