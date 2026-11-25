# JARVIS — AI Model Handoff Document

> **Purpose:** This file contains everything another AI model needs to understand, run, and continue developing this project. Read it top-to-bottom before making changes.
>
> **Repository state:** Last verified against the current checkout on 2026-11-25.

---

## 1. Project Overview

**JARVIS** is a privacy-first local AI assistant built on Python, FastAPI, and Ollama. Its server and Ollama API bind to localhost. The UI is a browser-based SPA served by FastAPI at `http://127.0.0.1:8765`.

### Core Principles
- **Privacy-first** — server traffic bound to localhost and no application telemetry
- **Local-first** — Ollama for inference, no cloud APIs
- **Discrete by default** — tool calls and internal JSON hidden from chat; shown only on explicit request
- **Modal architecture** — tools scoped to modes (GENERAL, DEV, VISION, OS_AUTO, GAMING)
- **Hot-reloadable plugins** — drop a `.py` file in `plugins/`, hit Reload

> [!CAUTION]
> The current UI loads Monaco Editor assets from a CDN. Optional web search sends user queries to Brave Search when configured; Ollama inference remains local.

### Hardware Target
- **CPU:** Intel i7-4790 (4C/8T, Haswell, AVX2)
- **RAM:** 8 GB total
- **GPU:** AMD Radeon R5 240 + Intel HD 4600 — **NO CUDA, CPU-only inference**
- **OS:** Windows 10/11
- **Python:** 3.13 (Microsoft Store install)

> [!IMPORTANT]
> This hardware is very constrained. Prefer the 1.5B model; current inference is set to `num_ctx` 1024 and `num_predict` 384 to reduce memory use. No Docker (eats 2-4GB RAM). No Electron (200MB overhead). The web UI is served directly by FastAPI.

---

## 2. How to Run

### Quick Start
```batch
cd /d "C:\Users\Lil spooky\test\jarvis\jarvis v1\Jarvis v1"
start_jarvis.bat
```
Or manually:
```bash
cd "C:\Users\Lil spooky\test\jarvis\jarvis v1\Jarvis v1"
python main.py
```
Then open `http://127.0.0.1:8765` in any browser.

`start_jarvis.bat` changes to the directory containing the batch file, so it works regardless of the caller's current directory.

To launch the dashboard in a native desktop window, install `requirements.txt` and run `start_jarvis_desktop.bat`. This uses pywebview and requires the Microsoft Edge WebView2 Runtime. It reuses an existing JARVIS server on the configured localhost port or starts and stops its own server with the window. Python and Ollama remain separate prerequisites.

### Prerequisites
1. **Python 3.13+** with pip
2. **Ollama** running on `http://127.0.0.1:11434` with at least one model pulled
3. Python packages from the repository manifest:
   ```
   python -m pip install -r requirements.txt
   ```
4. For the desktop window, install the Microsoft Edge WebView2 Runtime.
5. Optional web search requires a Brave Search API key in `BRAVE_SEARCH_API_KEY`. Set it in the environment before launching JARVIS; the key is never stored in the repository.

### Installed Ollama Models
- `qwen2.5-coder:1.5b` (986 MB) — primary default, best speed/quality ratio
- `qwen35-fast:latest` (3.3 GB) — user's custom model
- `qwen3.5:4b` (3.3 GB)

Model availability is machine-specific. The server queries Ollama through `GET /api/tags` and falls back to the first available model or `qwen35-fast:latest` if Ollama is unreachable.

---

## 3. File Map

```
jarvis/
├── main.py                  # FastAPI server — all API routes, SSE chat streaming
├── start_jarvis.bat         # One-click Windows launcher
├── desktop.py               # pywebview desktop-window entry point
├── start_jarvis_desktop.bat # Windows launcher for the native desktop window
├── requirements.txt         # Python runtime dependencies
├── HANDOFF.md               # This file
├── README.md                # Brief project readme
├── test_core.py             # Unit tests: AST sandbox, plugin discovery
├── test_web_search.py       # Web search behavior tests; no API key or network needed
├── test_server.py           # Integration tests: server startup, API
│
├── core/
│   ├── config.py            # Pydantic Config: HOST, PORT, OLLAMA_URL, PREFERRED_MODELS
│   ├── llm.py               # OllamaEngine: model selection, SSE stream_chat()
│   ├── plugins.py           # BasePlugin ABC, PluginManager, modal tool scoping
│   └── sandbox.py           # AST security scanner + isolated subprocess executor
│
├── plugins/
│   ├── sys_info.py          # get_system_info (GENERAL)
│   ├── web_search.py        # web_search (GENERAL; optional Brave API key)
│   ├── file_manager.py      # list_workspace_files (DEV)
│   ├── dev_tools.py         # get_git_status, search_workspace_code (DEV)
│   ├── os_tools.py          # inspect_windows, control_media, launch_application (OS_AUTO)
│   └── vision_tools.py      # take_screenshot (VISION) — mss→PIL fallback chain
│
└── static/
    ├── index.html           # Full SPA: chat, Monaco editor, screenshots, running apps
    └── screenshots/         # Auto-created dir for captured PNGs
```

