from typing import List, Optional, Tuple, Dict, Any
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass

from app.indexer.parser import TreeSitterParser
from app.indexer.chunker import CodeChunker
from app.indexer.embeddings import EmbeddingGenerator
from app.search.vector_db import VectorDatabase
from app.utils.config import AppConfig
from app.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class ProcessedFileResult:
    file_path: str
    chunks_count: int
    success: bool
    error: Optional[str] = None


class FileProcessor:
    def __init__(
        self,
        parser: TreeSitterParser,
        chunker: CodeChunker,
        embedding_gen: EmbeddingGenerator,
        vector_db: VectorDatabase
    ):
        self.parser = parser
        self.chunker = chunker
        self.embedding_gen = embedding_gen
        self.vector_db = vector_db

    def process_file(
        self,
        file_path: Path,
        relative_path: str,
        include_file_stats: bool = True,
        delete_existing: bool = False
    ) -> ProcessedFileResult:
        try:
            file_stat = file_path.stat() if include_file_stats else None
            size_bytes = file_stat.st_size if file_stat else None
            modified_at = datetime.fromtimestamp(file_stat.st_mtime).isoformat() if file_stat else None

            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()

            if len(content) > AppConfig.MAX_FILE_SIZE:
                return ProcessedFileResult(
                    file_path=str(file_path),
                    chunks_count=0,
                    success=False,
                    error="File too large"
                )

            parse_result = self.parser.parse_file(str(file_path), content)
            if not parse_result:
                return ProcessedFileResult(
                    file_path=str(file_path),
                    chunks_count=0,
                    success=False,
                    error="Parse failed"
                )

            chunks = self.chunker.chunk_code(
                content,
                relative_path,
                parse_result['language'],
                parse_result.get('nodes')
            )

            if not chunks:
                if delete_existing:
                    self.vector_db.delete_by_file(relative_path)
                return ProcessedFileResult(
                    file_path=str(file_path),
                    chunks_count=0,
                    success=True,
                    error=None
                )

            if include_file_stats and file_stat:
                for chunk in chunks:
                    chunk.size_bytes = size_bytes
                    chunk.modified_at = modified_at

            chunk_texts = [chunk.content for chunk in chunks]
            embeddings = self.embedding_gen.generate_embeddings(chunk_texts)

            chunk_dicts = [chunk.to_dict() for chunk in chunks]

            if delete_existing:
                self.vector_db.delete_by_file(relative_path)

            self.vector_db.add_chunks(chunk_dicts, embeddings)

            return ProcessedFileResult(
                file_path=str(file_path),
                chunks_count=len(chunks),
                success=True,
                error=None
            )

        except Exception as e:
            logger.warning(f"Failed to process {file_path}: {e}")
            return ProcessedFileResult(
                file_path=str(file_path),
                chunks_count=0,
                success=False,
                error=str(e)
            )

    def process_batch(
        self,
        files: List[Path],
        project_path: Path,
        callback_fn=None,
        include_file_stats: bool = True
    ) -> Tuple[int, int]:
        total_chunks = 0
        processed_count = 0

        for idx, file_path in enumerate(files, 1):
            if callback_fn:
                callback_fn(idx, len(files), file_path.name)

            relative_path = str(file_path.relative_to(project_path))
            result = self.process_file(
                file_path,
                relative_path,
                include_file_stats=include_file_stats,
                delete_existing=False
            )

            if result.success:
                total_chunks += result.chunks_count
                processed_count += 1
            elif result.error:
                if callback_fn:
                    callback_fn(idx, len(files), f"Error: {file_path.name} - {result.error}")

        return processed_count, total_chunks
