# CUSTOM: This file contains functions for generating deterministic IDs for documents and chunks.
# Part of Task 3 implementation.

import hashlib
from pathlib import Path
from typing import Optional

def compute_doc_id(file_path: Optional[Path] = None, file_bytes: Optional[bytes] = None) -> str:
    """
    Computes a stable document ID (SHA-1 hash) from file content.
    Prioritizes file_bytes if provided, otherwise reads from file_path.

    Args:
        file_path: Path to the document file.
        file_bytes: Bytes of the document file.

    Returns:
        A 40-character hexadecimal SHA-1 hash of the file content.

    Raises:
        ValueError: If neither file_path nor file_bytes is provided.
    """
    if file_bytes is not None:
        data = file_bytes
    elif file_path is not None:
        try:
            data = file_path.read_bytes()
        except Exception as e:
            raise ValueError(f"Could not read file at {file_path}: {e}") from e
    else:
        raise ValueError("Either file_path or file_bytes must be provided to compute doc_id.")

    return hashlib.sha1(data).hexdigest()

def compute_chunk_id(doc_id: str, text: str, length: int = 16) -> str:
    """
    Computes a deterministic chunk ID (truncated SHA-1 hash) from the
    document ID and chunk text.

    Args:
        doc_id: The ID of the document the chunk belongs to.
        text: The text content of the chunk.
        length: The desired length of the hexadecimal chunk ID. Defaults to 16.

    Returns:
        A hexadecimal SHA-1 hash of the (doc_id + text) truncated to the specified length.
    """
    # Strip trailing whitespace/newlines from text as per task spec,
    # but also leading to ensure consistency if text_item.text might vary.
    # The spec only mentioned .strip() on (doc_id + text.strip()), implying text only.
    # Let's stick to spec: text.strip()
    raw_input = (doc_id + text.strip()).encode('utf-8')
    full_hash = hashlib.sha1(raw_input).hexdigest()
    return full_hash[:length]
