"""Tests for OpenAI API compatible routes."""
import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from openwebui_gateway.main import app


@pytest.fixture
def client():
    return TestClient(app)


class TestHealthEndpoint:
    def test_health_returns_healthy(self, client):
        response = client.get("/v1/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "cyan-gateway"


class TestModelsEndpoint:
    def test_models_returns_list(self, client):
        response = client.get("/v1/models")
        assert response.status_code == 200
        data = response.json()
        assert data["object"] == "list"
        assert isinstance(data["data"], list)
        assert len(data["data"]) > 0
        # Each model should have id and object
        for model in data["data"]:
            assert "id" in model
            assert model["object"] == "model"


class TestChatCompletionsAuth:
    def test_missing_user_id_returns_401(self, client):
        response = client.post(
            "/v1/chat/completions",
            json={
                "model": "gpt-4",
                "messages": [{"role": "user", "content": "Hello"}],
                "stream": False,
            },
        )
        assert response.status_code == 401
        assert "X-User-Id" in response.json()["detail"]


class TestChatCompletionsNonStreaming:
    @patch("openwebui_gateway.routes.openai.agent_service")
    def test_nonstreaming_returns_openai_format(self, mock_service, client):
        mock_service.chat.return_value = "Hello, how can I help you?"

        response = client.post(
            "/v1/chat/completions",
            json={
                "model": "gpt-4",
                "messages": [{"role": "user", "content": "Hello"}],
                "stream": False,
            },
            headers={"X-User-Id": "test@company.com"},
        )

        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert data["object"] == "chat.completion"
        assert data["model"] == "gpt-4"
        assert "choices" in data
        assert len(data["choices"]) > 0
        choice = data["choices"][0]
        assert choice["message"]["role"] == "assistant"
        assert "Hello, how can I help you?" in choice["message"]["content"]
        assert choice["finish_reason"] == "stop"

    @patch("openwebui_gateway.routes.openai.agent_service")
    def test_nonstreaming_calls_agent_with_correct_params(
        self, mock_service, client
    ):
        mock_service.chat.return_value = "Test response"

        client.post(
            "/v1/chat/completions",
            json={
                "model": "gpt-4",
                "messages": [{"role": "user", "content": "Test message"}],
                "stream": False,
            },
            headers={"X-User-Id": "user1"},
        )

        mock_service.chat.assert_called_once_with(
            "user1", "Test message", model="gpt-4", stream=False
        )


class TestChatCompletionsStreaming:
    @patch("openwebui_gateway.routes.openai.agent_service")
    def test_streaming_returns_sse_format(self, mock_service, client):
        async def mock_stream(*args, **kwargs):
            yield "Hello"
            yield " world"

        mock_service.chat.return_value = mock_stream()

        response = client.post(
            "/v1/chat/completions",
            json={
                "model": "gpt-4",
                "messages": [{"role": "user", "content": "Hello"}],
                "stream": True,
            },
            headers={"X-User-Id": "test@company.com"},
        )

        assert response.status_code == 200
        assert "text/event-stream" in response.headers["content-type"]
        # Should contain data: lines and [DONE]
        body = response.text
        assert 'data:' in body
        assert "[DONE]" in body
