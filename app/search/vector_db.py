import lancedb
from pathlib import Path
from typing import List, Dict, Optional
import numpy as np
import pyarrow as pa
import threading
from app.utils.config import AppConfig


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
            raise

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
                    pa.field("size_bytes", pa.int64()),
                    pa.field("modified_at", pa.string()),
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
                raise

    def _ensure_fts_index(self):
        try:
            self.table.create_fts_index("content", replace=True)
        except Exception:
            pass

    def _refresh_table(self):
        try:
            if AppConfig.DB_TABLE_NAME in self.db.table_names():
                self.table = self.db.open_table(AppConfig.DB_TABLE_NAME)
        except Exception:
            pass

    def _update_fts_index(self):
        try:
            if self.table is not None:
                self.table.create_fts_index("content", replace=True)
        except Exception:
            pass

    def add_chunks(
        self,
        chunks: List[Dict],
        embeddings: np.ndarray
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
                        "size_bytes": chunk.get('size_bytes', 0),
                        "modified_at": chunk.get('modified_at', ''),
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

                self._update_fts_index()

            except Exception as e:
                raise

    def vector_search(
        self,
        query_vector: np.ndarray,
        limit: int = AppConfig.DEFAULT_SEARCH_LIMIT,
        filters: Optional[Dict] = None
    ) -> List[Dict]:
        if self.table is None:
            return []

        try:
            results = self.table.search(query_vector.tolist()).limit(limit)

            if filters:
                for key, value in filters.items():
                    results = results.where(f"{key} = '{value}'")

            results_list = results.to_list()

            return results_list

        except Exception:
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
                    results = results.where(f"{key} = '{value}'")

            results_list = results.to_list()
            return results_list

        except Exception:
            return []

    def delete_by_file(self, file_path: str):
        if self.table is None:
            return

        with self._lock:
            try:
                self.table.delete(f"file_path = '{file_path}'")

                self._refresh_table()

                self._update_fts_index()

            except Exception:
                pass

    def clear_table(self):
        if self.table is None:
            return

        with self._lock:
            try:
                self.db.drop_table(AppConfig.DB_TABLE_NAME)
                self.create_table(embedding_dim=self.embedding_dim)
            except Exception:
                pass

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
        except Exception:
            return {"count": 0}
