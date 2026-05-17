def test_gateway_config_default():
    from openwebui_gateway.config import GatewayConfig
    config = GatewayConfig()
    assert config.host == "0.0.0.0"
    assert config.openai_port == 18080
    assert config.max_concurrent_agents == 50
