import os
from dataclasses import dataclass


@dataclass(frozen=True)
class AppConfig:
    mode: str = "local"
    host: str = "127.0.0.1"
    port: int = 8080
    require_signature: bool = False
    shared_secret: str = ""
    azure_openai_endpoint: str = ""
    azure_openai_api_key: str = ""
    azure_openai_api_version: str = "2024-10-21"
    azure_openai_deployment: str = ""
    content_safety_endpoint: str = ""
    content_safety_key: str = ""
    content_safety_block_threshold: int = 4
    cosmos_endpoint: str = ""
    cosmos_key: str = ""
    cosmos_database: str = "loom"
    cosmos_container: str = "locks"

    @classmethod
    def from_env(cls) -> "AppConfig":
        return cls(
            mode=os.getenv("LOOM_MODE", "local").strip().lower(),
            host=os.getenv("LOOM_HOST", "127.0.0.1"),
            port=int(os.getenv("LOOM_PORT", "8080")),
            require_signature=os.getenv("LOOM_REQUIRE_SIGNATURE", "false").lower()
            in {"1", "true", "yes"},
            shared_secret=os.getenv("LOOM_SHARED_SECRET", ""),
            azure_openai_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT", ""),
            azure_openai_api_key=os.getenv("AZURE_OPENAI_API_KEY", ""),
            azure_openai_api_version=os.getenv(
                "AZURE_OPENAI_API_VERSION",
                "2024-10-21",
            ),
            azure_openai_deployment=os.getenv("AZURE_OPENAI_DEPLOYMENT", ""),
            content_safety_endpoint=os.getenv("CONTENT_SAFETY_ENDPOINT", ""),
            content_safety_key=os.getenv("CONTENT_SAFETY_KEY", ""),
            content_safety_block_threshold=int(
                os.getenv("CONTENT_SAFETY_BLOCK_THRESHOLD", "4")
            ),
            cosmos_endpoint=os.getenv("COSMOS_ENDPOINT", ""),
            cosmos_key=os.getenv("COSMOS_KEY", ""),
            cosmos_database=os.getenv("COSMOS_DATABASE", "loom"),
            cosmos_container=os.getenv("COSMOS_CONTAINER", "locks"),
        )
