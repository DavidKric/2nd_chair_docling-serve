# Ingestion API endpoint
# CUSTOM: This file is part of the new ingestion API

import asyncio
import tempfile
import os
import logging # CUSTOM: Added for Task 5 logging
from pathlib import Path
from typing import Optional, List # CUSTOM: Added List for Task 5

from fastapi import APIRouter, File, UploadFile, HTTPException, Form
from pydantic import HttpUrl

from docling_core.converter import DocumentConverter, ConverterConfig
# CUSTOM: Refactor - TextItem, DocumentAuthorship, Group, SectionHeaderItem may no longer be directly needed here
from docling_core.document.docling_document import DoclingDocument, DocumentOrigin
# from docling_core.document.document_authorship import DocumentAuthorship
# from docling_core.document.document_elements import Group, SectionHeaderItem

# CUSTOM: Updated model import for Task 5
from docling_serve.core.models import Chunk, ChunkMetadata, IngestionApiResponse
# CUSTOM: Import ID generation functions from Task 3
from docling_serve.core.ids import compute_doc_id, compute_chunk_id
# CUSTOM: Import citation building function from Task 4
from docling_serve.core.citations import build_citation
# CUSTOM: Import stub indexing function for Task 5
from docling_serve.indexing.vector_db import index_chunks_in_vector_db

# CUSTOM: Refactor - Imports for HybridChunker (Task 6 plan / Refactor)
from transformers import AutoTokenizer
# Assuming these paths are correct based on typical docling structure. May need verification.
from docling_core.chunker.tokenizer.huggingface import HuggingFaceTokenizer
from docling.chunker import HybridChunker # Or from docling.chunking import HybridChunker
from docling_core.document.chunk import Chunk as DoclingChunk # To avoid Pydantic model name collision

# CUSTOM: Setup logger for Task 5
logger = logging.getLogger(__name__)

# CUSTOM: Refactor - HybridChunker components (Task 6 plan / Refactor)
# It's often better to initialize these once if they are thread-safe, e.g. in app lifespan.
# For now, initializing per call as a starting point, but noting this for optimization.
EMBED_MODEL_ID = "sentence-transformers/all-MiniLM-L6-v2"
# Consider try-except for model loading if network issues are possible
try:
    hf_tokenizer_global = AutoTokenizer.from_pretrained(EMBED_MODEL_ID)
    docling_tokenizer_global = HuggingFaceTokenizer(tokenizer=hf_tokenizer_global)
    hybrid_chunker_global = HybridChunker(tokenizer=docling_tokenizer_global, merge_peers=True)
except Exception as e:
    logger.error(f"Failed to initialize HybridChunker components: {e}")
    # Fallback or raise critical error - for now, endpoint will fail if these are not ready
    hf_tokenizer_global = None
    docling_tokenizer_global = None
    hybrid_chunker_global = None


# Initialize router
# The prefix /v1 will be added when including this router in the main app
router = APIRouter(
    tags=["Ingestion"],
)

