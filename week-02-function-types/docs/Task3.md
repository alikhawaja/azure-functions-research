# Task 3, Part 1, Why Activity Functions Are the "Workhorses"

## Overview

Activity functions are where a Durable Functions orchestration actually *does things*, they're the units of real work: calling an API, writing to a database, sending an email, running a computation. The reason they're described as the "workhorses" of the system comes down to one core distinction: **activities are not replayed, so they're not bound by the determinism rules that orchestrators must follow.**

## Why orchestrators can't be workhorses

To understand why activities are special, it helps to remember what orchestrators can't do. Orchestrator functions are re-executed from the top every time they wake up (the replay mechanism), the framework relies on the orchestrator producing the *exact same sequence of decisions* on every replay, so it can match new code execution against its saved history log. Because of this, orchestrators must be deterministic: no direct I/O, no `DateTime.Now`, no random values, no `Thread.Sleep`. Any orchestrator code that could produce a different result on a second run risks desynchronizing from its own history, the exact non-determinism problem covered in the replay section.

This means orchestrators can't safely do the actual work themselves. They can only *describe* the work and *delegate* it, which is exactly what activities are for.

## Why activities are exempt
Activities don't have this constraint because **they are never replayed.** An activity function runs once per logical invocation (occasionally more than once due to retries, covered below), produces a result, and that result gets permanently recorded in the orchestration's history. The orchestrator never re-executes the activity's code to "check" it, it simply reads the saved result from history on future replays. Because nothing is being replayed and compared, it doesn't matter whether the activity's internal logic would produce a different result if run again.

This is what "no determinism constraints" means in practice: an activity is free to do things like:

- Call an external web API (which might return different data each time)
- Read the current time (`DateTime.Now`)
- Generate a random number or GUID
- Read/write from a database
- Read/write files
- Sleep, wait, or perform long-running computation
- Perform any kind of arbitrary I/O, network calls, disk access, queue messages, etc.

None of this breaks anything, because the activity's *result*, not its internal process, is the only thing that gets logged and reused.

## The trade-off: at-least-once execution

Being free from determinism doesn't mean activities are risk-free. The Durable Task Framework guarantees that every scheduled activity **will** run, but only *at least once*, not *exactly once*.

Here's the failure scenario that creates this guarantee: an activity finishes doing its real work, but *before* the framework can write "this activity completed" to the history log, the system crashes (host restart, worker failure, etc.). Since the framework's records don't show it as complete, it schedules the activity again when it recovers, even though the work already happened once. The re-run isn't performed by your code manually; it's automatic framework-level behavior, triggered when a "completed" confirmation is never received.

## Why this makes idempotency essential

Because an activity might genuinely execute more than once for the same logical step, activities that cause real-world side effects need to be **idempotent**, meaning running the activity multiple times produces the same real-world end state as running it once, rather than repeating the side effect each time.

This is a distinct concern from determinism. It doesn't matter what the framework *thinks* happened, what matters is what the activity actually *does* in the outside world if it's invoked twice.

**Example, credit card charge:**
- **Non-idempotent**: `ChargeCard($50)` unconditionally charges the card every time it's called. If it runs twice due to at-least-once execution, the customer is charged $100.
- **Idempotent**: `ChargeCard($50, orderId=123)` first checks whether order 123 has already been charged. If it has, it does nothing (or returns the existing confirmation) instead of charging again. Run once or run twice, the customer is only ever charged once.

Common idempotency techniques: checking for an existing record before writing, using upserts instead of inserts, using unique idempotency keys with external APIs (many payment providers support this natively), or making writes naturally overwrite-safe (e.g., "set status to Complete" rather than "increment counter by 1").

## Single input / single output

One more structural constraint worth noting alongside all this: each activity function accepts exactly one input parameter and returns exactly one output value. If a task genuinely needs multiple pieces of data, they're bundled into a single complex type or collection (e.g., a class or dictionary) rather than passed as separate parameters. This is unrelated to determinism, it's simply how the activity trigger binding is designed, but it's part of what defines the "shape" of an activity function.

## Summary

| | Orchestrator | Activity |
|---|---|---|
| Replayed? | Yes, from the top, every wake-up | No, runs once per logical call |
| Determinism required? | Yes, must match history on replay | No, free to use real time, randomness, I/O |
| Can call APIs/DBs directly? | No, must delegate to an activity | Yes, arbitrary I/O allowed |
| Execution guarantee | N/A (its *decisions* are logged) | At-least-once, may rerun on failure |
| Needs idempotency? | Not applicable in the same way | Yes, for side-effecting operations |


# Task 3, Part 2: Activity Function Retry Policies

## Overview

