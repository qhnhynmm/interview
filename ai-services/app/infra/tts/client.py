"""TTS adapter — wired by interview voice pipeline (not REST API)."""


class TTSClient:
    async def synthesize(self, text: str, *, language: str = "en") -> bytes:
        raise NotImplementedError("TTS adapter not implemented — connect Kokoro / vi-TTS")