# Pytest tests for the /v1/ingest API endpoint
# CUSTOM: Added as part of Task "Implement Pytest Suite"

import pytest
from fastapi.testclient import TestClient
from pathlib import Path
from typing import List, Optional, Dict, Any
from unittest.mock import MagicMock
import logging
import os

# Assuming MockDoclingChunk is defined in conftest.py
from tests.conftest import MockDoclingChunk
from docling_serve.core.models import IngestionApiResponse, Chunk, ChunkMetadata

def test_ingest_pdf_file_successful(
    client: TestClient,
    sample_pdf_path: Path,
    mocked_hybrid_chunker_components: Dict[str, MagicMock],
    monkeypatch: pytest.MonkeyPatch
):
    """Test successful ingestion of a PDF file with mocked chunker."""
    monkeypatch.delenv("WEAVIATE_URL", raising=False) # Ensure URL is not set for default status

    # Configure the mock HybridChunker instance
    mock_chunker_instance = mocked_hybrid_chunker_components["mock_hybrid_chunker_instance"]

    # Define what the mocked chunker.chunk() method should return
    mock_docling_chunks_data = [
        MockDoclingChunk(text="First chunk from PDF.", page_number=1, headings=["Title Page"], type="paragraph", bbox=[0.1, 0.1, 0.8, 0.2]),
        MockDoclingChunk(text="Second chunk, page 1.", page_number=1, headings=["Title Page", "Subtitle"], type="paragraph", bbox=[0.1, 0.3, 0.8, 0.4]),
        MockDoclingChunk(text="Table data.", page_number=2, headings=["Data Section"], type="table", bbox=[0.2,0.1,0.7,0.3]),
        MockDoclingChunk(text="Final paragraph on page 2.", page_number=2, headings=["Data Section", "Conclusion"], type="paragraph", bbox=None), # No bbox for this one
    ]
    mock_chunker_instance.chunk.return_value = mock_docling_chunks_data

    # Define behavior for contextualize - simple pass-through or prefix
    mock_chunker_instance.contextualize.side_effect = lambda chunk: f"Enriched: {chunk.text}"

    with open(sample_pdf_path, "rb") as f:
        response = client.post("/v1/ingest", files={"file": (sample_pdf_path.name, f, "application/pdf")})

    assert response.status_code == 200
    response_data = response.json()

    # Validate IngestionApiResponse structure
    assert "doc_id" in response_data
    assert response_data["doc_name"] == sample_pdf_path.stem # "sample"
    assert "chunks" in response_data
    assert response_data["vector_db_status"] == "disabled"

    api_response = IngestionApiResponse(**response_data) # Validate with Pydantic model
    assert len(api_response.chunks) == len(mock_docling_chunks_data)

    # Validate first chunk as an example
    first_api_chunk = api_response.chunks[0]
    first_mock_chunk = mock_docling_chunks_data[0]

    assert first_api_chunk.text == first_mock_chunk.text
    assert first_api_chunk.enriched_text == f"Enriched: {first_mock_chunk.text}"
    assert first_api_chunk.metadata.doc_id == api_response.doc_id
    assert first_api_chunk.metadata.doc_name == sample_pdf_path.stem
    assert first_api_chunk.metadata.page == first_mock_chunk.page_number
    assert first_api_chunk.metadata.chunk_index == 0
    assert first_api_chunk.metadata.section == first_mock_chunk.headings
    assert first_api_chunk.metadata.citation == f"{sample_pdf_path.stem}, p. {first_mock_chunk.page_number}"
    assert first_api_chunk.metadata.location == {"page": first_mock_chunk.page_number, "bbox": first_mock_chunk.bbox}
    assert first_api_chunk.metadata.content_type == first_mock_chunk.type
    assert first_api_chunk.chunk_id is not None # Check it's generated

    # Validate chunk with no bbox
    last_api_chunk = api_response.chunks[3]
    last_mock_chunk = mock_docling_chunks_data[3]
    assert last_api_chunk.metadata.location is None
    assert last_api_chunk.metadata.citation == f"{sample_pdf_path.stem}, p. {last_mock_chunk.page_number}"


def test_ingest_input_validation_no_file_no_source(client: TestClient):
    """Test API returns 400 if neither file nor source is provided."""
    response = client.post("/v1/ingest")
    assert response.status_code == 400
    assert "detail" in response.json()
    assert "file must be uploaded or a source URL" in response.json()["detail"]

