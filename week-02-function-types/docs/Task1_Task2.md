**Week 2 --- Durable Functions**

Function Type Architecture

Effa & Maham \| Supervisor: Dr. A. Khawaja \| SProj 2026-27-DCW

# **1. The Four Durable Function Types**

The reason we use Durable Functions is that Durable Functions are an extension of Azure Functions. Regular Azure Functions are stateless they are not able to retain state in between the steps of an entire workflow. Durable Functions solve this: they provide a way for state to be persisted, so you can know where you left your work off and pick up again from that exact point. There are four Durable Function types: the client function, the orchestrator function, the activity function, and the entity function.

## **Client Function**

The client function is the entry point, it is the very first function in the workflow. It can be triggered by any normal function, such as an HTTP trigger, a queue trigger, a blob storage trigger, or a Cosmos DB trigger; any such function can act as the trigger for the client. The client function has no particular constraints, and its main responsibility is to call and start the orchestrator function. It can also signal and read entity functions.

## **Orchestrator Function**

The orchestrator function cannot be called by any function outside the durable framework. It can only be called from within the framework, specifically by the client function. It determines which functions run, and in what order and sequence it is the conductor of the workflow. The orchestrator can call activity functions, entity functions, and even other orchestrator functions; when an orchestrator calls other orchestrators, this is known as a sub-orchestration.

The orchestrator has one key constraint: it must follow the property of determinism, which means the same input must always produce the same output. This is why functions such as date/time functions or random-number functions are forbidden inside an orchestrator they keep changing and would not give a consistent result. Determinism is required because the orchestrator must be able to pick up from exactly where it left off, using the replay mechanism (covered in detail in the next section), which re-runs the same steps of the workflow in the same order every time.

## **Activity Function**

The activity function is the workhorse and it is the function that actually gets the work done. It behaves like any other normal function but is designated to perform the real work of the workflow. An activity function can only be called by an orchestrator; it cannot be called by any external function outside the durable framework. Because it is not an orchestrator, it does not have the determinism constraint, so it is free to do non-deterministic work such as network calls, database access, or other I/O.

## **Entity Function**

The entity function is designed to read and update specific pieces of state it saves particular pieces of the state and updates them over time. An entity function can be called by a client function or by an orchestrator function, but like the orchestrator it cannot be called by any external function from outside the durable framework. The entity function also does not have the determinism constraint.

## **Summary of Call Relationships**

The diagram below summarises how the four function types interact which function can call which, and the key rules that govern those relationships.

![](./media/image1.png)

*The four Durable Function types and their call relationships (created in draw.io).*

  -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
  **Type**           **Role**                                                                            **What can call it**                                         **What it can call**
  ------------------ ----------------------------------------------------------------------------------- ------------------------------------------------------------ -----------------------------------------------------------------------------------
  **Client**         Entry point; starts and manages the workflow. No determinism constraint.            Any normal trigger (HTTP, queue, blob, timer, Cosmos DB).    Starts orchestrators; signals and reads entities.

  **Orchestrator**   The conductor; defines which steps run and in what order. Must be deterministic.    Only the client (never directly from outside).               Activities, other orchestrators (sub-orchestration), entities, timers.

  **Activity**       The workhorse; does the real work. No determinism constraint (free to do I/O).      Only an orchestrator.                                        Anything a normal function can (APIs, databases) --- not other durable functions.

  **Entity**         Reads and updates specific pieces of long-lived state. No determinism constraint.   A client or an orchestrator (never directly from outside).   Responds to operations that read or update its state.
  -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

## 

## 

## **The Determinism Requirement**

Orchestrator functions have one key constraint: determinism, meaning the same input should always produce the same output. Because the orchestrator is the coordinator of a workflow whose tasks depend on one another, it uses the replay mechanism (explained in detail in the next section) to know which tasks have already been executed and which still need to run. Each time an activity produces an output, that output is stored in the history; but the orchestrator itself re-runs from the very beginning on every execution. For it to correctly work out where to pick up from, the current run must match the saved history exactly so the same input must always give the same output, otherwise a contradiction arises between the current workflow and the history, and the orchestrator no longer knows which activities have run and which have not.

