import json
import sys
import time
from pathlib import Path
from typing import Optional, List
from datetime import datetime
from app.indexer.indexer import CoreIndexer
from app.utils.config import AppConfig
from app.utils.project_manager import ProjectManager
from app.utils.logger import get_logger
from app.core.indexing_manager import IndexingManager
from app.core.search_manager import SearchManager
from app.core.result_formatter import calculate_score, process_cli_results
from app.core.stats_manager import StatsManager
from app.core.cli_helpers import CLIErrorHandler, CLIProjectPathResolver
from app.core.model_validator import ModelValidator

logger = get_logger(__name__)


class CLIHandler:
    def __init__(self):
        AppConfig.init_directories()
        self.project_manager = ProjectManager(cli_mode=True)
        self.path_resolver = CLIProjectPathResolver(self.project_manager)
        self.search_manager: Optional[SearchManager] = None

    def search(
        self,
        query: str,
        mode: str = "hybrid",
        limit: int = 10,
        language: Optional[str] = None,
        output_format: str = "json",
        full_content: bool = False,
        preview_length: int = 200,
        context: int = 0
    ):
        try:
            search_start = time.time()
            project_path = self.path_resolver.get_path()

            # Initialize search manager (cached)
            if not self.search_manager:
                self.search_manager = SearchManager(project_path)

            # Execute search with validation
            search_result = self.search_manager.execute_search(
                query=query,
                mode=mode,
                limit=limit,
                language=language,
                validate_model=True
            )

            # Process results for CLI output
            results_with_context = process_cli_results(
                results=search_result.results,
                mode=mode,
                project_path=project_path,
                context=context,
                preview_length=preview_length,
                full_content=full_content,
                max_content_length=AppConfig.CLI_MAX_CONTENT_LENGTH
            )

            total_time = (time.time() - search_start) * 1000

            if output_format == "json":
                output_data = {
                    "success": True,
                    "query": query,
                    "mode": mode,
                    "count": len(search_result.results),
                    "performance": {
                        "search_duration_ms": round(search_result.execution_time_ms, 2),
                        "total_duration_ms": round(total_time, 2),
                        "results_count": len(search_result.results),
                        "results_per_second": round(len(search_result.results) / max((time.time() - search_start), 0.001), 2)
                    },
                    "model": ModelValidator.format_model_info_for_json(search_result.validation),
                    "results": results_with_context
                }
                CLIErrorHandler.handle_success(output_data)
            else:
                self._output_text_results(
                    query,
                    search_result.results,
                    search_result.validation.indexed_model,
                    search_result.validation.current_model,
                    search_result.validation.warning_message
                )

        except Exception as e:
            CLIErrorHandler.handle_error("Search", e)

    def index(
        self,
        project_path: Optional[str] = None,
        languages: Optional[List[str]] = None
    ):
        try:
            if project_path is None:
                project_path = self.path_resolver.get_path()
                logger.info(f"Indexing current directory: {project_path}")

            # Prepare indexing using IndexingManager
            indexing_ctx = IndexingManager.prepare_indexing(project_path, languages)

            # Execute indexing
            indexer = CoreIndexer(indexing_ctx.project_path, indexing_ctx.languages)
            result = indexer.index()

            if not result.success:
                raise Exception(result.error)

            # Finalize indexing (update metadata)
            IndexingManager.finalize_indexing(indexing_ctx.project_path, success=True)

            CLIErrorHandler.handle_success({
                "project_path": result.project_path,
                "project_hash": AppConfig.get_project_hash(result.project_path),
                "files_processed": result.total_files,
                "chunks_indexed": result.total_chunks,
                "languages": indexing_ctx.languages,
                "embedding_model": result.embedding_model,
                "database_location": result.database_location
            })

        except Exception as e:
            CLIErrorHandler.handle_error("Indexing", e)

    def stats(self):
        try:
            project_path = self.path_resolver.get_path()

            # Use StatsManager for centralized stats retrieval
            full_stats = StatsManager.get_full_stats(project_path)

            CLIErrorHandler.handle_success({
                "project": full_stats["project"],
                "database": full_stats["database"],
                "version": full_stats["version"]
            })

        except Exception as e:
            CLIErrorHandler.handle_error("Stats", e)

    def _output_text_results(
        self,
        query: str,
        results: List[dict],
        indexed_model: Optional[str] = None,
        current_model: Optional[str] = None,
        mismatch_warning: Optional[str] = None
    ):
        print(f"\nSearch: {query}")

        if indexed_model or current_model:
            model_display = f"Model: {indexed_model or 'unknown'} (indexed)"
            if current_model and indexed_model != current_model:
                model_display += f" | {current_model} (searching)"
            print(model_display)

        if mismatch_warning:
            print(f"\n⚠️  {mismatch_warning}")

        print(f"Results: {len(results)}\n")

        mode = results[0].get('search_mode', 'hybrid') if results else 'hybrid'
        total = len(results)

        for i, result in enumerate(results, 1):
            print(f"{i}. {result.get('file_path')} (Line {result.get('start_line')})")
            print(f"   Language: {result.get('language')}")
            print(f"   Score: {calculate_score(result, mode, i, total):.4f}")
            print(f"   Preview: {result.get('content', '')[:100]}...")
            print()
