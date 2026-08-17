"""
Embeddings function — Week 5, Task 2.
Takes raw text, generates an embedding vector via Azure OpenAI,
and stores the result in Blob Storage.
"""

import json
import logging
import os
import uuid

import azure.functions as func
from azure.storage.blob import BlobServiceClient

app = func.FunctionApp(http_auth_level=func.AuthLevel.FUNCTION)

_blob_service_client = None


def _get_container_client():
    global _blob_service_client
    if _blob_service_client is None:
        conn_str = os.environ["AzureWebJobsStorage"]
        _blob_service_client = BlobServiceClient.from_connection_string(conn_str)
    container = _blob_service_client.get_container_client("embeddings")
    if not container.exists():
        container.create_container()
    return container


# ---------------------------------------------------------------------------
# POST /api/embed   { "text": "..." }
# Uses the Embeddings input binding, then stores the result via the Blob SDK
# (an output binding can't be used here since the blob name — a UUID — is
# only known once the function body runs, not at trigger time).
# ---------------------------------------------------------------------------
@app.route(route="embed", methods=["POST"])
@app.generic_input_binding(
    arg_name="embeddings",
    type="embeddings",
    input="{text}",
    inputType="RawText",
    embeddingsModel="%EMBEDDING_MODEL_DEPLOYMENT_NAME%",
)
def embed(req: func.HttpRequest, embeddings: str) -> func.HttpResponse:
    try:
        body = req.get_json()
    except ValueError:
        return func.HttpResponse(
            json.dumps({"error": "Request body must be valid JSON."}),
            mimetype="application/json",
            status_code=400,
        )

    text = body.get("text")
    if not text:
        return func.HttpResponse(
            json.dumps({"error": "Field 'text' (string) is required."}),
            mimetype="application/json",
            status_code=400,
        )

    try:
        embeddings_obj = json.loads(embeddings)
        record_id = str(uuid.uuid4())
        record = {"id": record_id, "text": text, "embedding": embeddings_obj}

        container = _get_container_client()
        container.upload_blob(name=f"{record_id}.json", data=json.dumps(record))
    except Exception as exc:
        logging.exception("Embedding generation or storage failed")
        return func.HttpResponse(
            json.dumps({"error": str(exc)}),
            mimetype="application/json",
            status_code=502,
        )

    return func.HttpResponse(
        json.dumps({"id": record_id, "stored": True, "textLength": len(text)}),
        mimetype="application/json",
        status_code=201,
    )