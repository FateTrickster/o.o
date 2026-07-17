"""DashScope Embedding API 客户端（OpenAI 兼容端点），用于 RAG 查询向量生成。"""

from __future__ import annotations

import time

import numpy as np
from openai import APIConnectionError, OpenAI, OpenAIError

from backend.app.config import (
    get_dashscope_api_key,
    get_dashscope_base_url,
    get_dashscope_embedding_dimensions,
    get_dashscope_embedding_model,
)

_MAX_BATCH = 10  # DashScope text-embedding-v4 单次请求最多 10 条


class EmbeddingClient:
    """DashScope text-embedding-v4 客户端，配置来自环境变量或 .env.local。"""

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        model: str | None = None,
        dimensions: int | None = None,
        batch_size: int = _MAX_BATCH,
    ) -> None:
        self.api_key = api_key or get_dashscope_api_key()
        self.base_url = (base_url or get_dashscope_base_url()).rstrip("/")
        self.model = model or get_dashscope_embedding_model()
        self.dimensions = dimensions or get_dashscope_embedding_dimensions()
        self.batch_size = max(1, min(batch_size, _MAX_BATCH))
        self._client = OpenAI(api_key=self.api_key, base_url=self.base_url)

    def embed(self, texts: list[str] | str) -> np.ndarray:
        """批量生成向量，返回 float32 数组，形状 (N, dimensions)。"""
        if isinstance(texts, str):
            texts = [texts]
        if not texts:
            raise ValueError("embed() requires at least one input text")
        if any(not str(t).strip() for t in texts):
            raise ValueError("embed() input texts must be non-empty")

        vectors: list[np.ndarray] = []
        for start in range(0, len(texts), self.batch_size):
            batch = texts[start : start + self.batch_size]
            try:
                resp = self._client.embeddings.create(
                    model=self.model,
                    input=batch,
                    dimensions=self.dimensions,
                    encoding_format="float",
                )
            except APIConnectionError as exc:
                raise RuntimeError(
                    f"DashScope embedding request failed (network error): {exc}"
                ) from exc
            except OpenAIError as exc:
                raise RuntimeError(
                    f"DashScope embedding request failed (API error): {exc}"
                ) from exc

            received = len(resp.data) if resp.data else 0
            if received != len(batch):
                raise RuntimeError(
                    f"DashScope returned {received} embeddings for {len(batch)} inputs"
                )

            for item in resp.data:
                vec = np.asarray(item.embedding, dtype=np.float32)
                if vec.shape != (self.dimensions,):
                    raise ValueError(
                        f"Embedding dimension mismatch: expected ({self.dimensions},), "
                        f"got {vec.shape}"
                    )
                if np.any(np.isnan(vec)) or np.any(np.isinf(vec)):
                    raise ValueError("Embedding contains NaN or Inf values")
                vectors.append(vec)

            if start + self.batch_size < len(texts):
                time.sleep(0.5)  # DashScope 免费档限流约 2 QPS

        return np.array(vectors, dtype=np.float32)
