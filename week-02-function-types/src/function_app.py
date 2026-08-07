import logging
import azure.functions as func
import azure.durable_functions as df

app = df.DFApp(http_auth_level=func.AuthLevel.FUNCTION)

# In-memory counter used only to simulate a transient failure locally.
# Resets on process restart; not safe for multi-instance/production use.
_attempt_count = 0


# ---------------------------------------------------------------------------
# 1. ACTIVITY FUNCTION
# Deliberately fails the first 2 calls, then succeeds on the 3rd.
# No determinism constraints here — this is a normal Python function that
# happens to raise on purpose to simulate a flaky external dependency
# (e.g. an API that's temporarily down).
# ---------------------------------------------------------------------------
@app.activity_trigger(input_name="name")
def flaky_activity(name: str) -> str:
    global _attempt_count
    _attempt_count += 1

    logging.info(f"flaky_activity: attempt #{_attempt_count}")

    if _attempt_count < 3:
        raise Exception(f"Simulated transient failure on attempt #{_attempt_count}")

    result = f"Succeeded on attempt #{_attempt_count} (input: {name})"
    logging.info(f"flaky_activity: {result}")
    return result


# ---------------------------------------------------------------------------
# 2. ORCHESTRATOR FUNCTION
# Calls flaky_activity using an automatic retry policy instead of a plain
# call_activity. This is what actually demonstrates automatic retries.
# ---------------------------------------------------------------------------
@app.orchestration_trigger(context_name="context")
def retry_demo_orchestrator(context: df.DurableOrchestrationContext):
    retry_options = df.RetryOptions(
        first_retry_interval_in_milliseconds=5000,  # wait 5s before retry #1
        max_number_of_attempts=3                     # 1 initial try + 2 retries
    )

    result = yield context.call_activity_with_retry(
        "flaky_activity", retry_options, "demo-input"
    )

    return result


# ---------------------------------------------------------------------------
# 3. CLIENT FUNCTION (HTTP-triggered entry point)
# Starts the orchestration and returns status-check URLs so you can poll
# progress and watch the retries happen in the logs.
# ---------------------------------------------------------------------------
@app.route(route="retrydemo")
@app.durable_client_input(client_name="client")
async def retry_demo_starter(
    req: func.HttpRequest, client: df.DurableOrchestrationClient
) -> func.HttpResponse:
    instance_id = await client.start_new("retry_demo_orchestrator")
    logging.info(f"Started orchestration with ID = {instance_id}")
    return client.create_check_status_response(req, instance_id)