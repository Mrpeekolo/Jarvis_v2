import threading
import time
from urllib.error import URLError
from urllib.request import urlopen

import uvicorn
import webview

from core.config import cfg
from main import app


APP_URL = f"http://{cfg.HOST}:{cfg.PORT}"
WINDOW_TITLE = "JARVIS // Local Intelligence"
STARTUP_TIMEOUT_SEC = 20


def _is_jarvis_ready() -> bool:
    try:
        with urlopen(APP_URL, timeout=0.75) as response:
            page = response.read(512).decode("utf-8", errors="replace")
    except URLError:
        return False
    return response.status == 200 and f"<title>{WINDOW_TITLE}</title>" in page


def _start_server() -> tuple[uvicorn.Server, threading.Thread]:
    server = uvicorn.Server(
        uvicorn.Config(
            app,
            host=cfg.HOST,
            port=cfg.PORT,
            log_level="warning",
            access_log=False,
        )
    )
    thread = threading.Thread(target=server.run, name="jarvis-api", daemon=True)
    thread.start()
    return server, thread


def _wait_for_server(server: uvicorn.Server, thread: threading.Thread) -> None:
    deadline = time.monotonic() + STARTUP_TIMEOUT_SEC
    while time.monotonic() < deadline:
        if _is_jarvis_ready():
            return
        if not thread.is_alive():
            raise RuntimeError(f"JARVIS server stopped during startup on {APP_URL}")
        time.sleep(0.25)
    server.should_exit = True
    raise TimeoutError(f"JARVIS server did not become ready at {APP_URL}")


def main() -> None:
    owned_server = None
    server_thread = None

    if not _is_jarvis_ready():
        owned_server, server_thread = _start_server()
        _wait_for_server(owned_server, server_thread)

    try:
        webview.create_window(
            WINDOW_TITLE,
            APP_URL,
            width=1440,
            height=900,
            min_size=(960, 640),
        )
        webview.start()
    finally:
        if owned_server is not None and server_thread is not None:
            owned_server.should_exit = True
            server_thread.join(timeout=10)


if __name__ == "__main__":
    main()
