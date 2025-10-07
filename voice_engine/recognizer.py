import os
import numpy as np
import sherpa_onnx
from loguru import logger
from .interface import ASRInterface
from .utils import download_and_extract, check_and_extract_local_file
import onnxruntime

class VoiceRecognition:
    def __init__(
        self,
        sense_voice_model_dir: str,
        decoding_method: str = "greedy_search",
        debug: bool = False,
        sample_rate: int = 16000,
        provider: str = "cpu",
    ) -> None:
        self.sense_voice_model_dir = sense_voice_model_dir
        self.model_path = os.path.join(self.sense_voice_model_dir, "model.int8.onnx")
        self.tokens_path = os.path.join(self.sense_voice_model_dir, "tokens.txt")
        self.decoding_method = decoding_method
        self.debug = debug
        self.SAMPLE_RATE = sample_rate
        self.provider = provider

        if self.provider == "cuda":
            try:
                if "CUDAExecutionProvider" not in onnxruntime.get_available_providers():
                    logger.warning("CUDA provider not available for ONNX. Falling back to CPU.")
                    self.provider = "cpu"
            except ImportError:
                logger.warning("ONNX Runtime not installed. Falling back to CPU.")
                self.provider = "cpu"
        logger.info(f"Sherpa-Onnx-ASR: Using {self.provider} for inference")

        self._check_and_download_model()
        self.recognizer = self._create_recognizer()

    def _check_and_download_model(self):
        # Check for a key file to determine if the directory is valid.
        if not os.path.isfile(self.model_path):
            logger.warning("SenseVoice model not found. Downloading the model...")
            url = "https://github.com/k2-fsa/sherpa-onnx/releases/download/asr-models/sherpa-onnx-sense-voice-zh-en-ja-ko-yue-2024-07-17.tar.bz2"
            output_dir = os.path.dirname(self.sense_voice_model_dir)
            local_result = check_and_extract_local_file(url, output_dir)
            if local_result is None:
                logger.info("Local file not found. Downloading...")
                download_and_extract(url, output_dir)
            else:
                logger.info("Local file found. Using existing file.")

    def _create_recognizer(self):
        return sherpa_onnx.OfflineRecognizer.from_sense_voice(
            model=self.model_path,
            tokens=self.tokens_path,
            use_itn=True,
            debug=self.debug,
            provider=self.provider,
            num_threads=1,
        )

    def transcribe_np(self, audio: np.ndarray) -> str:
        stream = self.recognizer.create_stream()
        stream.accept_waveform(self.SAMPLE_RATE, audio)
        self.recognizer.decode_streams([stream])
        return stream.result.text

    async def async_transcribe_np(self, audio: np.ndarray) -> str:
        return self.transcribe_np(audio)
