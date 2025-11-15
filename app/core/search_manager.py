from typing import Optional, List, Dict, Any, Tuple
from dataclasses import dataclass

from app.search.vector_db import VectorDatabase
from app.search.hybrid import HybridSearch
from app.indexer.embeddings import EmbeddingGenerator
from app.core.model_validator import ModelValidator, ModelValidationResult
from app.core.project_context import ProjectContextManager
from app.core.search_factory import create_search_engine
from app.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class SearchResult:
    """Result of a search operation"""
    results: List[Dict[str, Any]]
    validation: ModelValidationResult
    total_results: int
    execution_time_ms: float


class SearchManager:
    """Centralized search workflow management for CLI"""

    def __init__(self, project_path: Optional[str] = None):
        """
        Initialize search manager

        Args:
            project_path: Project directory path (None uses current directory)
        """
        if project_path is None:
            project_ctx = ProjectContextManager()
            self.project_path = project_ctx.project_path
        else:
            self.project_path = project_path

        # Cached search engine components
        self._vector_db: Optional[VectorDatabase] = None
        self._hybrid_search: Optional[HybridSearch] = None
        self._embedding_gen: Optional[EmbeddingGenerator] = None

    def initialize_search(self) -> Tuple[VectorDatabase, HybridSearch, EmbeddingGenerator]:
        """
        Initialize or return cached search engine

        Returns:
            Tuple of (VectorDatabase, HybridSearch, EmbeddingGenerator)
        """
        if self._vector_db is None:
            logger.info(f"Initializing search engine for: {self.project_path}")
            self._vector_db, self._hybrid_search, self._embedding_gen = create_search_engine(
                self.project_path
            )
        else:
            logger.debug("Using cached search engine")

        return self._vector_db, self._hybrid_search, self._embedding_gen

    def validate_models(self) -> ModelValidationResult:
        """
        Validate indexed model vs current search model

        Returns:
            ModelValidationResult with validation details
        """
        return ModelValidator.validate_search_models(self.project_path)

    def execute_search(
        self,
        query: str,
        mode: str = "hybrid",
        limit: int = 10,
        language: Optional[str] = None,
        validate_model: bool = True
    ) -> SearchResult:
        """
        Execute search operation with validation

        Args:
            query: Search query string
            mode: Search mode (hybrid, vector, keyword)
            limit: Maximum number of results
            language: Optional language filter
            validate_model: Whether to validate model compatibility

        Returns:
            SearchResult with results and metadata

        Raises:
            ValueError: If search parameters are invalid
            RuntimeError: If search execution fails
        """
        import time

        if not query or not query.strip():
            raise ValueError("Search query cannot be empty")

        if limit <= 0:
            raise ValueError("Limit must be positive")

        if mode not in ["hybrid", "vector", "keyword"]:
            raise ValueError(f"Invalid search mode: {mode}")

        try:
            search_start = time.time()

            # Validate models if requested
            validation_result = None
            if validate_model:
                validation_result = self.validate_models()

                if validation_result.has_mismatch:
                    logger.warning(validation_result.warning_message)

            # Initialize search engine
            _, hybrid_search, _ = self.initialize_search()

            # Prepare filters
            filters = {}
            if language:
                filters['language'] = language

            # Execute search
            exec_start = time.time()
            results = hybrid_search.search(
                query=query,
                mode=mode,
                limit=limit,
                filters=filters
            )
            exec_time = (time.time() - exec_start) * 1000

            total_time = (time.time() - search_start) * 1000

            logger.info(
                f"Search completed: {len(results)} results in {total_time:.2f}ms "
                f"(execution: {exec_time:.2f}ms)"
            )

            return SearchResult(
                results=results,
                validation=validation_result,
                total_results=len(results),
                execution_time_ms=exec_time
            )

        except Exception as e:
            logger.error(f"Search failed: {str(e)}")
            raise RuntimeError(f"Search execution failed: {str(e)}") from e

    def clear_cache(self) -> None:
        """Clear cached search engine components"""
        self._vector_db = None
        self._hybrid_search = None
        self._embedding_gen = None
        logger.info("Search engine cache cleared")
