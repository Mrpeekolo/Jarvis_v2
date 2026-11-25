import json
from unittest.mock import patch

from fastapi.testclient import TestClient

from main import app, plugin_mgr


def _events(response_text):
    return [
        json.loads(line[6:])
        for line in response_text.splitlines()
        if line.startswith("data: ")
    ]


def test_explicit_app_request_launches_whitelisted_app():
    with patch("plugins.os_tools.subprocess.Popen") as popen:
        with TestClient(app) as client:
            response = client.post(
                "/api/chat",
                json={
                    "messages": [{"role": "user", "content": "Please open Notepad"}],
                    "mode": "SYSTEM",
                },
            )

    assert response.status_code == 200
    events = _events(response.text)
    assert any(event.get("type") == "token" and event.get("token") == "Opened Notepad." for event in events)
    popen.assert_called_once_with(["notepad.exe"])


def test_app_request_without_target_asks_which_app():
    with patch("plugins.os_tools.subprocess.Popen") as popen:
        with TestClient(app) as client:
            response = client.post(
                "/api/chat",
                json={
                    "messages": [{"role": "user", "content": "Can you open apps?"}],
                    "mode": "OS_AUTO",
                },
            )

    assert response.status_code == 200
    events = _events(response.text)
    assert any(
        event.get("type") == "token" and "Which app should I open?" in event.get("token", "")
        for event in events
    )
    popen.assert_not_called()


def test_app_launch_requires_system_mode():
    with patch("plugins.os_tools.subprocess.Popen") as popen:
        with TestClient(app) as client:
            response = client.post(
                "/api/chat",
                json={
                    "messages": [{"role": "user", "content": "Open Notepad"}],
                    "mode": "GENERAL",
                },
            )

    assert response.status_code == 200
    events = _events(response.text)
    assert any(
        event.get("type") == "token" and "Switch to SYSTEM mode" in event.get("token", "")
        for event in events
    )
    popen.assert_not_called()


def test_system_mode_alias_is_accepted_by_mode_endpoint():
    previous_mode = plugin_mgr.active_mode
    try:
        with TestClient(app) as client:
            response = client.post("/api/mode", json={"mode": "SYSTEM"})
        assert response.status_code == 200
        assert response.json()["active_mode"] == "OS_AUTO"
    finally:
        plugin_mgr.active_mode = previous_mode


def test_chat_switches_to_system_even_when_payload_has_old_mode():
    previous_mode = plugin_mgr.active_mode
    try:
        with TestClient(app) as client:
            response = client.post(
                "/api/chat",
                json={
                    "messages": [{"role": "user", "content": "Switch to system mode"}],
                    "mode": "GENERAL",
                },
            )
        assert response.status_code == 200
        events = _events(response.text)
        assert any(event.get("type") == "mode_info" and event.get("mode") == "OS_AUTO" for event in events)
        assert any(
            event.get("type") == "token" and event.get("token") == "Switched to SYSTEM mode."
            for event in events
        )
    finally:
        plugin_mgr.active_mode = previous_mode


if __name__ == "__main__":
    test_explicit_app_request_launches_whitelisted_app()
    test_app_request_without_target_asks_which_app()
    test_app_launch_requires_system_mode()
    test_system_mode_alias_is_accepted_by_mode_endpoint()
    test_chat_switches_to_system_even_when_payload_has_old_mode()
    print("All app launch tests passed.")
