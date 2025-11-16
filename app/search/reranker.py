from typing import List, Dict, Optional
import sys
import os
import pickle
from pathlib import Path
import hashlib
from app.utils.config import AppConfig

if sys.platform == "win32":
    try:
        import torch
        torch_lib_path = os.path.join(os.path.dirname(torch.__file__), "lib")
        if os.path.exists(torch_lib_path) and hasattr(os, 'add_dll_directory'):
            os.add_dll_directory(torch_lib_path)
    except Exception:
        pass

CROSS_ENCODER_AVAILABLE = None
CrossEncoder = None


class CrossEncoderReranker:
    """
    Cross-encoder based re-ranking for search results.
    Uses sentence-transformers CrossEncoder for semantic re-ranking.
    """

    def __init__(self, model_name: Optional[str] = None):
        self.model_name = model_name or AppConfig.RERANK_MODEL
        self.model = None
        self._cache_dir = AppConfig.HOME_DIR / "model_cache"
        self._cache_dir.mkdir(exist_ok=True, parents=True)
        self._enabled = AppConfig.RERANK_ENABLED

    def _get_cache_path(self) -> Path:
        model_hash = hashlib.md5(self.model_name.encode()).hexdigest()[:16]
        return self._cache_dir / f"reranker_{model_hash}.pkl"

    def _save_model_cache(self):
        if self.model is None:
            return

        try:
            cache_path = self._get_cache_path()
            with open(cache_path, 'wb') as f:
                pickle.dump(self.model, f, protocol=pickle.HIGHEST_PROTOCOL)
        except Exception:
            pass

    def _load_model_cache(self) -> bool:
        cache_path = self._get_cache_path()
        if not cache_path.exists():
            return False

        try:
            with open(cache_path, 'rb') as f:
                self.model = pickle.load(f)
            return True
        except Exception:
            try:
                cache_path.unlink()
            except Exception:
                pass
            return False

    def _init_model(self):
        """Lazy initialization of cross-encoder model."""
        global CROSS_ENCODER_AVAILABLE, CrossEncoder

        if CROSS_ENCODER_AVAILABLE is None:
            try:
                from sentence_transformers import CrossEncoder as CE
                CrossEncoder = CE
                CROSS_ENCODER_AVAILABLE = True
            except (ImportError, Exception):
                CROSS_ENCODER_AVAILABLE = False
                self.model = None
                return

        if not CROSS_ENCODER_AVAILABLE:
            self.model = None
            return

        if self._load_model_cache():
            return

        try:
            self.model = CrossEncoder(self.model_name)
            self._save_model_cache()
        except Exception:
            self.model = None

    def rerank(
        self,
        query: str,
        results: List[Dict],
        top_k: Optional[int] = None
    ) -> List[Dict]:
        """
        Re-rank search results using cross-encoder model.

        Args:
            query: Search query
            results: List of search results
            top_k: Number of top results to re-rank (default: RERANK_TOP_K)

        Returns:
            Re-ranked results (or original if disabled/unavailable)
        """
        # Skip if disabled in config
        if not self._enabled:
            return results

        # Skip if no results
        if not results:
            return results

        # Lazy load model on first use
        if self.model is None:
            self._init_model()

        # If model unavailable, return original results
        if self.model is None:
            return results

        top_k = top_k or AppConfig.RERANK_TOP_K
        top_k = min(top_k, len(results))

        # Split results into re-rankable and rest
        to_rerank = results[:top_k]
        rest = results[top_k:]

        # Prepare query-document pairs
        pairs = []
        for result in to_rerank:
            content = result.get('content', '')
            pairs.append([query, content])

        try:
            # Get cross-encoder scores
            scores = self.model.predict(pairs)

            # Merge scores with results
            for i, score in enumerate(scores):
                to_rerank[i]['cross_encoder_score'] = float(score)

            # Sort by cross-encoder score
            reranked = sorted(
                to_rerank,
                key=lambda x: x.get('cross_encoder_score', 0.0),
                reverse=True
            )

            # Combine reranked + rest
            return reranked + rest

        except Exception:
            # On error, return original results
            return results
