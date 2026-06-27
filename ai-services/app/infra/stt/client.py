"""STT adapter — wired by interview voice pipeline (not REST API)."""


class STTClient:
    async def transcribe(self, audio_bytes: bytes, *, language: str = "en") -> str:
        raise NotImplementedError("STT adapter not implemented — connect PhoWhisper / SenseVoice")