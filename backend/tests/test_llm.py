import dataclasses
import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

from app import llm


class FakeOllama(BaseHTTPRequestHandler):
    def log_message(self, *a):  # silence
        pass

    def _send(self, obj):
        body = json.dumps(obj).encode()
        self.send_response(200)
        self.send_header("content-type", "application/json")
        self.send_header("content-length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        self._send({"models": []})

    def do_POST(self):
        n = int(self.headers["content-length"])
        req = json.loads(self.rfile.read(n))
        assert req["model"] == "gpt-oss:20b" and req["messages"][0]["role"] == "system"
        self._send({"message": {"content": "  Grounded summary from the local model.  "}})


@pytest.fixture()
def fake_ollama(monkeypatch):
    srv = HTTPServer(("127.0.0.1", 0), FakeOllama)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    cfg = dataclasses.replace(llm.settings, llm_mode="auto", ollama_url=f"http://127.0.0.1:{srv.server_port}")
    monkeypatch.setattr(llm, "settings", cfg)
    monkeypatch.setattr(llm, "_health", (0.0, False))
    yield cfg
    srv.shutdown()


async def test_uses_ollama_when_reachable(fake_ollama):
    text, backend = await llm.generate("sys", "prompt", "fallback")
    assert text == "Grounded summary from the local model." and backend == "ollama:gpt-oss:20b"


async def test_falls_back_when_unreachable(monkeypatch):
    cfg = dataclasses.replace(llm.settings, llm_mode="auto", ollama_url="http://127.0.0.1:9")
    monkeypatch.setattr(llm, "settings", cfg)
    monkeypatch.setattr(llm, "_health", (0.0, False))
    assert await llm.generate("s", "p", "fallback") == ("fallback", "offline-template")


async def test_strict_mode_raises_when_unreachable(monkeypatch):
    cfg = dataclasses.replace(llm.settings, llm_mode="ollama", ollama_url="http://127.0.0.1:9")
    monkeypatch.setattr(llm, "settings", cfg)
    monkeypatch.setattr(llm, "_health", (0.0, False))
    with pytest.raises(RuntimeError):
        await llm.generate("s", "p", "fallback")
