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
