from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum


@dataclass(frozen=True)
class AbtFileMeta:
    file_name: str
    vin: str
    system: str
    captured_at: datetime


@dataclass(frozen=True)
class ParsedRecord:
    offset: int
    name: str
    value: int
    interpretation: str


class SafetyLevel(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


@dataclass(frozen=True)
class DtcInfo:
    code: str
    title: str
    system: str
    severity: SafetyLevel
    likely_causes: tuple[str, ...]
    recommended_steps: tuple[str, ...]


@dataclass(frozen=True)
class ChangePlan:
    module: str
    parameter: str
    current_value: str
    target_value: str
    safety_level: SafetyLevel
    pre_checks: tuple[str, ...]
    execution_steps: tuple[str, ...]
    rollback_steps: tuple[str, ...]
    warnings: tuple[str, ...]


@dataclass(frozen=True)
class SourceEvidence:
    title: str
    url: str
    category: str
    last_checked: str
    notes: str


@dataclass(frozen=True)
class TrustReport:
    legitimacy_score: int
    verdict: str
    strengths: tuple[str, ...]
    caveats: tuple[str, ...]
    sources: tuple[SourceEvidence, ...]


@dataclass(frozen=True)
class TopicExplanation:
    topic: str
    summary: str
    why_it_matters: tuple[str, ...]
    common_mistakes: tuple[str, ...]
    best_practices: tuple[str, ...]


ABT_CAPTURED_AT_FORMAT = "%Y%m%d%H%M%S"
ABT_FIELDS: tuple[tuple[int, str, str], ...] = (
    (0, "first_uint32", "Primary sample value"),
    (4, "second_uint32", "Secondary sample value"),
)
EXPLANATION_SEPARATOR = "\n" + "=" * 72 + "\n"
