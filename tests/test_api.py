import os
import sys
import pytest
from fastapi.testclient import TestClient

# Ensure project root is on PYTHONPATH so `src` is importable
sys.path.insert(0, os.path.abspath("."))


def make_fake_client():
    class FakeMessage:
        def __init__(self, content: str):
            self.content = content

    class FakeResponse:
        def __init__(self, content: str):
            self.message = FakeMessage(content)

    class FakeClient:
        def __init__(self):
            self.calls = {
                "list_models": 0,
                "pull_model": [],
                "warm_model": [],
                "chat": [],
            }

        def list_models(self):
            self.calls["list_models"] += 1
            return {"models": [
                {"name": "qwen3:1.7b"},
                {"name": "llama3.1:8b"},
            ]}

        def pull_model(self, model_name: str):
            self.calls["pull_model"].append(model_name)
            return None

        def warm_model(self, model_name: str):
            self.calls["warm_model"].append(model_name)
            return {"status": "warmed", "model": model_name}

        def chat(self, model_name, messages, options=None):
            self.calls["chat"].append({
                "model": model_name,
                "messages": messages,
                "options": options or {},
            })
            # echo back the last user message
            content = next((m.get("content", "") for m in reversed(messages) if m.get("role") == "user"), "")
            return FakeResponse(f"Echo: {content}")

    return FakeClient()


def get_app_and_patch_client(monkeypatch):
    # Import after monkeypatch is available to avoid side-effects ordering issues
    import importlib
    import src.back.api as api
    fake = make_fake_client()
    monkeypatch.setattr(api, "client", fake)
    return api.app, fake


def test_list_models_success(monkeypatch):
    app, fake = get_app_and_patch_client(monkeypatch)
    with TestClient(app) as c:
        resp = c.get("/models")
    assert resp.status_code == 200
    data = resp.json()
    assert "models" in data and isinstance(data["models"], list)
    assert fake.calls["list_models"] == 1


def test_pull_model_success(monkeypatch):
    app, fake = get_app_and_patch_client(monkeypatch)
    with TestClient(app) as c:
        resp = c.post("/models/pull", json={"model_name": "qwen3:1.7b"})
    assert resp.status_code == 200
    assert resp.json() == {"status": "success"}
    assert fake.calls["pull_model"] == ["qwen3:1.7b"]


def test_warm_model_success(monkeypatch):
    app, fake = get_app_and_patch_client(monkeypatch)
    with TestClient(app) as c:
        resp = c.post("/models/warm", json={"model_name": "llama3.1:8b"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "success"
    assert body["result"]["status"] == "warmed"
    assert body["result"]["model"] == "llama3.1:8b"
    assert fake.calls["warm_model"] == ["llama3.1:8b"]


def test_chat_success(monkeypatch):
    app, fake = get_app_and_patch_client(monkeypatch)
    payload = {
        "model_name": "qwen3:1.7b",
        "messages": [
            {"role": "system", "content": "Be helpful."},
            {"role": "user", "content": "Hello"},
        ],
    }
    with TestClient(app) as c:
        resp = c.post("/chat", json=payload)
    assert resp.status_code == 200
    assert resp.json() == {"message": "Echo: Hello"}
    assert fake.calls["chat"][0]["model"] == "qwen3:1.7b"


def test_pull_model_error_returns_400(monkeypatch):
    import src.back.api as api

    class FailingClient:
        def pull_model(self, model_name: str):
            raise RuntimeError("pull failed")

    monkeypatch.setattr(api, "client", FailingClient())

    with TestClient(api.app) as c:
        resp = c.post("/models/pull", json={"model_name": "bad"})
    assert resp.status_code == 400
    assert resp.json()["detail"] == "pull failed"
