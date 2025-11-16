import lancedb
from pathlib import Path
from typing import List, Dict, Optional
import numpy as np
import pyarrow as pa
import threading
import logging
import os
from app.utils.config import AppConfig

logger = logging.getLogger(__name__)


class VectorDatabase:
    def __init__(
        self,
        db_path: Optional[Path] = None,
        project_path: Optional[str] = None,
        embedding_dim: int = AppConfig.EMBEDDING_DIM
    ):
        if db_path:
            self.db_path = db_path
        elif project_path:
            self.db_path = AppConfig.get_project_data_dir(project_path)
        else:
            current_project = AppConfig.get_current_working_project()
            self.db_path = AppConfig.get_project_data_dir(current_project)

        self.project_path = project_path
        self.embedding_dim = embedding_dim
        self.db = None
        self.table = None
        self._lock = threading.RLock()
        self._connect()
        self.create_table(embedding_dim=self.embedding_dim)

    def _connect(self):
        try:
            self.db_path.mkdir(exist_ok=True, parents=True)
            self.db = lancedb.connect(str(self.db_path))
        except Exception as e:
            logger.error(f"Failed to connect to database at {self.db_path}: {e}")
            raise RuntimeError(f"Database connection failed: {e}") from e

    def create_table(self, embedding_dim: int = AppConfig.EMBEDDING_DIM):
        with self._lock:
            try:
                schema = pa.schema([
                    pa.field("id", pa.string()),
                    pa.field("content", pa.string()),
                    pa.field("file_path", pa.string()),
                    pa.field("start_line", pa.int32()),
                    pa.field("end_line", pa.int32()),
                    pa.field("language", pa.string()),
                    pa.field("chunk_type", pa.string()),
                    pa.field("node_name", pa.string()),
                    pa.field("signature", pa.string()),
                    pa.field("parameters", pa.string()),
                    pa.field("return_type", pa.string()),
                    pa.field("docstring", pa.string()),
                    pa.field("decorators", pa.string()),
                    pa.field("imports", pa.string()),
                    pa.field("parent_scope", pa.string()),
                    pa.field("full_path", pa.string()),
                    pa.field("scope_depth", pa.int32()),
                    pa.field("calls", pa.string()),
                    pa.field("vector", pa.list_(pa.float32(), embedding_dim))
                ])

                table_names = self.db.table_names()
                if AppConfig.DB_TABLE_NAME in table_names:
                    existing_table = self.db.open_table(AppConfig.DB_TABLE_NAME)
                    existing_schema = existing_table.schema

                    if existing_schema != schema:
                        self.db.drop_table(AppConfig.DB_TABLE_NAME)
                        self.table = self.db.create_table(
                            AppConfig.DB_TABLE_NAME,
                            schema=schema
                        )
                    else:
                        self.table = existing_table

                    self._ensure_fts_index()
                else:
                    self.table = self.db.create_table(
                        AppConfig.DB_TABLE_NAME,
                        schema=schema
                    )

                    self._ensure_fts_index()

            except Exception as e:
                logger.error(f"Failed to create table '{AppConfig.DB_TABLE_NAME}': {e}")
                raise RuntimeError(f"Table creation failed: {e}") from e

    def _ensure_fts_index(self):
        try:
            self.table.create_fts_index("content", replace=True)
            logger.debug("FTS index created/updated successfully")
        except Exception as e:
            logger.warning(f"Failed to create FTS index (keyword search may not work): {e}")

    def _refresh_table(self):
        with self._lock:
            try:
                if AppConfig.DB_TABLE_NAME in self.db.table_names():
                    self.table = self.db.open_table(AppConfig.DB_TABLE_NAME)
                    logger.debug("Table refreshed successfully")
            except Exception as e:
                logger.warning(f"Failed to refresh table: {e}")

    def _update_fts_index(self):
        with self._lock:
            try:
                if self.table is not None:
                    self.table.create_fts_index("content", replace=True)
                    logger.debug("FTS index updated successfully")
            except Exception as e:
                logger.warning(f"Failed to update FTS index: {e}")

    def add_chunks(
        self,
        chunks: List[Dict],
        embeddings: np.ndarray,
        update_fts: bool = True
    ):
        if not chunks or len(embeddings) == 0:
            return

        with self._lock:
            try:
                actual_dim = embeddings.shape[1] if len(embeddings.shape) > 1 else len(embeddings[0])

                if actual_dim != self.embedding_dim:
                    raise ValueError(
                        f"Embedding dimension mismatch: expected {self.embedding_dim}, "
                        f"got {actual_dim}. Check your embedding model configuration."
                    )

                data = []
                for i, chunk in enumerate(chunks):
                    vector_list = embeddings[i].tolist()

                    data.append({
                        "id": f"{chunk['file_path']}:{chunk['start_line']}",
                        "content": chunk['content'],
                        "file_path": chunk['file_path'],
                        "start_line": chunk['start_line'],
                        "end_line": chunk['end_line'],
                        "language": chunk['language'],
                        "chunk_type": chunk['chunk_type'],
                        "node_name": chunk.get('node_name', ''),
                        "signature": chunk.get('signature', ''),
                        "parameters": chunk.get('parameters', ''),
                        "return_type": chunk.get('return_type', ''),
                        "docstring": chunk.get('docstring', ''),
                        "decorators": chunk.get('decorators', ''),
                        "imports": chunk.get('imports', ''),
                        "parent_scope": chunk.get('parent_scope', ''),
                        "full_path": chunk.get('full_path', ''),
                        "scope_depth": chunk.get('scope_depth', 0),
                        "calls": chunk.get('calls', ''),
                        "vector": vector_list
                    })

                pa_data = pa.Table.from_pylist(data)

                if self.table is None:
                    self.table = self.db.create_table(
                        AppConfig.DB_TABLE_NAME,
                        data=pa_data
                    )
                else:
                    self.table.add(pa_data)

                self._refresh_table()

                if update_fts:
                    self._update_fts_index()

            except ValueError as e:
                logger.error(f"Embedding dimension error: {e}")
                raise
            except Exception as e:
                logger.error(f"Failed to add chunks to database: {e}")
                raise RuntimeError(f"Failed to add chunks: {e}") from e

    def vector_search(
        self,
        query_vector: np.ndarray,
        limit: int = AppConfig.DEFAULT_SEARCH_LIMIT,
        filters: Optional[Dict] = None
    ) -> List[Dict]:
        if self.table is None:
            return []

        try:
            results = self.table.search(query_vector.tolist())\
                .metric("cosine")\
                .limit(limit)

            if filters:
                for key, value in filters.items():
                    safe_value = str(value).replace("'", "''")
                    results = results.where(f"{key} = '{safe_value}'")

            results_list = results.to_list()

            return results_list

        except Exception as e:
            logger.error(f"Vector search failed: {e}")
            return []

    def keyword_search(
        self,
        query: str,
        limit: int = AppConfig.DEFAULT_SEARCH_LIMIT,
        filters: Optional[Dict] = None
    ) -> List[Dict]:
        if self.table is None:
            return []

        if not query or not query.strip():
            return []

        try:
            results = self.table.search(query, query_type="fts").limit(limit)

            if filters:
                for key, value in filters.items():
                    safe_value = str(value).replace("'", "''")
                    results = results.where(f"{key} = '{safe_value}'")

            results_list = results.to_list()
            return results_list

        except Exception as e:
            logger.error(f"Keyword search failed: {e}")
            return []

    def delete_by_file(self, file_path: str):
        if self.table is None:
            return

        with self._lock:
            try:
                safe_file_path = file_path.replace("'", "''")
                self.table.delete(f"file_path = '{safe_file_path}'")

                self._refresh_table()

                self._update_fts_index()

            except Exception as e:
                logger.error(f"Failed to delete file '{file_path}': {e}")

    def clear_table(self):
        if self.table is None:
            return

        with self._lock:
            try:
                self.db.drop_table(AppConfig.DB_TABLE_NAME)
                self.create_table(embedding_dim=self.embedding_dim)
                logger.info("Table cleared successfully")
            except Exception as e:
                logger.error(f"Failed to clear table: {e}")

    def get_stats(self) -> Dict:
        if self.table is None:
            return {"count": 0}

        try:
            count = self.table.count_rows()
            return {
                "count": count,
                "table_name": AppConfig.DB_TABLE_NAME,
                "db_path": str(self.db_path)
            }
        except Exception as e:
            logger.error(f"Failed to get stats: {e}")
            return {"count": 0}

    def get_language_breakdown(self) -> Dict[str, int]:
        if self.table is None:
            return {}

        try:
            df = self.table.to_pandas()
            if 'language' not in df.columns:
                return {}

            language_counts = df.groupby('language')['file_path'].nunique().to_dict()
            return language_counts

        except Exception as e:
            logger.error(f"Failed to get language breakdown: {e}")
            return {}

    def get_chunk_type_breakdown(self) -> Dict[str, int]:
        if self.table is None:
            return {}

        try:
            df = self.table.to_pandas()
            if 'chunk_type' not in df.columns:
                return {}

            chunk_type_counts = df['chunk_type'].value_counts().to_dict()
            return chunk_type_counts

        except Exception as e:
            logger.error(f"Failed to get chunk type breakdown: {e}")
            return {}

    def get_database_size_mb(self) -> float:
        try:
            if not self.db_path.exists():
                return 0.0

            total_size = 0
            for dirpath, dirnames, filenames in os.walk(self.db_path):
                for filename in filenames:
                    filepath = os.path.join(dirpath, filename)
                    if os.path.exists(filepath):
                        total_size += os.path.getsize(filepath)

            return round(total_size / (1024 * 1024), 2)

        except Exception as e:
            logger.error(f"Failed to get database size: {e}")
            return 0.0
