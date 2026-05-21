import re

SECRET_PATTERNS = [
    re.compile(r"(?i)(api[_-]?key\s*[:=]\s*)([^\s]+)"),
    re.compile(r"(?i)(bearer\s+)([a-z0-9._-]+)"),
]


def redact(text: str) -> str:
    """Mask obvious secrets before logs or traces are emitted."""
    redacted = text
    for pattern in SECRET_PATTERNS:
        redacted = pattern.sub(lambda match: f"{match.group(1)}[REDACTED]", redacted)
    return redacted
