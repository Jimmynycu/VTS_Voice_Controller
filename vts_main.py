import asyncio
import sys
import os
from loguru import logger
from qasync import QEventLoop
from PyQt6.QtWidgets import QApplication

from ui.app_ui import AppUI
from core.path_config import get_log_dir

def main():
    # --- Setup Logging ---
    log_dir = get_log_dir()
    log_path = os.path.join(log_dir, "vts_controller.log")
    logger.add(log_path, rotation="10 MB", retention="7 days", level="INFO", backtrace=True, diagnose=True)

    # --- Set up the asyncio event loop for qasync ---
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    loop = QEventLoop(app)
    asyncio.set_event_loop(loop)

    # --- Create and run the application ---
    app_ui = AppUI()
    
    with loop:
        loop.run_forever()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("Program terminated by user.")
    except Exception as e:
        logger.critical(f"An unhandled exception occurred: {e}", exc_info=True)
        sys.exit(1)
