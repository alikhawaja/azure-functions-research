"""
Week 4 - Task 1: Advanced Orchestration Patterns
==================================================
Demonstrates, in Azure Durable Functions (Python v2 model):
  1. Sub-orchestrations       -> ParentDeviceProvisioning / ChildDeviceProvisioning
  2. Human interaction        -> ApprovalOrchestrator (WaitForExternalEvent + timeout)
  3. Eternal orchestration    -> PeriodicCleanupOrchestrator (ContinueAsNew loop)

Run locally with: func start   (requires Azurite running for storage emulation)
"""

import logging
from datetime import timedelta

import azure.functions as func
import azure.durable_functions as df

myApp = df.DFApp(http_auth_level=func.AuthLevel.ANONYMOUS)


# ============================================================================
# GENERIC STARTER  -  POST /api/orchestrators/{functionName}
# Lets us kick off ANY orchestrator by name, e.g.
#   POST /api/orchestrators/parent_device_provisioning
#   POST /api/orchestrators/approval_orchestrator
#   POST /api/orchestrators/periodic_cleanup_orchestrator
# ============================================================================
@myApp.route(route="orchestrators/{functionName}")
@myApp.durable_client_input(client_name="client")
async def http_start(req: func.HttpRequest, client):
    function_name = req.route_params.get("functionName")

    try:
        payload = req.get_json()
    except ValueError:
        payload = None

    instance_id = await client.start_new(function_name, client_input=payload)
    logging.info(f"Started orchestration '{function_name}' with ID = '{instance_id}'.")

    return client.create_check_status_response(req, instance_id)


# ============================================================================
# PATTERN 1: SUB-ORCHESTRATIONS
# ----------------------------------------------------------------------------
# Scenario: provisioning a batch of IoT devices. Each device needs its own
# multi-step workflow (create package -> configure -> ping). Rather than
# cramming all of that (and its error handling) into one orchestrator, we
# push each device's workflow into a CHILD orchestrator, and the PARENT just
# fans out to N children in parallel and fans back in.
#
# When to break into a sub-orchestration:
#   - The child logic is reusable / independently testable
#   - The child has its own multi-step retry / compensation needs
#   - You're fanning out over a dynamic list and each item needs > 1 activity
#     (keeps parent history small - each child gets its OWN history)
# ============================================================================

@myApp.orchestration_trigger(context_name="context")
def parent_device_provisioning(context: df.DurableOrchestrationContext):
    device_ids = context.get_input() or ["device-001", "device-002", "device-003"]

    # Fan out: each device gets its own child orchestration instance,
    # running concurrently.
    child_tasks = [
        context.call_sub_orchestrator(
            "child_device_provisioning",
            device_id,
            instance_id=f"{context.instance_id}:{device_id}",  # deterministic, readable child IDs
        )
        for device_id in device_ids
    ]

    # Fan in: wait for all children to finish.
    results = yield context.task_all(child_tasks)

    return {
        "parent_instance_id": context.instance_id,
        "devices_provisioned": len(results),
        "results": results,
    }


@myApp.orchestration_trigger(context_name="context")
def child_device_provisioning(context: df.DurableOrchestrationContext):
    device_id = context.get_input()

    package_url = yield context.call_activity("create_install_package", device_id)
    config_result = yield context.call_activity("configure_device", {
        "device_id": device_id,
        "package_url": package_url,
    })
    ping_ok = yield context.call_activity("ping_device", device_id)

    return {
        "device_id": device_id,
        "package_url": package_url,
        "configured": config_result,
        "online": ping_ok,
    }


@myApp.activity_trigger(input_name="deviceid")
def create_install_package(deviceid: str) -> str:
    logging.info(f"Creating install package for {deviceid}")
    return f"https://storage.example.com/packages/{deviceid}.zip"


@myApp.activity_trigger(input_name="payload")
def configure_device(payload: dict) -> bool:
    logging.info(f"Configuring {payload['device_id']} with {payload['package_url']}")
    return True


@myApp.activity_trigger(input_name="deviceid")
def ping_device(deviceid: str) -> bool:
    logging.info(f"Pinging {deviceid}")
    return True


# ============================================================================
# PATTERN 2: HUMAN INTERACTION (approval workflow with timeout)
# ----------------------------------------------------------------------------
# Scenario: an order over a threshold needs manager approval within 24 hours
# (shortened to 60s here for local testing). We race an external event
# against a durable timer using task_any - whichever resolves first wins.
# This is the standard "reliable timeout" pattern for anything waiting on a
# human.
# ============================================================================

