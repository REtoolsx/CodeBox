import json
import sys
import time
from pathlib import Path
from typing import Optional, List
from datetime import datetime
from app.indexer.parser import TreeSitterParser
from app.indexer.chunker import CodeChunker
from app.indexer.embeddings import EmbeddingGenerator
from app.indexer.indexer import CoreIndexer
from app.search.vector_db import VectorDatabase
from app.search.hybrid import HybridSearch
from app.utils.config import AppConfig
from app.utils.project_manager import ProjectManager
from app.utils.logger import get_logger

logger = get_logger(__name__)


class CLIHandler:
    def __init__(self):
        AppConfig.init_directories()
        self.project_manager = ProjectManager(cli_mode=True)
        self.vector_db = None
        self.hybrid_search = None

    def _init_search(self, project_path: Optional[str] = None):
        if project_path is None:
            project_path = self.project_manager.get_current_project_path()

        if not self.vector_db:
            self.vector_db = VectorDatabase(project_path=project_path)
            embedding_gen = EmbeddingGenerator()
            self.hybrid_search = HybridSearch(self.vector_db, embedding_gen)

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
            self._init_search()

            project_path = self.project_manager.get_current_project_path()
            metadata = AppConfig.load_project_metadata(project_path)
            indexed_model = metadata.get("embedding_model")
            current_model = AppConfig.get_embedding_model()

            model_mismatch = indexed_model and indexed_model != current_model
            mismatch_warning = None
            if model_mismatch:
                mismatch_warning = f"Warning: Index was created with '{indexed_model}' but searching with '{current_model}'. Results may be suboptimal."
                logger.warning(mismatch_warning)

            filters = {}
            if language:
                filters['language'] = language

            search_exec_start = time.time()
            results = self.hybrid_search.search(
                query=query,
                mode=mode,
                limit=limit,
                filters=filters
            )
            search_exec_time = (time.time() - search_exec_start) * 1000

            if output_format == "json":
                results_with_context = []
                for idx, r in enumerate(results):
                    result_dict = {
                        "file_path": r.get("file_path"),
                        "start_line": r.get("start_line"),
                        "end_line": r.get("end_line"),
                        "language": r.get("language"),
                        "chunk_type": r.get("chunk_type"),
                        "node_name": r.get("node_name", ""),
                        "size_bytes": r.get("size_bytes", 0),
                        "modified_at": r.get("modified_at", ""),
                        "content": r.get("content", "")[:AppConfig.CLI_MAX_CONTENT_LENGTH] if full_content
                                  else r.get("content", "")[:preview_length],
                        "content_preview": r.get("content", "")[:preview_length],
                        "content_length": len(r.get("content", "")),
                        "is_truncated": len(r.get("content", "")) > (AppConfig.CLI_MAX_CONTENT_LENGTH if full_content else preview_length),
                        "score": self._get_score(r, mode, idx + 1, len(results))
                    }

                    if context > 0:
                        lines_before, lines_after = self._get_context_lines(
                            r.get("file_path"),
                            r.get("start_line"),
                            r.get("end_line"),
                            context,
                            project_path
                        )
                        result_dict["context"] = {
                            "lines_before": lines_before,
                            "lines_after": lines_after,
                            "range_before": f"{max(0, r.get('start_line') - context)}-{r.get('start_line') - 1}",
                            "range_after": f"{r.get('end_line') + 1}-{r.get('end_line') + context}"
                        }

                    results_with_context.append(result_dict)

                total_time = (time.time() - search_start) * 1000
                output_data = {
                    "success": True,
                    "query": query,
                    "mode": mode,
                    "count": len(results),
                    "performance": {
                        "search_duration_ms": round(search_exec_time, 2),
                        "total_duration_ms": round(total_time, 2),
                        "results_count": len(results),
                        "results_per_second": round(len(results) / max((time.time() - search_start), 0.001), 2)
                    },
                    "model": {
                        "indexed_with": indexed_model or "unknown",
                        "searching_with": current_model
                    },
                    "results": results_with_context
                }
                if mismatch_warning:
                    output_data["model"]["mismatch_warning"] = mismatch_warning
                self._output_json(output_data)
            else:
                self._output_text_results(query, results, indexed_model, current_model, mismatch_warning)

        except Exception as e:
            logger.error(f"Search failed: {e}")
            self._output_json({
                "success": False,
                "error": str(e)
            })
            sys.exit(1)

    def index(
        self,
        project_path: Optional[str] = None,
        languages: Optional[List[str]] = None
    ):
        try:
            if project_path is None:
                project_path = self.project_manager.get_current_project_path()
                logger.info(f"Indexing current directory: {project_path}")

            project_path_obj = Path(project_path)
            if not project_path_obj.exists():
                raise ValueError(f"Path does not exist: {project_path}")

            self.project_manager.ensure_project_directories(str(project_path_obj))

            if not languages:
                languages = list(AppConfig.SUPPORTED_LANGUAGES.keys())

            indexer = CoreIndexer(str(project_path_obj), languages)
            result = indexer.index()

            if not result.success:
                raise Exception(result.error)

            self.project_manager.update_project_index_time(str(project_path_obj))

            self._output_json({
                "success": True,
                "project_path": result.project_path,
                "project_hash": AppConfig.get_project_hash(result.project_path),
                "files_processed": result.total_files,
                "chunks_indexed": result.total_chunks,
                "languages": languages,
                "embedding_model": result.embedding_model,
                "database_location": result.database_location
            })

        except Exception as e:
            logger.error(f"Indexing failed: {e}")
            self._output_json({
                "success": False,
                "error": str(e)
            })
            sys.exit(1)

    def stats(self):
        try:
            project_path = self.project_manager.get_current_project_path()

            vector_db = VectorDatabase(project_path=project_path)
            stats = vector_db.get_stats()

            project_stats = self.project_manager.get_project_stats(project_path)

            metadata = AppConfig.load_project_metadata(project_path)
            schema_version = metadata.get("schema_version", "1.0")

            self._output_json({
                "success": True,
                "project": {
                    "path": project_path,
                    "name": project_stats.get("name"),
                    "hash": AppConfig.get_project_hash(project_path),
                    "indexed_at": project_stats.get("indexed_at")
                },
                "database": {
                    "path": stats.get("db_path"),
                    "table": stats.get("table_name"),
                    "total_chunks": stats.get("count", 0)
                },
                "version": {
                    "app_version": AppConfig.APP_VERSION,
                    "schema_version": schema_version,
                    "current_schema": AppConfig.SCHEMA_VERSION
                }
            })

        except Exception as e:
            logger.error(f"Failed to get stats: {e}")
            self._output_json({
                "success": False,
                "error": str(e)
            })
            sys.exit(1)

    def _output_json(self, data: dict):
        print(json.dumps(data, indent=2, ensure_ascii=False))

    def _get_score(self, result: dict, mode: str, rank: int = 1, total: int = 1) -> float:
        if mode == "hybrid":
            return result.get('rrf_score', 0.0)
        elif mode == "vector":
            distance = result.get('_distance', 1.0)
            return 1.0 / (1.0 + distance)
        elif mode == "keyword":
            return (total - rank + 1) / max(total, 1)
        else:
            return 0.0

    def _get_context_lines(
        self,
        file_path: str,
        start_line: int,
        end_line: int,
        context: int,
        project_path: str
    ) -> tuple:
        try:
            full_path = Path(project_path) / file_path
            if not full_path.exists():
                return ([], [])

            with open(full_path, 'r', encoding='utf-8', errors='ignore') as f:
                all_lines = f.readlines()

            context_start = max(0, start_line - context)
            lines_before = all_lines[context_start:start_line]

            context_end = min(len(all_lines), end_line + 1 + context)
            lines_after = all_lines[end_line + 1:context_end]

            return (
                [line.rstrip() for line in lines_before],
                [line.rstrip() for line in lines_after]
            )
        except Exception:
            return ([], [])

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
            print(f"   Score: {self._get_score(result, mode, i, total):.4f}")
            print(f"   Preview: {result.get('content', '')[:100]}...")
            print()
