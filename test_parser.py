import os
from parser import parse_docx


def test_parse_docx():
    sample_file = os.path.join("input", "v26cb09ph0601.docx")
    assert os.path.exists(sample_file), f"Test file not found: {sample_file}"

    result = parse_docx(sample_file)
    assert result["file_name"] == "v26cb09ph0601.docx"
    assert result["total_elements"] > 0
    assert len(result["elements"]) > 0

    # Verify table extraction
    tables = [e for e in result["elements"] if e["type"] == "table"]
    assert len(tables) >= 1
    first_table_rows = tables[0]["rows"]
    table_dict = {row[0]: row[1] for row in first_table_rows if len(row) >= 2}
    assert "Script Code" in table_dict
    assert table_dict["Script Code"] == "v26cb09ph0601_dr"

    # Verify paragraph extraction
    paragraphs = [e for e in result["elements"] if e["type"] == "paragraph"]
    assert len(paragraphs) > 0

    # Verify order preservation
    assert result["elements"][0]["type"] == "paragraph"
    assert "V25cb09ph0601_sc" in result["elements"][0]["text"]
    assert result["elements"][1]["type"] == "table"
    assert result["elements"][2]["type"] == "paragraph"
    assert "FADE IN:" in result["elements"][2]["text"]

    print(f"SUCCESS: Extracted {result['total_elements']} elements ({len(tables)} tables, {len(paragraphs)} paragraphs).")


if __name__ == "__main__":
    test_parse_docx()
