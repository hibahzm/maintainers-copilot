"""Rule-based NER for code-shaped entities in GitHub issue text."""

from __future__ import annotations

import re
from dataclasses import dataclass
from functools import lru_cache

from model_server.schemas.ner import CodeEntity, NERRequest, NERResponse

KNOWN_PACKAGES = (
    "pandas",
    "numpy",
    "pyarrow",
    "polars",
    "scipy",
    "sklearn",
    "matplotlib",
    "sqlalchemy",
    "pytest",
    "python",
    "pip",
    "jupyter",
)

PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    (
        "url",
        re.compile(r"https?://[^\s)\]}>'\"]+", re.IGNORECASE),
    ),
    (
        "file_path",
        re.compile(
            r"(?<![\w/.-])(?:[\w.-]+/)+(?:[\w.-]+)(?:\.(?:py|pyx|pxd|ipynb|md|rst|txt|csv|json|yml|yaml|toml|c|h|cpp|so))?",
            re.IGNORECASE,
        ),
    ),
    (
        "exception",
        re.compile(r"\b[A-Z][A-Za-z0-9_]*(?:Error|Exception|Warning)\b"),
    ),
    (
        "python_version",
        re.compile(r"\bPython\s*(?:version\s*)?\d+(?:\.\d+){1,2}\b", re.IGNORECASE),
    ),
    (
        "package_version",
        re.compile(
            rf"\b(?:{'|'.join(re.escape(package) for package in KNOWN_PACKAGES)})[-_ ]?\d+(?:\.\d+){{1,3}}(?:[a-zA-Z0-9.+-]*)?\b",
            re.IGNORECASE,
        ),
    ),
    (
        "version",
        re.compile(r"(?<![\w.])v?\d+(?:\.\d+){1,3}(?:[a-zA-Z0-9.+-]*)?(?![\w.])"),
    ),
    (
        "dotted_symbol",
        re.compile(r"\b[a-zA-Z_]\w*(?:\.[a-zA-Z_]\w*){1,}\b"),
    ),
    (
        "function",
        re.compile(r"\b[a-zA-Z_]\w*(?:\.[a-zA-Z_]\w*)?\s*(?=\()"),
    ),
    (
        "package",
        re.compile(rf"\b(?:{'|'.join(re.escape(package) for package in KNOWN_PACKAGES)})\b", re.IGNORECASE),
    ),
    (
        "operating_system",
        re.compile(r"\b(?:Windows|Linux|macOS|Mac OS|Darwin|Ubuntu|Debian|Alpine|RedHat|CentOS)\b", re.IGNORECASE),
    ),
    (
        "file_type",
        re.compile(r"\b(?:CSV|JSON|Parquet|Excel|XLSX|HTML|SQL|YAML|TOML)\b", re.IGNORECASE),
    ),
)


@dataclass(frozen=True)
class _Candidate:
    type: str
    text: str
    normalized: str
    start: int
    end: int


@lru_cache(maxsize=1)
def tokenizer_backend() -> str:
    """Initialize spaCy when available, but keep extraction deterministic/rule-based."""
    try:
        import spacy

        spacy.blank("en")
        return "spacy.blank(en)+regex"
    except Exception:  # pragma: no cover - only depends on runtime image deps
        return "regex"


def compose_ner_text(payload: NERRequest) -> str:
    parts = [payload.title.strip(), payload.body.strip(), (payload.text or "").strip()]
    return "\n\n".join(part for part in parts if part)


def extract_entities(payload: NERRequest) -> NERResponse:
    text = compose_ner_text(payload)
    candidates: list[_Candidate] = []

    for entity_type, pattern in PATTERNS:
        for match in pattern.finditer(text):
            raw = match.group(0).strip()
            if not raw or len(raw) > 240:
                continue
            normalized = _normalize(entity_type, raw)
            candidates.append(
                _Candidate(
                    type=entity_type,
                    text=raw,
                    normalized=normalized,
                    start=match.start(),
                    end=match.end(),
                )
            )

    entities = _dedupe(candidates)
    grouped: dict[str, list[str]] = {}
    for entity in entities:
        grouped.setdefault(entity.type, [])
        if entity.normalized not in grouped[entity.type]:
            grouped[entity.type].append(entity.normalized)

    return NERResponse(
        entities=[CodeEntity(**entity.__dict__) for entity in entities],
        grouped=grouped,
        tokenizer_backend=tokenizer_backend(),
    )


def _normalize(entity_type: str, text: str) -> str:
    cleaned = text.strip().strip("`.,;:()[]{}<>")
    if entity_type in {"package", "operating_system", "file_type"}:
        return cleaned.lower()
    if entity_type == "function":
        return cleaned.replace(" ", "")
    return cleaned


def _dedupe(candidates: list[_Candidate]) -> list[_Candidate]:
    # Prefer longer/more specific matches when spans overlap, e.g. pandas.read_csv over pandas.
    ordered = sorted(candidates, key=lambda item: (item.start, -(item.end - item.start), item.type))
    selected: list[_Candidate] = []
    seen: set[tuple[str, str]] = set()

    for candidate in ordered:
        key = (candidate.type, candidate.normalized.lower())
        if key in seen:
            continue
        if any(_overlaps(candidate, existing) and candidate.text in existing.text for existing in selected):
            continue
        selected.append(candidate)
        seen.add(key)

    return sorted(selected, key=lambda item: (item.start, item.end, item.type))


def _overlaps(left: _Candidate, right: _Candidate) -> bool:
    return left.start < right.end and right.start < left.end