---

## 4. Architecture

### Modal Tool System
Tools are scoped by mode. When mode is `DEV`, the LLM sees `GENERAL` + `DEV` tools only.

| Mode     | Tools Available                                           |
|----------|-----------------------------------------------------------|
| GENERAL  | `get_system_info`, `web_search`                           |
| DEV      | `list_workspace_files`, `get_git_status`, `search_workspace_code` |
| VISION   | `take_screenshot`                                         |
| OS_AUTO  | `inspect_windows`, `control_media`, `launch_application`  |
| GAMING   | *(empty — future phase)*                                  |

The plugin manager includes `GENERAL` plugins in every specific mode. `web_search` requires the `BRAVE_SEARCH_API_KEY` environment variable; without it, the tool returns a setup message. Search queries are sent to Brave Search. DEV, VISION, and OS_AUTO also work only when the corresponding mode is active; setting `GAMING` currently exposes no GAMING plugins and therefore also exposes no mode-specific tools.

### Plugin Contract
Every plugin extends `BasePlugin` from `core/plugins.py`:

```python
from core.plugins import BasePlugin, PluginMetadata, ParamSpec

class MyPlugin(BasePlugin):
    @property
    def metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name="my_tool_name",           # unique tool name
            description="What it does",     # shown to LLM
            version="1.0.0",
            mode="DEV",                     # GENERAL|DEV|VISION|OS_AUTO|GAMING
            parameters=[
                ParamSpec(name="query", type="string", description="Search term", required=True)
            ]
        )

    async def execute(self, query: str, **kwargs) -> dict:
        # Do work, return a dict
        return {"result": "..."}
```

Drop the file in `plugins/`, click Reload in the UI (or `POST /api/plugins/reload`). It's auto-discovered.

### AST Sandbox
`core/sandbox.py` scans code via Python's `ast` module before execution:
- **Blocked imports:** `os`, `sys`, `subprocess`, `shutil`, `socket`, `ctypes`, `pty`, `multiprocessing`, `pickle`, `importlib`, `webbrowser`
- **Blocked calls:** `eval()`, `exec()`, `open()`, `compile()`, `__import__()`, `globals()`, `locals()`
- Execution runs in an isolated subprocess with `-I` flag and stripped environment

### LLM Integration
`core/llm.py` wraps the Ollama `/api/chat` endpoint with SSE streaming:
- Auto-selects the best available model from `PREFERRED_MODELS` list
- Passes tool schemas via Ollama's `tools` parameter
- `temperature: 0.2`, `num_ctx: 1024`, `num_predict: 384`
- Keeps the selected model loaded for five minutes after the latest request
- 180-second HTTP timeout for slow CPU inference

### Small-Model Tool-Call Workaround
`qwen2.5-coder:1.5b` does **NOT** reliably use Ollama's native `tools` wire format. Instead it outputs:
````
```json
{"name": "tool_name", "arguments": {"key": "value"}}
```
````
The server has a regex fallback parser (`_extract_json_tool_calls()` in `main.py`) that catches these blocks and dispatches them. Additional mitigations:
- **Dedup set** (`executed_signatures`): prevents the model from re-triggering the same tool call in a loop
- **Tools only on first pass**: second LLM iteration gets no tools, forcing a natural summary
- **JSON buffering**: leading `{` or ` ``` ` tokens are buffered and suppressed from the chat stream so users don't see raw tool JSON

Native Ollama `tool_calls` and fenced/raw JSON fallback calls share the same dispatch loop.

### Discrete Operation
- `httpx` and `uvicorn.access` loggers are suppressed to WARNING
- Internal activity is logged to an in-memory `deque(maxlen=100)` accessible via `GET /api/logs`
- Chat stream hides tool execution by default; user toggles "Activity: Visible" button or asks "show me what you did"
- When user asks about logs/activity, the frontend auto-fetches `/api/logs` and renders the last 8 entries in the tool-trace div

---

## 5. API Reference

All endpoints are on `http://127.0.0.1:8765`.

