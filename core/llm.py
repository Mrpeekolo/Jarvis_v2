import json
import logging
from typing import AsyncGenerator, Dict, Any, List, Optional
import httpx
from core.config import cfg

logger = logging.getLogger("jarvis.llm")

class OllamaEngine:
    def __init__(self, base_url: str = cfg.OLLAMA_URL):
        self.base_url = base_url.rstrip("/")

    async def get_model_status(self) -> tuple[List[str], bool]:
        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                res = await client.get(f"{self.base_url}/api/tags")
                if res.status_code == 200:
                    data = res.json()
                    return [m["name"] for m in data.get("models", [])], True
                logger.warning("Ollama tags request returned HTTP %s", res.status_code)
        except Exception as e:
            logger.warning(f"Failed to query Ollama tags: {e}")
        return [], False

    async def get_available_models(self) -> List[str]:
        available, _ = await self.get_model_status()
        return available

    async def select_best_model(self, available: Optional[List[str]] = None) -> str:
        if available is None:
            available = await self.get_available_models()
        for preferred in cfg.PREFERRED_MODELS:
            # Check exact match or prefix match (e.g. qwen2.5-coder:1.5b vs qwen2.5-coder:1.5b-instruct)
            for m in available:
                if preferred in m or m in preferred:
                    return m
        if available:
            return available[0]
        return "qwen35-fast:latest"

    async def stream_chat(
        self,
        messages: List[Dict[str, Any]],
        model: Optional[str] = None,
        tools: Optional[List[Dict[str, Any]]] = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        selected_model = model or await self.select_best_model()

        payload = {
            "model": selected_model,
            "messages": messages,
            "stream": True,
            "options": {
                "temperature": 0.2,
                "num_ctx": cfg.DEFAULT_NUM_CTX,
                "num_predict": 384
            },
            "keep_alive": "5m"
        }
        if tools:
            payload["tools"] = tools

        url = f"{self.base_url}/api/chat"
        async with httpx.AsyncClient(timeout=180.0) as client:
            try:
                async with client.stream("POST", url, json=payload) as response:
                    if response.status_code != 200:
                        err_text = await response.aread()
                        yield {"type": "error", "content": f"Ollama HTTP {response.status_code}: {err_text.decode('utf-8', errors='replace')}"}
                        return

                    async for line in response.aiter_lines():
                        if not line.strip():
                            continue
                        try:
                            chunk = json.loads(line)
                            yield chunk
                        except json.JSONDecodeError:
                            continue
            except Exception as e:
                yield {"type": "error", "content": f"Connection to Ollama failed: {str(e)}"}

llm_engine = OllamaEngine()
