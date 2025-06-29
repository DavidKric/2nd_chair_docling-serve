# Pydantic models for ingestion API
# CUSTOM: This file is part of the new ingestion API support modules

from typing import List, Optional

from pydantic import BaseModel, HttpUrl

class ChunkMetadata(BaseModel):
    """
    Metadata for a single text chunk.
    """
    # CUSTOM: Added doc_id, doc_name, chunk_index as per Task 3
    # CUSTOM: Changed page to int (non-optional) as per Task 3 schema
    # CUSTOM: Added optional section as per Task 3
    doc_id: str
    doc_name: str
    page: int  # Assuming page numbers are always available or defaulted (e.g., to 0 or 1)
    chunk_index: int
    section: Optional[str] = None
    # Further metadata fields can be added here in subsequent tasks

class Chunk(BaseModel):
    """
    A single text chunk extracted from a document.
    """
    # CUSTOM: Added chunk_id as per Task 3
    chunk_id: str
    text: str
    metadata: ChunkMetadata

class IngestionRequest(BaseModel): # Added for completeness, though not strictly required by plan for response
    """
    Model for the ingestion request if we want to support JSON body for URL.
    Not directly used if only form-data for file and query/path for URL.
    However, the task mentioned "JSON with a file URL", this could model that.
    """
    source: HttpUrl

class IngestionResponse(BaseModel):
    """
    Response model for the document ingestion endpoint.
    """
    # CUSTOM: Added doc_id as per Task 3
    doc_id: str
    doc_name: str # doc_name was already here, ensuring it stays
    chunks: List[Chunk]
    # doc_id: Optional[str] = None # Previous placeholder, now a required field above
