import uuid
from typing import Dict

from fastapi import WebSocket

from logger_config import get_logger
from services.event_emmiter import EventEmitter

logger = get_logger("Stream")

class StreamService(EventEmitter):
    def __init__(self, websocket: WebSocket):
        super().__init__()
        self.ws = websocket
        self.expected_audio_index = 0
        self.audio_buffer: Dict[int, str] = {}
        self.stream_sid = ''

    def set_stream_sid(self, stream_sid: str):
        self.stream_sid = stream_sid

    async def buffer(self, index: int, audio: str):
        if index is None:
            await self.send_audio(audio)
        elif index == self.expected_audio_index:
            await self.send_audio(audio)
            self.expected_audio_index += 1

            while self.expected_audio_index in self.audio_buffer:
                buffered_audio = self.audio_buffer[self.expected_audio_index]
                await self.send_audio(buffered_audio)
                del self.audio_buffer[self.expected_audio_index]
                self.expected_audio_index += 1
        else:
            self.audio_buffer[index] = audio

    def reset(self):
        self.expected_audio_index = 0
        self.audio_buffer = {}

    async def send_audio(self, audio: str):
        await self.ws.send_json({
            "streamSid": self.stream_sid,
            "event": "media",
            "media": {
                "payload": audio
            }
        })

        mark_label = str(uuid.uuid4())

        await self.ws.send_json({
            "streamSid": self.stream_sid,
            "event": "mark",
            "mark": {
                "name": mark_label
            }
        })

        await self.emit('audiosent', mark_label)