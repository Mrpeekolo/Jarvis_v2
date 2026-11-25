import os
from pydantic import BaseModel

class Config(BaseModel):
    HOST: str = "127.0.0.1"
    PORT: int = 8765
    OLLAMA_URL: str = "http://127.0.0.1:11434"
    VOICE_MODEL_DIR: str = "models/vosk-model-small-en-us-0.15"
    VOICE_MAX_WAV_BYTES: int = 5 * 1024 * 1024
    PREFERRED_MODELS: list[str] = [
        "qwen2.5-coder:1.5b",
        "qwen35-fast:latest",
        "qwen3.5:4b"
    ]
    DEFAULT_NUM_CTX: int = 1024  # Reduce memory use on low-RAM CPU-only systems
    SANDBOX_TIMEOUT_SEC: int = 5

cfg = Config()
