import asyncio
import json
import threading
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace

import httpx
import pytest
from fastapi.testclient import TestClient

from backend.config import Settings, settings_file
from backend.main import create_app
from backend.provider import DeepSeek


@pytest.fixture
def config(tmp_path):
    return Settings(str(tmp_path / "mochi.sqlite3"), "", "https://api.deepseek.com", "deepseek-flash", ("http://127.0.0.1:8765",))


def payload(**kwargs):
    return {"api_base": "https://api.deepseek.com", "model": "deepseek-flash", **kwargs}


def test_save_mask_keep_clear_and_restore_over_environment(config):
    initial = replace(config, api_key="synthetic-old-key")
    with TestClient(create_app(initial)) as client:
        assert client.get("/api/settings").json() == {
            "api_base": initial.api_base, "model": initial.model, "has_api_key": True, "mode": "live"
        }
        for supplied in ({}, {"api_key": ""}, {"api_key": None}):
            response = client.put("/api/settings", json=payload(**supplied))
            assert response.status_code == 200 and "synthetic-old-key" not in response.text
            assert client.app.state.settings.api_key == "synthetic-old-key"
        assert client.put("/api/settings", json=payload(clear_api_key=True)).json()["mode"] == "demo"
        assert client.get("/api/health").json()["mode"] == "demo"
    data = json.loads(settings_file(initial).read_text(encoding="utf-8"))
    assert data["api_key"] == ""
    with TestClient(create_app(initial)) as restarted:
        assert restarted.get("/api/settings").json()["has_api_key"] is False
        assert restarted.get("/api/health").json()["mode"] == "demo"


def test_new_key_and_custom_file_persist_without_returning_key(config, tmp_path):
    settings = replace(config, settings_path=str(tmp_path / "private" / "custom-settings.json"))
    with TestClient(create_app(settings)) as client:
        response = client.put("/api/settings", json=payload(api_base="https://provider.example/v1/", model="qwen2.5:7b", api_key="synthetic-new-key"))
        assert response.status_code == 200
        assert response.json()["api_base"] == "https://provider.example/v1"
        assert "synthetic-new-key" not in response.text
    assert settings_file(settings).exists()
    assert not list(settings_file(settings).parent.glob(".provider-settings-*.tmp"))
    restored = create_app(settings).state.settings
    assert restored.model == "qwen2.5:7b" and restored.api_key == "synthetic-new-key"


def test_cross_provider_guard_prevents_reusing_old_key(config):
    with TestClient(create_app(replace(config, api_key="synthetic-old-key"))) as client:
        for base in ("https://other.example/v1", "https://api.deepseek.com:8443", "http://localhost:1234/v1"):
            response = client.put("/api/settings", json=payload(api_base=base))
            assert response.status_code == 422 and "synthetic-old-key" not in response.text
        assert client.put("/api/settings", json=payload(api_base="https://API.DEEPSEEK.COM:443/v1/")).status_code == 200
        assert client.put("/api/settings", json=payload(api_base="https://other.example", api_key="synthetic-other-key")).status_code == 200
        assert client.put("/api/settings", json=payload(clear_api_key=True)).json()["mode"] == "demo"


@pytest.mark.parametrize("change", [
    {"api_base": "http://remote.example"},
    {"api_base": "https://user:password@provider.example"},
    {"api_base": "https://provider.example?key=oops"},
    {"api_base": "https://provider.example:bad"},
    {"model": "bad model"},
    {"model": ""},
    {"api_key": "synthetic-key\ninjected"},
    {"api_key": "synthetic-key", "clear_api_key": True},
])
def test_invalid_settings_are_rejected_without_echoing_input(config, change):
    with TestClient(create_app(config)) as client:
        response = client.put("/api/settings", json=payload(**change))
        assert response.status_code == 422
        assert "synthetic-key" not in response.text
    assert not settings_file(config).exists()


def test_failed_save_does_not_replace_active_configuration(config, monkeypatch):
    def fail_write(settings):
        raise OSError("synthetic-key must never appear in response")
    monkeypatch.setattr("backend.main.save_provider_settings", fail_write)
    with TestClient(create_app(config)) as client:
        response = client.put("/api/settings", json=payload(api_key="synthetic-key"))
        assert response.status_code == 500 and "synthetic-key" not in response.text
        assert client.get("/api/settings").json()["has_api_key"] is False


