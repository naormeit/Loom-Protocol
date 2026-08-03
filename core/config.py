import os
from dataclasses import dataclass


@dataclass(frozen=True)
class AppConfig:
    mode: str = "local"
    host: str = "127.0.0.1"
    port: int = 8080
    require_signature: bool = False
    shared_secret: str = ""

    @classmethod
    def from_env(cls) -> "AppConfig":
        return cls(
            mode=os.getenv("LOOM_MODE", "local").strip().lower(),
            host=os.getenv("LOOM_HOST", "127.0.0.1"),
            port=int(os.getenv("LOOM_PORT", "8080")),
            require_signature=os.getenv("LOOM_REQUIRE_SIGNATURE", "false").lower()
            in {"1", "true", "yes"},
            shared_secret=os.getenv("LOOM_SHARED_SECRET", ""),
        )
