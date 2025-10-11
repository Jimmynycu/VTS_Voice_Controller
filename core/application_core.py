
import asyncio
import yaml
from loguru import logger
import os
import sys

from core.event_bus import EventBus
from agents.vts_output_agent import VTSWebSocketAgent
from core.intent_resolver import KeywordIntentResolver
from inputs.test_input_processor import TestInputProcessor
from inputs.asr_processor import ASRProcessor
from inputs.utils.utils import ensure_model_downloaded_and_extracted

class ApplicationCore:
    def __init__(self, config_path: str, test_mode: bool = False, recognition_mode: str = "fast", language: str = "en"):
        self.config_path = config_path
        self.test_mode = test_mode
        self.recognition_mode = recognition_mode
        self.language = language
        self.event_bus = EventBus()
        self.config = self._load_config()
        self.vts_agent = None
        self.intent_resolver = None
        self.input_processor = None

    def _load_config(self):
        if getattr(sys, 'frozen', False):
            base_path = os.path.dirname(sys.executable)
        else:
            base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

        config_path = os.path.join(base_path, self.config_path)

        if not os.path.exists(config_path):
            logger.warning(f"Configuration file not found at {config_path}. Creating a default one.")
            default_config = {
                'vts_settings': {
                    'host': '127.0.0.1',
                    'port': 8001,
                    'token_file': os.path.join(base_path, 'vts_token.txt')
                },
                'expressions': {
                    'DefaultExpression.exp3.json': {
                        'name': 'DefaultExpression',
                        'keywords': ['hello'],
                        'cooldown_s': 60
                    }
                }
            }
            try:
                with open(config_path, 'w') as f:
                    yaml.safe_dump(default_config, f, default_flow_style=False, allow_unicode=True)
                logger.info("Default configuration created.")
                return default_config
            except Exception as e:
                logger.error(f"Error creating default configuration: {e}")
                return None
        else:
            try:
                with open(config_path, 'r') as f:
                    return yaml.safe_load(f)
            except Exception as e:
                logger.error(f"Error loading configuration from {config_path}: {e}")
                return None

    async def _initialize_components(self):
        if not self.config:
            logger.error("Initialization failed: Configuration is not loaded.")
            return

        vts_settings = self.config['vts_settings']
        self.vts_agent = VTSWebSocketAgent(
            host=vts_settings['host'],
            port=vts_settings['port'],
            token_file=vts_settings['token_file'],
            event_bus=self.event_bus
        )

        await self.vts_agent.connect()
        await self.vts_agent.authenticate()

        expression_map = await self._synchronize_expressions()

        self.intent_resolver = KeywordIntentResolver(self.event_bus, expression_map)

        if self.test_mode:
            logger.info("--- RUNNING IN TEST MODE ---")
            self.input_processor = TestInputProcessor(self.event_bus)
        else:
            logger.info("--- RUNNING IN NORMAL MODE (MICROPHONE INPUT) ---")
            # This is where the real ASRProcessor is initialized
            model_config = {
                "en": {
                    "url": "https://github.com/k2-fsa/sherpa-onnx/releases/download/asr-models/sherpa-onnx-streaming-zipformer-en-20M-2023-02-17.tar.bz2",
                    "tokens": "tokens.txt",
                    "encoder": "encoder-epoch-99-avg-1.int8.onnx",
                    "decoder": "decoder-epoch-99-avg-1.int8.onnx",
                    "joiner": "joiner-epoch-99-avg-1.int8.onnx",
                },
                "zh": {
                    "url": "https://github.com/k2-fsa/sherpa-onnx/releases/download/asr-models/sherpa-onnx-streaming-zipformer-bilingual-zh-en-2023-02-20.tar.bz2",
                    "tokens": "tokens.txt",
                    "encoder": "encoder-epoch-99-avg-1.int8.onnx",
                    "decoder": "decoder-epoch-99-avg-1.int8.onnx",
                    "joiner": "joiner-epoch-99-avg-1.int8.onnx",
                },
                "ja": {
                    "url": "https://github.com/k2-fsa/sherpa-onnx/releases/download/asr-models/sherpa-onnx-streaming-zipformer-ja-2023-05-28.tar.bz2",
                    "tokens": "tokens.txt",
                    "encoder": "encoder-epoch-99-avg-1.onnx",
                    "decoder": "decoder-epoch-99-avg-1.onnx",
                    "joiner": "joiner-epoch-99-avg-1.onnx",
                }
            }

            selected_model = model_config.get(self.language.lower())
            if not selected_model:
                logger.error(f"Language '{self.language}' not supported. Please check the model_config.")
                return

            model_url = selected_model["url"]
            if getattr(sys, 'frozen', False):
                base_path = os.path.dirname(sys.executable)
            else:
                base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            model_base_dir = os.path.join(base_path, "models")

            async def progress_callback(progress):
                await self.event_bus.publish("model_download_progress", progress)

            actual_model_dir = await ensure_model_downloaded_and_extracted(model_url, model_base_dir, progress_callback)

            self.input_processor = ASRProcessor(
                event_bus=self.event_bus,
                tokens_path=os.path.join(actual_model_dir, selected_model["tokens"]),
                encoder_path=os.path.join(actual_model_dir, selected_model["encoder"]),
                decoder_path=os.path.join(actual_model_dir, selected_model["decoder"]),
                joiner_path=os.path.join(actual_model_dir, selected_model["joiner"]),
                provider="cpu", # Defaulting to CPU for broader compatibility
                recognition_mode=self.recognition_mode,
            )

    async def _synchronize_expressions(self):
        logger.info("Checking for expression updates from VTube Studio...")
        try:
            hotkey_list_response = await self.vts_agent.get_hotkey_list()
            if hotkey_list_response and 'data' in hotkey_list_response and 'availableHotkeys' in hotkey_list_response['data']:
                vts_expressions = [h for h in hotkey_list_response['data']['availableHotkeys'] if h.get('type') == 'ToggleExpression']

                yaml_expressions = self.config.get('expressions', {})
                new_yaml_expressions = {}
                updated = False

                # Map VTS hotkey IDs to their file names for quick lookup
                file_to_hotkey_id_map = {exp.get('file'): exp.get('hotkeyID') for exp in vts_expressions}

                for exp in vts_expressions:
                    exp_file = exp.get('file')
                    exp_name = exp.get('name')
                    if not exp_file or not exp_name:
                        continue

                    if exp_file in yaml_expressions: # Existing expression
                        # Preserve existing keywords and cooldown_s
                        new_yaml_expressions[exp_file] = yaml_expressions[exp_file]
                    else: # New expression from VTS
                        placeholder_keyword = f"NEW_KEYWORD_{exp_name.replace(' ', '_')}"
                        new_yaml_expressions[exp_file] = {
                            'name': exp_name,
                            'keywords': [placeholder_keyword],
                            'cooldown_s': 60 # Default cooldown
                        }
                        updated = True

                # Check for removed expressions (optional, but good practice)
                if len(new_yaml_expressions) != len(yaml_expressions):
                    updated = True

                if updated:
                    self.config['expressions'] = new_yaml_expressions
                    with open(self.config_path, 'w') as f:
                        yaml.dump(self.config, f, default_flow_style=False, allow_unicode=True)
                    logger.info(f"Successfully updated '{self.config_path}' with the latest expressions.")

                session_expression_map = {}
                # Build the session_expression_map from the updated config
                for exp_file, exp_data in new_yaml_expressions.items():
                    hotkey_id = file_to_hotkey_id_map.get(exp_file)
                    if hotkey_id:
                        for keyword in exp_data.get('keywords', []):
                            session_expression_map[keyword] = hotkey_id
                        # Also add the VTS expression name as a keyword
                        session_expression_map[exp_data['name']] = hotkey_id
                
                logger.info("Expression map created. Ready to detect keywords.")
                return session_expression_map

        except Exception as e:
            logger.error(f"Failed to auto-update expressions: {e}")
        return {}

    async def run(self):
        await self._initialize_components()
        if not self.vts_agent or not self.intent_resolver:
            logger.error("Application cannot start due to initialization failure.")
            return

        # If no input processor is available (i.e., not in test mode and ASR is disabled), exit gracefully.
        if not self.input_processor:
            logger.error("No input processor available. The application will now exit.")
            logger.error("Run with the --test flag for testing, or resolve the onnxruntime issue to enable microphone input.")
            await self.vts_agent.disconnect()
            return

        logger.info("Starting application components...")
        
        tasks = [
            asyncio.create_task(self.intent_resolver.resolve_intent()),
            asyncio.create_task(self.vts_agent.run()),
            asyncio.create_task(self.input_processor.process_input()),
        ]

        # If in test mode, we need a way to stop the application
        if self.test_mode:
            async def test_shutdown_manager():
                await asyncio.sleep(10) # Give ample time for the test event to fire and be processed
                logger.warning("--- TEST COMPLETE: SHUTTING DOWN APPLICATION ---")
                for task in tasks:
                    task.cancel()
            tasks.append(asyncio.create_task(test_shutdown_manager()))

        try:
            await asyncio.gather(*tasks)
        except asyncio.CancelledError:
            logger.info("Application tasks were cancelled.")
        except KeyboardInterrupt:
            logger.info("Stopping application...")
        finally:
            for task in asyncio.all_tasks():
                if task is not asyncio.current_task():
                    task.cancel()
            if self.vts_agent:
                await self.vts_agent.disconnect()
