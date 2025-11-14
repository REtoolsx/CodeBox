from PyQt6.QtWidgets import (
    QMainWindow, QTabWidget, QStatusBar, QToolBar, QComboBox, QLabel,
    QMenuBar, QMenu, QMessageBox, QApplication
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QAction, QIcon
from app.gui.indexer_widget import IndexerWidget
from app.gui.search_widget import SearchWidget
from app.gui.settings_widget import SettingsWidget
from app.gui.dialogs import DialogHelper
from app.indexer.auto_sync import AutoSyncWorker
from app.utils.config import AppConfig
from app.utils.project_manager import ProjectManager


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"{AppConfig.APP_NAME} v{AppConfig.APP_VERSION}")
        self.setMinimumSize(1200, 800)

        self.project_manager = ProjectManager(cli_mode=False)
        self.auto_sync_worker = None

        self._init_ui()
        self._init_toolbar()
        self._init_menu_bar()
        self._init_status_bar()
        self._load_initial_project()
        self._init_auto_sync()

        self._load_window_state()

    def _init_ui(self):
        self.tabs = QTabWidget()
        self.tabs.setTabPosition(QTabWidget.TabPosition.North)
        self.tabs.setMovable(False)

        self.search_widget = SearchWidget()
        self.indexer_widget = IndexerWidget()
        self.settings_widget = SettingsWidget()

        self.tabs.addTab(self.search_widget, "🔍 Search")
        self.tabs.addTab(self.indexer_widget, "📚 Indexer")
        self.tabs.addTab(self.settings_widget, "⚙️ Settings")

        self.setCentralWidget(self.tabs)

        self._connect_signals()

    def _init_toolbar(self):
        toolbar = QToolBar("Project Toolbar")
        toolbar.setMovable(False)
        self.addToolBar(Qt.ToolBarArea.TopToolBarArea, toolbar)

        toolbar.addWidget(QLabel("  Current Project: "))

        self.project_selector = QComboBox()
        self.project_selector.setMinimumWidth(300)
        self.project_selector.setToolTip("Select active project")
        self.project_selector.currentTextChanged.connect(self._on_project_changed)
        toolbar.addWidget(self.project_selector)

        toolbar.addSeparator()

        refresh_action = QAction("🔄 Refresh", self)
        refresh_action.setToolTip("Refresh project list")
        refresh_action.triggered.connect(self._refresh_project_list)
        toolbar.addAction(refresh_action)

        self._refresh_project_list()

    def _init_menu_bar(self):
        menubar = self.menuBar()

        file_menu = menubar.addMenu("&File")

        exit_action = QAction("E&xit", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        view_menu = menubar.addMenu("&View")

        search_action = QAction("&Search", self)
        search_action.setShortcut("Ctrl+1")
        search_action.triggered.connect(lambda: self.tabs.setCurrentIndex(0))
        view_menu.addAction(search_action)

        indexer_action = QAction("&Indexer", self)
        indexer_action.setShortcut("Ctrl+2")
        indexer_action.triggered.connect(lambda: self.tabs.setCurrentIndex(1))
        view_menu.addAction(indexer_action)

        settings_action = QAction("Se&ttings", self)
        settings_action.setShortcut("Ctrl+3")
        settings_action.triggered.connect(lambda: self.tabs.setCurrentIndex(2))
        view_menu.addAction(settings_action)

        help_menu = menubar.addMenu("&Help")

        about_action = QAction("&About", self)
        about_action.triggered.connect(self._show_about)
        help_menu.addAction(about_action)

    def _init_status_bar(self):
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready")

    def _init_auto_sync(self):
        if AppConfig.get_auto_sync_enabled():
            self._start_auto_sync()

    def _start_auto_sync(self):
        project_path = self.project_manager.get_current_project_path()
        if not project_path:
            return

        enabled_langs = AppConfig.get_enabled_languages()
        self.auto_sync_worker = AutoSyncWorker(project_path, enabled_langs)

        self.auto_sync_worker.file_changed.connect(self._on_file_changed)
        self.auto_sync_worker.sync_started.connect(self._on_sync_started)
        self.auto_sync_worker.sync_complete.connect(self._on_sync_complete)
        self.auto_sync_worker.sync_error.connect(self._on_sync_error)
        self.auto_sync_worker.health_status.connect(self._on_health_status)

        self.auto_sync_worker.start()
        self.status_bar.showMessage("Auto-Sync: Watching...")
        self.settings_widget.autosync_status.setText("Status: Watching")

    def _stop_auto_sync(self):
        if self.auto_sync_worker:
            self.auto_sync_worker.stop()
            self.auto_sync_worker.wait(5000)
            self.auto_sync_worker = None
            self.status_bar.showMessage("Auto-Sync: Stopped")
            self.settings_widget.autosync_status.setText("Status: Idle")

    def _on_file_changed(self, file_path: str, change_type: str):
        self.indexer_widget.log_output.append(
            f"[Auto-Sync] {change_type.title()}: {file_path}"
        )

    def _on_sync_started(self, file_count: int):
        self.status_bar.showMessage(f"Auto-Sync: Processing {file_count} files...")
        self.settings_widget.autosync_status.setText(f"Status: Processing {file_count} files")

    def _on_sync_complete(self, chunks_updated: int):
        self.status_bar.showMessage(
            f"Auto-Sync: Complete ({chunks_updated} chunks updated)"
        )
        QTimer.singleShot(3000, lambda: self.status_bar.showMessage("Auto-Sync: Watching..."))
        QTimer.singleShot(3000, lambda: self.settings_widget.autosync_status.setText("Status: Watching"))

    def _on_sync_error(self, file_path: str, error: str):
        self.indexer_widget.log_output.append(
            f"[Auto-Sync] Error processing {file_path}: {error}"
        )

    def _on_health_status(self, status: dict):
        pending = status.get('pending_count', 0)
        total_synced = status.get('total_files_synced', 0)
        total_errors = status.get('total_errors', 0)
        is_healthy = status.get('is_healthy', True)

        health_indicator = "✓" if is_healthy else "⚠"
        self.settings_widget.autosync_status.setText(
            f"Status: {health_indicator} Watching | "
            f"Synced: {total_synced} | Errors: {total_errors} | Pending: {pending}"
        )

    def _on_autosync_toggled(self, enabled: bool):
        if enabled:
            self._start_auto_sync()
        else:
            self._stop_auto_sync()

    def _on_reindex_requested(self):
        self.tabs.setCurrentIndex(1)

        DialogHelper.show_info(
            self,
            "Starting Re-index",
            "Please select your project directory and click 'Start Indexing' with "
            "'Clear existing index' enabled to re-index with the new embedding model."
        )

    def _on_indexing_started(self):
        self.status_bar.showMessage("Indexing in progress...")
        if self.auto_sync_worker:
            self._stop_auto_sync()

    def _on_indexing_finished(self, count: int):
        self.status_bar.showMessage(f"Indexing complete: {count} chunks indexed")

        self._refresh_project_list()

        if AppConfig.get_auto_sync_enabled():
            QTimer.singleShot(500, self._start_auto_sync)

    def _on_indexing_path_changed(self, project_path: str):
        if AppConfig.get_auto_sync_enabled():
            self._stop_auto_sync()
            self._start_auto_sync()

    def _connect_signals(self):
        self.indexer_widget.indexing_started.connect(self._on_indexing_started)
        self.indexer_widget.indexing_finished.connect(self._on_indexing_finished)
        self.indexer_widget.indexing_error.connect(
            lambda error: self.status_bar.showMessage(f"Error: {error}")
        )
        self.indexer_widget.indexing_path_changed.connect(self._on_indexing_path_changed)

        self.search_widget.search_started.connect(
            lambda: self.status_bar.showMessage("Searching...")
        )
        self.search_widget.search_finished.connect(
            lambda count: self.status_bar.showMessage(
                f"Found {count} results"
            )
        )

        self.settings_widget.autosync_toggled.connect(self._on_autosync_toggled)
        self.settings_widget.reindex_requested.connect(self._on_reindex_requested)

    def _show_about(self):
        QMessageBox.about(
            self,
            f"About {AppConfig.APP_NAME}",
            f"""
            <h2>{AppConfig.APP_NAME}</h2>
            <p>Version {AppConfig.APP_VERSION}</p>
            <p>A powerful code indexing and search tool built with Python and PyQt6.</p>
            <p><b>Features:</b></p>
            <ul>
                <li>Hybrid search (vector + keyword)</li>
                <li>Multi-language support</li>
                <li>AST-based code parsing</li>
                <li>Semantic embeddings</li>
            </ul>
            """
        )

    def _load_window_state(self):
        pass

    def _save_window_state(self):
        pass

    def _load_initial_project(self):
        projects = self.project_manager.list_all_projects()
        if projects:
            first_hash = list(projects.keys())[0]
            first_project = projects[first_hash]["path"]
            self.project_manager.set_current_project(first_project)

    def _refresh_project_list(self):
        self.project_selector.blockSignals(True)
        self.project_selector.clear()

        projects = self.project_manager.list_all_projects()

        if not projects:
            self.project_selector.addItem("(No projects indexed yet)")
            self.project_selector.setEnabled(False)
        else:
            self.project_selector.setEnabled(True)
            current_project = self.project_manager.get_current_project_path()

            for project_hash, project_info in projects.items():
                name = project_info.get("name", "Unknown")
                path = project_info.get("path", "")
                display_text = f"{name} ({path})"

                self.project_selector.addItem(display_text, userData=path)

                if current_project and path == current_project:
                    self.project_selector.setCurrentText(display_text)

        self.project_selector.blockSignals(False)

    def _on_project_changed(self, text: str):
        if not text or text == "(No projects indexed yet)":
            return

        current_index = self.project_selector.currentIndex()
        if current_index < 0:
            return

        project_path = self.project_selector.itemData(current_index)
        if not project_path:
            return

        self.project_manager.set_current_project(project_path)

        if AppConfig.get_auto_sync_enabled():
            self._stop_auto_sync()
            self._start_auto_sync()

        self.status_bar.showMessage(f"Switched to project: {project_path}")

    def closeEvent(self, event):
        self._stop_auto_sync()

        self._save_window_state()

        if self.indexer_widget.is_indexing():
            if not DialogHelper.show_confirm(
                self,
                "Confirm Exit",
                "Indexing is in progress. Are you sure you want to exit?"
            ):
                event.ignore()
                return

        event.accept()
