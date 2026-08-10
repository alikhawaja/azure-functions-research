# Task 1 — Durable Functions Architecture

## Bullet 1: Map out the full architecture — Task Hub, storage providers (Azure Storage vs Netherite vs MSSQL), and how orchestration state is persisted.

The Task Hub is a container present on Microsoft Azure that holds three different storage providers: Azure Storage, Netherite, and Microsoft SQL Server. Azure Storage is the default provider and uses the history table, which retains the state of each activity function. Netherite and Microsoft SQL Server are the alternative providers, with MSSQL storing state in a SQL Server database.

When the orchestrator starts and calls an activity function, it reads the state of that activity function from the relevant data in the history table.

If the activity function has already been executed and its status is "task completed", it is not re-executed, and the orchestrator moves on to the next activity function.

If the orchestrator reaches an activity function that has not yet been executed its status is not "task completed" then it has to await. This await triggers checkpointing. The orchestrator schedules that activity function to be executed, checkpointing is performed and the state is stored in the history table, and the orchestrator then unloads from memory. Once the activity function completes, its result is written as an updated state to the same history table within the Task Hub.

This is how state is persisted and maintained. Checkpointing is triggered only when the orchestrator reaches an activity function and has to await, which signals that the task has not yet been completed. The orchestrator then schedules the task, checkpoints, and unloads from memory, and the result of the activity function is written as an updated state to the history table.

## Bullet 2: Understand checkpointing when does the framework save state? What happens if the host crashes mid-execution? How does it recover?

The framework saves state only when the orchestrator runs and reaches an activity function whose task has not yet been completed. In that case, it schedules that task. Because the orchestrator hits an await  meaning the activity function has now been scheduled and will run  instead of waiting for that activity function to execute, it checkpoints the state to the history table within the Task Hub (the Azure table) and then unloads from memory. Once the activity function runs and returns its final answer, that answer is written to the history table present within Microsoft Azure.

If a host crashes mid-execution because of a failure such as the VM restarting or the function app restarting due to a new deployment  recovery is still possible. Either a new host (Host B) can be spun up, or the same host can continue and rerun. The host looks up the status of each activity function and knows which ones have already run, because "task completed" is the state stored within the history table. It uses that history table to determine progress and only runs the tasks that have not yet been executed.

This persistence is possible only because Durable Functions are being used, where state can persist through the history table.

---

*Architecture diagram \= attached as Task1 Taskhub architectural diagram*  
