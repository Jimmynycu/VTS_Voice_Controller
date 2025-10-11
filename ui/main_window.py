import sys
from PyQt6.QtWidgets import (
    QMainWindow, QVBoxLayout, QHBoxLayout, QWidget, QTextEdit, QTableWidget,
    QTableWidgetItem, QLabel, QPushButton, QHeaderView, QComboBox, QProgressBar, QMessageBox
)
from PyQt6.QtCore import Qt, pyqtSignal
import yaml
from core.path_config import get_config_path

class MainWindow(QMainWindow):
    closing = pyqtSignal()

    def __init__(self):
        super().__init__()

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QVBoxLayout(self.central_widget)

        self._init_ui_elements()
        self._load_translations()
        self.retranslate_ui("en") # Set initial language to English

    def _init_ui_elements(self):
        # Status Panel
        status_layout = QHBoxLayout()
        self.vts_status_label = QLabel()
        self.asr_status_label = QLabel()
        self.app_status_label = QLabel()
        status_layout.addWidget(self.vts_status_label)
        status_layout.addWidget(self.asr_status_label)
        status_layout.addWidget(self.app_status_label)
        self.main_layout.addLayout(status_layout)

        # Controls
        controls_layout = QHBoxLayout()
        self.start_button = QPushButton()
        self.stop_button = QPushButton()
        self.stop_button.setEnabled(False)
        self.mode_label = QLabel()
        self.mode_selector = QComboBox()
        self.mode_selector.addItems(["fast", "accurate"])

        self.language_label = QLabel()
        self.language_selector = QComboBox()

        self.provider_label = QLabel()
        self.provider_selector = QComboBox()
        self.provider_selector.addItems(["cpu", "cuda"])

        controls_layout.addWidget(self.start_button)
        controls_layout.addWidget(self.stop_button)
        controls_layout.addStretch()
        controls_layout.addWidget(self.mode_label)
        controls_layout.addWidget(self.mode_selector)
        controls_layout.addWidget(self.language_label)
        controls_layout.addWidget(self.language_selector)
        controls_layout.addWidget(self.provider_label)
        controls_layout.addWidget(self.provider_selector)
        self.main_layout.addLayout(controls_layout)

        # Download Progress Bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False) # Initially hidden
        self.main_layout.addWidget(self.progress_bar)

        # Transcription Log
        self.transcription_log = QTextEdit()
        self.transcription_log.setReadOnly(True)
        self.main_layout.addWidget(self.transcription_log)

        # Keyword Editor
        self.keyword_editor = QTableWidget()
        self.keyword_editor.setColumnCount(3)
        self.keyword_editor.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.keyword_editor.setSortingEnabled(True)
        self.main_layout.addWidget(self.keyword_editor)

        self.save_button = QPushButton()
        self.main_layout.addWidget(self.save_button)

    def _load_translations(self):
        try:
            with open(get_config_path("translations.yaml"), 'r', encoding='utf-8') as f:
                self.translations = yaml.safe_load(f)
        except FileNotFoundError:
            self._show_error_and_exit(f"Configuration file not found: {get_config_path('translations.yaml')}")
        except Exception as e:
            self._show_error_and_exit(f"Failed to load translations: {e}")

    def _show_error_and_exit(self, message):
        error_box = QMessageBox()
        error_box.setIcon(QMessageBox.Icon.Critical)
        error_box.setText(message)
        error_box.setWindowTitle("Configuration Error")
        error_box.setStandardButtons(QMessageBox.StandardButton.Ok)
        error_box.exec()
        sys.exit(1)

    def retranslate_ui(self, language: str):
        # Populate language selector
        if self.language_selector.count() == 0:
            self.language_selector.addItems(self.translations.keys())

        lang_code = language if language in self.translations else "en"
        t = self.translations[lang_code]

        self.setWindowTitle(t["window_title"])
        self.set_status(
            vts=t["vts_status_disconnected"],
            asr=t["asr_status_idle"],
            app=t["app_status_stopped"]
        )
        self.mode_label.setText(t["recognition_mode"])
        self.language_label.setText(t["language"])
        self.provider_label.setText(t["provider"])
        self.start_button.setText(t["start_button"])
        self.stop_button.setText(t["stop_button"])
        self.save_button.setText(t.get("save_button", "Save Keywords"))
        self.transcription_log.setPlaceholderText(t["log_placeholder"])
        self.keyword_editor.setHorizontalHeaderLabels([
            t["header_expression"], t["header_keywords"], t["header_cooldown"]
        ])

    def closeEvent(self, event):
        self.closing.emit()
        super().closeEvent(event)

    def append_log(self, text: str):
        self.transcription_log.append(text)

    def set_status(self, vts: str = None, asr: str = None, app: str = None):
        lang_code = self.language_selector.currentText() if self.language_selector.count() > 0 else "en"
        t = self.translations.get(lang_code, self.translations["en"])

        if vts: self.vts_status_label.setText(f"{t.get('vts_status', 'VTS Status:')} {vts}")
        if asr: self.asr_status_label.setText(f"{t.get('asr_status', 'ASR Status:')} {asr}")
        if app: self.app_status_label.setText(f"{t.get('app_status', 'App Status:')} {app}")

    def populate_keyword_editor(self, expressions: dict):
        self.keyword_editor.setRowCount(len(expressions))
        row = 0
        for exp_file, exp_data in expressions.items():
            self.keyword_editor.setItem(row, 0, QTableWidgetItem(exp_data.get('name', 'N/A')))
            self.keyword_editor.setItem(row, 1, QTableWidgetItem(", ".join(exp_data.get('keywords', []))))
            self.keyword_editor.setItem(row, 2, QTableWidgetItem(str(exp_data.get('cooldown_s', 'N/A'))))
            # Make the first column read-only
            self.keyword_editor.item(row, 0).setFlags(self.keyword_editor.item(row, 0).flags() & ~Qt.ItemFlag.ItemIsEditable)
            row += 1