import json
import sys
import time
import signal
from pathlib import Path
from typing import Optional, List
from datetime import datetime
from app.indexer.indexer import CoreIndexer
from app.indexer.auto_sync import AutoSyncWorker
from app.utils.config import AppConfig
from app.utils.project_manager import ProjectManager
from app.utils.logger import get_logger
from app.core.indexing_manager import IndexingManager
from app.core.search_manager import SearchManager
from app.core.result_formatter import process_cli_results
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

    def auto_sync(self):
        try:
            project_path = self.path_resolver.get_path()

            # Check if project is indexed
            metadata = AppConfig.load_project_metadata(project_path)
            if not metadata:
                print("Error: Project is not indexed. Please run 'index' command first.")
                sys.exit(1)

            # Get languages from config
            enabled_languages = AppConfig.get_enabled_languages()
            if not enabled_languages:
                enabled_languages = list(AppConfig.SUPPORTED_LANGUAGES.keys())

            print(f"Auto-sync started. Watching for changes... (Ctrl+C to stop)")
            print(f"Project: {project_path}")
            print(f"Languages: {', '.join(enabled_languages)}")
            print()

            # Sync statistics
            sync_stats = {
                'total_files': 0,
                'total_chunks': 0
            }

            # Callback definitions
            def on_sync_complete(chunks_updated: int):
                sync_stats['total_files'] += 1
                sync_stats['total_chunks'] += chunks_updated
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                print(f"[{timestamp}] Synced {sync_stats['total_files']} files, {sync_stats['total_chunks']} chunks updated")

            # Create and start worker
            worker = AutoSyncWorker(
                project_path=project_path,
                enabled_languages=enabled_languages,
                on_sync_complete=on_sync_complete
            )

            # Setup signal handler for graceful shutdown
            def signal_handler(sig, frame):
                print("\n\nStopping auto-sync...")
                worker.stop()
                print(f"Auto-sync stopped. Total: {sync_stats['total_files']} files synced, {sync_stats['total_chunks']} chunks updated")
                sys.exit(0)

            signal.signal(signal.SIGINT, signal_handler)

            # Start worker thread
            worker.start()

            # Keep main thread alive
            while worker.is_alive():
                time.sleep(1)

        except Exception as e:
            CLIErrorHandler.handle_error("Auto-sync", e)
