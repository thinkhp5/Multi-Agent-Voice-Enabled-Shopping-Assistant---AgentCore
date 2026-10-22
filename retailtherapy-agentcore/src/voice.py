"""
AWS-native voice I/O using Amazon Transcribe and Amazon Polly.

This module is for a local client (microphone and speaker). Transcription
uploads a temporary WAV object to the S3 bucket configured by
TRANSCRIBE_S3_BUCKET, submits an Amazon Transcribe job, and removes the
input object after the job completes. Polly generates speech audio.
"""
import io
import json
import os
import time
import uuid
import urllib.request

import boto3

from src.config import AWS_REGION

s3 = boto3.client("s3", region_name=AWS_REGION)
transcribe = boto3.client("transcribe", region_name=AWS_REGION)
polly = boto3.client("polly", region_name=AWS_REGION)


class VoiceRecorder:
    def __init__(self, duration_seconds: int = 5):
        self.duration_seconds = duration_seconds

    def record(self) -> bytes:
        """Record audio from the default microphone and return WAV bytes."""
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
        """Transcribe WAV bytes with Amazon Transcribe using a temporary S3 object."""
        bucket = os.getenv("TRANSCRIBE_S3_BUCKET")
        if not bucket:
            raise RuntimeError(
                "Set TRANSCRIBE_S3_BUCKET to an S3 bucket in your AWS_REGION "
                "for Amazon Transcribe input audio."
            )

        key = f"retailtherapy-transcribe/{uuid.uuid4().hex}.wav"
        job_name = f"retailtherapy-{uuid.uuid4().hex}"
        s3_uri = f"s3://{bucket}/{key}"
        s3.put_object(Bucket=bucket, Key=key, Body=wav_bytes, ContentType="audio/wav")

        try:
            transcribe.start_transcription_job(
                TranscriptionJobName=job_name,
                Media={"MediaFileUri": s3_uri},
                MediaFormat="wav",
                LanguageCode=os.getenv("TRANSCRIBE_LANGUAGE_CODE", "en-US"),
            )

            timeout_seconds = int(os.getenv("TRANSCRIBE_TIMEOUT_SECONDS", "180"))
            deadline = time.monotonic() + timeout_seconds
            while time.monotonic() < deadline:
                job = transcribe.get_transcription_job(
                    TranscriptionJobName=job_name
                )["TranscriptionJob"]
                status = job["TranscriptionJobStatus"]
                if status == "COMPLETED":
                    transcript_uri = job["Transcript"]["TranscriptFileUri"]
                    with urllib.request.urlopen(transcript_uri, timeout=30) as response:
                        transcript_json = json.loads(response.read().decode("utf-8"))
                    items = transcript_json.get("results", {}).get("transcripts", [])
                    return items[0]["transcript"] if items else ""
                if status == "FAILED":
                    raise RuntimeError(
                        "Amazon Transcribe failed: "
                        + job.get("FailureReason", "no failure reason returned")
                    )
                time.sleep(2)

            raise TimeoutError(
                f"Amazon Transcribe job did not finish within {timeout_seconds} seconds."
            )
        finally:
            try:
                s3.delete_object(Bucket=bucket, Key=key)
            except Exception:
                pass


class VoiceSpeaker:
    def speak(self, text: str) -> None:
        """Synthesize speech with Amazon Polly and play it through the speaker."""
        import numpy as np
        import sounddevice as sd

        response = polly.synthesize_speech(
            Text=text,
            OutputFormat="pcm",
            SampleRate="16000",
            VoiceId=os.getenv("POLLY_VOICE_ID", "Joanna"),
            Engine=os.getenv("POLLY_ENGINE", "neural"),
        )
        audio_bytes = response["AudioStream"].read()
        audio = np.frombuffer(audio_bytes, dtype=np.int16)
        sd.play(audio, samplerate=16000)
        sd.wait()
