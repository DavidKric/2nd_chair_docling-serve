# Pydantic models for ingestion API
# CUSTOM: This file is part of the new ingestion API support modules

from typing import List, Optional, Dict, Any # Added Dict, Any for location

from pydantic import BaseModel, HttpUrl, Field

class ChunkMetadata(BaseModel):
    """
    Metadata for a single text chunk.
    """
    # CUSTOM: Added doc_id, doc_name, chunk_index as per Task 3
    # CUSTOM: Added optional section as per Task 3
    # CUSTOM: Task 4 - Reverted page to Optional[int] and added citation, location
    doc_id: str
    doc_name: str
    page: Optional[int] = None # Changed back to Optional as per Task 4 schema and requirements
    chunk_index: int
    section: Optional[str] = None
    citation: str
    location: Optional[Dict[str, Any]] = Field(default=None, examples=[{"page": 1, "bbox": [0.1, 0.1, 0.5, 0.2]}])
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
    doc_name: str
    chunks: List[Chunk]
    # This model might be deprecated in favor of IngestionApiResponse for the /ingest endpoint


# CUSTOM: New response model for Task 5 to include vector_db_status
class IngestionApiResponse(BaseModel):
    """
    Standard API response for the document ingestion endpoint, including vector DB status.
    """
    doc_id: str
    doc_name: str
    chunks: List[Chunk] # List of Chunk objects (which include metadata)
    vector_db_status: str