| Method | Endpoint                | Description                                      |
|--------|-------------------------|--------------------------------------------------|
| GET    | `/`                     | Serves `static/index.html`                       |
| GET    | `/api/status`           | System status: model, mode, plugins, modes_map   |
| GET    | `/api/logs`             | Internal activity log (last 100 entries)          |
| GET    | `/api/apps`             | Running desktop apps via `inspect_windows` plugin |
| GET    | `/api/screenshots`      | List of recent screenshot URLs (last 10)          |
| POST   | `/api/chat`             | SSE streaming chat with tool dispatch             |
| POST   | `/api/mode`             | Switch active mode `{"mode": "DEV"}`              |
| POST   | `/api/sandbox/run`      | Execute sandboxed Python `{"code": "...", "timeout_sec": 5}` |
| POST   | `/api/plugins/reload`   | Hot-reload all plugins from `plugins/` dir        |
| POST   | `/api/screenshot`       | Capture screen via vision plugin                  |
| POST   | `/api/screenshot/upload`| Upload base64 screenshot `{"image_base64": "..."}` |
| GET    | `/static/*`             | Static file serving (index.html, screenshots)     |

The server currently allows CORS for all origins, but the application is intended to run behind FastAPI on `127.0.0.1`. `/api/status` is the best endpoint for checking which Ollama model and plugins are currently active.

### Chat SSE Event Types
The `POST /api/chat` endpoint returns `text/event-stream` with these event types:

```
data: {"type": "mode_info", "mode": "DEV"}
data: {"type": "token", "token": "Hello"}
data: {"type": "tool_start", "tool": "get_git_status", "args": {}}
data: {"type": "tool_result", "tool": "get_git_status", "result": {...}}
data: {"type": "error", "content": "Something went wrong"}
data: {"type": "done"}
```

---

## 6. Frontend (static/index.html)

Single-page app using Tailwind CSS (CDN) and Monaco Editor (CDN).

### Layout
- **Left panel:** Chat stream with SSE streaming, user input, mode indicator
- **Right panel:** Tabbed workspace with 3 tabs:
  - **CODE SANDBOX** — Monaco Python editor + execution console (AST guarded)
  - **SCREENSHOTS** — Capture button, preview image, thumbnail gallery
  - **RUNNING APPS** — Live process list with refresh, active window label, app count

### Key UI Features
- **Mode selector** in header — click to switch modes, updates available tools
- **Model selector** dropdown — populated from Ollama's available models
- **Activity toggle** — "Activity: Hidden/Visible" shows/hides tool trace in chat bubbles
- **Tab switching** — auto-refreshes data when switching to Screenshots or Running Apps tabs
- **Discrete tool handling** — if user asks "show me what you did", frontend auto-fetches `/api/logs`

---

## 7. Known Limitations & Gotchas

### Screenshot Capture in Headless Sessions
Both `mss` and `PIL.ImageGrab` fail with "BitBlt: Access is denied" when JARVIS runs in a headless or sandboxed session (like from an IDE terminal or remote agent). **Fix:** Launch JARVIS from an interactive desktop session via `start_jarvis.bat`. The plugin has a graceful fallback chain and returns an informative error.

The screenshot plugin writes timestamped PNG files and `latest.png` under `static/screenshots/`. `/api/screenshots` returns the ten most recent `screen_*.png` files.

### win32gui.EnumWindows
Window enumeration must be resilient to session-context failures. The `inspect_windows` plugin obtains process output with `tasklist /FI "STATUS eq RUNNING" /FO CSV` and also attempts foreground-window lookup through `win32gui`.

### Workspace and Git Roots
The DEV plugins currently use a hard-coded workspace root: `C:\Users\Lil spooky\test`. This is the parent directory in the current environment and therefore includes the repository at `test\jarvis\jarvis v1\Jarvis v1`.

If the project is moved or cloned elsewhere, update `WORKSPACE_ROOT` in `plugins/dev_tools.py` and `plugins/file_manager.py`. A future implementation should derive this path from `BASE_DIR` or explicit configuration instead of keeping machine-specific absolute paths.

### Small Model Tool Calling
`qwen2.5-coder:1.5b` outputs tool calls as markdown JSON blocks instead of using Ollama's native tool format. The server's regex parser handles this, but be aware:
- The model may try to call the same tool 2-3 times — the dedup set prevents this
- Tools are only provided on the first LLM iteration to force summarization on the second
- Very complex multi-tool chains may not work reliably with 1.5B models

### FastAPI Deprecation Warning
`@app.on_event("startup")` shows a deprecation warning. Cosmetic only. Can be migrated to the lifespan context manager pattern if desired.

### PowerShell Dollar Sign Escaping
When running commands via PowerShell programmatically, `$variable` references get eaten. Use Python scripts or avoid `$` in PowerShell one-liners when automating.

---

## 8. Implementation Status and Future Roadmap

### Implemented
- FastAPI server and browser UI
- Ollama model discovery and streaming chat
- Native and fallback tool calling
- Modal plugin scoping
- Plugin hot reload
- Optional Brave Search integration (requires local API key)
- Chat request history capped at ten messages and a Stop control for long-running generations
- AST-guarded Python sandbox
- Screenshot capture and upload
- Windows process inspection
- Media control and a small application whitelist

