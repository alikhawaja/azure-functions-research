"""
TextCompletion function — Week 5, Task 2.
Accepts a user prompt and returns a completion from Azure OpenAI.
"""

import json
import logging

import azure.functions as func

app = func.FunctionApp(http_auth_level=func.AuthLevel.FUNCTION)


# ---------------------------------------------------------------------------
# POST /api/complete-safe   { "prompt": "...", "temperature": 0.7, "maxTokens": 500 }
# Validates and clamps input BEFORE calling the AI-bound handler below.
# ---------------------------------------------------------------------------
@app.route(route="complete-safe", methods=["POST"])
def complete_safe(req: func.HttpRequest) -> func.HttpResponse:
    try:
        body = req.get_json()
    except ValueError:
        return func.HttpResponse(
            json.dumps({"error": "Request body must be valid JSON."}),
            mimetype="application/json",
            status_code=400,
        )

    prompt = body.get("prompt")
    if not prompt or not isinstance(prompt, str):
        return func.HttpResponse(
            json.dumps({"error": "Field 'prompt' (string) is required."}),
            mimetype="application/json",
            status_code=400,
        )

    temperature = body.get("temperature", 0.7)
    if not isinstance(temperature, (int, float)) or not (0 <= temperature <= 2):
        return func.HttpResponse(
            json.dumps({"error": "temperature must be a number between 0 and 2."}),
            mimetype="application/json",
            status_code=400,
        )

    max_tokens = body.get("maxTokens", 500)
    if not isinstance(max_tokens, int) or not (1 <= max_tokens <= 4000):
        return func.HttpResponse(
            json.dumps({"error": "maxTokens must be an integer between 1 and 4000."}),
            mimetype="application/json",
            status_code=400,
        )

    return func.HttpResponse(
        json.dumps(
            {
                "note": "Validated payload — forward to /api/complete with this body.",
                "prompt": prompt,
                "temperature": temperature,
                "maxTokens": max_tokens,
            }
        ),
        mimetype="application/json",
        status_code=200,
    )


# ---------------------------------------------------------------------------
# POST /api/complete   { "prompt": "...", "temperature": 0.7, "maxTokens": 500 }
# Uses the TextCompletion input binding to call Azure OpenAI directly.
# ---------------------------------------------------------------------------
@app.route(route="complete", methods=["POST"])
@app.generic_input_binding(
    arg_name="response",
    type="textCompletion",
    prompt="{prompt}",
    chatModel="%CHAT_MODEL_DEPLOYMENT_NAME%",
    temperature="{temperature}",
    maxTokens="{maxTokens}",
)
def complete(req: func.HttpRequest, response: str) -> func.HttpResponse:
    try:
        return func.HttpResponse(
            json.dumps({"completion": response}),
            mimetype="application/json",
            status_code=200,
        )
    except Exception as exc:
        logging.exception("TextCompletion call failed")
        return func.HttpResponse(
            json.dumps({"error": str(exc)}),
            mimetype="application/json",
            status_code=502,
        )