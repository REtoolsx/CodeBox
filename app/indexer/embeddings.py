from typing import List, Optional
import os
import sys
import numpy as np
from app.utils.config import AppConfig

if sys.platform == "win32":
    try:
        import torch
        torch_lib_path = os.path.join(os.path.dirname(torch.__file__), "lib")
        if os.path.exists(torch_lib_path) and hasattr(os, 'add_dll_directory'):
            os.add_dll_directory(torch_lib_path)
    except Exception:
        pass

SENTENCE_TRANSFORMERS_AVAILABLE = None
SentenceTransformer = None


class EmbeddingGenerator:
    def __init__(self, model_name: Optional[str] = None):
        config_model = model_name or AppConfig.get_embedding_model() or 'all-MiniLM-L6-v2'

        model_info = AppConfig.get_embedding_model_info(config_model)
        if model_info:
            self.model_name = model_info['full_name']
        else:
            self.model_name = config_model

        self.model = None
        self._init_model()

    def _init_model(self):
        global SENTENCE_TRANSFORMERS_AVAILABLE, SentenceTransformer

        if SENTENCE_TRANSFORMERS_AVAILABLE is None:
            try:
                from sentence_transformers import SentenceTransformer as ST
                SentenceTransformer = ST
                SENTENCE_TRANSFORMERS_AVAILABLE = True
            except (ImportError, Exception):
                SENTENCE_TRANSFORMERS_AVAILABLE = False
                self.model = None
                return

        if not SENTENCE_TRANSFORMERS_AVAILABLE:
            self.model = None
            return

        try:
            self.model = SentenceTransformer(self.model_name)

        except Exception:
            self.model = None

    def generate_embeddings(
        self,
        texts: List[str],
        batch_size: int = 32
    ) -> np.ndarray:
        if not texts:
            return np.array([])

        if self.model is None:
            return self._generate_placeholder_embeddings(len(texts))

        try:
            embeddings = self.model.encode(
                texts,
                batch_size=batch_size,
                show_progress_bar=len(texts) > 100,
                convert_to_numpy=True,
                normalize_embeddings=True
            )

            return embeddings

        except Exception:
            return self._generate_placeholder_embeddings(len(texts))

    def _generate_placeholder_embeddings(self, count: int) -> np.ndarray:
        dim = AppConfig.EMBEDDING_DIM
        embeddings = np.random.randn(count, dim).astype(np.float32)
        norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
        norms = np.where(norms == 0, 1, norms)
        return embeddings / norms

    def get_embedding_dim(self) -> int:
        if self.model is not None:
            return self.model.get_sentence_embedding_dimension()

        return AppConfig.EMBEDDING_DIM
