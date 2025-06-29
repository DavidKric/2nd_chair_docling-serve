# Pytest tests for the vector DB stub function
# CUSTOM: Added as part of Task "Implement Pytest Suite"

import pytest
import os
import logging
from unittest.mock import patch # patch is not used if monkeypatch is preferred for env vars

from docling_serve.indexing.vector_db import index_chunks_in_vector_db
from docling_serve.core.models import Chunk, ChunkMetadata # For creating dummy Chunk objects

# Helper to create dummy chunks for testing the stub function
def create_dummy_chunks(count: int) -> list[Chunk]:
    chunks = []
    for i in range(count):
        metadata = ChunkMetadata(
            doc_id="dummy_doc_id",
            doc_name="dummy_doc_name",
            page=1,
            chunk_index=i,
            section=["Dummy Section"],
            citation="dummy_doc_name, p. 1",
            location={"page": 1, "bbox": [0.1, 0.1, 0.2, 0.2]},
            content_type="paragraph"
        )
        chunk = Chunk(
            chunk_id=f"dummy_chunk_{i}",
            text=f"This is dummy chunk text {i}.",
            enriched_text=f"Enriched: This is dummy chunk text {i}.",
            metadata=metadata
        )
        chunks.append(chunk)
    return chunks

def test_index_chunks_weaviate_url_not_set(monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture):
    """Test index_chunks_in_vector_db when WEAVIATE_URL is not set."""
    monkeypatch.delenv("WEAVIATE_URL", raising=False) # Ensure it's not set

    dummy_chunks = create_dummy_chunks(3)
    doc_id = "test_doc_no_url"

    with caplog.at_level(logging.INFO):
        status = index_chunks_in_vector_db(chunks=dummy_chunks, doc_id=doc_id)

    assert status == "disabled"
    assert f"Vector-DB indexing disabled for doc_id {doc_id}. WEAVIATE_URL not set. Skipping." in caplog.text

def test_index_chunks_weaviate_url_set(monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture):
    """Test index_chunks_in_vector_db when WEAVIATE_URL is set."""
    test_url = "http://localhost:8080"
    monkeypatch.setenv("WEAVIATE_URL", test_url)

    dummy_chunks = create_dummy_chunks(5)
    doc_id = "test_doc_with_url"

    with caplog.at_level(logging.INFO):
        status = index_chunks_in_vector_db(chunks=dummy_chunks, doc_id=doc_id)

    assert status == "enabled_stub"
    expected_log_message = (
        f"WEAVIATE_URL is set ('{test_url}'). Future Weaviate indexing logic for doc_id {doc_id} "
        f"with {len(dummy_chunks)} chunks to be implemented here."
    )
    assert expected_log_message in caplog.text

def test_index_chunks_empty_chunk_list(monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture):
    """Test index_chunks_in_vector_db with an empty list of chunks."""
    test_url = "http://localhost:8081" # Different URL to distinguish logs if needed
    monkeypatch.setenv("WEAVIATE_URL", test_url)

    empty_chunks: list[Chunk] = []
    doc_id = "test_doc_empty_chunks"

    with caplog.at_level(logging.INFO):
        status = index_chunks_in_vector_db(chunks=empty_chunks, doc_id=doc_id)

    assert status == "enabled_stub"
    expected_log_message = (
        f"WEAVIATE_URL is set ('{test_url}'). Future Weaviate indexing logic for doc_id {doc_id} "
        f"with 0 chunks to be implemented here."
    )
    assert expected_log_message in caplog.text

    # Test with URL not set and empty chunks
    monkeypatch.delenv("WEAVIATE_URL", raising=False)
    caplog.clear()
    with caplog.at_level(logging.INFO):
        status_disabled = index_chunks_in_vector_db(chunks=empty_chunks, doc_id=doc_id)

    assert status_disabled == "disabled"
    assert f"Vector-DB indexing disabled for doc_id {doc_id}. WEAVIATE_URL not set. Skipping." in caplog.text
