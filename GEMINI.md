# VTS Voice Controller

## Project Overview

This project is a Python application that controls a VTube Studio model using voice commands. It periodically listens to the user's microphone, transcribes their speech, and triggers facial expressions in VTube Studio when specific keywords are detected.

The application features an automatic synchronization system that fetches available expressions from VTube Studio and updates the local configuration file, making it easy to add new keywords. It also includes a spam prevention mechanism to avoid repeatedly triggering the same expression.

## Core Technologies

- **VTube Studio Integration:** `pyvts` library for VTS API communication.
- **Voice Recognition:** `sherpa-onnx` for speech-to-text transcription.
- **Audio Input:** `sounddevice` for microphone audio capture.
- **Configuration:** `pyyaml` for managing application settings.
- **Logging:** `loguru` for application logging.
- **Async Operations:** `asyncio` for managing concurrent tasks.

## Application Structure

- **`vts_main.py`**: The main application entry point. It manages configuration, VTS connection, audio buffering, periodic transcription, and expression triggering.
- **`vts_client.py`**: A client class that encapsulates all interactions with the VTube Studio API, including connecting, authenticating, fetching hotkeys, and triggering expressions. It now includes a request lock to prevent API request race conditions.
- **`src/open_llm_vtuber/asr/sherpa_onnx_asr.py`**: A wrapper for the `sherpa-onnx` ASR engine, configured to use an offline model for transcription.
- **`vts_config.yaml`**: The configuration file for VTS settings and keyword-to-expression mappings. This file is now automatically updated on startup.
- **`requirements.txt`**: A list of all Python dependencies.

## Key Features

- **Automatic Expression Sync:** On startup, the application connects to VTube Studio, fetches the list of available expressions for the current model, and updates `vts_config.yaml`. New expressions are added with a placeholder keyword (e.g., `NEW_KEYWORD_ExpressionName`).
- **Flexible Keyword Detection:** Triggers expressions based on keywords defined in the YAML file. It also automatically uses the expression's name in VTube Studio as a keyword.
- **Batch Audio Processing:** Captures microphone audio into a buffer and processes it in chunks to transcribe speech.
- **Spam Prevention:** If an expression is triggered twice in a row, it is placed on a 60-second cooldown to prevent spam.
- **GPU Acceleration:** Can leverage a CUDA-enabled GPU for faster transcription if `onnxruntime-gpu` is installed and the provider is set to `cuda`.

## How It Works

1.  **Initialization:** The application loads settings from `vts_config.yaml`.
2.  **VTS Connection:** It connects to VTube Studio and authenticates.
3.  **Expression Sync:** It requests the list of all hotkeys from VTube Studio, filters for expressions, and updates `vts_config.yaml` with any new or changed expressions. It then builds a map of keywords to hotkey IDs for the current session.
4.  **Audio Streaming:** The application starts listening to the microphone, capturing audio into a buffer.
5.  **Periodic Transcription:** Every few seconds, the content of the audio buffer is processed. The audio is amplified and sent to the `sherpa-onnx` offline recognizer for transcription.
6.  **Keyword Matching:** The transcribed text is checked for matches with the keywords from the expression map.
7.  **Trigger Expression:** If a keyword is found and the expression is not on cooldown, the application sends a request to the VTube Studio API to trigger the corresponding expression hotkey.

## Development Setup

To ensure a clean and isolated environment, it is highly recommended to use a Python virtual environment (`venv`).

1.  **Create a Virtual Environment:**
    Open your terminal in the project root and run:
    ```bash
    python -m venv .venv
    ```

2.  **Activate the Virtual Environment:**
    -   **Windows (Command Prompt/PowerShell):**
        ```cmd
        .\.venv\Scripts\activate
        ```
    -   **macOS/Linux (Bash):**
        ```sh
        source .venv/bin/activate
        ```
    Your terminal prompt should now indicate that you are in the `.venv` environment.

3.  **Install Dependencies:**
    With the virtual environment active, install the required packages:
    ```bash
    pip install -r requirements.txt
    ```
    *(Note: For GPU support, you may need to install a specific version of `onnxruntime-gpu`)*

## Building and Running

1.  **Activate Environment:** Ensure your virtual environment is active (see step 2 above).

2.  **Run the Application:**
    ```bash
    python vts_main.py
    ```
3.  **First-Time Setup:**
    - On the first run, you will need to allow the plugin's authentication request inside VTube Studio.
    - The application will automatically populate `vts_config.yaml` with expressions from your current VTS model.

4.  **Configure Keywords:**
    - Open `vts_config.yaml`.
    - Change the placeholder keywords (e.g., `NEW_KEYWORD_MyExpression`) to the voice commands you want to use.
