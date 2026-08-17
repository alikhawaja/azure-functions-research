"""
Chatbot function — Week 5, Task 3.
Uses the Azure Functions OpenAI extension's Assistant bindings to run a
stateful, multi-turn conversation. Conversation history is stored and
managed automatically by the extension (Azure Table Storage by default).
"""

import json
import logging

import azure.functions as func

app = func.FunctionApp(http_auth_level=func.AuthLevel.FUNCTION)

CHAT_STORAGE_CONNECTION = "AzureWebJobsStorage"
COLLECTION_NAME = "ChatState"

DEFAULT_INSTRUCTIONS = (
    "You are a helpful assistant. Keep answers concise. "
    "Refer back to earlier parts of the conversation when relevant."
)


# ---------------------------------------------------------------------------
# PUT /api/chats/{chatId}
# Starts a new conversation session. Body is optional:
# { "instructions": "..." }
# ---------------------------------------------------------------------------
@app.function_name("CreateChatBot")
@app.route(route="chats/{chatId}", methods=["PUT"])
@app.assistant_create_output(arg_name="requests")
def create_chat_bot(req: func.HttpRequest, requests: func.Out[str]) -> func.HttpResponse:
    chat_id = req.route_params.get("chatId")

    try:
        body = req.get_json()
    except ValueError:
        body = {}

    instructions = body.get("instructions", DEFAULT_INSTRUCTIONS)

    logging.info("Creating chat session %s", chat_id)

    create_request = {
        "id": chat_id,
        "instructions": instructions,
        "chatStorageConnectionSetting": CHAT_STORAGE_CONNECTION,
        "collectionName": COLLECTION_NAME,
    }
    requests.set(json.dumps(create_request))

    return func.HttpResponse(
        json.dumps({"chatId": chat_id, "created": True}),
        status_code=202,
        mimetype="application/json",
    )


# ---------------------------------------------------------------------------
# POST /api/chats/{chatId}
# Sends a new message into an existing session and returns the reply.
# Body: { "message": "..." }
# ---------------------------------------------------------------------------
@app.function_name("PostUserResponse")
@app.route(route="chats/{chatId}", methods=["POST"])
@app.assistant_post_input(
    arg_name="state",
    id="{chatId}",
    user_message="{message}",
    model="%CHAT_MODEL_DEPLOYMENT_NAME%",
    chat_storage_connection_setting=CHAT_STORAGE_CONNECTION,
    collection_name=COLLECTION_NAME,
)
def post_user_response(req: func.HttpRequest, state: str) -> func.HttpResponse:
    try:
        data = json.loads(state)
        recent_message_content = data["recentMessages"][0]["content"]
    except (ValueError, KeyError, IndexError) as exc:
        logging.exception("Failed to parse assistant response")
        return func.HttpResponse(
            json.dumps({"error": f"Could not parse assistant response: {exc}"}),
            status_code=502,
            mimetype="application/json",
        )

    return func.HttpResponse(
        recent_message_content,
        status_code=200,
        mimetype="text/plain",
    )


# ---------------------------------------------------------------------------
# GET /api/chats/{chatId}?timestampUTC=2024-01-15T22:00:00
# Reads back the saved conversation history. timestampUTC is optional —
# when provided, only messages after that time are returned (polling).
# ---------------------------------------------------------------------------
@app.function_name("GetChatState")
@app.route(route="chats/{chatId}", methods=["GET"])
@app.assistant_query_input(
    arg_name="state",
    id="{chatId}",
    timestamp_utc="{Query.timestampUTC}",
    chat_storage_connection_setting=CHAT_STORAGE_CONNECTION,
    collection_name=COLLECTION_NAME,
)
def get_chat_state(req: func.HttpRequest, state: str) -> func.HttpResponse:
    return func.HttpResponse(
        state,
        status_code=200,
        mimetype="application/json",
    )