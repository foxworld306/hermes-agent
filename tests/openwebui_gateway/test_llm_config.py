"""
Test LLM endpoint configuration (base_url, api_key, provider)
"""
import os
import tempfile
from unittest.mock import patch, MagicMock


class TestLLMEndpointConfiguration:
    """Test that SessionManager passes base_url, api_key, provider to AIAgent."""

    def test_session_manager_accepts_llm_params(self):
        """SessionManager __init__ accepts base_url, api_key, provider."""
        from openwebui_gateway.session_manager import SessionManager
        with tempfile.TemporaryDirectory() as tmpdir:
            sm = SessionManager(
                profile_base_dir=tmpdir,
                base_url="http://internal-llm:8000/v1",
                api_key="test-key-123",
                provider="openai",
            )
            assert sm.base_url == "http://internal-llm:8000/v1"
            assert sm.api_key == "test-key-123"
            assert sm.provider == "openai"

    def test_session_manager_omits_none_params(self):
        """SessionManager does not pass None params to AIAgent."""
        from openwebui_gateway.session_manager import SessionManager
        with tempfile.TemporaryDirectory() as tmpdir:
            sm = SessionManager(profile_base_dir=tmpdir)
            assert sm.base_url is None
            assert sm.api_key is None
            assert sm.provider is None

    def test_gatewayconfig_reads_env_vars(self, monkeypatch):
        """GatewayConfig reads CYAN_BASE_URL, CYAN_API_KEY, CYAN_PROVIDER from env."""
        from importlib import reload
        import openwebui_gateway.config as config_module
        
        monkeypatch.setenv("CYAN_BASE_URL", "http://llm.internal:9000/v1")
        monkeypatch.setenv("CYAN_API_KEY", "secret-123")
        monkeypatch.setenv("CYAN_PROVIDER", "custom-llm")
        
        reload(config_module)
        from openwebui_gateway.config import GatewayConfig
        
        cfg = GatewayConfig()
        assert cfg.base_url == "http://llm.internal:9000/v1"
        assert cfg.api_key == "secret-123"
        assert cfg.provider == "custom-llm"

    def test_agent_service_reads_env_vars(self, monkeypatch):
        """AgentService reads LLM config from environment."""
        from openwebui_gateway.agent_service import AgentService
        
        monkeypatch.setenv("CYAN_BASE_URL", "http://llm.corp:8080/v1")
        monkeypatch.setenv("CYAN_API_KEY", "corp-key")
        
        service = AgentService()
        assert service.session_manager.base_url == "http://llm.corp:8080/v1"
        assert service.session_manager.api_key == "corp-key"
