from pathlib import Path
import shutil
import urllib.request
import zipfile


MODEL_NAME = "vosk-model-small-en-us-0.15"
MODEL_URL = f"https://alphacephei.com/vosk/models/{MODEL_NAME}.zip"
BASE_DIR = Path(__file__).resolve().parent
MODELS_DIR = BASE_DIR / "models"
MODEL_DIR = MODELS_DIR / MODEL_NAME
ZIP_PATH = MODELS_DIR / f"{MODEL_NAME}.zip"


def main() -> int:
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    if MODEL_DIR.is_dir() and any(MODEL_DIR.iterdir()):
        print(f"Voice model already installed: {MODEL_DIR}")
        return 0

    print("Downloading the small English (US) Vosk model...")
    with urllib.request.urlopen(MODEL_URL) as response, ZIP_PATH.open("wb") as output:
        shutil.copyfileobj(response, output)

    print("Extracting voice model...")
    with zipfile.ZipFile(ZIP_PATH, "r") as archive:
        archive.extractall(MODELS_DIR)
    ZIP_PATH.unlink(missing_ok=True)

    if not MODEL_DIR.is_dir():
        raise RuntimeError("The downloaded model did not unpack to the expected directory")
    print(f"Voice model installed at {MODEL_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
