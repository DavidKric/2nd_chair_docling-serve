# CUSTOM: This file contains functions for generating human-readable citations.
# Part of Task 4 implementation.

from pathlib import Path
from typing import Optional

def build_citation(doc_name: str, page: Optional[int]) -> str:
    """
    Builds a human-readable citation string from document name and page number.

    Args:
        doc_name: The original name of the document (e.g., "LeaseAgreement.pdf", "/tmp/MyDoc.docx").
                  The function will extract the stem (filename without extension).
        page: The page number. If None or 0, the page part is omitted.
              (Task spec implies page=0 from non-paginated source should also omit "p. N")

    Returns:
        A formatted citation string, e.g., "LeaseAgreement, p. 3" or "MyDoc".
    """
    if not doc_name: # Handle empty doc_name gracefully, though unlikely
        base = "Unknown Document"
    else:
        base = Path(doc_name).stem  # Extracts filename without extension and leading paths

    if page is not None and page > 0: # Only add page if it's a positive integer
        return f"{base}, p. {page}"
    else:
        return base
