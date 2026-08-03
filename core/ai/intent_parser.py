from dataclasses import dataclass


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
