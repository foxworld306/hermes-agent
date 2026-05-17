import os
from dataclasses import dataclass, field
from typing import List, Optional

@dataclass
class GatewayConfig:
    host: str = "0.0.0.0"
    openai_port: int = 18080
    max_concurrent_agents: int = 50
    profile_base_dir: str = "~/.hermes/profiles"
    admin_secret: Optional[str] = None
    allowed_models: List[str] = field(default_factory=list)
    default_model: str = "gpt-4"
    
    # LLM endpoint configuration
    base_url: Optional[str] = field(default_factory=lambda: os.environ.get("CYAN_BASE_URL"))
    api_key: Optional[str] = field(default_factory=lambda: os.environ.get("CYAN_API_KEY"))
    provider: Optional[str] = field(default_factory=lambda: os.environ.get("CYAN_PROVIDER", "openai"))
