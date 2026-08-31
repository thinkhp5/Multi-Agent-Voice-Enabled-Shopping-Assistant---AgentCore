"""
Voice I/O — unchanged in role from the original repo (mic in, OpenAI TTS out).

Not wired into runtime_app.py: AgentCore Runtime is a request/response HTTP
service, so voice capture/playback belongs on the client side (e.g. a local
script or web client that records audio, transcribes it, sends the text as
`prompt` to the deployed agent, then plays back the returned `answer` via
TTS). This module still handles the local mic/speaker plumbing for that
client-side piece; it does not run inside the Runtime container.
"""
import io

from openai import OpenAI

client = OpenAI()


class VoiceRecorder:
    def __init__(self, duration_seconds: int = 5):
        self.duration_seconds = duration_seconds

    def record(self) -> bytes:
        """Record `duration_seconds` of audio from the default mic, return WAV bytes."""
        import sounddevice as sd
        import soundfile as sf

        sample_rate = 16000
        audio = sd.rec(
            int(self.duration_seconds * sample_rate),
            samplerate=sample_rate,
            channels=1,
        )
        sd.wait()
        buf = io.BytesIO()
        sf.write(buf, audio, sample_rate, format="WAV")
        buf.seek(0)
        return buf.read()

    def transcribe(self, wav_bytes: bytes) -> str:
        buf = io.BytesIO(wav_bytes)
        buf.name = "audio.wav"
        result = client.audio.transcriptions.create(model="whisper-1", file=buf)
        return result.text


class VoiceSpeaker:
    def speak(self, text: str) -> None:
        """Synthesize `text` via OpenAI TTS and play it through the default speaker."""
        import sounddevice as sd
        import soundfile as sf

        response = client.audio.speech.create(model="tts-1", voice="alloy", input=text)
        buf = io.BytesIO(response.content)
        data, sample_rate = sf.read(buf)
        sd.play(data, sample_rate)
        sd.wait()
