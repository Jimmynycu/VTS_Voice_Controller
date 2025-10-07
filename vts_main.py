import asyncio
import sounddevice as sd
import numpy as np
import yaml
from loguru import logger
import os
import time

from voice_engine.recognizer import VoiceRecognition
from vts_client import VTSClient

# --- Configuration ---
CONFIG_PATH = "vts_config.yaml"

# --- Global Variables ---
vts_client = None
expression_map = {}
last_triggered_expression = None
consecutive_trigger_count = 0
expression_cooldowns = {}

async def asr_callback(transcribed_text: str):
    """Callback function to process transcribed text with spam prevention."""
    global last_triggered_expression, consecutive_trigger_count, expression_cooldowns

    if not transcribed_text:
        return

    logger.info(f"Transcribed: {transcribed_text}")
    lower_transcribed_text = transcribed_text.lower()

    for keyword, hotkey_id in expression_map.items():
        if keyword.lower() in lower_transcribed_text:
            # Check if the expression is on cooldown
            if hotkey_id in expression_cooldowns and time.time() < expression_cooldowns[hotkey_id]:
                remaining = expression_cooldowns[hotkey_id] - time.time()
                logger.info(f"Keyword '{keyword}' detected, but expression {hotkey_id} is on cooldown for {remaining:.1f} more seconds.")
                continue

            # Update consecutive trigger count
            if hotkey_id == last_triggered_expression:
                consecutive_trigger_count += 1
            else:
                last_triggered_expression = hotkey_id
                consecutive_trigger_count = 1

            # If this is the second consecutive trigger, apply cooldown
            if consecutive_trigger_count == 2:
                cooldown_duration = 60  # 1 minute
                expression_cooldowns[hotkey_id] = time.time() + cooldown_duration
                logger.warning(f"Expression {hotkey_id} triggered twice consecutively. Placing on cooldown for {cooldown_duration} seconds.")

            # Trigger the expression
            logger.info(f"Keyword '{keyword}' detected. Triggering expression: {hotkey_id}")
            print(f'Heard: "{transcribed_text}" -> Triggering "{hotkey_id}"')
            await vts_client.trigger_expression(hotkey_id)
            break

async def audio_callback(indata, frames, time, status):
    """This is called (from a separate thread) for each audio block."""
    if status:
        logger.warning(status)
    
    try:
        # The ASR engine expects a 1D numpy array of float32
        audio_np = indata.flatten().astype(np.float32)
        text = await asr_engine.async_transcribe_np(audio_np)
        if text:
            await asr_callback(text)
    except Exception as e:
        logger.error(f"Error during transcription: {e}")

async def main():
    global vts_client, expression_map, asr_engine

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

    # 2. Initialize ASR Engine
    script_dir = os.path.dirname(os.path.abspath(__file__))
    absolute_model_dir = os.path.join(script_dir, "models", "sherpa-onnx-sense-voice-zh-en-ja-ko-yue-2024-07-17")
    asr_engine = VoiceRecognition(
        sense_voice_model_dir=absolute_model_dir,
        debug=False,
        decoding_method="modified_beam_search",
        provider="cuda",
    )

    # 3. Initialize and connect VTSClient
    vts_client = VTSClient(
        host=vts_settings['host'],
        port=vts_settings['port'],
        token_file=vts_settings['token_file']
    )
    await vts_client.connect()
    await vts_client.authenticate()

    # 4. Auto-update YAML with VTS Expressions
    logger.info("Checking for expression updates from VTube Studio...")
    try:
        hotkey_list_response = await vts_client.get_hotkey_list()
        if hotkey_list_response and 'data' in hotkey_list_response and 'availableHotkeys' in hotkey_list_response['data']:
            vts_expressions = [h for h in hotkey_list_response['data']['availableHotkeys'] if h.get('type') == 'ToggleExpression']

            logger.info("--- Available Expressions in VTube Studio ---")
            if not vts_expressions:
                logger.info("No expressions found in the current VTS model.")
            else:
                for exp in vts_expressions:
                    logger.info(f"- {exp.get('name')} ({exp.get('file')})")
            logger.info("-------------------------------------------")

            yaml_expressions = config.get('expressions', {})
            reverse_yaml_map = {v: k for k, v in yaml_expressions.items()}
            new_yaml_expressions = {}
            updated = False

            for exp in vts_expressions:
                exp_file = exp.get('file')
                exp_name = exp.get('name')
                if not exp_file or not exp_name:
                    continue
                if exp_file in reverse_yaml_map:
                    keyword = reverse_yaml_map[exp_file]
                    new_yaml_expressions[keyword] = exp_file
                else:
                    placeholder_keyword = f"NEW_KEYWORD_{exp_name.replace(' ', '_')}"
                    new_yaml_expressions[placeholder_keyword] = exp_file
                    updated = True

            if len(new_yaml_expressions) != len(yaml_expressions) or updated:
                config['expressions'] = new_yaml_expressions
                with open(CONFIG_PATH, 'w') as f:
                    yaml.dump(config, f, default_flow_style=False, allow_unicode=True)
                logger.info("Successfully updated 'vts_config.yaml' with the latest expressions.")

            session_expression_map = {}
            file_to_hotkey_id_map = {exp.get('file'): exp.get('hotkeyID') for exp in vts_expressions}

            for keyword, file_name in new_yaml_expressions.items():
                if file_name in file_to_hotkey_id_map:
                    hotkey_id = file_to_hotkey_id_map[file_name]
                    session_expression_map[keyword] = hotkey_id

            for exp in vts_expressions:
                if exp.get('name') and exp.get('hotkeyID'):
                    session_expression_map[exp.get('name')] = exp.get('hotkeyID')
            
            expression_map = session_expression_map
            logger.info("Expression map created. Ready to detect keywords.")

    except Exception as e:
        logger.error(f"Failed to auto-update expressions: {e}")

    # 5. Start listening to the microphone
    logger.info("Starting microphone stream...")
    
    loop = asyncio.get_running_loop()

    def sync_audio_callback(indata, frames, time, status):
        asyncio.run_coroutine_threadsafe(audio_callback(indata, frames, time, status), loop)

    try:
        with sd.InputStream(callback=sync_audio_callback, channels=1, dtype='float32', samplerate=16000):
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
