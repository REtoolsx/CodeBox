import json
import sys
import time
import signal
from pathlib import Path
from typing import Optional, List
from datetime import datetime
from app.indexer.indexer import CoreIndexer, IndexingCallbacks
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
        full_content: bool = False,
        context: int = 0,
        profile: Optional[str] = None,
        output: str = "compact"
    ):
        try:
            search_start = time.time()
            project_path = self.path_resolver.get_path()

            if profile:
                AppConfig.apply_profile(profile, project_path)

            if not self.search_manager:
                self.search_manager = SearchManager(project_path)

            search_result = self.search_manager.execute_search(
                query=query,
                mode=mode,
                limit=limit,
                validate_model=True
            )

            preview_length = 800
            preview_lines = 20

            if output == "compact":
                preview_length = 150
                preview_lines = 3
                full_content = False
            elif output == "standard":
                preview_length = 800
                preview_lines = 15
                full_content = False
            elif output == "verbose":
                full_content = True

            results_with_context = process_cli_results(
                results=search_result.results,
                mode=mode,
                project_path=project_path,
                context=context,
                preview_length=preview_length,
                preview_lines=preview_lines,
                full_content=full_content,
                max_content_length=AppConfig.CLI_MAX_CONTENT_LENGTH,
                output_format=output
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
        profile: Optional[str] = None
    ):
        try:
            if project_path is None:
                project_path = self.path_resolver.get_path()
                logger.info(f"Indexing current directory: {project_path}")

            active_profile = profile if profile else "auto"
            AppConfig.ensure_config_loaded(project_path, active_profile)

            logger.info(f"Using profile: {active_profile}")

            indexing_ctx = IndexingManager.prepare_indexing(project_path)

            class ProgressBarCallbacks(IndexingCallbacks):
                def __init__(self):
                    self.indexed_count = 0
                    self.failed_count = 0
                    self.skipped_count = 0

                def on_progress(self, current: int, total: int, filename: str):
                    pass

                def on_file_processed(self, filename: str, status: str, chunks: int):
                    if status == "indexed":
                        self.indexed_count += 1
                    elif status == "failed":
                        self.failed_count += 1
                    elif status == "skipped":
                        self.skipped_count += 1

                def on_log(self, message: str):
                    pass

            callbacks = ProgressBarCallbacks()
            indexer = CoreIndexer(indexing_ctx.project_path)
            result = indexer.index(callbacks=callbacks)

            if not result.success:
                raise Exception(result.error)

            IndexingManager.finalize_indexing(indexing_ctx.project_path, success=True)

            CLIErrorHandler.handle_success({
                "project_path": result.project_path,
                "project_hash": AppConfig.get_project_hash(result.project_path),
                "files_processed": result.total_files,
                "chunks_indexed": result.total_chunks,
                "embedding_model": result.embedding_model,
                "database_location": result.database_location,
                "indexed_files": result.indexed_files_count,
                "failed_files": result.failed_files_count,
                "skipped_files": result.skipped_files_count,
                "processing_time_ms": round(result.processing_time_ms, 2),
                "embedding_time_ms": round(result.embedding_time_ms, 2),
                "language_breakdown": result.language_breakdown,
                "failed_files_details": result.failed_files if result.failed_files_count > 0 else None
            })

        except Exception as e:
            CLIErrorHandler.handle_error("Indexing", e)

    def stats(self):
        try:
            project_path = self.path_resolver.get_path()

            full_stats = StatsManager.get_full_stats(project_path)

            CLIErrorHandler.handle_success({
                "project": full_stats["project"],
                "database": full_stats["database"]
            })

        except Exception as e:
            CLIErrorHandler.handle_error("Stats", e)

    def auto_sync(self):
        try:
            project_path = self.path_resolver.get_path()

            metadata = AppConfig.load_project_metadata(project_path)
            if not metadata:
                print("Error: Project is not indexed. Please run 'index' command first.")
                sys.exit(1)

            print(f"Auto-sync started. Watching for changes... (Ctrl+C to stop)")
            print(f"Project: {project_path}")
            print(f"Auto-detecting all supported languages")
            print()

            def on_sync_complete(batch_files: List[str], chunks_updated: int):
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                if len(batch_files) == 1:
                    print(f"[{timestamp}] Synced {batch_files[0]}, {chunks_updated} chunks updated")
                else:
                    print(f"[{timestamp}] Synced {len(batch_files)} files, {chunks_updated} chunks updated")

            worker = AutoSyncWorker(
                project_path=project_path,
                on_sync_complete=on_sync_complete
            )

            def signal_handler(sig, frame):
                print("\n\nStopping auto-sync...")
                worker.stop()
                print("Auto-sync stopped.")
                sys.exit(0)

            signal.signal(signal.SIGINT, signal_handler)

            worker.start()

            while worker.is_alive():
                time.sleep(1)

        except Exception as e:
            CLIErrorHandler.handle_error("Auto-sync", e)
