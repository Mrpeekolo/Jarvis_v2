import io
import json
import wave
from pathlib import Path
from typing import Optional


class VoiceError(Exception):
    pass


def validate_wav(audio: bytes, max_bytes: int) -> tuple[bytes, float]:
    if not audio:
        raise VoiceError("No audio received")
    if len(audio) > max_bytes:
        raise VoiceError(f"Audio exceeds the {max_bytes // (1024 * 1024)} MB limit")

    try:
        with wave.open(io.BytesIO(audio), "rb") as wav:
            channels = wav.getnchannels()
            sample_width = wav.getsampwidth()
            sample_rate = wav.getframerate()
            frame_count = wav.getnframes()
            frames = wav.readframes(frame_count)
    except (wave.Error, EOFError) as exc:
        raise VoiceError("Invalid WAV audio") from exc

    if channels != 1:
        raise VoiceError("WAV audio must be mono")
    if sample_width != 2:
        raise VoiceError("WAV audio must use 16-bit PCM")
    if sample_rate != 16000:
        raise VoiceError("WAV audio must use a 16 kHz sample rate")
    if frame_count <= 0:
        raise VoiceError("WAV audio is empty")

    duration_sec = frame_count / sample_rate
    if duration_sec > 30:
        raise VoiceError("Recording exceeds the 30 second limit")
    return frames, duration_sec


def voice_status(model_dir: Path) -> dict:
    try:
        import vosk
        dependency_available = True
    except ImportError:
        dependency_available = False

    model_available = model_dir.is_dir() and any(model_dir.iterdir())
    return {
        "available": dependency_available and model_available,
        "dependency_available": dependency_available,
        "model_available": model_available,
        "model_dir": str(model_dir),
    }


def transcribe_wav(audio: bytes, model_dir: Path, max_bytes: int) -> dict:
    frames, duration_sec = validate_wav(audio, max_bytes)
    status = voice_status(model_dir)
    if not status["dependency_available"]:
        raise VoiceError("Vosk is not installed")
    if not status["model_available"]:
        raise VoiceError("Vosk model is missing")

    try:
        from vosk import KaldiRecognizer, Model

        model = Model(str(model_dir))
        recognizer = KaldiRecognizer(model, 16000)
        recognizer.SetWords(False)
        recognizer.AcceptWaveform(frames)
        result = json.loads(recognizer.FinalResult())
    except Exception as exc:
        raise VoiceError("Offline transcription failed") from exc

    transcript = str(result.get("text", "")).strip()
    return {"transcript": transcript, "duration_sec": round(duration_sec, 2)}