For this reason, any operation that can produce a different result for the same input is forbidden inside an orchestrator. This includes: the current date/time (e.g. DateTime.Now), which differs on each replay; random numbers or new GUIDs, which generate a different value every time with no dependable output; direct I/O such as reading from a database or calling an external API, since that data can change over time and return a different output; and Thread.Sleep or creating new threads, because the orchestrator must run on a single thread and blocking waits break that model (durable timers should be used for delays instead). Environment variables and non-constant static variables are likewise avoided, as their values can change over time. All such non-deterministic work is instead delegated to activity functions, which run once and have their result frozen in the history.

If these rules are violated, the replay diverges from the recorded history. The Durable Task Framework detects this mismatch and throws a NonDeterministicOrchestrationException indicating that the orchestrator ran but non-deterministic behaviour was observed and the orchestration is stopped and marked as Failed, with no automatic restart.

# **2. Replay Mechanism Deep Dive**

The orchestrator is the coordinator of the workflow: it decides which activity function runs first and in what order. It manages this using the replay mechanism, which relies on a history that the orchestrator has access to. The key idea is that the orchestrator does not stay in memory while waiting for an activity to finish that would waste compute, time, and money. Instead it unloads from memory between steps and rebuilds its position by replaying the history each time it resumes.

## **Step-by-Step Replay Scenario**

Consider an orchestrator that chains three activities A, then B, then C. The first time the orchestrator runs, an ExecutionStarted event is written to the history. The orchestrator reaches the first task, activity A, and since the history shows it has not yet run, it schedules task A. At this point the orchestrator stops and unloads from memory it does not sit waiting for A to finish, which prevents wasting compute and cost. Activity A then runs independently, and when it completes, a TaskCompleted (A) event with its result is written to the history.

Because A has completed, the replay mechanism causes the orchestrator to run again from the very start. This time, when it reaches task A, it checks the history, finds TaskCompleted (A), and uses that saved result instead of re-running A. It then moves on to task B, which is not yet in the history, so it schedules B and unloads from memory again. When B finishes, TaskScheduled (B) and TaskCompleted (B) with its result are recorded in the history.

The orchestrator then replays again from the top: it reads A and B from the history (skipping them), reaches task C, schedules it, and unloads. When C completes and is recorded, the orchestrator replays one final time A, B, and C are all found complete in the history, there are no new steps left, and the orchestration finishes with an OrchestrationCompleted event.

So on every replay the orchestrator re-runs from the beginning, reads already-completed steps from the history rather than re-executing them, and actually runs only the next new step before unloading again. This continues until no new steps remain. This is also exactly why the orchestrator must be deterministic because the code re-runs from the top every time, it must make the same decisions on each run so that the replay always lines up with the recorded history.

![](./media/image2.png)

*Step-by-step replay of a three-activity orchestrator (A → B → C), showing how each run re-runs from the top, reads completed steps from the history, schedules the next new step, and unloads --- until the orchestration completes.*

## **Event Sourcing & the Orchestration History Table**

Orchestrators maintain their state using a mechanism called event sourcing. The key idea of event sourcing is that, rather than storing the current state directly, you store the entire ordered flow of events exactly as they took place, and the current state is then derived by replaying those events. A helpful way to picture this is a bank account: instead of storing "balance = \$500" directly, event sourcing stores the list of transactions (opened +\$100, deposit +\$600, withdrawal −\$200) and computes the balance by replaying them. The events are the source of truth, and the state is rebuilt from them which is why it is called event sourcing.

In Durable Functions, these events are stored in a table in Azure Storage called the orchestration history table. Every significant step of the orchestration is appended to this table as an event, in the order it occurred. The main events recorded include: ExecutionStarted (the orchestration began), TaskScheduled (the orchestrator scheduled an activity), TaskCompleted (an activity finished, with its result saved), and OrchestrationCompleted (the whole workflow finished).

This is exactly what makes the replay mechanism possible. Because the orchestrator unloads from memory between steps and does not store its position directly, it needs the full record of how the tasks unfolded in order to resume. On each replay it reads this event log from the history table from the top, reconstructing its state the TaskCompleted events give it the saved results of activities that already ran, so it skips them and continues from the next unscheduled step. Event sourcing and the history table are therefore the machinery underneath replay: together they allow the orchestrator to retain state and reliably pick up from where it left off.