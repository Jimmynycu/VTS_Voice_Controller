from PyQt6.QtWidgets import (
    QMainWindow, QVBoxLayout, QHBoxLayout, QWidget, QTextEdit, QTableWidget,
    QTableWidgetItem, QLabel, QPushButton, QHeaderView, QComboBox, QProgressBar
)
from PyQt6.QtCore import Qt

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QVBoxLayout(self.central_widget)

        self._init_ui_elements()
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

        controls_layout.addWidget(self.start_button)
        controls_layout.addWidget(self.stop_button)
        controls_layout.addStretch()
        controls_layout.addWidget(self.mode_label)
        controls_layout.addWidget(self.mode_selector)
        controls_layout.addWidget(self.language_label)
        controls_layout.addWidget(self.language_selector)
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
        self.main_layout.addWidget(self.keyword_editor)

    def retranslate_ui(self, language: str):
        # This will be expanded with a proper localization system later.
        # For now, we'll use a simple dictionary for demonstration.
        self.translations = {
            "en": {
                "window_title": "VTS Voice Controller",
                "vts_status_disconnected": "Disconnected",
                "asr_status_idle": "Idle",
                "app_status_stopped": "Stopped",
                "recognition_mode": "Recognition Mode:",
                "language": "Language:",
                "start_button": "Start Application",
                "stop_button": "Stop Application",
                "log_placeholder": "Live Transcription Output...",
                "header_expression": "Expression Name",
                "header_keywords": "Keywords",
                "header_cooldown": "Cooldown (s)"
            },
            "zh": {
                "window_title": "VTS语音控制器",
                "vts_status_disconnected": "已断开",
                "asr_status_idle": "空闲",
                "app_status_stopped": "已停止",
                "recognition_mode": "识别模式:",
                "language": "语言:",
                "start_button": "启动应用",
                "stop_button": "停止应用",
                "log_placeholder": "实时语音识别输出...",
                "header_expression": "表情名称",
                "header_keywords": "关键词",
                "header_cooldown": "冷却(秒)"
            },
            "ja": {
                "window_title": "VTS音声コントローラー",
                "vts_status_disconnected": "切断されました",
                "asr_status_idle": "アイドル",
                "app_status_stopped": "停止",
                "recognition_mode": "認識モード:",
                "language": "言語:",
                "start_button": "アプリケーションを開始",
                "stop_button": "アプリケーションを停止",
                "log_placeholder": "ライブ文字起こし出力...",
                "header_expression": "表情名",
                "header_keywords": "キーワード",
                "header_cooldown": "クールダウン(秒)"
            }
        }

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
        self.start_button.setText(t["start_button"])
        self.stop_button.setText(t["stop_button"])
        self.transcription_log.setPlaceholderText(t["log_placeholder"])
        self.keyword_editor.setHorizontalHeaderLabels([
            t["header_expression"], t["header_keywords"], t["header_cooldown"]
        ])

    def append_log(self, text: str):
        self.transcription_log.append(text)

    def set_status(self, vts: str = None, asr: str = None, app: str = None):
        if vts: self.vts_status_label.setText(f"VTS Status: {vts}")
        if asr: self.asr_status_label.setText(f"ASR Status: {asr}")
        if app: self.app_status_label.setText(f"App Status: {app}")

    def populate_keyword_editor(self, expressions: dict):
        self.keyword_editor.setRowCount(len(expressions))
        row = 0
        for exp_file, exp_data in expressions.items():
            self.keyword_editor.setItem(row, 0, QTableWidgetItem(exp_data.get('name', 'N/A')))
            self.keyword_editor.setItem(row, 1, QTableWidgetItem(", ".join(exp_data.get('keywords', []))))
            self.keyword_editor.setItem(row, 2, QTableWidgetItem(str(exp_data.get('cooldown_s', 'N/A'))))
            row += 1
