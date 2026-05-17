import tempfile
from unittest.mock import patch

import pytest

from openwebui_gateway.agent_service import AgentService


@patch.dict("sys.modules", {"run_agent": None})
def test_agent_chat():
    """AgentService.chat returns a string response"""
    with tempfile.TemporaryDirectory() as tmpdir:
        service = AgentService(profile_base_dir=tmpdir)
        response = service.chat("user1@company.com", "Hello")
        assert isinstance(response, str)
        assert len(response) > 0


@patch.dict("sys.modules", {"run_agent": None})
def test_agent_chat_error_handling():
    """AgentService._sync_chat returns error string on exception (never raises)"""
    with tempfile.TemporaryDirectory() as tmpdir:
        service = AgentService(profile_base_dir=tmpdir)
        agent = service.session_manager.get_or_create_agent("user1@company.com")

        # Replace chat with a function that raises
        original_chat = agent.chat

        def broken_chat(message: str):
            raise RuntimeError("simulated failure")

        agent.chat = broken_chat

        try:
            result = service._sync_chat(agent, "test")
            assert result.startswith("Error:")
        finally:
            agent.chat = original_chat


@patch.dict("sys.modules", {"run_agent": None})
def test_agent_stream_chat():
    """AgentService._stream_chat yields response chunks (placeholder)"""
    import asyncio

    with tempfile.TemporaryDirectory() as tmpdir:
        service = AgentService(profile_base_dir=tmpdir)
        agent = service.session_manager.get_or_create_agent("user1@company.com")

        async def collect():
            chunks = []
            async for chunk in service._stream_chat(agent, "Hello"):
                chunks.append(chunk)
            return chunks

        chunks = asyncio.get_event_loop().run_until_complete(collect())
        assert len(chunks) == 1
        assert isinstance(chunks[0], str)


@patch.dict("sys.modules", {"run_agent": None})
def test_agent_get_models():
    """AgentService.get_models returns a list of model dicts"""
    with tempfile.TemporaryDirectory() as tmpdir:
        service = AgentService(profile_base_dir=tmpdir)
        models = service.get_models()

        assert isinstance(models, list)
        assert len(models) >= 1
        for m in models:
            assert "id" in m
            assert "object" in m
            assert m["object"] == "model"


@patch.dict("sys.modules", {"run_agent": None})
def test_agent_stop_agent():
    """AgentService.stop_agent delegates to SessionManager"""
    with tempfile.TemporaryDirectory() as tmpdir:
        service = AgentService(profile_base_dir=tmpdir)

        # Create agent first
        service.session_manager.get_or_create_agent("user1@company.com")

        # Stop should succeed
        assert service.stop_agent("user1@company.com") is True

        # Stopping again should return False (already removed)
        assert service.stop_agent("user1@company.com") is False
