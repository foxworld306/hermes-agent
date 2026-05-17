import tempfile
from pathlib import Path

import pytest

from openwebui_gateway.profile_service import ProfileService


def test_create_profile():
    """ProfileService.create_profile creates directory structure with config, db, and skills dirs"""
    with tempfile.TemporaryDirectory() as tmpdir:
        service = ProfileService(profile_base_dir=tmpdir)
        user_id = "test_user@company.com"

        profile_path = service.create_profile(user_id)

        assert profile_path.exists()
        assert (profile_path / "config.yaml").exists()
        assert (profile_path / "sessions.db").exists()
        assert (profile_path / "skills" / "admin_installed").is_dir()
        assert (profile_path / "skills" / "user_installed").is_dir()


def test_sanitize_user_id():
    """ProfileService._sanitize_user_id strips unsafe characters"""
    service = ProfileService(profile_base_dir=tempfile.gettempdir())

    assert service._sanitize_user_id("safe-user_123") == "safe-user_123"
    assert service._sanitize_user_id("test@example.com") == "test@example.com"
    assert service._sanitize_user_id("bad path/user") == "bad_path_user"
    assert service._sanitize_user_id("spaces in name") == "spaces_in_name"


def test_list_profiles():
    """ProfileService.list_profiles returns all created profiles"""
    with tempfile.TemporaryDirectory() as tmpdir:
        service = ProfileService(profile_base_dir=tmpdir)
        service.create_profile("user1")
        service.create_profile("user2")

        profiles = service.list_profiles()

        assert len(profiles) == 2
        user_ids = {p["user_id"] for p in profiles}
        assert "user1" in user_ids
        assert "user2" in user_ids


def test_get_profile_config():
    """ProfileService.get_profile_config returns parsed YAML or None"""
    with tempfile.TemporaryDirectory() as tmpdir:
        service = ProfileService(profile_base_dir=tmpdir)
        service.create_profile("user1")

        config = service.get_profile_config("user1")
        # Default config is empty dict (no global config.yaml exists in temp dir)
        assert isinstance(config, dict)

        # Non-existent user returns None
        assert service.get_profile_config("nobody") is None


def test_delete_profile():
    """ProfileService.delete_profile removes directory recursively"""
    with tempfile.TemporaryDirectory() as tmpdir:
        service = ProfileService(profile_base_dir=tmpdir)
        service.create_profile("user1")

        assert service.profile_exists("user1")
        result = service.delete_profile("user1")

        assert result is True
        assert not service.profile_exists("user1")

        # Deleting non-existent profile returns False
        assert service.delete_profile("user1") is False
