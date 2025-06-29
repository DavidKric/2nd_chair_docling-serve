# Pytest tests for ID generation functions
# CUSTOM: Added as part of Task "Implement Pytest Suite"

import pytest
from pathlib import Path
import tempfile
import os
import hashlib

from docling_serve.core.ids import compute_doc_id, compute_chunk_id

def test_compute_doc_id_with_bytes():
    """Test compute_doc_id with direct byte input."""
    test_bytes = b"This is a test document."
    expected_hash = hashlib.sha1(test_bytes).hexdigest()
    assert compute_doc_id(file_bytes=test_bytes) == expected_hash

def test_compute_doc_id_with_file_path():
    """Test compute_doc_id with a file path."""
    test_content = b"Sample content for file path test."
    expected_hash = hashlib.sha1(test_content).hexdigest()

    with tempfile.NamedTemporaryFile(delete=False, mode='wb') as tmp_file:
        tmp_file.write(test_content)
        tmp_file_path = tmp_file.name

    try:
        assert compute_doc_id(file_path=Path(tmp_file_path)) == expected_hash
    finally:
        os.remove(tmp_file_path)

def test_compute_doc_id_no_input():
    """Test compute_doc_id raises ValueError if no input is provided."""
    with pytest.raises(ValueError, match="Either file_path or file_bytes must be provided"):
        compute_doc_id()

def test_compute_doc_id_bad_file_path():
    """Test compute_doc_id raises ValueError for a non-existent file."""
    # Using a more specific error type might be better if the function raises it,
    # but ValueError is what's specified for "Could not read file".
    with pytest.raises(ValueError, match="Could not read file"):
        compute_doc_id(file_path=Path("non_existent_file.txt"))

def test_compute_chunk_id_basic():
    """Test basic functionality of compute_chunk_id."""
    doc_id = "test_doc_id_123"
    text = "This is the chunk text."
    # Expected: sha1("test_doc_id_123This is the chunk text.").hexdigest()[:16]
    # Pre-calculate expected hash to ensure stability
    raw_input = (doc_id + text.strip()).encode('utf-8')
    expected_full_hash = hashlib.sha1(raw_input).hexdigest()
    expected_chunk_id = expected_full_hash[:16]

    assert compute_chunk_id(doc_id, text) == expected_chunk_id

def test_compute_chunk_id_with_stripping():
    """Test compute_chunk_id correctly strips text."""
    doc_id = "doc456"
    text_with_spaces = "  Chunk text with leading/trailing spaces.  \n"
    text_stripped = "Chunk text with leading/trailing spaces."

    raw_input_stripped = (doc_id + text_stripped).encode('utf-8')
    expected_chunk_id_stripped = hashlib.sha1(raw_input_stripped).hexdigest()[:16]

    assert compute_chunk_id(doc_id, text_with_spaces) == expected_chunk_id_stripped

def test_compute_chunk_id_different_lengths():
    """Test compute_chunk_id with different output lengths."""
    doc_id = "doc789"
    text = "Some other text."
    raw_input = (doc_id + text.strip()).encode('utf-8')
    full_hash = hashlib.sha1(raw_input).hexdigest()

    assert compute_chunk_id(doc_id, text, length=10) == full_hash[:10]
    assert compute_chunk_id(doc_id, text, length=32) == full_hash[:32]
    assert compute_chunk_id(doc_id, text, length=40) == full_hash # Max length of SHA1 hex

def test_compute_chunk_id_empty_text():
    """Test compute_chunk_id with empty text (after stripping)."""
    doc_id = "doc_empty_text"
    text = "   \n   " # Text that becomes empty after strip()
    raw_input = (doc_id + "").encode('utf-8') # text.strip() is ""
    expected_chunk_id = hashlib.sha1(raw_input).hexdigest()[:16]

    assert compute_chunk_id(doc_id, text) == expected_chunk_id

def test_compute_chunk_id_consistency():
    """Test compute_chunk_id produces consistent IDs for the same input."""
    doc_id = "consistent_doc"
    text = "This text should always produce the same chunk ID."

    chunk_id1 = compute_chunk_id(doc_id, text)
    chunk_id2 = compute_chunk_id(doc_id, text)

    assert chunk_id1 == chunk_id2
