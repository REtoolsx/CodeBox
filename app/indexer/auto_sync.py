from pathlib import Path
from typing import Dict, Optional
from datetime import datetime, timedelta
import time
import traceback

from PyQt6.QtCore import QThread, pyqtSignal
from watchdog.observers import Observer
from watchdog.events import PatternMatchingEventHandler, FileSystemEvent

from app.indexer.parser import TreeSitterParser
from app.indexer.chunker import CodeChunker
from app.indexer.embeddings import EmbeddingGenerator
from app.search.vector_db import VectorDatabase
from app.utils.config import AppConfig


class ChangeEvent:
    CREATED = 'created'
    MODIFIED = 'modified'
    DELETED = 'deleted'
    MOVED = 'moved'


class FileChangeHandler(PatternMatchingEventHandler):
    def __init__(self, callback, patterns: list, ignore_patterns: list):
        super().__init__(
            patterns=patterns,
            ignore_patterns=ignore_patterns,
            ignore_directories=True,
            case_sensitive=False
        )
        self.callback = callback

    def on_created(self, event: FileSystemEvent):
        if not event.is_directory:
            self.callback(event.src_path, ChangeEvent.CREATED)

    def on_modified(self, event: FileSystemEvent):
        if not event.is_directory:
            self.callback(event.src_path, ChangeEvent.MODIFIED)

    def on_deleted(self, event: FileSystemEvent):
        if not event.is_directory:
            self.callback(event.src_path, ChangeEvent.DELETED)

    def on_moved(self, event: FileSystemEvent):
        if not event.is_directory:
            self.callback(event.src_path, ChangeEvent.DELETED)
            self.callback(event.dest_path, ChangeEvent.CREATED)


