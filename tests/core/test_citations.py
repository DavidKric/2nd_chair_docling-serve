# Pytest tests for citation building functions
# CUSTOM: Added as part of Task "Implement Pytest Suite"

import pytest

from docling_serve.core.citations import build_citation

@pytest.mark.parametrize(
    "doc_name, page, expected_citation",
    [
        ("MyDocument.pdf", 1, "MyDocument, p. 1"),
        ("AnotherDoc.docx", 10, "AnotherDoc, p. 10"),
        ("NoExtensionName", 5, "NoExtensionName, p. 5"),
        ("/path/to/MyDocument.pdf", 1, "MyDocument, p. 1"),
        ("  MyDocument.pdf  ", 1, "MyDocument, p. 1"), # Names needing stemming
        ("MyDocument.with.dots.pdf", 1, "MyDocument.with.dots, p. 1"),
        ("Plain Text File.txt", None, "Plain Text File"), # No page number
        ("WebPage", None, "WebPage"), # No page, no extension
        ("Document", 0, "Document"), # Page 0 should be treated as no page
        ("DocumentWithPageZero.pdf", 0, "DocumentWithPageZero"),
        ("DocumentWithNegativePage.pdf", -1, "DocumentWithNegativePage"), # Negative page
        ("", 1, "Unknown Document, p. 1"), # Empty doc_name with page
        ("", None, "Unknown Document"),     # Empty doc_name no page
    ],
)
def test_build_citation(doc_name: str, page: Optional[int], expected_citation: str):
    """Test build_citation with various inputs."""
    assert build_citation(doc_name, page) == expected_citation

def test_build_citation_doc_name_only_stem():
    """Test that build_citation uses only the stem of the doc_name."""
    assert build_citation("archive/reports/Q1Report.final.pdf", 5) == "Q1Report.final, p. 5"

def test_build_citation_no_page_number():
    """Test citation when page number is None."""
    assert build_citation("MyFile.txt", None) == "MyFile"

def test_build_citation_page_zero():
    """Test citation when page number is 0 (should omit page part)."""
    assert build_citation("MyFile.txt", 0) == "MyFile"
