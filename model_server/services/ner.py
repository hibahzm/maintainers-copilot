"""Named-entity extraction service."""

from model_server.schemas.ner import NERResponse


def extract_entities() -> NERResponse:
    """Placeholder until the lightweight NER extractor is implemented."""
    return NERResponse(status="todo", feature="entity extraction")