class AutoSyncWorker(QThread):
    file_changed = pyqtSignal(str, str)
    sync_started = pyqtSignal(int)
    sync_complete = pyqtSignal(int)
    sync_error = pyqtSignal(str, str)
    health_status = pyqtSignal(dict)

    def __init__(self, project_path: str, enabled_languages: list):
        super().__init__()
        self.project_path = Path(project_path)
        self.enabled_languages = enabled_languages
        self._is_running = False
        self.observer = None

        self.pending_changes: Dict[str, tuple] = {}
        self.debounce_seconds = AppConfig.AUTO_SYNC_DEBOUNCE_SECONDS
        self.batch_size = AppConfig.AUTO_SYNC_BATCH_SIZE

        self.last_sync_time: Optional[datetime] = None
        self.total_files_synced = 0
        self.total_errors = 0

        self.parser = None
        self.chunker = None
        self.embedding_gen = None
        self.vector_db = None

    def run(self):
        try:
            self._is_running = True

            self.parser = TreeSitterParser()
            self.chunker = CodeChunker()
            self.embedding_gen = EmbeddingGenerator()
            self.vector_db = VectorDatabase()

            patterns = self._get_watch_patterns()
            ignore_patterns = self._get_ignore_patterns()

            event_handler = FileChangeHandler(
                callback=self._on_file_change,
                patterns=patterns,
                ignore_patterns=ignore_patterns
            )

            self.observer = Observer()
            self.observer.schedule(
                event_handler,
                str(self.project_path),
                recursive=True
            )
            self.observer.start()

            while self._is_running:
                time.sleep(0.5)
                self._process_pending_changes()

            if self.observer:
                self.observer.stop()
                self.observer.join(timeout=5.0)

        except Exception as e:
            error_msg = f"Auto-sync failed: {str(e)}"
            self.sync_error.emit("system", error_msg)

    def stop(self):
        self._is_running = False

    def _on_file_change(self, file_path: str, change_type: str):
        try:
            rel_path = str(Path(file_path).relative_to(self.project_path))
        except ValueError:
            return

        if not self._should_process(file_path):
            return

        self.pending_changes[rel_path] = (change_type, datetime.now())
        self.file_changed.emit(rel_path, change_type)

    def _process_pending_changes(self):
        if not self.pending_changes:
            return

        now = datetime.now()
        cutoff = now - timedelta(seconds=self.debounce_seconds)

        ready_files = [
            (file_path, change_type)
            for file_path, (change_type, timestamp) in self.pending_changes.items()
            if timestamp <= cutoff
        ]

        if not ready_files:
            return

        batch = ready_files[:self.batch_size]

        self.sync_started.emit(len(batch))

        total_chunks = 0
        success_count = 0
        error_count = 0

        for file_path, change_type in batch:
            try:
                chunks_updated = self._update_file(file_path, change_type)
                total_chunks += chunks_updated
                success_count += 1

                self.pending_changes.pop(file_path, None)
            except Exception as e:
                error_msg = str(e)
                error_count += 1
                self.sync_error.emit(file_path, error_msg)
                self.pending_changes.pop(file_path, None)

        self.last_sync_time = datetime.now()
        self.total_files_synced += success_count
        self.total_errors += error_count

        self._emit_health_status()

        self.sync_complete.emit(total_chunks)

    def _emit_health_status(self):
        status = {
            'pending_count': len(self.pending_changes),
            'last_sync_time': self.last_sync_time.isoformat() if self.last_sync_time else None,
            'total_files_synced': self.total_files_synced,
            'total_errors': self.total_errors,
            'is_healthy': self.total_errors == 0 or (self.total_files_synced / max(1, self.total_files_synced + self.total_errors)) > 0.9
        }
        self.health_status.emit(status)

    def _update_file(self, rel_path: str, change_type: str) -> int:
        abs_path = self.project_path / rel_path

        if change_type == ChangeEvent.DELETED:
            self.vector_db.delete_by_file(rel_path)
            return 0


        if not abs_path.exists():
            self.vector_db.delete_by_file(rel_path)
            return 0

        file_size = abs_path.stat().st_size
        if file_size > AppConfig.MAX_FILE_SIZE:
            return 0

        try:
            with open(abs_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
        except Exception as e:
            raise Exception(f"Failed to read file: {e}")

        parse_result = self.parser.parse_file(str(abs_path), content)
        if not parse_result:
            raise Exception("Parsing failed")

        chunks = self.chunker.chunk_code(
            content,
            rel_path,
            parse_result['language'],
            parse_result.get('nodes')
        )

        if not chunks:
            self.vector_db.delete_by_file(rel_path)
            return 0

        chunk_texts = [chunk.content for chunk in chunks]
        embeddings = self.embedding_gen.generate_embeddings(chunk_texts)

        chunk_dicts = [chunk.to_dict() for chunk in chunks]

        self.vector_db.delete_by_file(rel_path)
        self.vector_db.add_chunks(chunk_dicts, embeddings)

        return len(chunks)

    def _should_process(self, file_path: str) -> bool:
        path = Path(file_path)

        enabled_exts = set()
        for lang in self.enabled_languages:
            ext_value = AppConfig.SUPPORTED_LANGUAGES.get(lang)
            if isinstance(ext_value, list):
                enabled_exts.update(ext_value)
            else:
                enabled_exts.add(ext_value)

        if path.suffix not in enabled_exts:
            return False

        path_str = str(path)
        for pattern in AppConfig.DEFAULT_IGNORE_PATTERNS:
            if pattern in path_str:
                return False

        return True

    def _get_watch_patterns(self) -> list:
        patterns = []
        for lang in self.enabled_languages:
            ext_value = AppConfig.SUPPORTED_LANGUAGES.get(lang)
            if isinstance(ext_value, list):
                for ext in ext_value:
                    patterns.append(f"*{ext}")
            else:
                patterns.append(f"*{ext_value}")
        return patterns

    def _get_ignore_patterns(self) -> list:
        ignore = []
        for pattern in AppConfig.DEFAULT_IGNORE_PATTERNS:
            if pattern.startswith('*.'):
                ignore.append(pattern)
            else:
                ignore.append(f"*/{pattern}/*")
                ignore.append(f"*{pattern}*")
        return ignore
