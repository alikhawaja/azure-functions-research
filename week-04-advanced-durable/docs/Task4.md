# Week 4 — Task 4: Orchestrator Versioning

**Reference:** [Versioning in Durable Functions | Microsoft Learn](https://learn.microsoft.com/en-us/azure/azure-functions/durable/durable-functions-versioning)

**Note:** This task is research only. No code. No deployment.

---

## why this is even a problem

An orchestrator function can run for a long time. Sometimes days. Sometimes longer.

Azure does not keep an orchestrator "alive" the whole time. Instead, it keeps a **history** of every step the orchestrator has done. When the orchestrator needs to wake up or continue, Azure **replays** the code from the start. It uses the history to skip steps already done, and picks up from where it left off.

For this to work, the orchestrator code must always do the **same steps in the same order**, every time it replays. This is called being **deterministic**.

---

## The question: what happens if you change the code while instances are running?

Say an orchestration is halfway done. It has a history of, say, 5 steps completed.

Now you deploy new code. The new code has different logic. Maybe you added a step, removed a step, or changed the order.

When Azure replays that old instance, it tries to match the history against the **new** code. But the new code does not match what actually happened before. Azure cannot make sense of it.

**Result: a "nondeterminism error."** The orchestration instance breaks. It may fail completely. If it was a long-running orchestration, that could mean hours or days of work lost.

So: **changing orchestrator code while instances are running is risky.** It can break the instances that are already in progress.

---

## The question: what strategies exist to do this safely?

Here are the main strategies, from worst to best.

### 1. Do nothing (not a real strategy — avoid this)

Just deploy the new code and hope for the best.

**Why this is bad:** if a function used by a running instance gets removed or changed, the app can hit low-level failures. This can cause serious performance problems. Not recommended.

### 2. Stop all running instances first

Before deploying, stop every instance that is still running.

For the default Azure Storage setup, you can clear out the internal queues Durable Functions uses (called the control-queue and workitem-queue). Or you can stop the app, delete these queues, and restart it. Azure recreates them automatically.

**Why this is only okay sometimes:** you are throwing away all in-progress work. This is fine for local testing or early prototypes. It is not okay for a real production app where people are waiting on those workflows to finish.

### 3. Side-by-side deployment

Deploy the new version of your app **next to** the old version, instead of replacing it.

One way to do this: use a **different storage account** for the new version. This keeps the old and new orchestrations completely separate. They cannot interfere with each other.

**Why this works:** old instances keep running on old code. New instances run on new code. Nothing collides.

**Downside:** more setup. You are running two versions of your app at once, which costs more and needs more management.

### 4. Version-specific task hub names

Similar idea to side-by-side deployment, but simpler. Instead of a whole new storage account, you just give each version of your app a different **task hub name** (a task hub is like a named workspace for your orchestrations).

**Why this works:** same reason as side-by-side. Old and new orchestrations are kept apart, just using a lighter-weight method.

### 5. Built-in orchestration versioning (the recommended modern approach)

This is a feature built directly into Durable Functions. Here is how it works:

* Every orchestration instance gets a **version number** the moment it is created. This version never changes for that instance.
* Your orchestrator code can **check its own version** and run different logic depending on which version it is. This means old and new logic can live in the **same codebase**, at the same time.
* Azure's runtime enforces a rule: workers running **older** code are not allowed to run instances that need **newer** code. But workers running **newer** code CAN still run older instances.

**Why this is the best option:**

* No need for separate deployments, storage accounts, or task hubs. It is built in.
* It works no matter which storage backend you use.
* This is the approach Microsoft currently recommends for apps that need zero-downtime deployments with breaking changes.

This also enables **rolling updates**. Because newer workers can still handle older instances, you can update your servers gradually, one at a time, without breaking anything mid-rollout.

---

## Summary table

| Strategy | Safe for production? | Effort | Notes |
|---|---|---|---|
| Do nothing | No | None | Can cause serious runtime failures |
| Stop all running instances | Only for dev/testing | Low | Throws away in-progress work |
| Side-by-side deployment (separate storage account) | Yes | High | Most bulletproof, but costly to manage |
| Version-specific task hub names | Yes | Medium | Lighter version of side-by-side |
| Built-in orchestration versioning | Yes (recommended) | Low | Built into the platform, supports rolling updates |

---
