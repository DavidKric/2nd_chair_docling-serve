# Usage and Integration Guide: Docling Serve Ingestion API

This document provides instructions on how to run the `docling-serve` service with the new ingestion pipeline, how to run the test suite, details about the expected API response, and guidelines for future integration with Weaviate.

## How to Run the Service

### Prerequisites

*   Python (version specified in `pyproject.toml`, e.g., >=3.10)
*   `uv` (recommended, for managing dependencies as per `pyproject.toml`) or `pip`.
*   Access to a terminal/shell.

### Dependency Installation

1.  Clone the repository.
2.  Navigate to the root directory of the project.
3.  If using `uv`:
    ```bash
    uv pip sync
    ```
    To include development dependencies (like `pytest`):
    ```bash
    uv pip sync --all-extras # Or specify groups like dev, ui etc.
    ```
4.  Alternatively, if using `pip` with `setuptools` (less common for this project structure but as a general fallback):
    ```bash
    pip install -e .[dev] # Or relevant extras
    ```

### Running the FastAPI Application

The service can be run using Uvicorn. The main application is created by the `create_app` factory in `docling_serve/app.py`.

```bash
uvicorn docling_serve.app:create_app --factory --reload --host 0.0.0.0 --port 8000
```

*   `--factory`: Tells Uvicorn to use `create_app()` to get the FastAPI app instance.
*   `--reload`: Enables auto-reloading on code changes (useful for development).
*   `--host 0.0.0.0`: Makes the service accessible on your network.
*   `--port 8000`: Specifies the port to run on.

The `docling-serve` CLI might also be available if configured to run this application:
```bash
docling-serve run # Check 'docling-serve --help' for options
```

### Environment Variables

*   **`WEAVIATE_URL`** (Optional):
    *   If set (e.g., `export WEAVIATE_URL="http://localhost:8080"`), the service will log that it's configured for Weaviate, and the `/v1/ingest` API response will reflect `vector_db_status: "enabled_stub"`. Indexing is still a no-op.
    *   If not set, `vector_db_status` will be `"disabled"`.
*   Other environment variables specific to `docling-core` or `docling-serve` (e.g., for OCR backend selection, model paths) may apply. Refer to the main `docling-serve` documentation for those.

## How to Run the Tests

### Prerequisites

*   Development dependencies installed (including `pytest`). See "Dependency Installation" above.

### Running Tests

Navigate to the root directory of the project and run:

```bash
pytest
```
Or, for more verbose output:
```bash
pytest -vv
```

This will discover and run all tests in the `tests/` directory.

## Expected Results from `/v1/ingest` Endpoint

The `/v1/ingest` endpoint (POST request) returns a JSON response conforming to the `IngestionApiResponse` schema.

**`IngestionApiResponse` Structure:**

```json
{
  "doc_id": "string",                 // SHA1 hash of the entire document content
  "doc_name": "string",               // Original document name (stemmed, without extension)
  "chunks": [ /* List of Chunk objects */ ],
  "vector_db_status": "string"      // "disabled" or "enabled_stub"
}
```

**`Chunk` Object Structure (within the `chunks` list):**

```json
{
  "chunk_id": "string",               // Deterministic ID for the chunk (salted with doc_id)
  "text": "string",                   // Raw text content of the chunk
  "enriched_text": "string | null",   // Text content with added context (e.g., headings) for embedding
  "metadata": { /* ChunkMetadata object */ }
}
```

