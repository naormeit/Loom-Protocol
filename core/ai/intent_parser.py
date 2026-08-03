from dataclasses import dataclass
import json


@dataclass(frozen=True)
class ParsedIntent:
    action: str
    normalized_text: str
    confidence: float


class LocalIntentParser:
    def parse(self, raw_text: str) -> ParsedIntent:
        normalized = " ".join(raw_text.strip().upper().split())
        action = normalized.split(" ", 1)[0] if normalized else "UNKNOWN"
        return ParsedIntent(
            action=action,
            normalized_text=normalized,
            confidence=0.90 if normalized else 0.0,
        )


class AzureOpenAIIntentParser:
    def __init__(
        self,
        endpoint: str,
        api_key: str,
        deployment: str,
        api_version: str = "2024-10-21",
        client=None,
    ):
        if client is None:
            if not endpoint or not api_key or not deployment:
                raise ValueError(
                    "Azure OpenAI endpoint, API key, and deployment are required"
                )
            try:
                from openai import AzureOpenAI
            except ImportError as exc:
                raise RuntimeError(
                    "Install the azure optional dependencies to use Azure OpenAI"
                ) from exc

            client = AzureOpenAI(
                azure_endpoint=endpoint,
                api_key=api_key,
                api_version=api_version,
            )

        self.client = client
        self.deployment = deployment

    def parse(self, raw_text: str) -> ParsedIntent:
        response = self.client.chat.completions.create(
            model=self.deployment,
            temperature=0,
            response_format={"type": "json_object"},
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Convert agent transaction intent into compact JSON with "
                        "keys action, normalized_text, confidence. Use uppercase "
                        "normalized_text and a confidence from 0 to 1."
                    ),
                },
                {"role": "user", "content": raw_text},
            ],
        )
        content = response.choices[0].message.content
        parsed = json.loads(content)
        normalized = str(parsed.get("normalized_text") or raw_text).upper().strip()
        action = str(parsed.get("action") or normalized.split(" ", 1)[0] or "UNKNOWN")
        confidence = float(parsed.get("confidence", 0.75))
        return ParsedIntent(
            action=action.upper(),
            normalized_text=normalized,
            confidence=max(0.0, min(confidence, 1.0)),
        )
