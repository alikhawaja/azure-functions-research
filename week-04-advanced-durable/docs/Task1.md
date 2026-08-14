# Week 4 — Task 1: Advanced Orchestration Patterns

**Focus:** Durable Functions — Advanced Patterns & Error Handling
**Reference:** [Durable Functions overview | Microsoft Learn](https://learn.microsoft.com/en-us/azure/azure-functions/durable/durable-functions-overview)
**Language used:** Python

---

## What is an orchestrator?
An orchestrator function is a special function. It can pause and wait, sometimes for a long time. It does not do the real work itself. It tells other small functions (called activities) what to do.

Azure keeps a record of everything the orchestrator has done. This record is called the **history**. If the orchestrator stops or restarts, Azure uses the history to pick up where it left off. This is called a **replay**.


---

## Part 1: Sub-Orchestrations

### The question

When should you break one big orchestrator into smaller ones?

### The answer

Break it up when:

* One orchestrator is doing too many jobs at once.
* You have a list of items, and each item needs its own set of steps.
* You want the same steps to run again somewhere else later.
* You want one item's failure to not stop the other items.

### What we built

We built a **parent** orchestrator. It does not do any real work. It just gives out jobs.

The parent takes a list of devices, like `device-A`, `device-B`, `device-C`.

For each device, the parent starts a **child** orchestrator. This is called a **sub-orchestration**.

All children run **at the same time**. The parent waits for all of them to finish. Then it collects their results.

Each child does 3 steps, one after another, for one device:

1. Create an install package
2. Configure the device
3. Ping the device to check it is online

### Why this is better

If we put everything in one big orchestrator:

* The history keeps growing and growing.
* It is hard to test one part on its own.
* Running things in parallel is harder to set up.

With sub-orchestrations:

* Each child gets its **own small history**. The parent stays small no matter how many devices there are.
* Each child can be tested by itself.
* Running many children at once is easy. This is called **fan-out**. Waiting for them all to finish is called **fan-in**.

### The code

```python
# PARENT
def parent_device_provisioning(context):
    device_ids = context.get_input()

    # Start one child per device
    child_tasks = [
        context.call_sub_orchestrator("child_device_provisioning", device_id)
        for device_id in device_ids
    ]

    # Wait for all children to finish
    results = yield context.task_all(child_tasks)
    return results


# CHILD
def child_device_provisioning(context):
    device_id = context.get_input()
    package_url = yield context.call_activity("create_install_package", device_id)
    yield context.call_activity("configure_device", {"device_id": device_id, "package_url": package_url})
    online = yield context.call_activity("ping_device", device_id)
    return {"device_id": device_id, "online": online}
```

The key line is `context.call_sub_orchestrator(...)`. This is what starts a child orchestrator from inside a parent orchestrator.

### How we proved it worked

We sent in 3 devices. We waited for the parent to finish. The result showed all 3 devices, each one done by its own child:

```json
{
  "runtimeStatus": "Completed",
  "output": {
    "devices_provisioned": 3,
    "results": [
      { "device_id": "device-A", "online": true },
      { "device_id": "device-B", "online": true },
      { "device_id": "device-C", "online": true }
    ]
  }
}
```

---

## Part 2: Human Interaction Pattern

### The problem

Sometimes a workflow needs a real person to do something. For example: "wait for a manager to approve this order."

This creates two problems:

1. The orchestrator must pause and wait, maybe for a long time, without wasting resources.
2. It cannot wait forever. If no one answers, it needs to give up after some time.

### The two tools we use

* `context.wait_for_external_event("ApprovalEvent")` — this pauses the orchestrator. It waits until someone sends it a signal called `"ApprovalEvent"`.
* `context.create_timer(deadline)` — this pauses the orchestrator until a certain time.

If we only used `wait_for_external_event`, it could wait forever. So we race it against a timer. Whichever one finishes first is the winner. This race is done with `context.task_any([...])`.

### What we built

Our `approval_orchestrator` does this:

1. Asks for approval (calls an activity that sends a request).
2. Sets a deadline, 60 seconds in the future.
3. Waits for **either**:
   * someone approving it, or
   * the deadline arriving first.
4. If the deadline wins, the result is `"TimedOut"`.
5. If the approval wins, the timer is cancelled, and the result is the approval answer, like `"Approved"`.

### The code (simplified)

```python
def approval_orchestrator(context):
    order = context.get_input()
    yield context.call_activity("request_approval", order)

    deadline = context.current_utc_datetime + timedelta(seconds=60)
    approval_event = context.wait_for_external_event("ApprovalEvent")
    timeout_task = context.create_timer(deadline)

    winner = yield context.task_any([approval_event, timeout_task])

    if winner == timeout_task:
        return {"status": "TimedOut"}

    timeout_task.cancel()
    return {"status": approval_event.result}
```

### Important rule: use `context.current_utc_datetime`

Do not use normal Python `datetime.utcnow()` inside an orchestrator. Remember, Azure replays orchestrator code. If we used the normal clock, we would get a different time every replay. That breaks things.

`context.current_utc_datetime` gives the same frozen time every replay. This is called being **deterministic**. It means: same input, same result, every time.

### How a person actually approves it

We built a simple web link for this:

```
POST /api/orchestrators/{instanceId}/raiseEvent/ApprovalEvent
Body: "Approved"
```

Calling this link sends the signal into the paused orchestrator and wakes it up. In a real app, this link could be a button in an email or a chat message.

### How we proved it worked

* We started the orchestrator.
* We checked its status. It said `"Running"`. This proves it was paused and waiting, not stuck or broken.
* We sent the approval signal.
* We checked the status again. It said `"Completed"`, with `"status": "Approved"`.

---

## Part 3: Eternal Orchestrations

### The problem

Some jobs should run forever. Example: check something every 30 minutes, forever, like a cleanup task.

You might think: just use a `while True` loop inside the orchestrator. But this causes a problem.

### Why a normal loop is a bad idea

Remember, Azure keeps a history of everything the orchestrator does. If we loop forever in one execution, the history never stops growing. Over time this becomes slow and can even hit hard limits.

### The fix: `context.continue_as_new(...)`

Instead of looping forever, the orchestrator does **one round of work**, then calls `continue_as_new`. This:

* Finishes the current run completely. Its history is closed.
* Starts a brand new run right away, with a fresh, empty history.
* Carries forward only a small piece of state, like a counter.

From the outside, it looks like one job running forever. Underneath, it is really a chain of short runs, each with a small history.

### What we built

Our `periodic_cleanup_orchestrator` does this:

1. Runs a cleanup activity.
2. Waits 30 seconds.
3. Calls `continue_as_new` to restart itself with an updated counter.

For the demo, we made it stop after 5 rounds. This is just so it doesn't run forever on our laptop. In a real app, we would remove this limit.

### The code (simplified)

```python
def periodic_cleanup_orchestrator(context):
    state = context.get_input() or {"run_count": 0}

    yield context.call_activity("cleanup_old_records", state["run_count"])
    state["run_count"] += 1

    next_run = context.current_utc_datetime + timedelta(seconds=30)
    yield context.create_timer(next_run)

    if state["run_count"] >= 5:      # only for the demo
        return f"Stopped after {state['run_count']} cycles."

    context.continue_as_new(state)   # restart with fresh history
```

---

## Summary Table

| Pattern | Problem it solves | Main tool used |
|---|---|---|
| Sub-orchestrations | One orchestrator doing too much, or needing to run many similar jobs at once | `call_sub_orchestrator` |
| Human interaction | Waiting for a person, but not forever | `wait_for_external_event` + `create_timer` + `task_any` |
| Eternal orchestration | Running forever without the history growing forever | `continue_as_new` |

---