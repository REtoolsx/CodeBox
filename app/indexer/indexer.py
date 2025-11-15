from typing import List, Optional, Dict
from pathlib import Path
from datetime import datetime
import shutil
import time
from app.indexer.parser import TreeSitterParser
from app.indexer.chunker import CodeChunker
from app.indexer.embeddings import EmbeddingGenerator
from app.search.vector_db import VectorDatabase
from app.utils.config import AppConfig
from app.utils.logger import get_logger

logger = get_logger(__name__)


class IndexingCallbacks:
    def on_progress(self, current: int, total: int, filename: str):
        pass

    def on_log(self, message: str):
        pass

    def should_cancel(self) -> bool:
        return False

    def on_file_processed(self, filename: str, status: str, chunks: int):
        """Aşama 4: Called when a file is processed (status: 'indexed', 'failed', 'skipped')"""
        pass


class IndexingResult:
    def __init__(self):
        self.success: bool = False
        self.total_files: int = 0
        self.total_chunks: int = 0
        self.error: Optional[str] = None
        self.embedding_model: str = ""
        self.database_location: str = ""
        self.project_path: str = ""

        # Aşama 1: Index Stats
        self.indexed_files_count: int = 0
        self.failed_files_count: int = 0
        self.skipped_files_count: int = 0
        self.processing_time_ms: float = 0.0
        self.embedding_time_ms: float = 0.0
        self.language_breakdown: Dict[str, int] = {}

        # Aşama 2: Error Tracking
        self.failed_files: List[Dict[str, str]] = []  # [{file, error_type, message}]
        self.skipped_files: List[str] = []
        self.indexed_files: List[str] = []


