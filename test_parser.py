import os
from parser import parse_script, parse_docx, parse_pdf


def test_docx_parsing():
    docx_file = os.path.join("input", "v26cb09ph0601.docx")
    assert os.path.exists(docx_file), f"DOCX test file not found: {docx_file}"

    result = parse_script(docx_file)
    assert result["file_name"] == "v26cb09ph0601.docx"
    assert result["format"] == "docx"
    assert result["total_elements"] > 0

    # Verify tables
    tables = [e for e in result["elements"] if e["type"] == "table"]
    assert len(tables) >= 1
    table_dict = {row[0]: row[1] for row in tables[0]["rows"] if len(row) >= 2}
    assert "Script Code" in table_dict
    assert table_dict["Script Code"] == "v26cb09ph0601_dr"

    # Verify paragraphs
    paragraphs = [e for e in result["elements"] if e["type"] == "paragraph"]
    assert len(paragraphs) > 0
    assert "FADE IN:" in [p["text"] for p in paragraphs[:5]]

    print(f"PASS: DOCX parsing ({result['total_elements']} elements, {len(tables)} table, {len(paragraphs)} paragraphs)")


def test_pdf_parsing():
    pdf_file = os.path.join("input", "v26cb07ge0110.pdf")
    assert os.path.exists(pdf_file), f"PDF test file not found: {pdf_file}"

    result = parse_script(pdf_file)
    assert result["file_name"] == "v26cb07ge0110.pdf"
    assert result["format"] == "pdf"
    assert result["total_elements"] > 0

    # Verify tables
    tables = [e for e in result["elements"] if e["type"] == "table"]
    assert len(tables) >= 1
    first_row = tables[0]["rows"][0]
    assert "v26cb07ge0110" in " ".join(first_row)

    # Verify paragraphs
    paragraphs = [e for e in result["elements"] if e["type"] == "paragraph"]
    assert len(paragraphs) > 0

    # Verify link extraction
    linked_elements = [e for e in paragraphs if "links" in e]
    assert len(linked_elements) > 0, "Expected hyperlinks to be extracted from PDF"

    print(f"PASS: PDF parsing ({result['total_elements']} elements, {len(tables)} tables, {len(linked_elements)} linked blocks)")


if __name__ == "__main__":
    test_docx_parsing()
    test_pdf_parsing()
    print("ALL TESTS PASSED SUCCESSFULLY.")
