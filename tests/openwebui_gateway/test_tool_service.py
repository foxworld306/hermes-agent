def test_tool_enable_disable():
    import tempfile
    from openwebui_gateway.tool_service import ToolService

    with tempfile.TemporaryDirectory() as tmpdir:
        service = ToolService(config_path=tmpdir + "/config.yaml")

        # Initially all tools should be enabled
        assert service.is_tool_enabled("web_search") is True

        # Disable a tool
        service.disable_tool("web_search")
        assert service.is_tool_enabled("web_search") is False

        # Re-enable
        service.enable_tool("web_search")
        assert service.is_tool_enabled("web_search") is True
