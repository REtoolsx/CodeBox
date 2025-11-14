from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QGroupBox, QSpinBox, QLineEdit, QPushButton,
    QComboBox, QFormLayout, QMessageBox, QTextEdit, QCheckBox
)
from PyQt6.QtCore import Qt, pyqtSignal
from app.gui.dialogs import DialogHelper
from app.utils.config import AppConfig
from app.core.stats_manager import StatsManager
from app.core.model_validator import ModelValidator


class SettingsWidget(QWidget):
    autosync_toggled = pyqtSignal(bool)
    reindex_requested = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.current_model = None
        self._init_ui()
        self._load_settings()

    def _init_ui(self):
        layout = QVBoxLayout()

        model_group = QGroupBox("Embedding Model Configuration")
        model_layout = QFormLayout()

        self.model_info_label = QLabel(
            "Select embedding model for semantic code search. "
            "Changing model requires re-indexing."
        )
        self.model_info_label.setWordWrap(True)
        self.model_info_label.setStyleSheet("color: gray; font-size: 10px;")

        model_layout.addRow(self.model_info_label)

        self.model_combo = QComboBox()
        for key, info in AppConfig.AVAILABLE_EMBEDDING_MODELS.items():
            display_text = f"{key} - {info['description']} ({info['dim']}D)"
            self.model_combo.addItem(display_text, key)
        self.model_combo.addItem("Custom model...", "custom")
        self.model_combo.currentIndexChanged.connect(self._on_model_changed)

        model_layout.addRow("Model:", self.model_combo)

        self.custom_model_input = QLineEdit()
        self.custom_model_input.setPlaceholderText("Enter HuggingFace model name or path...")
        self.custom_model_input.setVisible(False)
        model_layout.addRow("Custom Model:", self.custom_model_input)

        model_group.setLayout(model_layout)
        layout.addWidget(model_group)

        indexing_group = QGroupBox("Indexing Settings")
        indexing_layout = QFormLayout()

        self.chunk_size_spin = QSpinBox()
        self.chunk_size_spin.setRange(256, 2048)
        self.chunk_size_spin.setSingleStep(64)
        self.chunk_size_spin.setValue(AppConfig.DEFAULT_CHUNK_SIZE)
        indexing_layout.addRow("Chunk Size (chars):", self.chunk_size_spin)

        self.overlap_spin = QSpinBox()
        self.overlap_spin.setRange(0, 256)
        self.overlap_spin.setSingleStep(10)
        self.overlap_spin.setValue(AppConfig.DEFAULT_CHUNK_OVERLAP)
        indexing_layout.addRow("Chunk Overlap (chars):", self.overlap_spin)

        self.max_file_spin = QSpinBox()
        self.max_file_spin.setRange(512, 10240)
        self.max_file_spin.setSingleStep(512)
        self.max_file_spin.setValue(AppConfig.MAX_FILE_SIZE // 1024)
        indexing_layout.addRow("Max File Size (KB):", self.max_file_spin)

        indexing_group.setLayout(indexing_layout)
        layout.addWidget(indexing_group)

        search_group = QGroupBox("Search Settings")
        search_layout = QFormLayout()

        self.search_limit_spin = QSpinBox()
        self.search_limit_spin.setRange(10, 500)
        self.search_limit_spin.setSingleStep(10)
        self.search_limit_spin.setValue(AppConfig.DEFAULT_SEARCH_LIMIT)
        search_layout.addRow("Default Result Limit:", self.search_limit_spin)

        self.rrf_k_spin = QSpinBox()
        self.rrf_k_spin.setRange(1, 100)
        self.rrf_k_spin.setValue(AppConfig.RRF_K)
        search_layout.addRow("RRF Constant (k):", self.rrf_k_spin)

        search_group.setLayout(search_layout)
        layout.addWidget(search_group)

        autosync_group = QGroupBox("Background Auto-Sync")
        autosync_layout = QVBoxLayout()

        self.autosync_checkbox = QCheckBox("Enable Auto-Sync")
        self.autosync_checkbox.setChecked(AppConfig.get_auto_sync_enabled())
        self.autosync_checkbox.toggled.connect(self._on_autosync_toggled)

        autosync_info = QLabel(
            "Automatically monitor project files and update index when changes are detected."
        )
        autosync_info.setWordWrap(True)
        autosync_info.setStyleSheet("color: gray; font-size: 10px;")

        self.autosync_status = QLabel("Status: Idle")
        self.autosync_status.setStyleSheet("font-weight: bold;")

        debounce_layout = QHBoxLayout()
        debounce_layout.addWidget(QLabel("Debounce delay (seconds):"))
        self.debounce_spin = QSpinBox()
        self.debounce_spin.setRange(1, 10)
        self.debounce_spin.setValue(int(AppConfig.AUTO_SYNC_DEBOUNCE_SECONDS))
        self.debounce_spin.setToolTip("Wait time before processing file changes")
        debounce_layout.addWidget(self.debounce_spin)
        debounce_layout.addStretch()

        autosync_layout.addWidget(self.autosync_checkbox)
        autosync_layout.addWidget(autosync_info)
        autosync_layout.addWidget(self.autosync_status)
        autosync_layout.addLayout(debounce_layout)

        autosync_group.setLayout(autosync_layout)
        layout.addWidget(autosync_group)

        stats_group = QGroupBox("Database Statistics")
        stats_layout = QVBoxLayout()

        self.stats_text = QTextEdit()
        self.stats_text.setReadOnly(True)
        self.stats_text.setMaximumHeight(120)

        refresh_btn = QPushButton("Refresh Stats")
        refresh_btn.clicked.connect(self._load_db_stats)

        stats_layout.addWidget(self.stats_text)
        stats_layout.addWidget(refresh_btn)

        stats_group.setLayout(stats_layout)
        layout.addWidget(stats_group)

        btn_layout = QHBoxLayout()

        self.save_btn = QPushButton("Save Settings")
        self.save_btn.clicked.connect(self._save_settings)

        self.reset_btn = QPushButton("Reset to Defaults")
        self.reset_btn.clicked.connect(self._reset_settings)

        btn_layout.addWidget(self.save_btn)
        btn_layout.addWidget(self.reset_btn)
        btn_layout.addStretch()

        layout.addLayout(btn_layout)

        layout.addStretch()
        self.setLayout(layout)

    def _load_settings(self):
        self._load_db_stats()
        self._load_embedding_model()
        self._load_indexing_and_search_settings()

    def _load_db_stats(self):
        try:
            # Use StatsManager for centralized full stats retrieval
            stats_html = StatsManager.format_full_stats_html()
            self.stats_text.setHtml(stats_html)

        except Exception as e:
            self.stats_text.setText(f"Error loading stats: {str(e)}")

    def _load_embedding_model(self):
        saved_model = AppConfig.get_embedding_model()
        self.current_model = saved_model

        if saved_model:
            index = self.model_combo.findData(saved_model)
            if index >= 0:
                self.model_combo.setCurrentIndex(index)
            else:
                custom_index = self.model_combo.findData("custom")
                self.model_combo.setCurrentIndex(custom_index)
                self.custom_model_input.setText(saved_model)
                self.custom_model_input.setVisible(True)
        else:
            self.model_combo.setCurrentIndex(0)
            self.current_model = self.model_combo.currentData()

    def _load_indexing_and_search_settings(self):
        AppConfig.load_indexing_settings()
        AppConfig.load_search_settings()

        self.chunk_size_spin.setValue(AppConfig.DEFAULT_CHUNK_SIZE)
        self.overlap_spin.setValue(AppConfig.DEFAULT_CHUNK_OVERLAP)
        self.max_file_spin.setValue(AppConfig.MAX_FILE_SIZE // 1024)
        self.search_limit_spin.setValue(AppConfig.DEFAULT_SEARCH_LIMIT)
        self.rrf_k_spin.setValue(AppConfig.RRF_K)

    def _on_model_changed(self):
        selected_data = self.model_combo.currentData()

        if selected_data == "custom":
            self.custom_model_input.setVisible(True)
        else:
            self.custom_model_input.setVisible(False)

    def _on_autosync_toggled(self, checked: bool):
        AppConfig.set_auto_sync_enabled(checked)
        self.autosync_toggled.emit(checked)
        status = "Enabled" if checked else "Disabled"
        self.autosync_status.setText(f"Status: {status}")

    def _save_settings(self):
        AppConfig.save_indexing_settings(
            chunk_size=self.chunk_size_spin.value(),
            chunk_overlap=self.overlap_spin.value(),
            max_file_size=self.max_file_spin.value() * 1024
        )

        AppConfig.save_search_settings(
            search_limit=self.search_limit_spin.value(),
            rrf_k=self.rrf_k_spin.value()
        )

        selected_data = self.model_combo.currentData()

        if selected_data == "custom":
            new_model = self.custom_model_input.text().strip()
            if not new_model:
                DialogHelper.show_warning(
                    self,
                    "Invalid Model",
                    "Please enter a custom model name or select a predefined model."
                )
                return
        else:
            model_info = AppConfig.get_embedding_model_info(selected_data)
            new_model = model_info['full_name'] if model_info else selected_data

        model_changed = (self.current_model != new_model)

        if model_changed:
            self._show_reindex_dialog(new_model)
        else:
            AppConfig.set_embedding_model(new_model)
            self.current_model = new_model

            DialogHelper.show_info(
                self,
                "Settings Saved",
                "Settings have been saved successfully."
            )

    def _show_reindex_dialog(self, new_model: str):
        msg_box = QMessageBox(self)
        msg_box.setIcon(QMessageBox.Icon.Warning)
        msg_box.setWindowTitle("Embedding Model Changed")
        msg_box.setText(
            f"<b>Embedding model has been changed to:</b><br>{new_model}"
        )
        msg_box.setInformativeText(
            "Model change requires re-indexing all code to generate new embeddings. "
            "Existing search results may be inaccurate until re-indexing is complete.\n\n"
            "What would you like to do?"
        )

        reindex_now_btn = msg_box.addButton("Re-index Now", QMessageBox.ButtonRole.AcceptRole)
        later_btn = msg_box.addButton("Save and Re-index Later", QMessageBox.ButtonRole.RejectRole)
        cancel_btn = msg_box.addButton("Cancel", QMessageBox.ButtonRole.DestructiveRole)

        msg_box.setDefaultButton(reindex_now_btn)
        msg_box.exec()

        clicked_button = msg_box.clickedButton()

        if clicked_button == reindex_now_btn:
            AppConfig.set_embedding_model(new_model)
            self.current_model = new_model

            DialogHelper.show_info(
                self,
                "Settings Saved",
                "Model saved successfully. Switching to Indexer tab to start re-indexing..."
            )

            self.reindex_requested.emit()

        elif clicked_button == later_btn:
            AppConfig.set_embedding_model(new_model)
            self.current_model = new_model

            DialogHelper.show_info(
                self,
                "Settings Saved",
                "Model saved successfully. Please re-index your project when ready."
            )

    def _reset_settings(self):
        if DialogHelper.show_confirm(
            self,
            "Reset Settings",
            "Reset all settings to default values?"
        ):
            self.chunk_size_spin.setValue(512)
            self.overlap_spin.setValue(50)
            self.max_file_spin.setValue(1024)
            self.search_limit_spin.setValue(50)
            self.rrf_k_spin.setValue(60)
