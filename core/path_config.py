import os
import sys

def get_project_root() -> str:
    """
    Determines the project root directory.
    For a regular run, it's the directory of this script.
    For a frozen app (e.g., PyInstaller), it's the directory of the executable.
    """
    if getattr(sys, 'frozen', False):
        # The application is frozen
        return os.path.dirname(sys.executable)
    else:
        # The application is not frozen
        # This will be the 'core' directory, so we go up one level
        return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

ROOT_DIR = get_project_root()

def get_config_path(filename: str) -> str:
    """Returns the absolute path to a configuration file."""
    return os.path.join(ROOT_DIR, "config", filename)

def get_vts_config_path() -> str:
    """Returns the absolute path to the main vts_config.yaml."""
    return os.path.join(ROOT_DIR, "vts_config.yaml")

def get_log_dir() -> str:
    """Returns the absolute path to the log directory."""
    log_dir = os.path.join(ROOT_DIR, "logs")
    os.makedirs(log_dir, exist_ok=True)
    return log_dir

def get_models_dir() -> str:
    """Returns the absolute path to the models directory."""
    models_dir = os.path.join(ROOT_DIR, "models")
    os.makedirs(models_dir, exist_ok=True)
    return models_dir