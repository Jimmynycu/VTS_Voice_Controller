# VTS Voice Controller

A Python application that controls your VTube Studio model's expressions using real-time voice recognition.

## Features

- **Real-time Voice Recognition**: Listens to your microphone and transcribes speech in real-time.
- **Keyword-Based Expression Triggering**: Triggers expressions in VTube Studio when specific keywords or phrases are detected.
- **Automatic Expression Sync**: On startup, automatically discovers expressions from your VTube Studio model and updates the configuration file.
- **Flexible Keyword System**: Supports both custom keywords defined in a config file and the expression names set directly in VTube Studio.
- **Spam Prevention**: Prevents the same expression from being spammed by enforcing a 1-minute cooldown if triggered twice consecutively.

## Setup and Installation

1.  **Clone the Repository**
    ```bash
    git clone <your-repository-url>
    cd VTS_Voice_Controller
    ```

2.  **Create a Python Virtual Environment**
    ```bash
    python -m venv .venv
    ```

3.  **Activate the Environment**
    -   On Windows (Command Prompt):
        ```cmd
        .\.venv\Scripts\activate
        ```
    -   On macOS/Linux (Bash):
        ```sh
        source .venv/bin/activate
        ```

4.  **Install Dependencies**
    ```bash
    pip install -r requirements.txt
    ```

## Configuration

The application uses the `vts_config.yaml` file for configuration.

-   **VTS Settings**: Ensure the `host` and `port` under `vts_settings` match your VTube Studio API configuration.
-   **Expressions**:
    -   On the first run, the application will automatically populate the `expressions` section with all expressions found in your VTube Studio model.
    -   It will create placeholder keywords for new expressions (e.g., `NEW_KEYWORD_...`).
    -   You can edit these keywords to be any phrase you want. The program will recognize both your custom keyword and the original expression name from VTube Studio.

    Example:
    ```yaml
    expressions:
      # This keyword was auto-generated, you can change it
      NEW_KEYWORD_Shock: Shock.exp3.json
      # You can change it to a custom phrase
      oh my god: Shock.exp3.json
    ```

## Running the Application

This project includes convenient scripts to run the application.

-   **On Windows (Command Prompt/PowerShell):**
    ```cmd
    .\run.bat
    ```
-   **On macOS/Linux (or Git Bash on Windows):**
    ```sh
    ./run.sh
    ```

You may need to make the `.sh` script executable first: `chmod +x run.sh`.

Alternatively, you can run the program manually after activating the virtual environment:
```bash
python vts_main.py
```
