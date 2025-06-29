# CUSTOM: Stub for vector database indexing logic.
# Added as part of Task 5.

import os
import logging
from typing import List

# Import Chunk from the correct location. Assuming it's in docling_serve.core.models
# Adjust if Chunk is defined elsewhere or if a different representation is needed here.
from docling_serve.core.models import Chunk

logger = logging.getLogger(__name__)

def index_chunks_in_vector_db(chunks: List[Chunk], doc_id: str) -> str:
    """
    Stub function for future upsert of chunks into a vector database like Weaviate.
    Currently, it's a no-op unless the WEAVIATE_URL environment variable is set.

    Args:
        chunks: A list of Chunk objects to be indexed.
        doc_id: The ID of the document these chunks belong to.

    Returns:
        A string indicating the status of the indexing attempt:
        "disabled" if WEAVIATE_URL is not set.
        "enabled_stub" if WEAVIATE_URL is set (indicating the stub was called).
    """
    weaviate_url = os.getenv("WEAVIATE_URL")

    if not weaviate_url:
        logger.info(f"Vector-DB indexing disabled for doc_id {doc_id}. WEAVIATE_URL not set. Skipping.")
        return "disabled"
    else:
        logger.info(
            f"WEAVIATE_URL is set ('{weaviate_url}'). Future Weaviate indexing logic for doc_id {doc_id} "
            f"with {len(chunks)} chunks to be implemented here."
        )
        # Placeholder for actual Weaviate client interaction
        # For example:
        # client = weaviate.Client(weaviate_url)
        # objects_to_create = []
        # for chunk_obj in chunks:
        #     properties = {
        #         "chunk_id": chunk_obj.chunk_id,
        #         "text": chunk_obj.text,
        #         "doc_id": chunk_obj.metadata.doc_id,
        #         "doc_name": chunk_obj.metadata.doc_name,
        #         "page": chunk_obj.metadata.page,
        #         "section": chunk_obj.metadata.section,
        #         "citation": chunk_obj.metadata.citation,
        #         "chunk_index": chunk_obj.metadata.chunk_index,
        #         "location": chunk_obj.metadata.location,
        #     }
        #     # Remove None properties for Weaviate if it doesn't handle them well for certain types
        #     properties = {k: v for k, v in properties.items() if v is not None}

        #     objects_to_create.append({
        #         "class": "DocumentChunk", # Target class name in Weaviate
        #         "properties": properties,
        #         "id": chunk_obj.chunk_id # Use our deterministic chunk_id as Weaviate's UUID
        #     })
        # client.batch.create_objects(objects_to_create)
        # logger.info(f"Successfully stub-indexed {len(chunks)} chunks for doc_id {doc_id} (not really).")
        return "enabled_stub"
