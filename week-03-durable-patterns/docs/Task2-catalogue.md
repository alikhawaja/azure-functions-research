# Task 2: Research on Core Orchestration Patterns

A catalogue of the four core Durable Functions orchestration patterns. For each pattern: what it is, when to use it, the API call / SDK tool involved, potential pitfalls, and a sequence diagram.

---

## Pattern : Function Chaining

### What it is?

Function chaining is an orchestration pattern in which the result of one activity function serves as the input for the next activity function. A single workflow has multiple activity functions, and the output of one becomes the input of the next. It is a sequential execution model in which the result of each activity function depends on the result of the activity function that ran before it.

Because of this dependency, if any activity function does not return a correct answer, stops midway, or hits a code error during execution, the entire pipeline cannot complete  each step depends on the one before it.

### When to use it

This pattern is important when the functions in a workflow depend on each other and their results depend on each other.

**Example is of order processing:** A customer places an order. The first step validates the order. Once validated, the customer is charged. Once charged, the order is shipped. After shipping is done, the customer is notified. Each step cannot be performed independently of the step before it  there is a dependency between every step in the workflow.

`validate → charge → ship → notify`

### API call / SDK tool

`call_activity()` — the orchestrator repeatedly calls this to run each activity function in sequence, yielding and saving each result, then passing that result as the input to the next activity function.

### Pitfalls

- The steps run **sequentially**, which makes the workflow slow.  
- If one activity function is slow to execute, it impacts the entire workflow.  
- If one activity function fails to execute, the entire workflow stops.  
- There is **no parallel execution**.

### Sequence Diagram

graph LR

    A\[Validate\] \--\> B\[Charge\] \--\> C\[Ship\] \--\> D\[Notify\]

---

## Pattern 2 — Fan-out / Fan-in

### What it is?

Fan-out/Fan-in is an orchestration pattern used for executing tasks that can be done in parallel. If you have multiple activity functions that are independent and if they do not depend on each other and you do not need the result of any other activity function to process their own work  then this pattern applies.

Instead of waiting for one activity function to finish before starting the next, you take all N activity functions and run them in parallel at the same time.

- **Fan-out** \-you take N activity functions and start their parallel execution at the same time.  
- **Fan-in** \-you wait for all the activity functions to finish, then take all the outputs received from those functions and accumulate them into a final answer.

### When to use it

When you have many independent activity functions that do not depend on each other's results, and you want to run them simultaneously rather than one at a time.

**Example:** Processing N files concurrently, then merging the results.

### API call / SDK tool

`task_all()` (in Python) — once you have delegated the activity functions and they are all executing, `task_all()` waits for all of them to finish and return their answers, then all those answers are combined and aggregated into a final answer.

### Pitfalls

- Because fan-in must wait for **all** activity functions to finish before aggregating, even if one activity function takes a lot of time, the aggregation is delayed overall this can be time-consuming.  
- Fan-out executes N activity functions at the same time, which can use a lot of compute.  
- Because of this high throughput and compute demand, **Netherite** is generally preferred as the storage provider for large fan-outs.

### Sequence Diagram

graph LR

    O\[Orchestrator\] \--\> A\[Activity 1\]

    O \--\> B\[Activity 2\]

    O \--\> C\[Activity 3\]

    O \--\> D\[Activity N\]

    A \--\> M\[Aggregate results\]

    B \--\> M

    C \--\> M

    D \--\> M

---

## Pattern 3 : Async HTTP API

### What it is?

The Async HTTP API is an orchestration pattern that handles the case where a client sends an HTTP request to start an orchestration, but the orchestration process is complicated and takes a lot of time. We cannot expect the client to keep waiting until the orchestration completes and returns a final result so we prevent that from happening.

Instead, as soon as the client makes an HTTP request to start the orchestration workflow, the pattern returns an **HTTP 202** code, which tells the client that processing is being done and that it has to wait. Along with the 202, it returns a **status URL**. The client then uses a process of **polling** against that status URL to keep getting updated on the current status of the orchestration workflow which can be failed, terminated, or success.

### When to use it?

When an orchestration is long-running and the client cannot be kept waiting with an open connection until the workflow finishes.

**Example:** A long-running file/video processing job started over HTTP, where the client is given a status URL and polls it until the job is done.

### API call / SDK tool

`create_check_status_response()` — when the client function starts the orchestration, this builds the HTTP 202 response together with the status URLs. One of those URLs is the **status query URL** (`check_status_url` / `statusQueryGetUri`), which the client keeps polling to get the current status of the orchestration.

### Pitfalls

- The client has to be prepared to handle all outcomes which includes failures as well as successes (and terminated).  
- Polling itself uses a lot of compute  repeatedly asking for the status consumes resources.  
- You have to be precise about the polling interval polling too frequently wastes compute, while polling too slowly delays getting the result.

### Sequence Diagram

graph LR

    C\[Client\] \--\>|HTTP request| O\[Orchestration starts\]

    O \--\>|HTTP 202 \+ status URL| C

    C \--\>|poll status URL| S\[Status: Running / Completed / Failed\]

    S \--\>|Completed| R\[Final result returned\]

---

## Pattern 4 — Monitor

### What it is?

The Monitor pattern is used when an orchestration workflow needs to check the status of an **external event**, and that checking is done from within the orchestrator. The orchestrator keeps checking the status of the external event on a recurring basis until an **exit condition** is met.

The interval between checks is flexible there is no fixed time. You can keep changing the time duration you want between checks, for example checking every ten minutes or every few seconds, depending on your needs.

### When to use it?

When you want polling to be done for an **external event from within an orchestrator**  repeatedly checking a condition over time until it becomes true.

**Example:** You want to buy a perfume, but it goes out of stock. Using the Monitor pattern, the orchestrator keeps checking the status of the perfume based on a chosen time duration  until the exit condition is met, which is the perfume coming back in stock. Once it is back in stock, the monitor stops.

### API call / SDK tool

`create_timer()` — a durable timer used to wait a chosen interval before the next status check. There is no fixed time; the duration between checks can be changed as needed, so the orchestrator can keep polling for the external event at whatever interval you set.

### Pitfalls

- Repeated polling uses a lot of compute and resources, so you have to be specific about the polling interval and avoid wasting resources.  
- There must be a clear exit condition, otherwise the monitor keeps checking indefinitely.

### Sequence Diagram

graph LR

    O\[Orchestrator\] \--\> C{Check status of external event}

    C \--\>|Condition not met| W\[Wait interval \- create\_timer\]

    W \--\> C

    C \--\>|Condition met| A\[Take final action and stop\]  