def test_ingest_weaviate_url_toggle(
    client: TestClient,
    sample_txt_path: Path,
    mocked_hybrid_chunker_components: Dict[str, MagicMock],
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture
):
    """Test vector_db_status and logging based on WEAVIATE_URL."""
    mock_chunker_instance = mocked_hybrid_chunker_components["mock_hybrid_chunker_instance"]
    mock_chunker_instance.chunk.return_value = [
        MockDoclingChunk(text="Text file chunk.", page_number=None, headings=None, type="paragraph")
    ]
    mock_chunker_instance.contextualize.side_effect = lambda chunk: f"Enriched: {chunk.text}"

    # Case 1: WEAVIATE_URL not set
    monkeypatch.delenv("WEAVIATE_URL", raising=False)
    with open(sample_txt_path, "rb") as f, caplog.at_level(logging.INFO):
        response_disabled = client.post("/v1/ingest", files={"file": (sample_txt_path.name, f, "text/plain")})

    assert response_disabled.status_code == 200
    data_disabled = response_disabled.json()
    assert data_disabled["vector_db_status"] == "disabled"
    assert "Vector-DB indexing disabled" in caplog.text
    assert f"Prepared 1 chunks for doc {data_disabled['doc_id']} (vector DB status: disabled)" in caplog.text

    caplog.clear()

    # Case 2: WEAVIATE_URL is set
    test_weaviate_url = "http://fake-weaviate:8080"
    monkeypatch.setenv("WEAVIATE_URL", test_weaviate_url)
    with open(sample_txt_path, "rb") as f, caplog.at_level(logging.INFO):
        response_enabled = client.post("/v1/ingest", files={"file": (sample_txt_path.name, f, "text/plain")})

    assert response_enabled.status_code == 200
    data_enabled = response_enabled.json()
    assert data_enabled["vector_db_status"] == "enabled_stub"
    assert f"WEAVIATE_URL is set ('{test_weaviate_url}')" in caplog.text
    assert f"Prepared 1 chunks for doc {data_enabled['doc_id']} (vector DB status: enabled_stub)" in caplog.text

def test_ingest_url_input_docling_hash_missing(
    client: TestClient,
    mocked_hybrid_chunker_components: Dict[str, MagicMock],
    monkeypatch: pytest.MonkeyPatch
):
    """
    Test ingestion from URL when Docling's binary_hash is NOT available.
    This relies on the DocumentConverter being mocked or the actual one
    returning a doc without origin.binary_hash.
    For this test, we need to mock the behavior *after* DocumentConverter.convert
    specifically for the doc.origin part.
    """
    mock_doc_converter_instance = MagicMock()
    mock_doc_result_instance = MagicMock()
    mock_docling_document_instance = MagicMock()

    # Simulate doc.origin not having binary_hash or being None
    mock_docling_document_instance.origin = MagicMock()
    mock_docling_document_instance.origin.binary_hash = None # Key part: simulate hash missing

    mock_doc_result_instance.document = mock_docling_document_instance
    mock_doc_converter_instance.convert.return_value = mock_doc_result_instance

    # Patch the DocumentConverter constructor in ingest.py to return our mock_doc_converter_instance
    monkeypatch.setattr("docling_serve.api.ingest.DocumentConverter", lambda config: mock_doc_converter_instance)

    # Mock HybridChunker as it would still be called if DocumentConverter succeeds
    mock_chunker_instance = mocked_hybrid_chunker_components["mock_hybrid_chunker_instance"]
    mock_chunker_instance.chunk.return_value = [] # No chunks needed as it should fail before that for URL

    response = client.post("/v1/ingest", data={"source": "http://example.com/test.pdf"})

    assert response.status_code == 501 # Not Implemented, as per current error handling
    assert "doc_id could not be determined for URL input" in response.json()["detail"]

# More tests can be added:
# - Different file types (DOCX, TXT) similar to PDF test.
# - Test with DoclingChunk having no page_number (citation should not include "p. None").
# - Test with DoclingChunk having empty list for headings (section should be None or empty list).
# - Test actual OCR path if we can reliably mock/trigger it (harder without running full Docling).
# - Test for extremely large files (might require adjusting TestClient timeout or be out of scope for unit tests).
# - Test for specific error conditions from Docling (e.g., conversion failure).
# - Test for `doc_id` from URL when `doc.origin.binary_hash` IS available (requires more specific mocking of DocumentConverter result).

def test_ingest_doc_with_no_page_info(
    client: TestClient,
    sample_txt_path: Path,
    mocked_hybrid_chunker_components: Dict[str, MagicMock],
    monkeypatch: pytest.MonkeyPatch
):
    """Test ingestion of a document where chunks have no page info."""
    monkeypatch.delenv("WEAVIATE_URL", raising=False)
    mock_chunker_instance = mocked_hybrid_chunker_components["mock_hybrid_chunker_instance"]

    mock_docling_chunks_data = [
        MockDoclingChunk(text="Chunk from text file.", page_number=None, headings=None, type="paragraph", bbox=None)
    ]
    mock_chunker_instance.chunk.return_value = mock_docling_chunks_data
    mock_chunker_instance.contextualize.side_effect = lambda chunk: f"Enriched: {chunk.text}"

    with open(sample_txt_path, "rb") as f:
        response = client.post("/v1/ingest", files={"file": (sample_txt_path.name, f, "text/plain")})

    assert response.status_code == 200
    response_data = response.json()
    api_response = IngestionApiResponse(**response_data)

    assert api_response.chunks[0].metadata.page is None
    assert api_response.chunks[0].metadata.citation == sample_txt_path.stem # e.g., "sample"
    assert api_response.chunks[0].metadata.location is None
    assert api_response.chunks[0].metadata.section is None
    assert api_response.chunks[0].metadata.content_type == "paragraph"
