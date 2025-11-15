from typing import List, Dict, Optional
import numpy as np
from app.search.vector_db import VectorDatabase
from app.indexer.embeddings import EmbeddingGenerator
from app.utils.config import AppConfig


class HybridSearch:
    def __init__(
        self,
        vector_db: VectorDatabase,
        embedding_gen: EmbeddingGenerator,
        rrf_k: int = AppConfig.RRF_K
    ):
        self.vector_db = vector_db
        self.embedding_gen = embedding_gen
        self.rrf_k = rrf_k

    def search(
        self,
        query: str,
        mode: str = "hybrid",
        limit: int = AppConfig.DEFAULT_SEARCH_LIMIT,
        filters: Optional[Dict] = None
    ) -> List[Dict]:
        if mode == "vector":
            return self._vector_search(query, limit, filters)
        elif mode == "keyword":
            return self._keyword_search(query, limit, filters)
        elif mode == "hybrid":
            return self._hybrid_search(query, limit, filters)
        else:
            return self._hybrid_search(query, limit, filters)

    def _vector_search(
        self,
        query: str,
        limit: int,
        filters: Optional[Dict]
    ) -> List[Dict]:
        query_embedding = self.embedding_gen.generate_embeddings([query])[0]

        results = self.vector_db.vector_search(query_embedding, limit, filters)

        for result in results:
            result['search_mode'] = 'vector'

        return results

    def _keyword_search(
        self,
        query: str,
        limit: int,
        filters: Optional[Dict]
    ) -> List[Dict]:
        results = self.vector_db.keyword_search(query, limit, filters)

        for result in results:
            result['search_mode'] = 'keyword'

        return results

    def _hybrid_search(
        self,
        query: str,
        limit: int,
        filters: Optional[Dict]
    ) -> List[Dict]:
        fetch_limit = int(limit * 1.5)
        vector_results = self._vector_search(query, fetch_limit, filters)
        keyword_results = self._keyword_search(query, fetch_limit, filters)

        fused_results = self._rrf_fusion(
            [vector_results, keyword_results],
            limit
        )

        for result in fused_results:
            result['search_mode'] = 'hybrid'

        return fused_results

    def _rrf_fusion(
        self,
        result_lists: List[List[Dict]],
        limit: int
    ) -> List[Dict]:
        rrf_scores = {}

        for result_list in result_lists:
            for rank, result in enumerate(result_list, start=1):
                doc_id = result.get('id', result.get('file_path', ''))

                score = 1.0 / (self.rrf_k + rank)

                if doc_id not in rrf_scores:
                    rrf_scores[doc_id] = {
                        'score': 0.0,
                        'result': result
                    }

                rrf_scores[doc_id]['score'] += score

        sorted_results = sorted(
            rrf_scores.values(),
            key=lambda x: x['score'],
            reverse=True
        )

        final_results = []
        for item in sorted_results[:limit]:
            result = item['result']
            result['rrf_score'] = item['score']
            final_results.append(result)

        return final_results
