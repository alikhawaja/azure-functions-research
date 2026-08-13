# Task 2 Error Handling & Resilience Guide

**Focus:** Durable Functions, Error Handling, Retry Policies, and Compensation (Saga Pattern)

---

## 1\. Error Propagation in Orchestrations

When an activity throws an exception and when it is unable to perform the function it was designated to perform, that exception is written to the **history table** on Microsoft Azure as a "task failed" status.

When the orchestrator runs and reaches the line `yield context.call_activity(...)` where it calls that activity function, it checks the status of that activity in the history table. If it sees "task failed," that is where the orchestrator **re-raises the exception** that caused the activity to fail. This is handled using a **try/except** block: if the activity ran smoothly with a "task completed" status, the `try` block executes normally; if it has a "task failed" status, the same exception is re-raised inside the orchestrator and caught by the `except` block, where it is available as an error object `e`.

The re-raised exception is called a **`FunctionFailedException`**. This is how the orchestrator is able to see that an activity function failed — the failure is recorded in the history table, and the exception is re-raised at the line where the activity was called. If the exception is **not** caught, it propagates up and the entire orchestration fails.

try:

    result \= yield context.call\_activity("risky\_activity", data)

    \# if the activity SUCCEEDS, execution continues here with the result

except Exception as e:

    \# if the activity FAILS, the exception is re-raised here and handled

    yield context.call\_activity("handle\_failure", str(e))

---

## 2\. Retry Policies

Many times activity functions fail, and instead of letting that disturb or destroy the entire orchestration workflow, there are built-in **retry policies** that can be attached to activity functions using **`call_activity_with_retry`**. This keeps the orchestration workflow from being disturbed when an activity fails.

A **backoff** setting controls the time duration between retries when an activity is rerun multiple times:

- **Linear backoff** : the time duration between each retry stays the same. For example, with three retries, each retry has the same gap (e.g. 3 seconds).  
- **Exponential backoff**:  a **backoff coefficient** increases the duration between retries. For example, with a coefficient of 2 starting at 2 seconds, the next retry waits 4 seconds, then 8 seconds, and so on.

There is also a **maximum number of retries** which is the maximum number of times the activity function will rerun, after which the exception is always raised.

This is tested using a **deliberately failing activity** (one that throws an exception on purpose) to confirm the retries happen at the expected intervals and that it gives up after the max limit.

### Code

\# A deliberately failing activity \- always throws, so the retries are visible

@myApp.activity\_trigger(input\_name="attemptnote")

def flaky\_activity(attemptnote: str) \-\> str:

    logging.warning(f"\[flaky\_activity\] running \- will fail on purpose ({attemptnote})")

    raise Exception("Deliberate failure to demonstrate retries")

\# LINEAR BACKOFF \- constant 3s gap, up to 3 attempts

@myApp.orchestration\_trigger(context\_name="context")

def retry\_linear(context):

    retry\_options \= df.RetryOptions(

        first\_retry\_interval\_in\_milliseconds=3000,   \# 3 seconds

        max\_number\_of\_attempts=3,

    )

    \# backoff\_coefficient defaults to 1 \=\> LINEAR (delay stays constant)

    try:

        result \= yield context.call\_activity\_with\_retry("flaky\_activity", retry\_options, "linear")

        return {"policy": "linear", "result": result}

    except Exception as e:

        return {"policy": "linear", "outcome": "gave up after 3 attempts, 3s apart", "error": str(e)}

\# EXPONENTIAL BACKOFF \- 2s, then 4s (coefficient 2), up to 3 attempts

@myApp.orchestration\_trigger(context\_name="context")

def retry\_exponential(context):

    retry\_options \= df.RetryOptions(

        first\_retry\_interval\_in\_milliseconds=2000,

        max\_number\_of\_attempts=3,

    )

    retry\_options.backoff\_coefficient \= 2.0   \# doubles each retry \=\> 2s, 4s

    try:

        result \= yield context.call\_activity\_with\_retry("flaky\_activity", retry\_options, "exponential")

        return {"policy": "exponential", "result": result}

    except Exception as e:

        return {"policy": "exponential", "outcome": "gave up after 3 attempts, doubling delay", "error": str(e)}

\# MAX RETRY LIMIT \- up to 5 attempts, then gives up

@myApp.orchestration\_trigger(context\_name="context")

def retry\_maxout(context):

    retry\_options \= df.RetryOptions(

        first\_retry\_interval\_in\_milliseconds=2000,

        max\_number\_of\_attempts=5,

    )

    try:

        result \= yield context.call\_activity\_with\_retry("flaky\_activity", retry\_options, "maxout")

        return {"policy": "maxout", "result": result}

    except Exception as e:

        return {"policy": "maxout", "outcome": "gave up after the max limit of 5 attempts", "error": str(e)}

---

## 3\. Compensation Logic (the Saga Pattern)

Compensation logic, also known as the **Saga pattern**, means that when functions run in sequence and a later function fails, you undo the earlier functions that have already completed. For every function that performs a change, there is a compensating function that undoes it in case a later step fails.

For example: I book a hotel, and that succeeds. Then I need to book a flight but booking the flight fails. Because the flight could not be booked, I run the compensations in **reverse order**: I undo the hotel booking by running its compensating function, which cancels the hotel reservation.

This is the Saga pattern for each step that makes a change, you write a compensating function, and if a later step fails, you run those compensations in reverse to roll everything back.

### Code

@myApp.orchestration\_trigger(context\_name="context")

def saga\_booking(context):

    completed \= \[\]          \# remember which steps actually succeeded

    log \= \[\]

    try:

        \# Step 1: book hotel (succeeds)

        hotel \= yield context.call\_activity("book\_hotel", None)

        completed.append("hotel")

        log.append(hotel)

        \# Step 2: book flight (FAILS on purpose)

        flight \= yield context.call\_activity("book\_flight", None)

        completed.append("flight")

        log.append(flight)

        return {"status": "Booked successfully", "log": log}

    except Exception as e:

        \# A step failed \-\> undo completed steps in REVERSE order

        log.append(f"FAILURE: {str(e)}")

        if "flight" in completed:

            log.append(yield context.call\_activity("cancel\_flight", None))

        if "hotel" in completed:

            log.append(yield context.call\_activity("cancel\_hotel", None))

        return {"status": "Failed \- rolled back", "log": log}

\# Forward activities

@myApp.activity\_trigger(input\_name="ignored")

def book\_hotel(ignored):

    return "Hotel booked"

@myApp.activity\_trigger(input\_name="ignored")

def book\_flight(ignored):

    raise Exception("Flight booking failed \- no seats available")

\# Compensating activities (the undo actions)

@myApp.activity\_trigger(input\_name="ignored")

def cancel\_flight(ignored):

    return "Flight cancelled"

@myApp.activity\_trigger(input\_name="ignored")

def cancel\_hotel(ignored):

    return "Hotel cancelled (compensated)"

**Expected result when run:** the hotel books, the flight fails, and the compensation cancels the hotel returning `{"status": "Failed - rolled back", "log": ["Hotel booked", "FAILURE: Flight booking failed - no seats available", "Hotel cancelled (compensated)"]}`.

---

