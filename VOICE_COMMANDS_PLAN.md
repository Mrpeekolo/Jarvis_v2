# JARVIS Voice Commands Plan

## Goal

Add push-to-talk voice commands to JARVIS with fully offline transcription and optional spoken replies. Captured audio must remain on the local machine and must not be sent to a cloud speech-recognition service.

## Confirmed decisions

- Use the small Vosk English (US) model.
- Allow a one-time model download during setup; keep model files outside tracked source files.
- Show recognized speech in the chat composer for review. Do not send it automatically.
- Spoken replies are wanted, but only use a browser/OS voice marked as local. Keep text visible and do not speak if no local voice is available.
- Vosk is the recognition engine, rather than browser cloud speech recognition.

## Implementation outline

1. Add Vosk and the existing runtime dependencies to a `requirements.txt` manifest.
2. Add a one-time model setup script for the small English (US) Vosk model. Store it in an ignored local `models/` directory; do not commit model binaries.
3. Add a local Vosk transcription module and API endpoint. Validate bounded mono 16 kHz PCM WAV input, run blocking recognition outside the async event loop, and return clear errors when the package or model is unavailable.
4. Add a push-to-talk microphone control. Capture audio in the browser, convert it locally to mono 16 kHz PCM WAV, and send it only to JARVIS on localhost.
5. Place the transcript in the composer for review before sending. A voice transcript must not launch an app or execute another command without the user's explicit send action.
6. Add a spoken-reply toggle that uses only local speech-synthesis voices. If no local voice is available, retain the text response without speaking.
7. Add focused tests for audio validation, Vosk result handling, endpoint failures, transcript review behavior, and spoken-reply fallback. Update the setup documentation with model installation, microphone permission, and privacy details.

## Likely components

- `core/voice.py` and `core/config.py` for local model loading and configuration
- `main.py` for the transcription endpoint and voice availability status
- `static/index.html` for microphone controls, transcript review, and local speech output
- `requirements.txt`, a model setup script, and `.gitignore` for reproducible local setup
- Voice-focused tests and `README.md` setup/privacy documentation

## Validation

- Run focused tests for supported WAV format, invalid or oversized input, missing model/dependency, and successful mocked transcription.
- Verify that the browser's microphone workflow submits only to the local JARVIS server and leaves the transcript editable before sending.
- Verify spoken output uses only local voices and gracefully falls back to text when none are installed.
