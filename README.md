# JARVIS // Discrete Local AI Assistant

A discrete, privacy-first, local assistant engine engineered specifically for resource-conscious hardware (Intel Core i7-4790 AVX2 / 8 GB RAM / CPU-only inference).

---

## Quick Start

### 1. Launch JARVIS
Double-click `start_jarvis.bat` or run in your terminal:
```bash
cd "C:\Users\Lil spooky\test\jarvis\jarvis v1\Jarvis v1"
python main.py
```
This automatically boots the FastAPI daemon on `127.0.0.1:8765` and opens your browser directly to the dashboard.

---

## Key Features

1. **Local-First & No Application Telemetry:**
   - Bound strictly to `127.0.0.1`.
   - Ollama and JARVIS application traffic stay local.
   - The browser UI currently loads Tailwind CSS and Monaco Editor from CDNs, so first-load asset requests are external unless the assets are cached or vendored locally.
2. **AST-Guarded Code Surface:**
   - Embedded **Monaco Editor** with live syntax highlighting.
   - Any code executed via the UI runs in an isolated Python subprocess inspected by an **Abstract Syntax Tree (AST) safety scanner**.
   - Dangerous imports (`os`, `sys`, `subprocess`, `socket`, `ctypes`, etc.) and unsafe calls (`eval`, `exec`, `open`) are blocked deterministically.
3. **Hot-Reloadable Plugin Engine:**
   - Add new tool capabilities without restarting the server!
   - Simply drop any `.py` file into `jarvis/plugins/` implementing `BasePlugin`.
   - Click **Reload Plugins** in the top bar to register the new tool instantly.
4. **Autonomous Streaming & Tool Calling:**
   - Real-time Server-Sent Events (SSE) token streaming.
   - Native tool execution loop: the assistant can call local tools (e.g., inspect hardware, list files), receive the output, and synthesize the final answer.
   - Small local models may emit fenced JSON tool calls; the server includes a fallback parser and deduplicates repeated calls.

---

## Prerequisites

- Windows 10 or 11
- Python 3.13+
- Ollama running on `127.0.0.1:11434`
- Required Python packages: `fastapi`, `uvicorn`, `httpx`, `pydantic`, `mss`, `Pillow`, and `pywin32`

The project currently has no dependency manifest. Install the packages explicitly or add `requirements.txt`/`pyproject.toml` before preparing a reproducible environment.

---

## Directory Structure

```text
jarvis/
├── main.py              # FastAPI server & SSE streaming router
├── start_jarvis.bat     # One-click desktop launcher
├── test_core.py         # Automated test suite (Sandbox + Plugins)
├── core/
│   ├── config.py        # Environment & Ollama settings
│   ├── sandbox.py       # AST scanner & isolated subprocess runner
│   ├── plugins.py       # BasePlugin contract & dynamic loader
│   └── llm.py           # Ollama client with fallback model detection
├── plugins/
│   ├── sys_info.py      # Host CPU/OS hardware info plugin
│   └── file_manager.py  # Sandboxed workspace file listing plugin
└── static/
    └── index.html       # Split-pane UI (Monaco Editor + Live Stream)
```

---

## Adding Custom Plugins

Create a new file in `jarvis/plugins/my_tool.py`:

```python
from core.plugins import BasePlugin, PluginMetadata, ParamSpec

class MyTool(BasePlugin):
    @property
    def metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name="greet_user",
            description="Greets a user by name.",
            parameters=[
                ParamSpec(name="user_name", type="string", description="The name of the user")
            ]
        )

    async def execute(self, user_name: str, **kwargs):
        return {"greeting": f"Hello, {user_name}! JARVIS is ready."}
```
Click **Reload Plugins** in the top bar, and your new tool is immediately available to the LLM!