def test_settings_origin_and_size_boundaries(config):
    with TestClient(create_app(config)) as client:
        assert client.put("/api/settings", json=payload(api_key="synthetic-key"), headers={"Origin": "https://evil.example"}).status_code == 403
        assert client.post("/api/settings/test", headers={"Origin": "https://evil.example"}).status_code == 403
        assert client.put("/api/settings", content=b"x" * 600001).status_code == 413
        response = client.options("/api/settings", headers={"Origin": "http://127.0.0.1:8765", "Access-Control-Request-Method": "PUT", "Access-Control-Request-Headers": "Content-Type"})
        assert response.status_code == 200 and "PUT" in response.headers["access-control-allow-methods"]


def test_connection_gets_only_models_uses_saved_config_and_is_rate_limited(config):
    requests = []
    def handle(request):
        requests.append(request)
        assert request.method == "GET" and request.url.path == "/v1/models" and request.content == b""
        assert request.headers["authorization"] == "Bearer synthetic-new-key"
        return httpx.Response(200, json={"data": [{"id": "new-model"}]})
    adapter = DeepSeek(config, httpx.MockTransport(handle))
    with TestClient(create_app(config, adapter)) as client:
        assert client.put("/api/settings", json=payload(api_base="https://provider.example/v1", model="new-model", api_key="synthetic-new-key")).status_code == 200
        response = client.post("/api/settings/test")
        assert response.status_code == 200 and response.json()["ok"] is True
        assert response.json()["model"] == "new-model" and "synthetic-new-key" not in response.text
        assert client.post("/api/settings/test").status_code == 429
    assert len(requests) == 1


def test_connection_without_key_never_calls_provider(config):
    def forbidden(request):
        raise AssertionError("Offline connection test must not issue network requests")
    with TestClient(create_app(config, DeepSeek(config, httpx.MockTransport(forbidden)))) as client:
        assert client.post("/api/settings/test").json()["ok"] is False


@pytest.mark.parametrize("status,body", [
    (401, {"error": "synthetic-key and private upstream details"}),
    (200, {"data": [{"id": "another-model"}]}),
    (200, {"unexpected": "synthetic-key and private upstream details"}),
])
def test_connection_failures_are_safe_and_do_not_claim_success(config, status, body):
    config = replace(config, api_key="synthetic-key")
    adapter = DeepSeek(config, httpx.MockTransport(lambda request: httpx.Response(status, json=body)))
    with TestClient(create_app(config, adapter)) as client:
        response = client.post("/api/settings/test")
        assert response.status_code == 200 and response.json()["ok"] is False
        assert "synthetic-key" not in response.text and "private upstream details" not in response.text


def test_inflight_chat_keeps_original_provider_snapshot(config):
    started, release = threading.Event(), threading.Event()
    captured = []

    class DelayedStream(httpx.AsyncByteStream):
        async def __aiter__(self):
            started.set()
            await asyncio.to_thread(release.wait, 3)
            message = {"choices": [{"delta": {"content": "BM25 evidence [S1]"}, "finish_reason": "stop"}]}
            yield ("data: " + json.dumps(message) + "\n\ndata: [DONE]\n\n").encode()

    def handle(request):
        captured.append((json.loads(request.content)["model"], request.headers["authorization"]))
        return httpx.Response(200, stream=DelayedStream())

    initial = replace(config, api_key="synthetic-old-key", model="old-model")
    adapter = DeepSeek(initial, httpx.MockTransport(handle))
    with TestClient(create_app(initial, adapter)) as client:
        doc = client.post("/api/documents", json={"title": "BM25", "text": "BM25 is a lexical retrieval method using term frequency."}).json()
        with ThreadPoolExecutor(max_workers=1) as executor:
            pending = executor.submit(client.post, "/api/chat", json={"document_id": doc["id"], "question": "BM25?"})
            try:
                assert started.wait(3)
                assert client.put("/api/settings", json=payload(model="new-model", api_key="synthetic-new-key")).status_code == 200
            finally:
                release.set()
            assert '"mode": "live"' in pending.result(timeout=5).text
        assert client.post("/api/chat", json={"document_id": doc["id"], "question": "BM25?"}).status_code == 200
    assert captured == [("old-model", "Bearer synthetic-old-key"), ("new-model", "Bearer synthetic-new-key")]