class CoreIndexer:
    def __init__(self, project_path: str):
        self.project_path = Path(project_path)

    def index(
        self,
        callbacks: Optional[IndexingCallbacks] = None
    ) -> IndexingResult:
        result = IndexingResult()
        callbacks = callbacks or IndexingCallbacks()

        # Aşama 1: Processing time tracking
        processing_start = time.time()

        try:
            if not self.project_path.exists():
                result.error = f"Path does not exist: {self.project_path}"
                return result

            result.project_path = str(self.project_path)

            callbacks.on_log("Initializing indexer...")

            project_dir = AppConfig.get_project_dir(str(self.project_path))
            if project_dir.exists():
                callbacks.on_log("Clearing existing project data...")
                shutil.rmtree(project_dir)
                callbacks.on_log("Previous project data cleared completely")

            parser = TreeSitterParser()
            chunker = CodeChunker()
            embedding_gen = EmbeddingGenerator()
            embedding_dim = embedding_gen.get_embedding_dim()
            vector_db = VectorDatabase(
                project_path=str(self.project_path),
                embedding_dim=embedding_dim
            )

            callbacks.on_log(f"Scanning directory: {self.project_path}")
            files = self._find_files()
            result.total_files = len(files)
            callbacks.on_log(f"Found {len(files)} files to index")

            if not files:
                callbacks.on_log("No files found to index")
                result.success = True
                return result

            # Aşama 3: Memory Opt - Batch size from config
            EMBEDDING_BATCH_SIZE = AppConfig.EMBEDDING_BATCH_SIZE or 100
            all_chunks = []

            total_chunks = 0
            total_embedding_time = 0.0

            for i, file_path in enumerate(files):
                if callbacks.should_cancel():
                    callbacks.on_log("Indexing cancelled by user")
                    result.error = "Cancelled by user"
                    return result

                callbacks.on_progress(i + 1, len(files), file_path.name)

                try:
                    file_stat = file_path.stat()
                    size_bytes = file_stat.st_size
                    modified_at = datetime.fromtimestamp(file_stat.st_mtime).isoformat()

                    # Aşama 2: Error Tracking - Size check
                    if size_bytes > AppConfig.MAX_FILE_SIZE:
                        size_mb = size_bytes / (1024 * 1024)
                        result.skipped_files.append(str(file_path.relative_to(self.project_path)))
                        result.skipped_files_count += 1
                        callbacks.on_log(f"Skipping {file_path.name} (file too large: {size_mb:.1f}MB)")
                        callbacks.on_file_processed(file_path.name, "skipped", 0)  # Aşama 4
                        continue

                    # Aşama 2: Error Tracking - Encoding error
                    try:
                        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                            content = f.read()
                    except Exception as e:
                        result.failed_files.append({
                            'file': str(file_path.relative_to(self.project_path)),
                            'error_type': 'encoding_error',
                            'message': str(e)
                        })
                        result.failed_files_count += 1
                        callbacks.on_log(f"Failed {file_path.name} (encoding error): {str(e)}")
                        callbacks.on_file_processed(file_path.name, "failed", 0)  # Aşama 4
                        continue

                    # Aşama 2: Error Tracking - Parse error
                    parse_result = parser.parse_file(str(file_path), content)
                    if not parse_result:
                        result.failed_files.append({
                            'file': str(file_path.relative_to(self.project_path)),
                            'error_type': 'parse_error',
                            'message': 'Failed to parse file'
                        })
                        result.failed_files_count += 1
                        callbacks.on_log(f"Failed {file_path.name} (parse failed)")
                        callbacks.on_file_processed(file_path.name, "failed", 0)  # Aşama 4
                        continue

                    chunks = chunker.chunk_code(
                        content,
                        str(file_path.relative_to(self.project_path)),
                        parse_result['language'],
                        parse_result.get('nodes')
                    )

                    if not chunks:
                        result.skipped_files.append(str(file_path.relative_to(self.project_path)))
                        result.skipped_files_count += 1
                        callbacks.on_file_processed(file_path.name, "skipped", 0)  # Aşama 4
                        continue

                    file_imports = parse_result.get('imports', [])
                    imports_str = ','.join(file_imports) if file_imports else ''

                    for chunk in chunks:
                        chunk.size_bytes = size_bytes
                        chunk.modified_at = modified_at
                        chunk.imports = imports_str

                    all_chunks.extend(chunks)

                    # Aşama 1: Language breakdown tracking
                    language = parse_result['language']
                    result.language_breakdown[language] = result.language_breakdown.get(language, 0) + 1

                    # Aşama 2: Track indexed file
                    result.indexed_files.append(str(file_path.relative_to(self.project_path)))
                    result.indexed_files_count += 1

                    callbacks.on_log(f"Processed {file_path.name}: {len(chunks)} chunks (total buffered: {len(all_chunks)})")
                    callbacks.on_file_processed(file_path.name, "indexed", len(chunks))  # Aşama 4

                    if len(all_chunks) >= EMBEDDING_BATCH_SIZE:
                        chunk_texts = [chunk.content for chunk in all_chunks]

                        # Aşama 1: Embedding time tracking
                        embed_start = time.time()
                        embeddings = embedding_gen.generate_embeddings(chunk_texts)
                        total_embedding_time += (time.time() - embed_start)

                        chunk_dicts = [chunk.to_dict() for chunk in all_chunks]
                        is_last_batch = (i == len(files) - 1)
                        vector_db.add_chunks(chunk_dicts, embeddings, update_fts=is_last_batch)

                        total_chunks += len(all_chunks)
                        callbacks.on_log(f"Batch indexed: {len(all_chunks)} chunks")

                        all_chunks = []

                except PermissionError as e:
                    # Aşama 2: Permission error tracking
                    result.failed_files.append({
                        'file': str(file_path.relative_to(self.project_path)),
                        'error_type': 'permission_error',
                        'message': str(e)
                    })
                    result.failed_files_count += 1
                    callbacks.on_log(f"Failed {file_path.name} (permission denied): {str(e)}")
                    callbacks.on_file_processed(file_path.name, "failed", 0)  # Aşama 4

                except Exception as e:
                    # Aşama 2: Unknown error tracking
                    result.failed_files.append({
                        'file': str(file_path.relative_to(self.project_path)),
                        'error_type': 'unknown',
                        'message': str(e)
                    })
                    result.failed_files_count += 1
                    callbacks.on_log(f"Failed {file_path.name} (error): {str(e)}")
                    callbacks.on_file_processed(file_path.name, "failed", 0)  # Aşama 4
                    logger.warning(f"Failed to index {file_path}: {e}")

            if all_chunks:
                callbacks.on_log(f"Processing final batch: {len(all_chunks)} chunks")
                chunk_texts = [chunk.content for chunk in all_chunks]

                # Aşama 1: Embedding time tracking for final batch
                embed_start = time.time()
                embeddings = embedding_gen.generate_embeddings(chunk_texts)
                total_embedding_time += (time.time() - embed_start)

                chunk_dicts = [chunk.to_dict() for chunk in all_chunks]
                vector_db.add_chunks(chunk_dicts, embeddings, update_fts=True)

                total_chunks += len(all_chunks)
                callbacks.on_log(f"Final batch indexed: {len(all_chunks)} chunks")

            model_info = AppConfig.get_embedding_model_info(embedding_gen.model_name)
            metadata = AppConfig.load_project_metadata(str(self.project_path))
            metadata["embedding_model"] = embedding_gen.model_name
            metadata["embedding_dim"] = model_info.get("dim") if model_info else None
            AppConfig.save_project_metadata(str(self.project_path), metadata)

            result.success = True
            result.total_chunks = total_chunks
            result.embedding_model = embedding_gen.model_name
            result.database_location = str(vector_db.db_path)

            # Aşama 1: Finalize stats
            result.processing_time_ms = (time.time() - processing_start) * 1000
            result.embedding_time_ms = total_embedding_time * 1000

            callbacks.on_log(f"Indexing complete! Total chunks: {total_chunks}")
            callbacks.on_log(f"Stats: {result.indexed_files_count} indexed, {result.failed_files_count} failed, {result.skipped_files_count} skipped")

            return result

        except Exception as e:
            logger.error(f"Indexing failed: {e}")
            result.error = str(e)
            callbacks.on_log(f"Indexing failed: {str(e)}")
            return result

    def _find_files(self) -> List[Path]:
        files = []
        parser = TreeSitterParser()

        supported_exts = parser.get_all_supported_extensions()

        for file_path in self.project_path.rglob('*'):
            if not file_path.is_file():
                continue

            if self._should_ignore(file_path):
                continue

            if file_path.suffix.lower() in supported_exts:
                files.append(file_path)

        return files

    def _should_ignore(self, file_path: Path) -> bool:
        path_str = str(file_path)
        for pattern in AppConfig.DEFAULT_IGNORE_PATTERNS:
            if pattern in path_str:
                return True
        return False
