# Task 4: ContinueAsNew & History Management

## 1. Why This Matters

An orchestrator function keeps a **history**. This history is a log. It records every step the orchestrator did: every activity call, every timer, every event.

The framework uses this log to "replay" the orchestrator after every checkpoint. Replay is how it rebuilds the current state.

If an orchestrator runs forever (a loop that never ends), the history keeps growing. It never gets cleared on its own. A big history causes problems:

- It takes longer to replay.
- It uses more memory.
- It slows down the whole app over time.

This is the exact problem ContinueAsNew solves.

---

## 2. What Is ContinueAsNew

ContinueAsNew lets an orchestration **restart itself**, but with a clean history.

Think of it like this: instead of one long, never-ending story with thousands of pages, the orchestrator closes the book after a chapter and opens a brand new one. Same character (same instance ID), new book (fresh history), and it can carry forward some info (the new input) into the next chapter.

Key points:

- The **instance ID stays the same**.
- The **history resets to zero**.
- Internally, a new "execution ID" is created for the new run. This ID is hidden from you, but it exists behind the scenes.
- You pass in a new input value. That input becomes the starting point for the next run.

So instead of the orchestrator looping forever inside itself, it keeps "restarting" itself from scratch, again and again, without the history ever piling up.

---

## 3. How It Prevents Unbounded History Growth

Without ContinueAsNew:

```
Loop iteration 1 → history grows
Loop iteration 2 → history grows more
Loop iteration 3 → history grows even more
...
Loop iteration 10,000 → history is huge → app slows down or breaks
```

With ContinueAsNew:

```
Run 1 (small history) → ContinueAsNew → history wiped
Run 2 (small history) → ContinueAsNew → history wiped
Run 3 (small history) → ContinueAsNew → history wiped
...
```

The history never gets the chance to grow big, because it keeps getting reset before it becomes a problem.

This pattern (an orchestration that loops forever using ContinueAsNew) has a name: the **Eternal Orchestration** pattern.

---

## 4. Eternal Orchestration Pattern: Example

A common use case: a cleanup job that runs every hour, forever.

Steps:

1. Do the cleanup work (call an activity function).
2. Wait one hour (using a durable timer).
3. Call ContinueAsNew to restart the loop, with a clean history.
4. Repeat forever.

Pseudocode:

```python
import azure.durable_functions as df
from datetime import timedelta
 
def orchestrator_function(context: df.DurableOrchestrationContext):
    # Step 1: do the actual work
    yield context.call_activity("DoCleanup", None)
 
    # Step 2: wait for 1 hour
    next_cleanup = context.current_utc_datetime + timedelta(hours=1)
    yield context.create_timer(next_cleanup)
 
    # Step 3: restart with a clean history
    context.continue_as_new(None)
 
main = df.Orchestrator.create(orchestrator_function)
```
 

Other real uses for this pattern:

- **Aggregators**: an orchestration that keeps collecting and combining data forever.
- **Counters**: an orchestration that waits for events (like "increase" or "decrease") and keeps a running total, calling ContinueAsNew after each update.
- **Polling loops**: checking something on a schedule, forever, without the history piling up.

---

## 5. When To Call ContinueAsNew

call it when:

- The orchestration is meant to run **forever** or for a **very long time** (eternal orchestrations).
- The orchestration works through a **big list** in small chunks, and it would be better to process a bit, checkpoint, then continue with the rest as a "new" run.
- The history is getting close to a size or count limit (some frameworks let you check this and decide).

Things to be careful about:

- Anything you didn't save into the new input is **lost**. The next run starts fresh, so pass forward any data you still need.
- Don't call ContinueAsNew in the middle of unfinished work (like activity calls that haven't returned yet). Let the current round of work finish first, then call it.
- It's a restart, not a "return with a result": if the orchestration is truly done, just return normally instead of calling ContinueAsNew.

---

## 6. Instance Management:

Once you have running orchestrations (especially long or eternal ones), you also need ways to **watch them, stop them, and clean them up**. Durable Functions gives you built-in tools for this. They come in two flavors:

- **HTTP Management API**: plain HTTP calls (GET, POST, DELETE) that anyone can use, even outside your app.
- **Client bindings (code)**: the same actions, but called directly from your own function code using the orchestration client.

Both let you do the same core things: **query, terminate, suspend/resume, and purge**.

### 6.1 Query Instances

You can ask: "show me all orchestrations," or "show me only the ones that are still running," or "show me ones created in the last 2 days."

What you can filter by:

- **Status**: Running, Completed, Failed, Terminated, Pending, etc.
- **Time range**: created after/before a certain date.
- **Instance ID**: check one specific orchestration.

This is how you check the health of your workflows without guessing. It also tells you the current history and status of a single instance if you need to debug something.

### 6.2 Terminate Stuck Orchestrations

Sometimes an orchestration gets stuck. Maybe it's waiting on an event that will never come, or it's just stuck in a bad state.

You can send a **terminate** request for that instance ID. This stops it.

- Terminate is **not instant**. The request is accepted right away (you get a "202 Accepted" response), but the actual stopping happens a bit later, in the background.
- In rare cases, termination can be slow or unreliable, especially if the orchestration is deep in a step. Setting timeouts on your orchestrations and activities ahead of time helps avoid needing to force-terminate in the first place.

### 6.3 Suspend and Resume

You can also **pause** (suspend) an orchestration and **start it again later** (resume), without fully stopping it. Useful when you want to temporarily halt work: for example, during a maintenance window: without losing progress.

### 6.4 Purge History

"Purge" means: delete the stored history/records for finished orchestrations, so they stop taking up storage space.

Important rule: **you can only purge instances that are done.** That means their status must be Completed, Failed, or Terminated: not Running.

Ways to purge:

- **Purge a single instance**: give its instance ID, and its history gets deleted.
- **Purge by criteria**: give a time range and/or a list of statuses (e.g., "delete everything Completed before 30 days ago"), and it deletes all matching instances in one go.
- **Command line**: there's also a CLI command (func durable purge-history) that does the same thing, useful for scripts or scheduled cleanup.

Good practice: don't do this manually and randomly. Set up a **timer-triggered function** that runs on a schedule (e.g., once a day) and purges old completed instances automatically. This keeps your storage account from filling up with data you no longer need.

### 6.5 Handling Stuck Orchestrations: Step by Step

Putting it together, here's a simple recovery routine:

1. **Query** all instances with status "Running."
2. Look for ones that have been running much longer than expected (this means something is likely stuck).
3. **Terminate** the stuck ones.
4. Once their status changes to "Terminated," you can **purge** their history if you don't need it anymore.
5. If needed, start a fresh instance to redo the work.

---

## 7. Summary Table

| Concept | What it does | Why it matters |
|---|---|---|
| History | Log of everything the orchestrator has done | Used to replay and rebuild state |
| ContinueAsNew | Restarts an orchestration with a clean history, same instance ID | Stops history from growing forever |
| Eternal Orchestration | An orchestration that loops forever using ContinueAsNew | Used for aggregators, counters, periodic jobs |
| Query instances | Look up orchestrations by status, ID, or time range | Lets you monitor and debug workflows |
| Terminate | Stops a running orchestration | Used to kill stuck or unwanted orchestrations |
| Suspend / Resume | Pause and later restart an orchestration | Useful for maintenance windows |
| Purge | Deletes stored history for finished orchestrations | Keeps storage clean and cheap; only works on Completed/Failed/Terminated instances |

---