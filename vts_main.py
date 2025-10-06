import asyncio
import sounddevice as sd
import numpy as np
import yaml
from loguru import logger
import sys
import os
import importlib

current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(current_dir, 'src'))

# Ensure the module is loaded fresh, bypassing cache issues
module_name = 'open_llm_vtuber.asr.sherpa_onnx_asr'
if module_name in sys.modules:
    del sys.modules[module_name]

import open_llm_vtuber.asr.sherpa_onnx_asr as sherpa_onnx_asr_module
from vts_client import VTSClient

# --- Configuration ---
CONFIG_PATH = "vts_config.yaml"

# --- ASR Setup ---
# This is a simplified ASR setup. In a real application, this would be more robust.
# For now, we will use a pre-configured SenseVoice model.
# The ASR class will handle downloading the model if the path is relative.
relative_model_dir = os.path.join("./models", "sherpa-onnx-sense-voice-zh-en-ja-ko-yue-2024-07-17")
asr_engine = sherpa_onnx_asr_module.VoiceRecognition(
    model_type="sense_voice",
    sense_voice=os.path.join(relative_model_dir, "model.int8.onnx"),
    tokens=os.path.join(relative_model_dir, "tokens.txt"),
    debug=False,
    decoding_method="modified_beam_search", # New: Use beam search for better accuracy
    provider="cuda", # New: Enable GPU acceleration if available
)

# --- Global Variables ---
vts_client = None
expression_map = {}

async def asr_callback(transcribed_text: str, client, exp_map):
    """Callback function to process transcribed text."""
    # Print the transcribed text for debugging
    print(f"Heard: \"{transcribed_text}\"")
    
    logger.info(f"Transcribed: {transcribed_text}")
    
    # Make the comparison case-insensitive
    lower_transcribed_text = transcribed_text.lower()
    
    for keyword, expression_file in exp_map.items():
        if keyword.lower() in lower_transcribed_text:
            hotkey_id = exp_map[keyword] # Get the hotkey ID from the map
            logger.info(f"Keyword '{keyword}' detected. Triggering expression: {hotkey_id}")
            await client.trigger_expression(hotkey_id)

async def audio_callback(indata, frames, time, status):
    """This is called (from a separate thread) for each audio block."""
    if status:
        logger.warning(status)
    
    # Amplify the audio signal, but clip it to the valid range [-1, 1]
    amplified_audio = indata * 20.0
    clipped_audio = np.clip(amplified_audio, -1.0, 1.0)

    # The ASR engine expects a 1D numpy array of float32
    audio_np = clipped_audio.flatten().astype(np.float32)
    try:
        text = await asr_engine.async_transcribe_np(audio_np)
        if text:
            await asr_callback(text, vts_client, expression_map)
    except Exception as e:
        logger.error(f"Error during transcription: {e}")

async def main():
    global vts_client, expression_map

    # 1. Load Configuration
    try:
        with open(CONFIG_PATH, 'r') as f:
            config = yaml.safe_load(f)
        vts_settings = config['vts_settings']
        expression_map = config['expressions']
        logger.info("Configuration loaded.")
    except FileNotFoundError:
        logger.error(f"Configuration file not found at {CONFIG_PATH}. Please create it.")
        return
    except Exception as e:
        logger.error(f"Error loading configuration: {e}")
        return

    # 2. Initialize and connect VTSClient
    vts_client = VTSClient(
        host=vts_settings['host'],
        port=vts_settings['port'],
        token_file=vts_settings['token_file']
    )
    await vts_client.connect()
    await vts_client.authenticate()

    # 3. Start listening to the microphone
    logger.info("Starting microphone stream...")
    
    loop = asyncio.get_running_loop()

    def sync_audio_callback(indata, frames, time, status):
        """A synchronous callback that schedules the async audio processing on the main event loop."""
        asyncio.run_coroutine_threadsafe(audio_callback(indata, frames, time, status), loop)

    try:
        with sd.InputStream(callback=sync_audio_callback,
                             channels=1, dtype='float32', samplerate=16000):
            logger.info("Microphone stream started. Say something!")
            while True:
                await asyncio.sleep(1)
    except KeyboardInterrupt:
        logger.info("Stopping...")
    except Exception as e:
        logger.error(f"An error occurred during audio streaming: {e}")
    finally:
        if vts_client:
            await vts_client.disconnect()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Program terminated by user.")
