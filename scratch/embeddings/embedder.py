from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

class SentenceEmbedder:
    """
    Wrapper cho Sentence Transformers để sinh Embedding vectors.
    Sử dụng model phù hợp với tiếng Việt.
    """
    def __init__(self, model_name: str = "keepitreal/vietnamese-sbert") -> None:
        self.model_name = model_name
        self._model: Any = None
        
    def _load_model(self) -> None:
        if self._model is None:
            logger.info("Đang tải model embedding: %s", self.model_name)
            try:
                from sentence_transformers import SentenceTransformer
                self._model = SentenceTransformer(self.model_name)
            except ImportError:
                raise ImportError(
                    "Cần cài đặt thư viện sentence-transformers để dùng tính năng này. "
                    "Hãy chạy: pip install sentence-transformers"
                )

    def embed(self, text: str | list[str]) -> list[float] | list[list[float]]:
        """
        Sinh embedding cho 1 câu hoặc 1 mảng câu.
        Trả về vector dưới dạng list python tiêu chuẩn (Float array).
        """
        self._load_model()
        
        if isinstance(text, str):
            embedding = self._model.encode(text)
            return embedding.tolist()
            
        embeddings = self._model.encode(text)
        return embeddings.tolist()
