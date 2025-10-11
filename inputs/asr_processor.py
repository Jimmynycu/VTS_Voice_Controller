import asyncio
import sounddevice as sd
import numpy as np
import sherpa_onnx
from loguru import logger
import onnxruntime
import webrtcvad

from core.interfaces import InputProcessor
from core.event_bus import EventBus

class ASRProcessor(InputProcessor):
    def __init__(
        self,
        event_bus: EventBus,
        tokens_path: str,
        encoder_path: str,
        decoder_path: str,
        joiner_path: str,
        decoding_method: str = "greedy_search",
        debug: bool = False,
        sample_rate: int = 16000,
        provider: str = "cpu",
        vad_aggressiveness: int = 3, # 0 (least aggressive) to 3 (most aggressive)
        vad_frame_duration_ms: int = 30, # 10, 20, or 30
        recognition_mode: str = "fast", # "fast" or "accurate"
    ) -> None:
        self.event_bus = event_bus
        self.tokens_path = tokens_path
        self.encoder_path = encoder_path
        self.decoder_path = decoder_path
        self.joiner_path = joiner_path
        self.decoding_method = decoding_method
        self.debug = debug
        self.SAMPLE_RATE = sample_rate
        self.provider = provider
        self.recognition_mode = recognition_mode

        if self.provider == "cuda":
            try:
                if "CUDAExecutionProvider" not in onnxruntime.get_available_providers():
                    logger.warning("CUDA provider not available for ONNX. Falling back to CPU.")
                    self.provider = "cpu"
            except ImportError:
                logger.warning("ONNX Runtime not installed. Falling back to CPU.")
                self.provider = "cpu"
        logger.info(f"Sherpa-Onnx-ASR: Using {self.provider} for inference")

        self.recognizer = self._create_recognizer()
        self.stream = self.recognizer.create_stream()
        self.audio_buffer = np.array([], dtype=np.float32)
        self.buffer_lock = asyncio.Lock()
        self.last_text = "" # For tracking partial results

        # VAD initialization
        self.vad = webrtcvad.Vad(vad_aggressiveness)
        self.vad_frame_duration_ms = vad_frame_duration_ms
        self.vad_frame_size = int(self.SAMPLE_RATE * self.vad_frame_duration_ms / 1000)
        self.vad_buffer = b'' # Buffer for VAD frames

    def _create_recognizer(self):
        return sherpa_onnx.OnlineRecognizer.from_transducer(
            tokens=self.tokens_path,
            encoder=self.encoder_path,
            decoder=self.decoder_path,
            joiner=self.joiner_path,
            num_threads=1,
            sample_rate=self.SAMPLE_RATE,
            feature_dim=80,
            enable_endpoint_detection=True,
            decoding_method=self.decoding_method,
            provider=self.provider,
            debug=self.debug,
            rule3_min_utterance_length=3.0, # Encourage faster partial results
        )

    def _transcribe_np(self, audio: np.ndarray) -> str:
        self.stream.accept_waveform(self.SAMPLE_RATE, audio)
        while self.recognizer.is_ready(self.stream):
            self.recognizer.decode_stream(self.stream)

        if self.recognition_mode == "fast":
            result = self.recognizer.get_result(self.stream)
            text = result.text.strip() if hasattr(result, 'text') else result.strip()

            text_to_return = ""
            if text and text != self.last_text:
                text_to_return = text
                self.last_text = text

            if self.recognizer.is_endpoint(self.stream):
                self.recognizer.reset(self.stream)
                self.last_text = ""
            
            return text_to_return
        
        else: # Accurate mode
            text_to_return = ""
            if self.recognizer.is_endpoint(self.stream):
                result = self.recognizer.get_result(self.stream)
                text_to_return = result.text.strip() if hasattr(result, 'text') else result.strip()
                self.recognizer.reset(self.stream)
            
            return text_to_return

    async def _audio_callback(self, indata, frames, time, status):
        logger.trace(f"Audio callback received {frames} frames.")
        if status:
            logger.warning(status)

        # Convert float32 to int16 for VAD
        pcm_data = (indata * 32767).astype(np.int16).tobytes()
        self.vad_buffer += pcm_data

        # Process VAD frames
        while len(self.vad_buffer) >= self.vad_frame_size * 2: # 2 bytes per int16 sample
            frame = self.vad_buffer[:self.vad_frame_size * 2]
            self.vad_buffer = self.vad_buffer[self.vad_frame_size * 2:]

            logger.trace("Checking frame for speech with VAD.")
            is_speech = self.vad.is_speech(frame, self.SAMPLE_RATE)

            if is_speech:
                logger.trace("Speech detected, adding to ASR buffer.")
                # If speech is detected, append to the ASR buffer
                async with self.buffer_lock:
                    # Convert back to float32 for ASR if needed, or handle directly if ASR accepts int16
                    # Sherpa-onnx expects float32, so convert back
                    float_frame = np.frombuffer(frame, dtype=np.int16).astype(np.float32) / 32767.0
                    self.audio_buffer = np.concatenate((self.audio_buffer, float_frame))

    async def process_input(self):
        logger.info("Starting microphone stream...")
        await self.event_bus.publish("asr_status_update", "Listening")
        loop = asyncio.get_running_loop()

        def sync_audio_callback(indata, frames, time, status):
            asyncio.run_coroutine_threadsafe(self._audio_callback(indata, frames, time, status), loop)

        async def process_audio_buffer_periodically():
            while True:
                await asyncio.sleep(0.05)  # Process buffer every 0.05 seconds (50ms)
                async with self.buffer_lock:
                    if self.audio_buffer.size > 0:
                        logger.trace("Processing audio buffer.")
                        await self.event_bus.publish("asr_status_update", "Transcribing")
                        transcribed_text = self._transcribe_np(self.audio_buffer)
                        if transcribed_text:
                            logger.trace(f"Transcription received: {transcribed_text}")
                            await self.event_bus.publish("transcription_received", transcribed_text)
                        self.audio_buffer = np.array([], dtype=np.float32)  # Clear the buffer
                        await self.event_bus.publish("asr_status_update", "Listening")

        audio_processing_task = asyncio.create_task(process_audio_buffer_periodically())

        try:
            # blocksize should be a multiple of VAD frame size
            blocksize = self.vad_frame_size * 2 # Process two VAD frames at a time, for example
            with sd.InputStream(callback=sync_audio_callback,
                                 channels=1, dtype='float32', samplerate=self.SAMPLE_RATE, blocksize=blocksize):
                logger.info("Microphone stream started. Say something!")
                await self.event_bus.publish("asr_ready", True)
                await audio_processing_task
        except Exception as e:
            logger.error(f"An error occurred during audio streaming: {e}")
            await self.event_bus.publish("asr_status_update", "Error")
            audio_processing_task.cancel()
            raise
