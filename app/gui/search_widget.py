from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLineEdit, QLabel, QSplitter, QTreeWidget,
    QTreeWidgetItem, QComboBox, QGroupBox, QMessageBox
)
from PyQt6.QtCore import Qt, pyqtSignal, QThread
from app.gui.dialogs import DialogHelper
from app.gui.code_viewer import CodeViewer
from app.search.vector_db import VectorDatabase
from app.search.hybrid import HybridSearch
from app.indexer.embeddings import EmbeddingGenerator


class SearchThread(QThread):
    finished = pyqtSignal(list)
    error = pyqtSignal(str)

    def __init__(self, query: str, mode: str, limit: int):
        super().__init__()
        self.query = query
        self.mode = mode
        self.limit = limit

    def run(self):
        try:
            vector_db = VectorDatabase()
            embedding_gen = EmbeddingGenerator()
            hybrid_search = HybridSearch(vector_db, embedding_gen)

            results = hybrid_search.search(
                self.query,
                mode=self.mode,
                limit=self.limit
            )

            self.finished.emit(results)

        except Exception as e:
            self.error.emit(f"Search failed: {str(e)}")


class SearchWidget(QWidget):
    search_started = pyqtSignal()
    search_finished = pyqtSignal(int)

    def __init__(self):
        super().__init__()
        self.search_thread = None
        self.current_results = []
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout()

        search_group = QGroupBox("Search Query")
        search_layout = QVBoxLayout()

        search_bar_layout = QHBoxLayout()

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Enter search query...")
        self.search_input.returnPressed.connect(self._perform_search)

        self.search_btn = QPushButton("Search")
        self.search_btn.clicked.connect(self._perform_search)

        search_bar_layout.addWidget(self.search_input)
        search_bar_layout.addWidget(self.search_btn)

        search_layout.addLayout(search_bar_layout)

        options_layout = QHBoxLayout()

        mode_label = QLabel("Mode:")
        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["Hybrid", "Vector", "Keyword"])
        self.mode_combo.setCurrentText("Hybrid")

        limit_label = QLabel("Max Results:")
        self.limit_combo = QComboBox()
        self.limit_combo.addItems(["10", "25", "50", "100"])
        self.limit_combo.setCurrentText("50")

        options_layout.addWidget(mode_label)
        options_layout.addWidget(self.mode_combo)
        options_layout.addSpacing(20)
        options_layout.addWidget(limit_label)
        options_layout.addWidget(self.limit_combo)
        options_layout.addStretch()

        search_layout.addLayout(options_layout)
        search_group.setLayout(search_layout)
        layout.addWidget(search_group)

        splitter = QSplitter(Qt.Orientation.Horizontal)

        results_widget = QWidget()
        results_layout = QVBoxLayout()
        results_layout.setContentsMargins(0, 0, 0, 0)

        self.results_label = QLabel("Results: 0")
        results_layout.addWidget(self.results_label)

        self.results_tree = QTreeWidget()
        self.results_tree.setHeaderLabels(["File", "Line", "Type", "Score"])
        self.results_tree.setColumnWidth(0, 300)
        self.results_tree.itemClicked.connect(self._on_result_selected)
        results_layout.addWidget(self.results_tree)

        results_widget.setLayout(results_layout)
        splitter.addWidget(results_widget)

        self.code_viewer = CodeViewer()
        splitter.addWidget(self.code_viewer)

        splitter.setSizes([400, 600])

        layout.addWidget(splitter)

        self.setLayout(layout)

    def _perform_search(self):
        query = self.search_input.text().strip()

        if not query:
            DialogHelper.show_warning(
                self,
                "Empty Query",
                "Please enter a search query."
            )
            return

        mode = self.mode_combo.currentText().lower()
        limit = int(self.limit_combo.currentText())

        self.search_btn.setEnabled(False)
        self.search_input.setEnabled(False)

        self.results_tree.clear()
        self.code_viewer.clear()

        self.search_thread = SearchThread(query, mode, limit)
        self.search_thread.finished.connect(self._display_results)
        self.search_thread.error.connect(self._search_error)
        self.search_thread.start()

        self.search_started.emit()

    def _display_results(self, results: list):
        self.current_results = results

        self.search_btn.setEnabled(True)
        self.search_input.setEnabled(True)

        self.results_label.setText(f"Results: {len(results)}")

        files_dict = {}
        for result in results:
            file_path = result.get('file_path', 'Unknown')
            if file_path not in files_dict:
                files_dict[file_path] = []
            files_dict[file_path].append(result)

        for file_path, file_results in files_dict.items():
            file_item = QTreeWidgetItem(self.results_tree)
            file_item.setText(0, file_path)
            file_item.setText(1, f"{len(file_results)} chunks")

            for result in file_results:
                chunk_item = QTreeWidgetItem(file_item)
                chunk_item.setText(
                    0,
                    f"  {result.get('content', '')[:50]}..."
                )
                chunk_item.setText(
                    1,
                    f"{result.get('start_line', 0)}-{result.get('end_line', 0)}"
                )
                chunk_item.setText(2, result.get('chunk_type', 'code'))

                score = result.get('rrf_score', result.get('_distance', 0))
                chunk_item.setText(3, f"{score:.4f}")

                chunk_item.setData(0, Qt.ItemDataRole.UserRole, result)

            file_item.setExpanded(True)

        self.search_finished.emit(len(results))

    def _search_error(self, error: str):
        self.search_btn.setEnabled(True)
        self.search_input.setEnabled(True)
        DialogHelper.show_error(self, "Search Error", error)

    def _on_result_selected(self, item: QTreeWidgetItem, column: int):
        result = item.data(0, Qt.ItemDataRole.UserRole)

        if result:
            content = result.get('content', '')
            language = result.get('language', 'text')
            file_path = result.get('file_path', '')
            start_line = result.get('start_line', 0)

            self.code_viewer.display_code(
                content,
                language,
                f"{file_path} (Line {start_line})"
            )
