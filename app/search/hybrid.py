from typing import List, Dict, Optional
import re
import time
from app.search.vector_db import VectorDatabase
from app.indexer.embeddings import EmbeddingGenerator
from app.search.reranker import CrossEncoderReranker
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
        self.reranker = CrossEncoderReranker()

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
        query_embedding = self.embedding_gen.generate_embeddings(
            [query],
            task="retrieval.query"
        )[0]

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

        # RRF fusion with adaptive K and symbol boosting
        fused_results = self._rrf_fusion(
            query,
            [vector_results, keyword_results],
            limit
        )

        # Cross-encoder re-ranking (automatic if enabled in config)
        rerank_start = time.time()
        reranked_results = self.reranker.rerank(query, fused_results)
        rerank_time = (time.time() - rerank_start) * 1000  # ms

        for result in reranked_results:
            result['search_mode'] = 'hybrid'
            result['rerank_time_ms'] = rerank_time

        return reranked_results

    def _adaptive_rrf_k(self, query: str, result_lists: List[List[Dict]]) -> int:
        """
        Automatically determine optimal RRF K value based on query characteristics.

        Returns:
            - 20: Symbol-specific queries (camelCase, snake_case patterns)
            - 30: Short queries (<5 words) - sharper ranking
            - 60: Default - balanced ranking
        """
        query_lower = query.lower()
        words = query.split()

        # Detect symbol patterns (camelCase, snake_case, specific function/class names)
        has_camel_case = bool(re.search(r'[a-z][A-Z]', query))
        has_snake_case = bool(re.search(r'\w+_\w+', query))

        if has_camel_case or has_snake_case:
            return 20  # Sharp ranking for symbol searches

        # Short queries benefit from sharper ranking
        if len(words) < 5:
            return 30

        # Default balanced ranking
        return self.rrf_k

    def _calculate_symbol_boost(self, result: Dict, query: str) -> float:
        """
        Calculate automatic symbol-aware boost score for a result.

        Boost factors:
        - +0.3: Query term matches node_name exactly
        - +0.2: Query term appears in signature
        - +0.15: Function/class/method definition
        - +0.1: Has docstring
        - +0.05: Top-level scope (depth 0)
        - -0.05 * depth: Penalty for nested scopes
        """
        boost = 0.0
        query_lower = query.lower()
        query_terms = set(re.findall(r'\w+', query_lower))

        # Node name matching
        node_name = result.get('node_name', '').lower()
        if node_name and any(term in node_name for term in query_terms):
            boost += 0.3

        # Signature matching
        signature = result.get('signature', '').lower()
        if signature and any(term in signature for term in query_terms):
            boost += 0.2

        # Prioritize function/class definitions
        chunk_type = result.get('chunk_type', '')
        if chunk_type in ['function_definition', 'class_definition',
                         'method_definition', 'interface_declaration']:
            boost += 0.15

        # Boost documented code
        docstring = result.get('docstring', '')
        if docstring and len(docstring.strip()) > 0:
            boost += 0.1

        # Scope depth: prefer top-level definitions
        scope_depth = result.get('scope_depth', 0)
        if scope_depth == 0:
            boost += 0.05
        else:
            boost -= 0.05 * scope_depth  # Penalty for nested code

        return boost

    def _rrf_fusion(
        self,
        query: str,
        result_lists: List[List[Dict]],
        limit: int
    ) -> List[Dict]:
        # Adaptive K: automatically optimize based on query
        adaptive_k = self._adaptive_rrf_k(query, result_lists)

        rrf_scores = {}

        for result_list in result_lists:
            for rank, result in enumerate(result_list, start=1):
                doc_id = result.get('id', result.get('file_path', ''))

                # Base RRF score
                score = 1.0 / (adaptive_k + rank)

                if doc_id not in rrf_scores:
                    rrf_scores[doc_id] = {
                        'score': 0.0,
                        'result': result
                    }

                rrf_scores[doc_id]['score'] += score

        # Apply symbol-aware boosting
        for doc_id, item in rrf_scores.items():
            symbol_boost = self._calculate_symbol_boost(item['result'], query)
            item['score'] += symbol_boost
            item['result']['symbol_boost'] = symbol_boost

        sorted_results = sorted(
            rrf_scores.values(),
            key=lambda x: x['score'],
            reverse=True
        )

        final_results = []
        for item in sorted_results[:limit]:
            result = item['result']
            result['rrf_score'] = item['score']
            result['adaptive_k'] = adaptive_k
            final_results.append(result)

        return final_results
