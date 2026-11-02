from pathlib import Path

import numpy as np
import pytest
from fastapi.testclient import TestClient

from src.food11 import serve

PHOTO = (Path(__file__).parent / "fixtures/bread.jpg").read_bytes()


class FakeModel:
    def predict(self, inputs):
        assert inputs.shape == (1, 3, 224, 224)
        assert inputs.dtype == np.float32 and np.isfinite(inputs).all()
        # Production model returns logits: log probabilities produce 0.90 after softmax.
        return np.log([[0.90] + [0.01] * 10])


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("SKIP_MODEL", "1")
    with TestClient(serve.app) as test_client:
        yield test_client


def test_health_and_unloaded_model(client):
    assert client.get("/health").json() == {"status": "ok"}
    assert client.get("/model").json()["loaded_version"] is None
    assert client.post("/predict", files={"file": ("bread.jpg", PHOTO)}).status_code == 503


def test_predict_returns_valid_json(client, monkeypatch):
    monkeypatch.setattr(serve, "model", FakeModel())
    response = client.post("/predict", files={"file": ("bread.jpg", PHOTO, "image/jpeg")})
    assert response.status_code == 200
    assert response.json()["category"] == "Bread"
    assert response.json()["confidence"] == pytest.approx(0.90)


@pytest.mark.parametrize(("content", "status"), [(b"", 400), (b"not an image", 400), (b"x" * (10 * 1024 * 1024 + 1), 413)])
def test_invalid_upload(client, monkeypatch, content, status):
    monkeypatch.setattr(serve, "model", FakeModel())
    assert client.post("/predict", files={"file": ("bad.jpg", content)}).status_code == status


def test_missing_upload(client, monkeypatch):
    monkeypatch.setattr(serve, "model", FakeModel())
    assert client.post("/predict").status_code == 422


@pytest.mark.parametrize("output", [[[float("nan")] * 11], [[0.5, 0.5]]])
def test_bad_model_output(client, monkeypatch, output):
    class BadModel:
        def predict(self, inputs):
            return output
    monkeypatch.setattr(serve, "model", BadModel())
    assert client.post("/predict", files={"file": ("bread.jpg", PHOTO)}).status_code == 500