Activity functions can fail: a downstream API might be temporarily unavailable, a database connection might time out, a network blip might interrupt a call. These are usually **transient failures**: temporary, self-resolving problems where trying again shortly after often succeeds. Rather than making every activity implement its own retry loop manually, Durable Functions provides a **built-in automatic retry policy** you can attach to any activity call.

## How retries are configured

Instead of calling an activity with the plain scheduling method, you call it with a retry-aware variant and pass a retry policy object alongside it:

```csharp
var retryOptions = new RetryOptions(
    firstRetryInterval: TimeSpan.FromSeconds(5),
    maxNumberOfAttempts: 3)
{
    BackoffCoefficient = 2.0,
    MaxRetryInterval = TimeSpan.FromMinutes(1),
    RetryTimeout = TimeSpan.FromMinutes(10)
};

var result = await context.CallActivityWithRetryAsync<string>(
    "FlakyActivity", retryOptions, input);
```

The key difference from a normal call: `CallActivityAsync` just runs the activity once and propagates any failure immediately. `CallActivityWithRetryAsync` wraps that same call in a policy that automatically re-attempts it on failure, following the rules below.

## Retry policy parameters explained

| Parameter | What it controls |
|---|---|
| **`maxNumberOfAttempts`** | The total number of times the activity will be tried, including the first attempt. If set to `1`, no retries happen at all: it's a single try. |
| **`firstRetryIntervalInSeconds`** | How long to wait after the *first* failure before attempting retry #2. This is the starting point for the backoff calculation. |
| **`backoffCoefficient`** | A multiplier that controls how much the wait time grows with each subsequent retry. Defaults to `1` (no growth: a fixed delay every time). A value like `2.0` means each retry waits twice as long as the previous one (exponential backoff). |
| **`maxRetryIntervalInSeconds`** | A ceiling on the wait time: even as backoff grows the delay exponentially, it will never wait longer than this between attempts. |
| **`retryTimeout`** | A hard time limit on the *entire* retry process. If this elapses, retrying stops even if `maxNumberOfAttempts` hasn't been reached yet. By default, there is no timeout: retries continue until attempts are exhausted. |

### Example of backoff growth

With `firstRetryInterval = 5s` and `backoffCoefficient = 2.0`:
- Attempt 1: fails immediately
- Wait 5s → Attempt 2: fails
- Wait 10s → Attempt 3: fails
- Wait 20s → Attempt 4: fails
- ...and so on, until `maxNumberOfAttempts` or `retryTimeout` is hit, whichever comes first.

## What happens when all retries are exhausted

If the activity keeps failing until `maxNumberOfAttempts` (or `retryTimeout`) is reached, the framework stops retrying and the exception is thrown back up into the **orchestrator** as a `FunctionFailedException` (.NET): or the equivalent wrapped exception type in other languages. This means the orchestrator can catch it with an ordinary `try/catch` block and decide what to do next: log the failure, run a compensating activity, fall back to an alternative activity, or fail the whole orchestration.

```csharp
try
{
    await context.CallActivityWithRetryAsync<string>("FlakyActivity", retryOptions, input);
}
catch (FunctionFailedException)
{
    // All retries exhausted: handle the permanent failure here
    await context.CallActivityAsync("LogPermanentFailure", input);
}
```

## Demonstration: an activity that fails then recovers

To actually demonstrate automatic retries, you need an activity that behaves like a real transient failure: failing the first couple of calls, then succeeding. A simple way to simulate this locally is a static counter:

```csharp
public static class FlakyActivity
{
    private static int _attemptCount = 0;

    [FunctionName("FlakyActivity")]
    public static string Run([ActivityTrigger] string input, ILogger log)
    {
        _attemptCount++;
        log.LogInformation($"Attempt #{_attemptCount}");

        if (_attemptCount < 3)
        {
            throw new Exception($"Simulated transient failure on attempt #{_attemptCount}");
        }

        return $"Succeeded on attempt #{_attemptCount}";
    }
}
```

```csharp
[FunctionName("RetryDemoOrchestrator")]
public static async Task<string> RunOrchestrator(
    [OrchestrationTrigger] IDurableOrchestrationContext context)
{
    var retryOptions = new RetryOptions(
        firstRetryInterval: TimeSpan.FromSeconds(5),
        maxNumberOfAttempts: 3)
    {
        BackoffCoefficient = 2.0
    };

    string result = await context.CallActivityWithRetryAsync<string>(
        "FlakyActivity", retryOptions, null);

    return result;
}
```

Running this orchestration produces log output showing the activity failing on attempts 1 and 2, waiting with growing delays between each, then succeeding on attempt 3: a real, observable demonstration of the retry policy in action rather than just a description of it.

## Why this matters

Transient failures are common in distributed systems: networks blip, services throttle requests, databases briefly time out under load. Building automatic retries directly into the framework means every activity gets resilient behavior for free, without every developer having to hand-write their own retry loop, backoff math, and exception handling each time.

