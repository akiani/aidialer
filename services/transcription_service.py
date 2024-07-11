import os

from deepgram import DeepgramClient, LiveOptions, LiveTranscriptionEvents

from logger_config import get_logger
from services.event_emmiter import EventEmitter

logger = get_logger("Transcription")

class TranscriptionService(EventEmitter):
    def __init__(self):
        super().__init__()
        self.client = DeepgramClient(os.getenv("DEEPGRAM_API_KEY"))
        self.deepgram_live = None
        self.final_result = ""
        self.speech_final = False
        self.stream_sid = None

    def set_stream_sid(self, stream_id):
        self.stream_sid = stream_id

    def get_stream_sid(self):
        return self.stream_sid

    async def connect(self):
        self.deepgram_live = self.client.listen.asynclive.v("1")
        await self.deepgram_live.start(LiveOptions(
            model="nova-2", 
            language="en-US", 
            encoding="mulaw",
            sample_rate=8000,
            channels=1,
            punctuate=True,
            interim_results=True,
            endpointing=200,
            utterance_end_ms=1000
        ))

        self.deepgram_live.on(LiveTranscriptionEvents.Transcript, self.handle_transcription)
        self.deepgram_live.on(LiveTranscriptionEvents.Error, self.handle_error)
        self.deepgram_live.on(LiveTranscriptionEvents.Close, self.handle_close)
        self.deepgram_live.on(LiveTranscriptionEvents.Warning, self.handle_warning)
        self.deepgram_live.on(LiveTranscriptionEvents.Metadata, self.handle_metadata)
        self.deepgram_live.on(LiveTranscriptionEvents.UtteranceEnd, self.handle_utterance_end)

    async def handle_utterance_end(self, self_obj, utterance_end):
        try:
            if not self.speech_final:
                logger.info(f"UtteranceEnd received before speech was final, emit the text collected so far: {self.final_result}")
                await self.emit('transcription', self.final_result)
                self.final_result = ''
                self.speech_final = True
                return
            else:
                return
        except Exception as e:
            logger.error(f"Error while handling utterance end: {e}")
            e.print_stack()

    async def handle_transcription(self, self_obj, result):
        try:
            alternatives = result.channel.alternatives if hasattr(result, 'channel') else []
            text = alternatives[0].transcript if alternatives else ""

            if result.is_final and text.strip():
                self.final_result += f" {text}"
                if result.speech_final:
                    self.speech_final = True
                    await self.emit('transcription', self.final_result)
                    self.final_result = ''
                else:
                    self.speech_final = False
            else:
                if text.strip():
                    stream_sid = self.stream_sid
                    await self.emit('utterance', text, stream_sid)
        except Exception as e:
            logger.error(f"Error while handling transcription: {e}")
            e.print_stack()

            
    async def handle_error(self, self_obj, error):
        logger.error(f"Deepgram error: {error}")
        self.is_connected = False
    
    async def handle_warning(self, self_obj, warning):
        logger.info('Deepgram warning:', warning)

    async def handle_metadata(self, self_obj, metadata):
        logger.info('Deepgram metadata:', metadata)

    async def handle_close(self, self_obj, close):
        logger.info("Deepgram connection closed")
        self.is_connected = False

    async def send(self, payload: bytes):
        if self.deepgram_live:            
            await self.deepgram_live.send(payload)
    
    async def disconnect(self):
        if self.deepgram_live:
            await self.deepgram_live.finish()
            self.deepgram_live = None
        self.is_connected = False
        logger.info("Disconnected from Deepgram")