import os
import shutil
import sqlite3
from pathlib import Path
from typing import Optional
import yaml


class ProfileService:
    """Manage user profile directory creation, queries, and sync"""

    def __init__(self, profile_base_dir: str = "~/.hermes/profiles"):
        self.profile_base_dir = Path(profile_base_dir).expanduser()
        self.profile_base_dir.mkdir(parents=True, exist_ok=True)
        self.global_config_path = Path("~/.hermes/config.yaml").expanduser()

    def _sanitize_user_id(self, user_id: str) -> str:
        """Convert user_id to safe directory name"""
        safe = "".join(c if c.isalnum() or c in "-_@." else "_" for c in user_id)
        return safe

    def get_profile_path(self, user_id: str) -> Path:
        """Get user profile directory path"""
        safe_id = self._sanitize_user_id(user_id)
        return self.profile_base_dir / safe_id

    def profile_exists(self, user_id: str) -> bool:
        """Check if user profile exists"""
        return self.get_profile_path(user_id).exists()

    def create_profile(self, user_id: str) -> Path:
        """Create new user profile"""
        profile_path = self.get_profile_path(user_id)

        if profile_path.exists():
            return profile_path

        # Create directory structure
        profile_path.mkdir(parents=True, exist_ok=True)
        (profile_path / "skills" / "admin_installed").mkdir(parents=True)
        (profile_path / "skills" / "user_installed").mkdir(parents=True)

        # Copy global default config
        default_config = self._load_default_config()
        with open(profile_path / "config.yaml", "w", encoding="utf-8") as f:
            yaml.dump(default_config, f, default_flow_style=False, allow_unicode=True)

        # Initialize SQLite DB
        self._init_database(profile_path / "sessions.db")

        # Sync global skills
        self._sync_global_skills(profile_path)

        return profile_path

    def _load_default_config(self) -> dict:
        """Load global default config"""
        if self.global_config_path.exists():
            with open(self.global_config_path, "r", encoding="utf-8") as f:
                return yaml.safe_load(f) or {}
        return {}

    def _init_database(self, db_path: Path):
        """Initialize SQLite database"""
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                id TEXT PRIMARY KEY,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()
        conn.close()

    def _sync_global_skills(self, profile_path: Path):
        """Sync global skills to newly created profile"""
        global_skills_dir = Path("~/.hermes/skills").expanduser()
        admin_installed_dir = profile_path / "skills" / "admin_installed"

        if global_skills_dir.exists():
            for skill_dir in global_skills_dir.iterdir():
                if skill_dir.is_dir() and skill_dir.name not in [".archive", ".usage.json"]:
                    target = admin_installed_dir / skill_dir.name
                    if not target.exists():
                        shutil.copytree(skill_dir, target)

    def list_profiles(self) -> list:
        """List all created profiles"""
        profiles = []
        for profile_dir in self.profile_base_dir.iterdir():
            if profile_dir.is_dir():
                profiles.append({
                    "user_id": profile_dir.name,
                    "path": str(profile_dir),
                    "created": profile_dir.stat().st_ctime
                })
        return profiles

    def get_profile_config(self, user_id: str) -> Optional[dict]:
        """Get user profile config"""
        config_path = self.get_profile_path(user_id) / "config.yaml"
        if config_path.exists():
            with open(config_path, "r", encoding="utf-8") as f:
                return yaml.safe_load(f)
        return None

    def delete_profile(self, user_id: str) -> bool:
        """Delete user profile (dangerous!)"""
        profile_path = self.get_profile_path(user_id)
        if profile_path.exists():
            shutil.rmtree(profile_path)
            return True
        return False
