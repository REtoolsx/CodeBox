from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QLineEdit, QFileDialog, QProgressBar,
    QTextEdit, QGroupBox, QCheckBox, QGridLayout,
    QMessageBox
)
from PyQt6.QtCore import Qt, pyqtSignal, QThread
from pathlib import Path
from datetime import datetime
from app.gui.dialogs import DialogHelper
from app.indexer.indexer import CoreIndexer, IndexingCallbacks
from app.search.vector_db import VectorDatabase
from app.utils.config import AppConfig


class IndexerThread(QThread):
    progress = pyqtSignal(int, int, str)
    log = pyqtSignal(str)
    finished = pyqtSignal(int)
    error = pyqtSignal(str)

    def __init__(self, project_path: str, enabled_languages: list):
        super().__init__()
        self.project_path = project_path
        self.enabled_languages = enabled_languages
        self._is_cancelled = False

    def run(self):
        try:
            callbacks = IndexingCallbacks()
            callbacks.on_progress = lambda c, t, f: self.progress.emit(c, t, f)
            callbacks.on_log = lambda msg: self.log.emit(msg)
            callbacks.should_cancel = lambda: self._is_cancelled

            indexer = CoreIndexer(self.project_path, self.enabled_languages)
            result = indexer.index(callbacks=callbacks)

            if not result.success:
                self.error.emit(result.error)
                return

            self.finished.emit(result.total_chunks)

        except Exception as e:
            error_msg = f"Indexing failed: {str(e)}"
            self.log.emit(error_msg)
            self.error.emit(error_msg)

    def cancel(self):
        self._is_cancelled = True


class IndexerWidget(QWidget):
    indexing_started = pyqtSignal()
    indexing_finished = pyqtSignal(int)
    indexing_error = pyqtSignal(str)
    indexing_path_changed = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.indexer_thread = None
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout()

        path_group = QGroupBox("Project Path")
        path_layout = QHBoxLayout()

        self.path_input = QLineEdit()
        self.path_input.setPlaceholderText("Select project directory to index...")
        self.path_input.setText("")

        self.browse_btn = QPushButton("Browse...")
        self.browse_btn.clicked.connect(self._browse_folder)

        path_layout.addWidget(self.path_input)
        path_layout.addWidget(self.browse_btn)
        path_group.setLayout(path_layout)
        layout.addWidget(path_group)

        lang_group = QGroupBox("Languages to Index")
        lang_layout = QGridLayout()

        self.lang_checkboxes = {}
        enabled_langs = AppConfig.get_enabled_languages()

        row, col = 0, 0
        for lang in AppConfig.SUPPORTED_LANGUAGES.keys():
            checkbox = QCheckBox(lang.replace('_', ' ').title())
            checkbox.setChecked(lang in enabled_langs)
            self.lang_checkboxes[lang] = checkbox

            lang_layout.addWidget(checkbox, row, col)
            col += 1
            if col >= 4:
                col = 0
                row += 1

        lang_group.setLayout(lang_layout)
        layout.addWidget(lang_group)

        btn_layout = QHBoxLayout()

        self.start_btn = QPushButton("Start Indexing")
        self.start_btn.clicked.connect(self._start_indexing)

        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setEnabled(False)
        self.cancel_btn.clicked.connect(self._cancel_indexing)

        btn_layout.addWidget(self.start_btn)
        btn_layout.addWidget(self.cancel_btn)
        btn_layout.addStretch()

        layout.addLayout(btn_layout)

        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        layout.addWidget(self.progress_bar)

        self.progress_label = QLabel("Ready")
        layout.addWidget(self.progress_label)

        log_group = QGroupBox("Indexing Log")
        log_layout = QVBoxLayout()

        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        self.log_output.setMaximumHeight(250)

        log_layout.addWidget(self.log_output)
        log_group.setLayout(log_layout)
        layout.addWidget(log_group)

        layout.addStretch()
        self.setLayout(layout)

    def _browse_folder(self):
        folder = QFileDialog.getExistingDirectory(
            self,
            "Select Project Directory",
            self.path_input.text() or ""
        )
        if folder:
            self.path_input.setText(folder)

    def _start_indexing(self):
        project_path = self.path_input.text()

        if not project_path or not Path(project_path).exists():
            DialogHelper.show_warning(
                self,
                "Invalid Path",
                "Please select a valid project directory."
            )
            return

        enabled_languages = [
            lang for lang, checkbox in self.lang_checkboxes.items()
            if checkbox.isChecked()
        ]

        if not enabled_languages:
            DialogHelper.show_warning(
                self,
                "No Languages Selected",
                "Please select at least one language to index."
            )
            return

        AppConfig.set_enabled_languages(enabled_languages)

        self.indexing_path_changed.emit(project_path)

        self.log_output.clear()

        self.indexer_thread = IndexerThread(project_path, enabled_languages)
        self.indexer_thread.progress.connect(self._update_progress)
        self.indexer_thread.log.connect(self._append_log)
        self.indexer_thread.finished.connect(self._indexing_finished)
        self.indexer_thread.error.connect(self._indexing_error)

        self.start_btn.setEnabled(False)
        self.cancel_btn.setEnabled(True)
        self.browse_btn.setEnabled(False)

        self.indexer_thread.start()
        self.indexing_started.emit()

    def _cancel_indexing(self):
        if self.indexer_thread:
            self.indexer_thread.cancel()
            self.cancel_btn.setEnabled(False)

    def _update_progress(self, current: int, total: int, message: str):
        self.progress_bar.setMaximum(total)
        self.progress_bar.setValue(current)
        self.progress_label.setText(f"Processing: {message} ({current}/{total})")

    def _append_log(self, message: str):
        self.log_output.append(message)

    def _indexing_finished(self, total_chunks: int):
        self.start_btn.setEnabled(True)
        self.cancel_btn.setEnabled(False)
        self.browse_btn.setEnabled(True)
        self.progress_label.setText(f"Complete: {total_chunks} chunks indexed")
        self.indexing_finished.emit(total_chunks)

    def _indexing_error(self, error: str):
        self.start_btn.setEnabled(True)
        self.cancel_btn.setEnabled(False)
        self.browse_btn.setEnabled(True)
        self.progress_label.setText("Error occurred")
        self.indexing_error.emit(error)
        DialogHelper.show_error(self, "Indexing Error", error)

    def is_indexing(self) -> bool:
        return self.indexer_thread is not None and self.indexer_thread.isRunning()