### Not Implemented
- **Offline voice engine:** No Vosk or pyttsx3 integration is exposed in the UI or server.
- **Persistent memory:** No SQLite, FTS5, session summaries, or recall system is implemented.
- **Gaming plugins:** The GAMING mode exists, but no GAMING-scoped plugin is registered.
- **Emergency kill-switch:** No global hotkey or stop mechanism is implemented.

### Future Work
- **Voice:** Add offline STT/TTS after stabilizing the core chat loop.
- **Memory:** Use a local SQLite/FTS5 store with explicit recall controls.
- **Gaming:** Add only after the two-tier read-versus-mutate safety model is implemented.
- **Kill-switch:** Add a global hotkey and central action cancellation, especially before enabling mutating plugins.

---

## 9. Dependencies

```
# Core
fastapi
uvicorn
httpx
pydantic

# Sandbox/Vision
mss
Pillow

# Windows OS Tools
pywin32

# Desktop Window
pywebview

# Already installed for future phases
vosk
pyttsx3
```

**Python version:** 3.13+ (Microsoft Store install)
**Ollama:** Must be running on port 11434

---

## 10. Testing

```bash
# Run from the repository root
python test_core.py

# Optional pytest discovery
python -m pytest test_core.py test_server.py -v
```

### What the tests cover:
- `test_core.py`: AST blocks `import os`, safe code executes correctly, plugin discovery loads all plugins
- `test_server.py`: Attempts a server startup, `/api/status` response, and UI serving

> [!IMPORTANT]
> `test_server.py` contains a machine-specific server working directory (`C:/Users/Lil spooky/test/jarvis`) that is inconsistent with this repository location. Update it to use the repository directory (for example, `Path(__file__).resolve().parent`) before relying on pytest or this script as an integration test.

There is no automated test currently covering chat streaming, tool dispatch, media controls, screenshot capture, or the frontend JavaScript.

---

## 11. Quick Reference for Continuing Development

### Adding a new plugin
1. Create `plugins/my_plugin.py`
2. Define a class extending `BasePlugin` with `metadata` property and `execute()` method
3. Set `mode` in metadata to scope it (GENERAL/DEV/VISION/OS_AUTO/GAMING)
4. Click Reload in UI or `POST /api/plugins/reload`

### Adding a new API endpoint
1. Add route in `main.py` using FastAPI decorators
2. For discrete logging: call `log_activity("event_name", detail)` inside the handler
3. Restart the server (kill and re-run `python main.py`)

### Adding a new right-panel tab
1. Add a tab button in the `right-tab-btn` row with `data-tab="newtab"`
2. Add a `tab-action-newtab` div for the action bar
3. Add a `panel-newtab` div for the content
4. The `switchTab()` JS function handles show/hide automatically
5. Add auto-load logic in `switchTab()` if the tab needs data fetching

### Changing the LLM model
- Pull a new model: `ollama pull model-name`
- Add it to `PREFERRED_MODELS` in `core/config.py`
- Or select it from the dropdown in the UI

### Before changing the code
1. Check Ollama with `ollama list`.
2. Run `python test_core.py`.
3. Start JARVIS with `python main.py` or `start_jarvis.bat`.
4. Verify `http://127.0.0.1:8765/api/status`.
5. Test the affected mode and plugin through the UI.

### Priorities for the next contributor
1. Replace hard-coded workspace paths with repository/config-derived paths.
2. Add a dependency manifest and test setup.
3. Vendor frontend dependencies to fully eliminate external network requests.
4. Fix `test_server.py` so it uses the current repository and always cleans up the server process.
5. Add streamed-chat/tool-dispatch tests and plugin-specific tests.
6. Review sandbox boundaries before using the editor for untrusted code.

---

## 12. Maintenance Notes

- FastAPI currently uses `@app.on_event("startup")`, which is retained for compatibility but may emit deprecation warnings in newer FastAPI releases.
- The sandbox is AST-based, not a security boundary for hostile code. Execute untrusted code only after completing a review of subprocess isolation and operating-system process permissions.
- The UI's Monaco CDN reference requires internet access on first load unless browser cache satisfies it.
- Brave Search receives the user's search query when `web_search` is used. Returned text is untrusted reference material; source links are shown in the UI.
- The `win32*` and `pywin32` dependencies are Windows-specific. The server can import plugins only if `win32gui`, `win32con`, and `win32api` are available.
- Do not expose JARVIS publicly through port forwarding or disable localhost binding without separate authentication and authorization design.

*Generated for AI model handoff. Last updated: 2026-11-25.*
