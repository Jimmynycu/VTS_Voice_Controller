# VTS Voice Controller

## Project Overview

This project is a Python application that controls a VTube Studio model using voice commands. It listens to the user's microphone, transcribes their speech in real-time, and triggers facial expressions in VTube Studio when specific keywords are detected. The focus is on low-latency, real-time reactions.

The core technologies used are:
- **VTube Studio Integration:** `pyvts` library is used to communicate with the VTube Studio API.
- **Voice Recognition:** `sherpa-onnx` (specifically `OnlineRecognizer`) is used for real-time speech-to-text transcription.
- **Audio Input:** `sounddevice` is used to capture audio from the microphone with optimized buffering for real-time performance.
- **Configuration:** `pyyaml` is used to manage application settings.

The application is structured as follows:
- `vts_main.py`: The main entry point of the application. It handles loading the configuration, initializing the VTS client, and managing the audio stream.
- `vts_client.py`: A client class to interact with the VTube Studio API, including connecting, authenticating, and triggering expressions.
- `vts_config.yaml`: The configuration file for VTS settings (host, port, token file) and the keyword-to-expression mappings.
- `test_vts_main.py`: Contains unit tests for the main application logic.

## Building and Running

To run this project, follow these steps:

1. **Install Dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure the Application:**
   - Open the `vts_config.yaml` file.
   - Under `vts_settings`, ensure the `host` and `port` match your VTube Studio API settings.
   - The `token_file` will be created automatically on the first run.
   - Under `expressions`, map the keywords you want to detect to the corresponding VTube Studio expression files (`.exp3.json`).

3. **Run the Application:**
   ```bash
   python vts_main.py
   ```
   The first time you run the application, you will need to authenticate the plugin in VTube Studio.

4. **Run Tests:**
    ```bash
    pytest
    ```

## Development Conventions

- The application uses asynchronous programming with `asyncio`.
- Logging is handled by the `loguru` library.
- Unit tests are written using `pytest` and `unittest.mock`.
- Configuration is managed through a `vts_config.yaml` file.
- The `VTSClient` class in `vts_client.py` encapsulates all interactions with the VTube Studio API.
- The main application logic in `vts_main.py` is responsible for orchestrating the audio input, real-time voice recognition using `sherpa-onnx.OnlineRecognizer`, and VTS expression triggering.