@myApp.orchestration_trigger(context_name="context")
def approval_orchestrator(context: df.DurableOrchestrationContext):
    order = context.get_input() or {"order_id": "demo-order", "amount": 1500}

    yield context.call_activity("request_approval", order)

    # IMPORTANT: use context.current_utc_datetime (deterministic on replay),
    # never datetime.utcnow(), inside an orchestrator.
    timeout_at = context.current_utc_datetime + timedelta(seconds=60)

    approval_event = context.wait_for_external_event("ApprovalEvent")
    timeout_task = context.create_timer(timeout_at)

    winner = yield context.task_any([approval_event, timeout_task])

    if winner == timeout_task:
        # Cancel the timer's "sibling" isn't needed here, but if approval_event
        # had won we WOULD want to cancel the timer to avoid a dangling timer:
        yield context.call_activity("notify_timeout", order)
        return {"order_id": order["order_id"], "status": "TimedOut"}

    # Approval event won the race - cancel the now-unneeded timer.
    timeout_task.cancel()
    approval_result = approval_event.result  # payload sent via raise_event
    yield context.call_activity("notify_decision", {"order": order, "decision": approval_result})

    return {"order_id": order["order_id"], "status": approval_result}


@myApp.activity_trigger(input_name="order")
def request_approval(order: dict) -> None:
    logging.info(f"Requesting approval for order {order.get('order_id')} (${order.get('amount')})")


@myApp.activity_trigger(input_name="order")
def notify_timeout(order: dict) -> None:
    logging.info(f"Order {order.get('order_id')} timed out waiting for approval")


@myApp.activity_trigger(input_name="payload")
def notify_decision(payload: dict) -> None:
    logging.info(f"Order {payload['order']['order_id']} decision: {payload['decision']}")


# HTTP endpoint a real approver (or a webhook / Teams button / email link)
# would call to unblock the waiting orchestration:
#   POST /api/orchestrators/{instanceId}/raiseEvent/ApprovalEvent
#   body: "Approved"  (or "Rejected")
@myApp.route(route="orchestrators/{instanceId}/raiseEvent/{eventName}", methods=["POST"])
@myApp.durable_client_input(client_name="client")
async def raise_event_http(req: func.HttpRequest, client):
    instance_id = req.route_params.get("instanceId")
    event_name = req.route_params.get("eventName")

    try:
        event_data = req.get_json()
    except ValueError:
        event_data = req.get_body().decode() or "Approved"

    await client.raise_event(instance_id, event_name, event_data)
    return func.HttpResponse(
        f"Event '{event_name}' raised for instance '{instance_id}'.", status_code=200
    )


# ============================================================================
# PATTERN 3: ETERNAL ORCHESTRATION
# ----------------------------------------------------------------------------
# Scenario: a periodic cleanup job that should run forever, e.g. every N
# seconds/minutes, without the orchestration's history growing without
# bound (which would eventually hurt performance / storage).
#
# The trick: instead of looping with `while True` inside ONE execution, the
# orchestrator does ONE unit of work, waits on a timer, then calls
# context.continue_as_new(...) - this restarts the orchestration instance
# with a brand-new, empty history, carrying forward only the small piece of
# state you pass in.
# ============================================================================

@myApp.orchestration_trigger(context_name="context")
def periodic_cleanup_orchestrator(context: df.DurableOrchestrationContext):
    state = context.get_input() or {"run_count": 0}

    deleted = yield context.call_activity("cleanup_old_records", state["run_count"])

    state["run_count"] += 1
    state["last_deleted"] = deleted

    # Wait before the next cycle (30s here; would be minutes/hours in prod).
    next_run = context.current_utc_datetime + timedelta(seconds=30)
    yield context.create_timer(next_run)

    # OPTIONAL SAFETY VALVE for a demo/test env so it doesn't run forever:
    # remove this guard for a genuinely eternal orchestration.
    if state["run_count"] >= 5:
        return f"Stopped after {state['run_count']} demo cycles."

    # Restart with fresh history, carrying forward only `state`.
    context.continue_as_new(state)


@myApp.activity_trigger(input_name="runcount")
def cleanup_old_records(runcount: int) -> int:
    logging.info(f"Cleanup cycle #{runcount}: deleting stale records...")
    return 3  # pretend we deleted 3 records