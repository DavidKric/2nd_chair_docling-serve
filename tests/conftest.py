# Pytest fixtures for the test suite
# CUSTOM: Added as part of Task "Implement Pytest Suite"

import pytest
from fastapi.testclient import TestClient
from pathlib import Path
from typing import List, Optional, Dict, Any, Generator
from unittest.mock import MagicMock, patch

from docling_serve.app import create_app # Main FastAPI app factory
# Assuming DoclingChunk is the type yielded by HybridChunker.chunk
# This might need to be imported from docling_core.document.chunk or similar
# For now, we'll define a simple mockable class for it.

class MockDoclingChunk:
    """A mock class for docling_core.document.chunk.Chunk"""
    def __init__(self, text: str, page_number: Optional[int], headings: Optional[List[str]], type: str, bbox: Optional[List[float]] = None, prov: Optional[List[Any]] = None):
        self.text = text
        self.page_number = page_number
        self.headings = headings
        self.type = type
        self.bbox = bbox # Direct bbox attribute
        self.prov = prov # Provenance items, e.g., for alternative bbox access

    def __repr__(self):
        return f"MockDoclingChunk(text='{self.text[:20]}...', page={self.page_number}, type='{self.type}')"


@pytest.fixture(scope="session")
def client() -> Generator[TestClient, None, None]:
    """
    Provides a TestClient instance for the FastAPI application.
    """
    app = create_app()
    with TestClient(app) as c:
        yield c

@pytest.fixture(scope="session")
def fixtures_dir() -> Path:
    """
    Returns the path to the test fixtures directory.
    """
    return Path(__file__).parent / "fixtures"

@pytest.fixture(scope="session")
def sample_pdf_path(fixtures_dir: Path) -> Path:
    return fixtures_dir / "sample.pdf"

@pytest.fixture(scope="session")
def sample_docx_path(fixtures_dir: Path) -> Path:
    return fixtures_dir / "sample.docx"

@pytest.fixture(scope="session")
def sample_txt_path(fixtures_dir: Path) -> Path:
    return fixtures_dir / "sample.txt"

@pytest.fixture(scope="session")
def scanned_sample_pdf_path(fixtures_dir: Path) -> Path:
    return fixtures_dir / "scanned_sample.pdf"


@pytest.fixture
def mocked_hybrid_chunker_components(monkeypatch: pytest.MonkeyPatch) -> Dict[str, MagicMock]:
    """
    Mocks the HybridChunker and its related components (AutoTokenizer, HuggingFaceTokenizer).
    Allows tests to control the output of the chunking process.

    Returns a dictionary of mocks for further configuration in tests if needed:
    {
        "mock_autotokenizer_from_pretrained": mock_autotokenizer_from_pretrained,
        "mock_hf_tokenizer_class": mock_hf_tokenizer_class,
        "mock_hybrid_chunker_class": mock_hybrid_chunker_class,
        "mock_hybrid_chunker_instance": mock_hybrid_chunker_instance
    }
    """
    mock_autotokenizer_from_pretrained = MagicMock()
    # This mock instance will be returned by AutoTokenizer.from_pretrained()
    mock_tokenizer_instance = MagicMock()
    mock_autotokenizer_from_pretrained.return_value = mock_tokenizer_instance

    monkeypatch.setattr("transformers.AutoTokenizer.from_pretrained", mock_autotokenizer_from_pretrained)

    mock_hf_tokenizer_class = MagicMock()
    mock_docling_tokenizer_instance = MagicMock()
    mock_hf_tokenizer_class.return_value = mock_docling_tokenizer_instance
    # The path to HuggingFaceTokenizer used in ingest.py
    monkeypatch.setattr("docling_serve.api.ingest.HuggingFaceTokenizer", mock_hf_tokenizer_class)
    # Also patch the global instance if it's used directly due to initialization at module level
    monkeypatch.setattr("docling_serve.api.ingest.docling_tokenizer_global", mock_docling_tokenizer_instance)


    mock_hybrid_chunker_class = MagicMock()
    mock_hybrid_chunker_instance = MagicMock()

    # Default behavior for mocked chunker - can be overridden in tests
    mock_hybrid_chunker_instance.chunk.return_value = [
        MockDoclingChunk(text="Default chunk 1 from mock.", page_number=1, headings=["Section 1"], type="paragraph", bbox=[0.1,0.1,0.2,0.2]),
        MockDoclingChunk(text="Default chunk 2 from mock.", page_number=1, headings=["Section 1"], type="paragraph", bbox=[0.2,0.2,0.3,0.3])
    ]
    mock_hybrid_chunker_instance.contextualize.side_effect = lambda chunk: f"Enriched: {chunk.text}"

    mock_hybrid_chunker_class.return_value = mock_hybrid_chunker_instance
    # The path to HybridChunker used in ingest.py
    monkeypatch.setattr("docling_serve.api.ingest.HybridChunker", mock_hybrid_chunker_class)
    # Also patch the global instance
    monkeypatch.setattr("docling_serve.api.ingest.hybrid_chunker_global", mock_hybrid_chunker_instance)

    # Patch the global tokenizer variables in ingest.py to use these mocks
    monkeypatch.setattr("docling_serve.api.ingest.hf_tokenizer_global", mock_tokenizer_instance)

    # This is important: the global variables in ingest.py are initialized at import time.
    # If the test needs to control their mocked behavior *before* the ingest module is fully imported
    # by the TestClient loading the app, this monkeypatching might need to happen earlier,
    # or the ingest.py module needs to be structured to allow easier patching of these globals,
    # e.g., by having them initialized by a function that can be patched.
    # For now, this fixture patches them. If tests show issues with global instances not being
    # patched correctly by the time the endpoint code runs, we may need to adjust how globals
    # are initialized in ingest.py or how they are patched here.

    # Ensure the global chunker in ingest.py is the instance we control
    # This is critical because ingest.py initializes hybrid_chunker_global at module level.
    # We need to make sure that by the time the endpoint is called, it uses our mock.
    import docling_serve.api.ingest
    docling_serve.api.ingest.hybrid_chunker_global = mock_hybrid_chunker_instance
    docling_serve.api.ingest.docling_tokenizer_global = mock_docling_tokenizer_instance
    docling_serve.api.ingest.hf_tokenizer_global = mock_tokenizer_instance


    return {
        "mock_autotokenizer_from_pretrained": mock_autotokenizer_from_pretrained,
        "mock_hf_tokenizer_class": mock_hf_tokenizer_class,
        "mock_hybrid_chunker_class": mock_hybrid_chunker_class,
        "mock_hybrid_chunker_instance": mock_hybrid_chunker_instance
    }
