import asyncio
import sys
import yaml
from loguru import logger

from PyQt6.QtWidgets import QApplication

from ui.main_window import MainWindow
from core.application_core import ApplicationCore

def load_initial_config():
    try:
        with open("vts_config.yaml", 'r') as f:
            return yaml.safe_load(f)
    except Exception as e:
        logger.error(f"Failed to load initial config: {e}")
        return None

class AppUI:
    def __init__(self):
        # App instance is now managed in vts_main.py
        self.main_window = MainWindow()
        self.app_core_task = None

        # Connect signals to synchronous slots
        self.main_window.start_button.clicked.connect(self._start_button_clicked)
        self.main_window.stop_button.clicked.connect(self._stop_button_clicked)
        self.main_window.language_selector.currentTextChanged.connect(self._language_changed)
        self.main_window.closing.connect(self._on_main_window_closing)

        # Initial UI setup
        initial_config = load_initial_config()
        if initial_config:
            self.main_window.populate_keyword_editor(initial_config.get('expressions', {}))
        
        self.main_window.show()

    def _start_button_clicked(self):
        logger.info("--- UI: Start button clicked ---")
        # This synchronous method creates the async task
        self.app_core_task = asyncio.create_task(self.start_application())

    def _stop_button_clicked(self):
        logger.info("--- UI: Stop button clicked ---")
        if self.app_core_task:
            self.app_core_task.cancel()

    def _language_changed(self, language_code: str):
        self.main_window.retranslate_ui(language_code)

    def _on_main_window_closing(self):
        logger.info("--- UI: Main window closing ---")
        if self.app_core_task:
            self.app_core_task.cancel()

    async def start_application(self):
        self.main_window.set_status(app="Starting...")
        self.main_window.start_button.setEnabled(False)
        self.main_window.mode_selector.setEnabled(False)
        self.main_window.language_selector.setEnabled(False)
        self.main_window.stop_button.setEnabled(True)

        recognition_mode = self.main_window.mode_selector.currentText()
        language = self.main_window.language_selector.currentText()
        provider = self.main_window.provider_selector.currentText()

        app_core = ApplicationCore(
            config_path="vts_config.yaml",
            recognition_mode=recognition_mode,
            language=language,
            provider=provider
        )

        # Setup listeners on the running instance
        transcription_queue = await app_core.event_bus.subscribe("transcription_received")
        hotkey_queue = await app_core.event_bus.subscribe("hotkey_triggered")
        vts_status_queue = await app_core.event_bus.subscribe("vts_status_update")
        asr_status_queue = await app_core.event_bus.subscribe("asr_status_update")
        asr_ready_queue = await app_core.event_bus.subscribe("asr_ready")
        model_download_queue = await app_core.event_bus.subscribe("model_download_progress")

        listener_tasks = [
            asyncio.create_task(self._handle_transcription_events(transcription_queue)),
            asyncio.create_task(self._handle_hotkey_events(hotkey_queue)),
            asyncio.create_task(self._handle_vts_status_events(vts_status_queue)),
            asyncio.create_task(self._handle_asr_status_events(asr_status_queue)),
            asyncio.create_task(self._handle_asr_ready_events(asr_ready_queue)),
            asyncio.create_task(self._handle_model_download_events(model_download_queue)),
        ]

        try:
            await app_core.run()
        except asyncio.CancelledError:
            logger.info("Application core task was cancelled by UI.")
        except Exception as e:
            logger.error(f"An error occurred in the application core: {e}")
            self.main_window.append_log(f"[ERROR] {e}")
        finally:
            for task in listener_tasks:
                task.cancel()
            self.main_window.set_status(app="Stopped", vts="Disconnected", asr="Idle")
            self.main_window.start_button.setEnabled(True)
            self.main_window.mode_selector.setEnabled(True)
            self.main_window.language_selector.setEnabled(True)
            self.main_window.stop_button.setEnabled(False)
            self.main_window.progress_bar.setVisible(False)

    async def _handle_model_download_events(self, queue: asyncio.Queue):
        while True:
            try:
                event = await queue.get()
                progress = event.payload
                if progress == 0:
                    self.main_window.progress_bar.setVisible(True)
                    self.main_window.progress_bar.setRange(0, 100)
                    self.main_window.progress_bar.setValue(0)
                elif progress >= 100:
                    self.main_window.progress_bar.setVisible(False)
                else:
                    self.main_window.progress_bar.setValue(progress)
                queue.task_done()
            except asyncio.CancelledError:
                break

    async def _handle_transcription_events(self, queue: asyncio.Queue):
        while True:
            try:
                event = await queue.get()
                self.main_window.append_log(f"Heard: {event.payload}")
                queue.task_done()
            except asyncio.CancelledError:
                break

    async def _handle_hotkey_events(self, queue: asyncio.Queue):
        while True:
            try:
                event = await queue.get()
                self.main_window.append_log(f">>> Triggered: {event.payload}")
                queue.task_done()
            except asyncio.CancelledError:
                break

    async def _handle_vts_status_events(self, queue: asyncio.Queue):
        while True:
            try:
                event = await queue.get()
                self.main_window.set_status(vts=event.payload)
                queue.task_done()
            except asyncio.CancelledError:
                break

    async def _handle_asr_status_events(self, queue: asyncio.Queue):
        while True:
            try:
                event = await queue.get()
                self.main_window.set_status(asr=event.payload)
                queue.task_done()
            except asyncio.CancelledError:
                break

    async def _handle_asr_ready_events(self, queue: asyncio.Queue):
        while True:
            try:
                await queue.get()
                self.main_window.set_status(app="Running")
                queue.task_done()
            except asyncio.CancelledError:
                break