## Code

- [Retry demo: activity, orchestrator, and HTTP starter](../src/function_app.py)

<br>

# Task 3, Part 3: Client Functions as the Entry Point

## Overview

Every Durable Functions orchestration has to start somewhere: something outside the orchestration world has to trigger it, check on it, or stop it. That's the job of a **client function**. Client functions aren't a special trigger type on their own: they're defined by *which binding they use*, not by how they're triggered. Any function (HTTP, timer, queue, whatever) becomes a "client" the moment it uses the **durable client (orchestration client) binding** to interact with orchestrations or entities.

## What makes a function a "client"

A client function is the bridge between the outside world and the Durable Functions runtime. It's typically HTTP-triggered (since starting a workflow from an API call is the most common pattern), but it doesn't have to be: a timer-triggered function that kicks off a nightly orchestration is just as much a "client" function, because what defines it is the presence of the durable client binding, not its trigger.

Client functions are the only place allowed to:
- **Start** new orchestration instances
- **Query the status** of running or completed instances
- **Terminate** running instances
- **Raise external events** into orchestrators that are waiting for them
- **Signal entities** with one-way messages

Orchestrators and activities never do these things themselves: starting/managing orchestrations always comes from outside, through a client.

## The DurableClient binding

The durable client binding gives you an object (`DurableOrchestrationClient` in Python, `IDurableClient` in .NET) with methods for every one of the operations above. The three called out in this task:

### `start_new` / `StartNewAsync`

Starts a brand-new orchestration instance and immediately returns an **instance ID**: a unique string identifying that specific run. This ID is required for every future interaction with that instance (checking its status, terminating it, signaling it), so it needs to be captured and typically returned to the caller.

```python
instance_id = await client.start_new("retry_demo_orchestrator")
```

### `get_status` / `GetStatusAsync`

Given an instance ID, returns the current state of that orchestration. The response includes a **runtime status**, which can be:

| Status | Meaning |
|---|---|
| `Pending` | Instance has been scheduled but hasn't started running yet |
| `Running` | Currently executing |
| `Completed` | Finished successfully |
| `Failed` | Ended due to an unhandled exception |
| `Terminated` | Was explicitly stopped via `terminate` |
| `ContinuedAsNew` | Restarted itself as a new execution (used for eternal orchestrations) |

```python
status = await client.get_status(instance_id)
```

In practice, you usually don't even need to call this manually for basic polling: `create_check_status_response` (used in the retry demo) automatically returns a URL that, when polled, calls `get_status` under the hood and reports back the current state as JSON.

### `terminate` / `TerminateAsync`

Forcefully stops a running orchestration instance before it completes naturally. This is different from an orchestration *failing*: failure happens internally due to an unhandled exception; termination is an explicit, external command, typically used when a user cancels an action or a workflow needs to be stopped for business reasons.

```python
await client.terminate(instance_id, "Cancelled by user request")
```

The reason string is stored and shows up in the instance's status once terminated.

## Related client capabilities (encountered while researching this bullet)

Two other client-binding methods are worth understanding alongside the three above, since they round out what "entry point" really means:

- **`raise_event` / `RaiseEventAsync`**: sends data *into* an orchestration instance that is currently paused waiting for an external event (e.g. `context.wait_for_external_event(...)` inside the orchestrator). This is how things like human-approval steps work: the orchestrator pauses, and a client function later raises an event to unblock it.
- **`signal_entity` / `SignalEntityAsync`**: sends a one-way message to an entity function, used for entity-based state updates rather than orchestration workflows.

## Why this design makes sense

Keeping "start / check / stop" logic exclusively in client functions (rather than letting orchestrators or activities do it) preserves the separation of concerns that runs through the whole Durable Functions model: orchestrators describe workflow logic, activities do work, and client functions are the only components responsible for talking to the outside world about an orchestration's lifecycle. This mirrors why orchestrators can't do I/O directly: the client function is where "outside world" interaction is meant to happen.

## Code

- [HTTP client that starts the orchestration](../src/function_app.py): see `retry_demo_starter`, which uses `start_new` and `create_check_status_response`

## Summary

- A client function is defined by using the durable client binding: not by its trigger type.
- `start_new`/`StartNewAsync` begins a new orchestration and returns an instance ID needed for all future interactions with it.
- `get_status`/`GetStatusAsync` reports the current runtime status (Pending, Running, Completed, Failed, Terminated, ContinuedAsNew).
- `terminate`/`TerminateAsync` explicitly force-stops a running instance: distinct from a natural failure.
- `raise_event` and `signal_entity` extend the client's role to sending data into paused orchestrators and entities, respectively.
- Client functions exist specifically so that all interaction between the outside world and an orchestration's lifecycle happens in one well-defined place.