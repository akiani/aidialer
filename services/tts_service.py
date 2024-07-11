
import base64
import os
from abc import ABC, abstractmethod
from typing import Any, Dict

import aiohttp
import numpy as np
from deepgram import DeepgramClient, LiveOptions
from dotenv import load_dotenv

from logger_config import get_logger
from services.event_emmiter import EventEmitter

load_dotenv()
logger = get_logger("TTS")


class AbstractTTSService(EventEmitter, ABC):
    @abstractmethod
    async def generate(self, llm_reply: Dict[str, Any], interaction_count: int):
        pass

    @abstractmethod
    async def set_voice(self, voice_id: str):
        pass

    @abstractmethod
    async def disconnect(self):
        pass

class ElevenLabsTTS(AbstractTTSService):
    def __init__(self):
        super().__init__()
        self.voice_id = os.getenv("ELEVENLABS_VOICE_ID")
        self.api_key = os.getenv("ELEVENLABS_API_KEY")
        self.model_id = os.getenv("ELEVENLABS_MODEL_ID")
        self.speech_buffer = {}


    def set_voice(self, voice_id):
        self.voice_id = voice_id

    async def disconnect(self):
        # ElevenLabs client doesn't require explicit disconnection
        return


    async def generate(self, llm_reply: Dict[str, Any], interaction_count: int):
        partial_response_index, partial_response = llm_reply['partialResponseIndex'], llm_reply['partialResponse']

        if not partial_response:
            return

        try:
            output_format = "ulaw_8000"            
            url = f"https://api.elevenlabs.io/v1/text-to-speech/{self.voice_id}/stream"
            headers = {
                "xi-api-key": self.api_key,
                "Content-Type": "application/json",
                "Accept": "audio/wav"
            }
            params = {
                "output_format": output_format,
                "optimize_streaming_latency": 4
            }
            data = {
                "model_id": self.model_id,
                "text": partial_response
            }

            async with aiohttp.ClientSession() as session:
                async with session.post(url, headers=headers, params=params, json=data) as response:
                    if response.status == 200:
                        audio_content = await response.read()
                        audio_base64 = base64.b64encode(audio_content).decode('utf-8')
                        await self.emit('speech', partial_response_index, audio_base64, partial_response, interaction_count)
        except Exception as err:
            logger.error("Error occurred in ElevenLabs TTS service", exc_info=True)
            logger.error(str(err))


class DeepgramTTS(AbstractTTSService):
    def __init__(self):
        super().__init__()
        self.client = DeepgramClient(os.getenv("DEEPGRAM_API_KEY"))

    async def generate(self, llm_reply, interaction_count):
        partial_response_index = llm_reply['partialResponseIndex']
        partial_response = llm_reply['partialResponse']

        if not partial_response:
            return

        try:
            source = {
                "text": partial_response
            }

            options = {
                "model": "aura-asteria-en",
                "encoding": "mulaw", 
                "sample_rate": 8000 
            }
            
            response = await self.client.asyncspeak.v("1").stream(
                source={"text": partial_response},
                options=options
            )

            if response.stream:
                audio_content = response.stream.getvalue()
                
                # Convert audio to numpy array
                audio_array = np.frombuffer(audio_content, dtype=np.uint8)
                
                # Trim the first 10ms (80 samples at 8000Hz) to remove the initial noise
                trim_samples = 80
                trimmed_audio = audio_array[trim_samples:]
                
                # Convert back to bytes
                trimmed_audio_bytes = trimmed_audio.tobytes()

                audio_base64 = base64.b64encode(trimmed_audio_bytes).decode('utf-8')
                await self.emit('speech', partial_response_index, audio_base64, partial_response, interaction_count)
            else:
                logger.error("Error in TTS generation: No audio stream returned")

        except Exception as e:
            logger.error(f"Error in TTS generation: {str(e)}")


    async def set_voice(self, voice_id):
        logger.info(f"Attempting to set voice to {voice_id}, but Deepgram TTS doesn't support direct voice selection.")
        # TODO(akiani): Implement voice selection in Deepgram TTS

    async def disconnect(self):
        # Deepgram client doesn't require explicit disconnection
        logger.info("DeepgramTTS service disconnected")


class TTSFactory:
    @staticmethod
    def get_tts_service(service_name: str) -> AbstractTTSService:
        if service_name.lower() == "elevenlabs":
            return ElevenLabsTTS()
        elif service_name.lower() == "deepgram":
            return DeepgramTTS()
        else:
            raise ValueError(f"Unsupported TTS service: {service_name}")

# Usage in your main application
tts_service_name = os.getenv("TTS_SERVICE", "deepgram")  # Default to deepgram if not specified
tts_service = TTSFactory.get_tts_service(tts_service_name)