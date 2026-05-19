from model_server.schemas.ner import NERRequest
from model_server.services.ner import extract_entities


def test_extract_entities_finds_code_shaped_issue_entities():
    response = extract_entities(
        NERRequest(
            title="BUG: read_csv crashes on pandas 2.2 with Python 3.12",
            body="ValueError raised in pandas/io/parsers.py on Windows when loading CSV files.",
        )
    )

    grouped = response.grouped
    assert "read_csv" in grouped["function"]
    assert "valueerror" not in grouped.get("exception", [])
    assert "ValueError" in grouped["exception"]
    assert "pandas" in grouped["package"]
    assert "Python 3.12" in grouped["python_version"]
    assert "pandas/io/parsers.py" in grouped["file_path"]
    assert "windows" in grouped["operating_system"]
    assert "csv" in grouped["file_type"]
