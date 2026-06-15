"""Simple quality gate helper for RawSignal."""
from __future__ import annotations

from pydantic import BaseModel

from .raw_signal_schema import RawSignal


class QualityGateResult(BaseModel):
    signal_id: str
    passed: bool
    reasons: list[str] = []


class QualityGate:
    """Rule-based quality checks for RawSignal objects.

    Projects may subclass and add domain-specific rules.
    """

    def __init__(self, min_text_length: int = 30) -> None:
        self.min_text_length = min_text_length

    def check(self, signal: RawSignal) -> QualityGateResult:
        reasons: list[str] = []
        if len(signal.raw_text.strip()) < self.min_text_length:
            reasons.append(f"raw_text too short (< {self.min_text_length} chars)")
        passed = len(reasons) == 0
        return QualityGateResult(signal_id=signal.signal_id, passed=passed, reasons=reasons)

    def filter_signals(self, signals: list[RawSignal]) -> tuple[list[RawSignal], list[QualityGateResult]]:
        passed: list[RawSignal] = []
        failed: list[QualityGateResult] = []
        for sig in signals:
            result = self.check(sig)
            if result.passed:
                passed.append(sig)
            else:
                failed.append(result)
        return passed, failed
