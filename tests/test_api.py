import sys
from pathlib import Path
from typing import Dict, List, Any, Optional

import pytest
from fastapi.testclient import TestClient
from pydantic import BaseModel

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
BACK_PACKAGE_ROOT = SRC_DIR / "back"


def _import_api(monkeypatch: Optional[pytest.MonkeyPatch] = None):
    for candidate in (PROJECT_ROOT, BACK_PACKAGE_ROOT):
        candidate_str = str(candidate)
        if monkeypatch is not None:
            monkeypatch.syspath_prepend(candidate_str)
        elif candidate_str not in sys.path:
            sys.path.insert(0, candidate_str)
    import src.back.api as api  # type: ignore

    return api


class FakeChatResponse(BaseModel):
    model: str
    message: Dict[str, str]
    done: bool = True


def make_fake_client():
    class FakeClient:
        def __init__(self):
            self.calls = {
                "list_models": 0,
                "pull_model": [],
                "warm_model": [],
                "chat": [],
            }
            self._models: List[Dict[str, Any]] = [
                {"name": "qwen3:1.7b"},
                {"name": "llama3.1:8b"},
            ]

        def list_models(self):
            self.calls["list_models"] += 1
            return {"models": self._models}

        def pull_model(self, model_name: str):
            self.calls["pull_model"].append(model_name)

        def warm_model(self, model_name: str):
            self.calls["warm_model"].append(model_name)
            return {"status": "warmed", "model": model_name}

        def chat(self, model_name: str, messages: List[Dict[str, Any]], options=None):
            options = options or {}
            self.calls["chat"].append({
                "model": model_name,
                "messages": messages,
                "options": options,
            })
            user_message = next(
                (m.get("content", "") for m in reversed(messages) if m.get("role") == "user"),
                "",
            )
            return FakeChatResponse(
                model=model_name,
                message={"role": "assistant", "content": f"Echo: {user_message}"},
            )

    return FakeClient()


@pytest.fixture()
def app_and_client(monkeypatch):
    api = _import_api(monkeypatch)

    fake = make_fake_client()
    monkeypatch.setattr(api, "client", fake)
    return api.app, fake


def test_health_check():
    api = _import_api()

    with TestClient(api.app) as client:
        response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_list_models_success(app_and_client):
    app, fake = app_and_client

    with TestClient(app) as client:
        resp = client.get("/models")

    assert resp.status_code == 200
    data = resp.json()
    assert "models" in data and isinstance(data["models"], list)
    assert fake.calls["list_models"] == 1


def test_pull_model_success(app_and_client):
    app, fake = app_and_client

    with TestClient(app) as client:
        resp = client.post("/models/pull", json={"model_name": "qwen3:1.7b"})

    assert resp.status_code == 200
    assert resp.json() == {"status": "success"}
    assert fake.calls["pull_model"] == ["qwen3:1.7b"]


def test_warm_model_success(app_and_client):
    app, fake = app_and_client

    with TestClient(app) as client:
        resp = client.post("/models/warm", json={"model_name": "llama3.1:8b"})

    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "success"
    assert body["result"] == {"status": "warmed", "model": "llama3.1:8b"}
    assert fake.calls["warm_model"] == ["llama3.1:8b"]


def test_chat_success(app_and_client):
    app, fake = app_and_client
    payload = {
        "model_name": "qwen3:1.7b",
        "messages": [
            {"role": "system", "content": "Be helpful."},
            {"role": "user", "content": "Hello"},
        ],
    }

    with TestClient(app) as client:
        resp = client.post("/chat", json=payload)

    assert resp.status_code == 200
    body = resp.json()
    assert body["model"] == "qwen3:1.7b"
    assert body["message"]["content"] == "Echo: Hello"
    assert body["message"]["role"] == "assistant"
    assert fake.calls["chat"][0]["model"] == "qwen3:1.7b"


def test_pull_model_error_returns_400(monkeypatch):
    api = _import_api(monkeypatch)

    class FailingClient:
        def pull_model(self, model_name: str):
            raise RuntimeError("pull failed")

    monkeypatch.setattr(api, "client", FailingClient())

    with TestClient(api.app) as client:
        resp = client.post("/models/pull", json={"model_name": "bad"})
    assert resp.status_code == 400
    assert resp.json()["detail"] == "pull failed"