@router.post("/ingest", response_model=IngestionApiResponse) # CUSTOM: Changed response_model for Task 5
async def ingest_document(
    file: Optional[UploadFile] = File(None, description="Document file to ingest."),
    source: Optional[HttpUrl] = Form(None, description="URL of the document to ingest.") # Using Form for HttpUrl to be part of form-data
):
    """
    Ingests a document from a file upload or URL, parses it,
    and returns extracted text chunks with basic metadata.
    """
    if not file and not source:
        raise HTTPException(
            status_code=400,
            detail="Either a file must be uploaded or a source URL must be provided.",
        )

    input_to_docling: str | bytes
    temp_file_path: Optional[str] = None
    doc_name: str = "untitled_document"
    doc_id: str = ""
    file_bytes_content: Optional[bytes] = None

    # CUSTOM: Refactor - Removed unused sections_map (Task 6 plan / Refactor)
    # sections_map: list[tuple[int, str]] = []

    try:
        if file:
            original_filename = file.filename if file.filename else "uploaded_file"
            doc_name = Path(original_filename).stem

            file_bytes_content = await file.read()
            doc_id = compute_doc_id(file_bytes=file_bytes_content)

            # Save UploadFile to a temporary file for Docling
            # Suffix helps Docling identify file type if it relies on it.
            suffix = Path(original_filename).suffix if original_filename else ".tmp"
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp_file:
                tmp_file.write(file_bytes_content)
                temp_file_path = tmp_file.name
            input_to_docling = temp_file_path

        elif source:
            doc_name = Path(str(source)).stem
            # For URLs, we need to fetch the content to calculate doc_id based on bytes.
            # This means Docling will also process these bytes, not the URL directly,
            # unless Docling provides a binary hash we can trust.
            # For now, assume we download then process.
            # This part would need an HTTP client like httpx if we implement download here.
            # For simplicity in this step, if source is a URL, we'll try to use Docling's hash
            # if available, otherwise this path will need enhancement or will fail if
            # Docling can't provide a hash and we don't download.
            # Let's assume Docling will process the URL directly for now,
            # and we'll try to get the hash from Docling's result. If not possible, this is a gap.
            input_to_docling = str(source)
            # doc_id will be computed after conversion if possible from Docling result,
            # or this will be an issue to resolve (downloading URL content first).

        else: # Should be caught by the initial check, but as a safeguard
             raise HTTPException(status_code=500, detail="Input source could not be determined.")

        converter = DocumentConverter(
            config=ConverterConfig(ocr_backend="default", layout_backend="default")
        )

        # Perform conversion
        # print(f"DEBUG: Converting document from: {input_to_docling}")
        result = await asyncio.to_thread(converter.convert, input_to_docling)
        doc: Optional[DoclingDocument] = result.document

        if not doc:
            raise HTTPException(status_code=500, detail="Document conversion failed or produced no document.")

        # CUSTOM: doc_id calculation strategy
        if file: # We already computed doc_id from file_bytes_content
            pass
        elif source:
            # Try to get hash from Docling's origin info if it's a URL
            # This is speculative, actual field name and hash type need verification
            if doc.origin and hasattr(doc.origin, 'binary_hash') and doc.origin.binary_hash:
                # Assuming binary_hash is SHA1 hex, if not, this needs adjustment
                # Also, this hash must be from the *original, unmodified* remote file bytes.
                doc_id = doc.origin.binary_hash
                # print(f"DEBUG: Using doc_id from Docling origin: {doc_id}")
            else:
                # FALLBACK: If Docling doesn't provide a hash for URLs, we MUST download the file first
                # to compute a content-based doc_id. This requires adding an HTTP client (e.g. httpx)
                # and downloading the content of `source` URL to `file_bytes_content`.
                # For now, this is a known limitation if Docling doesn't provide the hash.
                # If we had file_bytes_content from a download, it would be:
                # doc_id = compute_doc_id(file_bytes=downloaded_url_content)
                # And Docling would then process these bytes (e.g. via a temp file).
                # For this iteration, if hash not from docling, doc_id might remain empty for URL,
                # which is not ideal and needs to be addressed.
                # To ensure it's not empty, let's raise if not found for URL for now.
                raise HTTPException(status_code=501,
                                    detail="doc_id could not be determined for URL input. "
                                           "Docling did not provide a binary_hash, and direct URL download "
                                           "for hashing is not yet implemented in this version.")

        if not doc_id: # Final check
            raise HTTPException(status_code=500, detail="doc_id could not be determined.")

        # CUSTOM: Section Extraction (Opportunistic)
        # This is a simplified approach. A more robust one would map char offsets.
        # Docling's `doc.groups` often contains structural elements like sections.
        # A `Group` can have a `label` (e.g. "SECTION_HEADER") and `texts` (list of TextItems).
        # Or `text_item.parent_group` might point to a group.
        # The `SectionHeaderItem` is a specific type of `TextItem`.
        # Let's try to find SectionHeaderItems and build a simple map.
        # This assumes text_items appear in order in doc.texts.

        # Placeholder for actual section mapping logic.
        # For now, we will defer proper section implementation as it might be complex.
        # The task allows deferring if non-trivial.
        # Proper implementation would involve mapping character offsets of TextItems
        # to the character offsets of SectionHeaderItems or titles of Groups.
        # CUSTOM: Task 3 - Section Heading Extraction Status
        # Section heading extraction is currently DEFERRED. The logic to reliably map
        # TextItems to their corresponding section titles based on DoclingDocument structure
        # (e.g., character offsets, group hierarchy) requires further investigation
        # and was deemed non-trivial for this iteration.
        # Thus, `metadata.section` will be `None` for all chunks.
        # current_section_title: Optional[str] = None # This will be replaced by docling_chunk.headings

        # CUSTOM: Refactor - Use HybridChunker (Task 6 plan / Refactor)
        if not hybrid_chunker_global or not docling_tokenizer_global:
            logger.error("HybridChunker or Tokenizer not initialized. Cannot process document.")
            raise HTTPException(status_code=503, detail="Chunking service not available.")

        extracted_chunks: List[Chunk] = []
        # Assuming HybridChunker.chunk() is not async, if it is, needs 'await asyncio.to_thread'
        # Also, DoclingDocument 'doc' is the input to chunker.chunk()
        try:
            # Note: The plan uses `list(chunker.chunk(dl_doc=dl_doc))`.
            # Here, `doc` is the `DoclingDocument` instance.
            hybrid_docling_chunks: List[DoclingChunk] = list(hybrid_chunker_global.chunk(dl_doc=doc))
        except Exception as e:
            logger.error(f"Error during HybridChunker processing for doc_id {doc_id}: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"Error during document chunking: {str(e)}")

        for chunk_idx, docling_chunk in enumerate(hybrid_docling_chunks):
            text_content = docling_chunk.text
            if not text_content or text_content.isspace(): # Should ideally be handled by HybridChunker
                continue

            # Enriched text for embedding
            enriched_text_content = hybrid_chunker_global.contextualize(docling_chunk)

            # Page number from DoclingChunk
            # Assuming docling_chunk.page_number exists and is Optional[int]
            page_number: Optional[int] = getattr(docling_chunk, 'page_number', None)

            # Headings for section metadata
            # Assuming docling_chunk.headings is List[str] or similar
            headings: Optional[List[str]] = getattr(docling_chunk, 'headings', None)
            if headings is not None and not isinstance(headings, list): # Ensure it's a list if not None
                headings = [str(headings)]


            # Content type
            content_type: Optional[str] = getattr(docling_chunk, 'type', None)
            if content_type is None: # Fallback if 'type' attribute is missing
                content_type = "paragraph" # Default content type

            # CUSTOM: Refactor - Log table content for inspection (Task 6 plan / Refactor)
            if content_type == 'table':
                logger.debug(f"Table chunk detected (doc_id: {doc_id}, chunk_idx: {chunk_idx}). Text content snippet: '{text_content[:100]}...'")

            # CUSTOM: Generate chunk_id (Task 3)
            chunk_id = compute_chunk_id(doc_id=doc_id, text=text_content)

            # CUSTOM: Task 4 - Build citation string (Visual Grounding)
            citation_str = build_citation(doc_name=doc_name, page=page_number)

            # CUSTOM: Task 4 - Prepare location data (Visual Grounding)
            # How HybridChunker chunks provide bbox needs to be verified.
            # Option 1: Direct bbox attribute on DoclingChunk
            # Option 2: Through provenance items within DoclingChunk
            # For now, let's assume a direct 'bbox' attribute similar to 'page_number'.
            # This is a critical point for visual grounding.
            bbox_from_chunk: Optional[List[float]] = None
            if hasattr(docling_chunk, 'bbox') and isinstance(docling_chunk.bbox, list) and len(docling_chunk.bbox) == 4:
                 if all(isinstance(coord, (float, int)) for coord in docling_chunk.bbox):
                    bbox_from_chunk = [float(coord) for coord in docling_chunk.bbox]

            # If not direct, try to get from provenance if available on DoclingChunk
            elif hasattr(docling_chunk, 'prov') and docling_chunk.prov and \
                 hasattr(docling_chunk.prov[0], 'bbox') and \
                 isinstance(docling_chunk.prov[0].bbox, list) and len(docling_chunk.prov[0].bbox) == 4:
                if all(isinstance(coord, (float, int)) for coord in docling_chunk.prov[0].bbox):
                    bbox_from_chunk = [float(coord) for coord in docling_chunk.prov[0].bbox]
                    # If page_number was None but prov[0] has one, prefer prov[0]'s page for location
                    if page_number is None and docling_chunk.prov[0].page_no is not None:
                        page_number = docling_chunk.prov[0].page_no


            location_info: Optional[dict] = None
            if page_number is not None and bbox_from_chunk:
                location_info = {"page": page_number, "bbox": bbox_from_chunk}

            # CUSTOM: Populate enhanced metadata
            metadata = ChunkMetadata(
                doc_id=doc_id,
                doc_name=doc_name,
                page=page_number,
                chunk_index=chunk_idx,
                section=headings, # From docling_chunk.headings
                citation=citation_str,
                location=location_info,
                content_type=content_type # From docling_chunk.type
            )

            current_chunk = Chunk(
                chunk_id=chunk_id,
                text=text_content,
                enriched_text=enriched_text_content,
                metadata=metadata
            )
            extracted_chunks.append(current_chunk)

        # CUSTOM: Task 5 - Call stub indexing function and log status
        vector_db_status = index_chunks_in_vector_db(chunks=extracted_chunks, doc_id=doc_id) # type: ignore
        logger.info(
            "Prepared %s chunks for doc %s (vector DB status: %s)",
            len(extracted_chunks),
            doc_id,
            vector_db_status, # Using the status from the function
        )

        return IngestionApiResponse(
            doc_id=doc_id,
            doc_name=doc_name,
            chunks=extracted_chunks,
            vector_db_status=vector_db_status
        )

    except HTTPException:
        raise
    except Exception as e:
        # print(f"DEBUG: Error during ingestion: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error processing document: {str(e)}")
    finally:
        if temp_file_path and os.path.exists(temp_file_path):
            os.remove(temp_file_path)
        if file:
            await file.close()

@router.get("/ingest/health", status_code=200)
async def health_check():
    """Simple health check for the ingestion endpoint."""
    return {"status": "ok"}
