from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True)
class SafetyDecision:
    safe: bool
    reason: str = "allowed"


class LocalContentSafety:
    def __init__(self, prohibited_terms: Iterable[str] = None):
        self.prohibited_terms = tuple(
            term.upper()
            for term in (
                prohibited_terms
                or ("DELETE", "HACK", "BYPASS", "MALWARE", "STEAL", "EXPLOIT")
            )
        )

    def evaluate(self, text: str) -> SafetyDecision:
        normalized = text.upper()
        for term in self.prohibited_terms:
            if term in normalized:
                return SafetyDecision(False, f"blocked prohibited term: {term}")
        return SafetyDecision(True)


class AzureContentSafety:
    def __init__(
        self,
        endpoint: str,
        key: str,
        block_threshold: int = 4,
        client=None,
    ):
        if client is None:
            if not endpoint or not key:
                raise ValueError("Content Safety endpoint and key are required")
            try:
                from azure.ai.contentsafety import ContentSafetyClient
                from azure.core.credentials import AzureKeyCredential
            except ImportError as exc:
                raise RuntimeError(
                    "Install the azure optional dependencies to use Content Safety"
                ) from exc

            client = ContentSafetyClient(endpoint, AzureKeyCredential(key))

        self.client = client
        self.block_threshold = block_threshold

    def evaluate(self, text: str) -> SafetyDecision:
        try:
            from azure.ai.contentsafety.models import AnalyzeTextOptions
        except ImportError:
            AnalyzeTextOptions = None

        request = AnalyzeTextOptions(text=text) if AnalyzeTextOptions else {"text": text}
        response = self.client.analyze_text(request)
        category_results = getattr(response, "categories_analysis", []) or []
        blocked = [
            item
            for item in category_results
            if int(getattr(item, "severity", 0) or 0) >= self.block_threshold
        ]
        if blocked:
            summary = ", ".join(
                f"{getattr(item, 'category', 'Unknown')}={getattr(item, 'severity', 0)}"
                for item in blocked
            )
            return SafetyDecision(False, f"Azure Content Safety blocked intent: {summary}")
        return SafetyDecision(True)
