from typing import List, Optional
from pathlib import Path
from datetime import datetime
import shutil
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


class IndexingResult:
    def __init__(self):
        self.success: bool = False
        self.total_files: int = 0
        self.total_chunks: int = 0
        self.error: Optional[str] = None
        self.embedding_model: str = ""
        self.database_location: str = ""
        self.project_path: str = ""


class CoreIndexer:
    def __init__(self, project_path: str):
        self.project_path = Path(project_path)

    def index(
        self,
        callbacks: Optional[IndexingCallbacks] = None
    ) -> IndexingResult:
        result = IndexingResult()
        callbacks = callbacks or IndexingCallbacks()

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

            # Batch processing configuration
            EMBEDDING_BATCH_SIZE = 100  # Process chunks in batches
            all_chunks = []
            all_chunk_dicts = []

            total_chunks = 0
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

                    # Check file size before reading into memory
                    if size_bytes > AppConfig.MAX_FILE_SIZE:
                        size_mb = size_bytes / (1024 * 1024)
                        callbacks.on_log(f"Skipping {file_path.name} (file too large: {size_mb:.1f}MB)")
                        continue

                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()

                    parse_result = parser.parse_file(str(file_path), content)
                    if not parse_result:
                        callbacks.on_log(f"Skipping {file_path.name} (parse failed)")
                        continue

                    chunks = chunker.chunk_code(
                        content,
                        str(file_path.relative_to(self.project_path)),
                        parse_result['language'],
                        parse_result.get('nodes')
                    )

                    if not chunks:
                        continue

                    file_imports = parse_result.get('imports', [])
                    imports_str = ','.join(file_imports) if file_imports else ''

                    for chunk in chunks:
                        chunk.size_bytes = size_bytes
                        chunk.modified_at = modified_at
                        chunk.imports = imports_str

                    # Accumulate chunks for batch processing
                    all_chunks.extend(chunks)
                    callbacks.on_log(f"Processed {file_path.name}: {len(chunks)} chunks (total buffered: {len(all_chunks)})")

                    # Process batch when we reach EMBEDDING_BATCH_SIZE
                    if len(all_chunks) >= EMBEDDING_BATCH_SIZE:
                        chunk_texts = [chunk.content for chunk in all_chunks]
                        embeddings = embedding_gen.generate_embeddings(chunk_texts)

                        chunk_dicts = [chunk.to_dict() for chunk in all_chunks]
                        is_last_batch = (i == len(files) - 1)
                        vector_db.add_chunks(chunk_dicts, embeddings, update_fts=is_last_batch)

                        total_chunks += len(all_chunks)
                        callbacks.on_log(f"Batch indexed: {len(all_chunks)} chunks")

                        # Clear batch
                        all_chunks = []

                except Exception as e:
                    callbacks.on_log(f"Error indexing {file_path.name}: {str(e)}")
                    logger.warning(f"Failed to index {file_path}: {e}")

            # Process remaining chunks (final batch)
            if all_chunks:
                callbacks.on_log(f"Processing final batch: {len(all_chunks)} chunks")
                chunk_texts = [chunk.content for chunk in all_chunks]
                embeddings = embedding_gen.generate_embeddings(chunk_texts)

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

            callbacks.on_log(f"Indexing complete! Total chunks: {total_chunks}")

            return result

        except Exception as e:
            logger.error(f"Indexing failed: {e}")
            result.error = str(e)
            callbacks.on_log(f"Indexing failed: {str(e)}")
            return result

    def _find_files(self) -> List[Path]:
        """Find all files that can be parsed (auto-detect from Pygments)"""
        files = []
        parser = TreeSitterParser()

        # Get all supported extensions from Pygments
        supported_exts = parser.get_all_supported_extensions()

        for file_path in self.project_path.rglob('*'):
            if not file_path.is_file():
                continue

            if self._should_ignore(file_path):
                continue

            # Check if file extension is supported
            if file_path.suffix.lower() in supported_exts:
                files.append(file_path)

        return files

    def _should_ignore(self, file_path: Path) -> bool:
        path_str = str(file_path)
        for pattern in AppConfig.DEFAULT_IGNORE_PATTERNS:
            if pattern in path_str:
                return True
        return False