**`ChunkMetadata` Object Structure (within each `Chunk`'s `metadata`):**

```json
{
  "doc_id": "string",                 // Matches the top-level doc_id
  "doc_name": "string",               // Matches the top-level doc_name
  "page": "integer | null",          // Page number where the chunk originates (1-based if available)
  "chunk_index": "integer",           // 0-based index of the chunk within the document
  "section": "Array[string] | null",  // List of headings/sections this chunk belongs to
  "citation": "string",               // Human-readable citation (e.g., "MyDocument, p. 1")
  "location": {                       // Optional: For PDF highlights
    "page": "integer",
    "bbox": [ /* Array of 4 floats: x0, y0, x1, y1 */ ]
  } | null,
  "content_type": "string | null"     // Type of content (e.g., "paragraph", "table", "list_item")
}
```

### `vector_db_status` Field

*   If the `WEAVIATE_URL` environment variable is **not set**, this field will be `"disabled"`.
*   If `WEAVIATE_URL` **is set**, this field will be `"enabled_stub"`, indicating that the system recognizes the configuration, but actual indexing is still a placeholder.

## How to Integrate with Weaviate (Future Steps)

The current service includes a **stub** for Weaviate integration. To enable actual indexing:

1.  **Add Weaviate Client Library:**
    Add `weaviate-client` (e.g., `weaviate-client~=3.x.x` or `weaviate-client~=4.x.x` depending on your Weaviate version) to the `dependencies` in your `pyproject.toml` file and update your environment (e.g., `uv pip sync`).

2.  **Set Environment Variable:**
    Ensure the `WEAVIATE_URL` environment variable is set to your Weaviate instance's URL (e.g., `export WEAVIATE_URL="http://localhost:8080"` or your cloud endpoint).

3.  **Implement Indexing Logic:**
    Modify the `index_chunks_in_vector_db` function in `docling_serve/indexing/vector_db.py`.
    The current stub contains commented-out placeholder code. You will need to:
    *   Initialize the Weaviate client: `client = weaviate.Client(weaviate_url)`
    *   Define your Weaviate class schema if it doesn't exist. The target class name is `DocumentChunk`. Properties should match the fields in the "Target Object Model" (e.g., `chunk_id`, `text`, `doc_id`, etc.).
    *   For each `Chunk` object received by the function:
        *   Transform its structure (Pydantic `Chunk` model with nested `metadata`) into a flat dictionary matching the `DocumentChunk` class properties in Weaviate.
        *   The `chunk_id` (which is deterministic) should be used as the Weaviate object's UUID to ensure idempotency on re-ingestion.
    *   Use `client.batch.create_objects()` or `client.batch.add_data_object()` for efficient bulk importing.

    **Example (Conceptual - within `index_chunks_in_vector_db`):**
    ```python
    # import weaviate # Add to imports

    # ... (inside the function, after WEAVIATE_URL check)
    # client = weaviate.Client(weaviate_url) # Or weaviate.connect_to_local(), etc. for v4

    # client.batch.configure(...) # For v3, or use auto-batching in v4

    # with client.batch as batch: # For v3, or direct batch calls in v4
    #     for chunk_obj in chunks:
    #         properties = {
    #             "text": chunk_obj.text, # This is the field Weaviate will embed by default if using text2vec-*
    #             # "enriched_text": chunk_obj.enriched_text, # Or choose to embed this
    #             "doc_id": chunk_obj.metadata.doc_id,
    #             "doc_name": chunk_obj.metadata.doc_name,
    #             "page": chunk_obj.metadata.page,
    #             "chunk_index": chunk_obj.metadata.chunk_index,
    #             "section": chunk_obj.metadata.section, # Weaviate might prefer string or list of strings
    #             "citation": chunk_obj.metadata.citation,
    #             "location_page": chunk_obj.metadata.location["page"] if chunk_obj.metadata.location else None,
    #             "location_bbox": chunk_obj.metadata.location["bbox"] if chunk_obj.metadata.location else None,
    #             "content_type": chunk_obj.metadata.content_type,
    #             # Ensure all property names match your Weaviate class schema
    #         }
    #         # Remove None properties if your Weaviate schema doesn't allow nulls for certain fields
    #         # or handle type conversions (e.g. List[str] for section)
    #         properties = {k: v for k, v in properties.items() if v is not None}

    #         # For Weaviate v3 client.batch.add_data_object(...)
    #         # For Weaviate v4 client.collections.get("DocumentChunk").data.insert({...})
    #         # Use chunk_obj.chunk_id as the UUID for the Weaviate object.
    #         # Example for v3:
    #         # batch.add_data_object(
    #         #     data_object=properties,
    #         #     class_name="DocumentChunk",
    #         #     uuid=chunk_obj.chunk_id
    #         # )
    # logger.info(f"Successfully submitted {len(chunks)} chunks to Weaviate for doc_id {doc_id}.")
    # return "indexed" # Or a more descriptive status
    ```

4.  **Embeddings Strategy:**
    Decide whether to:
    *   Let Weaviate generate embeddings using a `text2vec-*` module (e.g., `text2vec-transformers`, `text2vec-openai`). This requires configuring the `DocumentChunk` class in Weaviate to use such a module for the `text` (or `enriched_text`) property.
    *   Pre-compute embeddings in the `docling-serve` service (e.g., using Sentence Transformers directly or another embedding API) and pass the `vector` explicitly when adding objects to Weaviate.

This guide should provide a solid foundation for using the service and integrating it further.
---
