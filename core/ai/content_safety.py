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
