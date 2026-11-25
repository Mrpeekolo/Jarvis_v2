import io
import sys
import tempfile
import types
import unittest
import wave
from pathlib import Path

from core.voice import VoiceError, transcribe_wav, validate_wav, voice_status


def make_wav(frames=b"\0\0" * 1600, channels=1, sample_width=2, sample_rate=16000):
    output = io.BytesIO()
    with wave.open(output, "wb") as wav:
        wav.setnchannels(channels)
        wav.setsampwidth(sample_width)
        wav.setframerate(sample_rate)
        wav.writeframes(frames)
    return output.getvalue()


class VoiceTests(unittest.TestCase):
    def test_validate_supported_wav(self):
        frames, duration = validate_wav(make_wav(), 5 * 1024 * 1024)
        self.assertEqual(len(frames), 3200)
        self.assertEqual(duration, 0.1)

    def test_validate_rejects_wrong_channel_and_rate(self):
        with self.assertRaises(VoiceError):
            validate_wav(make_wav(channels=2, frames=b"\0\0" * 3200), 5 * 1024 * 1024)
        with self.assertRaises(VoiceError):
            validate_wav(make_wav(sample_rate=8000), 5 * 1024 * 1024)

    def test_validate_rejects_invalid_and_oversized_audio(self):
        with self.assertRaises(VoiceError):
            validate_wav(b"not wav", 1024)
        with self.assertRaises(VoiceError):
            validate_wav(make_wav(), 1)

    def test_voice_status_missing_model(self):
        with tempfile.TemporaryDirectory() as directory:
            status = voice_status(Path(directory) / "missing")
            self.assertFalse(status["model_available"])

    def test_mocked_vosk_transcription(self):
        with tempfile.TemporaryDirectory() as directory:
            model_dir = Path(directory)
            (model_dir / "model").mkdir(exist_ok=True)

            vosk = types.ModuleType("vosk")

            class Model:
                def __init__(self, path):
                    self.path = path

            class KaldiRecognizer:
                def __init__(self, model, rate):
                    pass
                def SetWords(self, enabled):
                    pass
                def AcceptWaveform(self, frames):
                    return True
                def FinalResult(self):
                    return '{"text": "hello jarvis"}'

            vosk.Model = Model
            vosk.KaldiRecognizer = KaldiRecognizer
            sys.modules["vosk"] = vosk
            try:
                result = transcribe_wav(make_wav(), model_dir, 5 * 1024 * 1024)
            finally:
                sys.modules.pop("vosk", None)

            self.assertEqual(result["transcript"], "hello jarvis")


if __name__ == "__main__":
    unittest.main()
