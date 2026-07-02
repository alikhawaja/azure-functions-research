# Azure Functions — Deep Dive Research Plan

**Project:** Supervised Research (SProj 2026-27-DCW)  
**Students:** Effa & Maham  
**Supervisor:** Dr. A. Khawaja  
**Duration:** 8 Weeks (July – August 2026)  
**Start Date:** Week of July 6, 2026

---

## How to Use This Plan

Each week has a **focus area**, **learning objectives**, **tasks**, and **deliverables**. Students should:

1. Read the listed Microsoft Learn references thoroughly.
2. Complete all hands-on tasks in a shared Azure subscription.
3. Prepare the weekly deliverable and submit/present by the end of each week.

---

## Week 1 — Azure Functions Fundamentals

**Focus:** Azure Functions Overview  
**Reference:** [Azure Functions overview | Microsoft Learn](https://learn.microsoft.com/en-us/azure/azure-functions/functions-overview)

### Learning Objectives
- Understand what Azure Functions is and where it fits in the serverless ecosystem.
- Learn the core concepts: triggers, bindings, function apps, and execution models.
- Understand the programming model (v1 vs v2 for Python / in-process vs isolated for .NET).

### Tasks

#### 1. Serverless Computing & Azure Functions Position
- Research the evolution of cloud computing: IaaS → PaaS → FaaS. Where does Azure Functions sit?
- Investigate the concept of "cold starts" at a high level — what causes them and why they matter.

#### 2. Core Concepts Deep Dive
- Study the **execution model**: how does the Functions runtime receive a trigger event, spin up a host, execute your code, and return a result? Trace the full lifecycle of a single function invocation.
- Understand **triggers vs bindings**: how do input bindings differ from output bindings? What is declarative binding vs imperative binding?
- Explore the **function.json** schema — what gets configured there vs in code? How does this differ between programming models (v1 vs v2 for Python, in-process vs isolated for .NET)?

#### 3. Environment Setup & First Function
- Set up: Azure subscription, Azure Functions Core Tools (v4), VS Code with Azure Functions extension, Azure Storage Emulator (Azurite).
- Create an HTTP-triggered function. Run it **locally first** using `func start`. Set breakpoints and examine request/response objects.
- Deploy to Azure using VS Code or CLI (`func azure functionapp publish`). Compare the local vs cloud execution experience.

#### 4. Trigger & Binding Exploration
- Build a catalogue of the key trigger types: HTTP, Timer, Blob Storage, Queue Storage, Service Bus, Event Grid, Cosmos DB. For each, document: when to use it and configuration parameters.
- Implement at least **two trigger types** beyond HTTP (e.g., Timer + Queue). Observe how each trigger activates your function differently.
- Write a function that reads from one source (e.g., Queue trigger) and writes to another (e.g., Blob output binding) — a simple data pipeline.

### Deliverable
- **Summary document** covering Azure Functions position in the serverless landscape, core concepts, and execution lifecycle.
- **Trigger & binding catalogue** with configuration details and use-case guidance.
- **Working functions** (HTTP + two others) deployed to Azure, with source code and walkthrough notes.

---

## Week 2 — Function Types & Trigger Deep Dive

**Focus:** Function Types in Azure Durable Functions  
**Reference:** [Function types in Azure Durable Functions | Microsoft Learn](https://learn.microsoft.com/en-us/azure/azure-functions/durable/durable-functions-types-features-overview)

### Learning Objectives
- Understand the different function types: Orchestrator, Activity, Entity, and Client functions.
- Learn when and why each type is used.
- Grasp the concept of stateful vs stateless functions.

### Tasks

#### 1. Function Type Architecture
- Study the four Durable Function types: **Orchestrator**, **Activity**, **Entity**, and **Client** functions. For each, answer: What is its role? What constraints does it operate under? What can it call and what can call it?
- Investigate the **determinism requirement** for orchestrator functions — why must they be deterministic? What operations are forbidden inside an orchestrator (I/O, random numbers, DateTime.Now, Thread.Sleep)? What happens if you violate these rules?

#### 2. Replay Mechanism Deep Dive
- Understand the **replay mechanism**: how does the Durable Task Framework replay orchestrator code after each activity completes? Walk through a step-by-step replay scenario with a diagram.
- Study how orchestrators maintain state using **event sourcing**. What is the orchestration history table? What events are recorded (TaskScheduled, TaskCompleted, ExecutionStarted, etc.)?

#### 3. Activity & Client Functions
- Understand why activity functions are the "workhorses" — they have no determinism constraints and can do arbitrary I/O.
- Study **activity function retry policies**: `maxNumberOfAttempts`, `firstRetryIntervalInSeconds`, backoff coefficient. Write code that demonstrates automatic retries on transient failures.
- Study how client functions serve as the entry point — they start orchestrations, send signals to entities, and query status. Investigate the **DurableClient binding**: `StartNewAsync`, `GetStatusAsync`, `TerminateAsync`.

#### 4. Stateful vs Stateless Decision Framework
- Create a decision framework: when should you use a regular (stateless) Azure Function vs a Durable Function? Consider factors like execution duration, coordination needs, state management, and cost.
- Document the overhead of Durable Functions — storage transactions, latency from replay, serialisation costs.

### Deliverable
- **Function type deep-dive document** with architecture diagrams showing interaction between all four function types.
- **Replay mechanism walkthrough** — a step-by-step traced example with event history.
- **Decision framework** for stateful vs stateless function selection.

---

## Week 3 — Durable Functions: Patterns & Orchestration

**Focus:** Durable Functions Overview  
**Reference:** [Durable Functions overview | Microsoft Learn](https://learn.microsoft.com/en-us/azure/azure-functions/durable/durable-functions-overview)

### Learning Objectives
- Understand the Durable Functions extension and its architecture.
- Learn the core patterns: chaining, fan-out/fan-in, async HTTP APIs, monitoring, and human interaction.
- Understand the Task Hub, replay mechanism, and checkpointing.

### Tasks

#### 1. Durable Functions Architecture
- Map out the full architecture: **Task Hub**, storage providers (Azure Storage vs Netherite vs MSSQL), and how orchestration state is persisted.
- Understand **checkpointing**: when does the framework save state? What happens if the host crashes mid-execution? How does it recover?

#### 2. Core Orchestration Patterns
- Study each pattern in depth and draw a sequence diagram for each:
  - **Function chaining** — sequential pipeline (e.g., order processing: validate → charge → ship → notify).
  - **Fan-out/Fan-in** — parallel execution with aggregation (e.g., process N files concurrently, then merge results).
  - **Async HTTP API** — long-running operations with status polling endpoints.
  - **Monitor pattern** — periodic polling with dynamic intervals.
- For each pattern, document: when to use it, the API calls involved, and potential pitfalls.

#### 3. Hands-On Implementation
- Implement a **function-chaining** pattern: build a multi-step data processing pipeline where each step transforms data and passes it to the next.
- Implement a **fan-out/fan-in** pattern: take a list of items, process each in parallel, and aggregate the results.
- Test both implementations locally and deploy to Azure. Use the Durable Functions HTTP management APIs to query orchestration status, history, and purge completed instances.

#### 4. ContinueAsNew & History Management
- Research the **ContinueAsNew** pattern — how does it prevent unbounded history growth in long-running orchestrations?
- Investigate orchestration instance management: how to query running instances, purge history, and handle stuck orchestrations.

### Deliverable
- **Architecture diagram** of Durable Functions internals (Task Hub, storage, replay).
- **Pattern catalogue** with sequence diagrams and real-world use-case guidance.
- **Two working demos** (chaining + fan-out/fan-in) deployed to Azure with documented API interactions.

---

## Week 4 — Durable Functions: Advanced Patterns & Hands-On

**Focus:** Durable Functions — Advanced Patterns & Error Handling  
**Reference:** [Durable Functions overview | Microsoft Learn](https://learn.microsoft.com/en-us/azure/azure-functions/durable/durable-functions-overview)

### Learning Objectives
- Explore advanced patterns: sub-orchestrations, eternal orchestrations, and the human interaction pattern.
- Understand error handling, retry policies, and compensation logic.
- Learn about Durable Entities (virtual actors) for stateful singletons.

### Tasks

#### 1. Advanced Orchestration Patterns
- Study **sub-orchestrations**: when should you break a large orchestrator into smaller sub-orchestrators? Implement an example where a parent orchestrator delegates work to child orchestrators.
- Research the **human interaction pattern**: how to pause an orchestration waiting for external input (approval workflows). Implement a simple approval flow using `WaitForExternalEvent` with a timeout.
- Investigate **eternal orchestrations**: how to build orchestrations that run indefinitely (e.g., periodic cleanup jobs) without unbounded history.

#### 2. Error Handling & Resilience
- Study error propagation in orchestrations — what happens when an activity throws an exception? How does the orchestrator see it?
- Implement **retry policies** with different configurations: linear backoff, exponential backoff, and max retry limits. Test with a deliberately failing activity.
- Research **compensation logic** (the Saga pattern) — how to undo completed steps when a later step fails. Implement a simple example (e.g., book hotel → book flight → if flight fails, cancel hotel).

#### 3. Durable Entities (Virtual Actors)
- Study the **virtual actor model** — how do Durable Entities compare to traditional actor frameworks? Understand entity addressing (entity ID + entity name) and how clients signal or call entities.
- Research **serialised access** — how does the framework guarantee that only one operation executes on an entity at a time?
- Build a practical entity: a counter, a shopping cart, or a rate limiter. Test concurrent access to verify serialisation guarantees.

#### 4. Orchestrator Versioning
- Investigate what happens when you change orchestrator code while instances are running. What strategies exist for safe versioning (side-by-side deployment, rolling updates)?

### Deliverable
- **Working demos** of sub-orchestration, human interaction pattern, and a Durable Entity.
- **Error handling guide** with code showing retry policies and compensation (Saga) pattern.
- **Mid-project checkpoint presentation** (Weeks 1–4 review).

---

## Week 5 — AI-Enabled Azure Functions

**Focus:** Using AI Tools and Models in Azure Functions  
**Reference:** [Use AI tools and models in Azure Functions | Microsoft Learn](https://learn.microsoft.com/en-us/azure/azure-functions/functions-bindings-openai)

### Learning Objectives
- Understand how to integrate Azure OpenAI and other AI services with Azure Functions.
- Learn about AI bindings and extensions available for Functions.
- Explore patterns for building AI-powered serverless applications.

### Tasks

#### 1. Azure Functions OpenAI Extension
- Study the Azure Functions OpenAI extension — what bindings does it provide? Understand the **TextCompletion input binding**, **Embeddings input binding**, **Semantic Search**, and **Assistant** bindings.
- Investigate how the extension abstracts away direct REST/SDK calls to Azure OpenAI. What are the benefits and limitations of using bindings vs calling the SDK directly?

#### 2. Azure OpenAI Setup & Integration
- Provision an Azure OpenAI resource. Deploy a model (e.g., GPT-4o). Understand the relationship between resources, deployments, and model versions.
- Build an HTTP-triggered function that accepts a user prompt and returns a completion from Azure OpenAI using the **TextCompletion input binding**. Handle token limits, temperature settings, and error responses.
- Build a second function using the **Embeddings binding** — take a piece of text, generate an embedding vector, and store it (e.g., in Blob Storage or Cosmos DB).

#### 3. Assistants & Conversational AI
- Study the **Assistant bindings** — how do they manage conversation state across multiple turns? What storage backs the conversation history?
- Implement a simple chatbot function using the Assistant bindings that maintains conversation context.

#### 4. RAG Pattern with Azure Functions
- Research the **Retrieval-Augmented Generation (RAG)** pattern: how do Azure Functions + Azure AI Search + Azure OpenAI work together?
- Understand the **Semantic Search binding** — how does it integrate with vector stores to ground LLM responses in your own data?
- Design (and optionally prototype) a RAG pipeline: ingest documents → generate embeddings → store in a vector index → query with semantic search → augment prompt → return grounded response.

### Deliverable
- **AI integration architecture diagram** showing the data flow between Functions, Azure OpenAI, and AI Search.
- **Two working AI functions** — one using TextCompletion, one using Embeddings or Assistants.
- **RAG pattern design document** describing the pipeline, components, and feasibility assessment.

---

## Week 6 — Networking & Security

**Focus:** Azure Functions Networking Options  
**Reference:** [Azure Functions networking options | Microsoft Learn](https://learn.microsoft.com/en-us/azure/azure-functions/functions-networking-options)

### Learning Objectives
- Understand inbound and outbound networking features for Azure Functions.
- Learn about VNet integration, private endpoints, hybrid connections, and IP restrictions.
- Understand network security best practices for production deployments.

### Tasks

#### 1. Networking Architecture
- Study inbound vs outbound networking — what controls are available for traffic coming into your function app vs traffic going out?
- Create a **networking feature matrix** mapping capabilities by hosting plan (Consumption, Flex Consumption, Premium, Dedicated). Which features require which plans?

#### 2. VNet Integration & Private Endpoints
- Research **regional VNet integration** for outbound traffic — how does it allow your function to reach resources inside a VNet (databases, APIs, storage with private endpoints)?
- Study **private endpoints** for inbound traffic restriction — how do you make a function app accessible only from within a VNet, eliminating public internet exposure?
- Draw an architecture diagram showing a function app with: VNet integration (outbound) + private endpoint (inbound) + a private Cosmos DB or Storage account behind the VNet.

#### 3. Identity & Authentication
- Study **Azure App Service Authentication (EasyAuth)** — how does it work as a turn-key authentication layer? What identity providers does it support (Entra ID, Google, GitHub)?
- Investigate **Managed Identity** — how do system-assigned and user-assigned managed identities let functions access other Azure resources without storing credentials? Demonstrate accessing Key Vault or Storage using managed identity.
- Research **Key Vault references** in application settings — how can function app settings pull secrets from Key Vault automatically?

#### 4. Network Security Patterns
- Study **IP restrictions and access rules** — how to allowlist/blocklist IP ranges for inbound access.
- Research **service endpoints vs private endpoints** — what are the differences and when to use each?
- Document a **production security checklist** covering: HTTPS enforcement, minimum TLS version, CORS configuration, authentication, managed identity, network isolation, and secrets management.

### Deliverable
- **Networking feature matrix** (hosting plan × feature availability).
- **Security checklist** for production Azure Functions deployments.
- **Architecture diagram** showing a fully secured, VNet-integrated function app with private endpoints and managed identity.

---

## Week 7 — Hosting, Scaling & Monitoring

**Focus:** Azure Functions Scale, Hosting & Monitoring  
**Reference:** [Azure Functions hosting options | Microsoft Learn](https://learn.microsoft.com/en-us/azure/azure-functions/functions-scale)

### Learning Objectives
- Compare hosting plans: Consumption, Flex Consumption, Premium, Dedicated (App Service), and Container Apps.
- Understand scaling behaviour, cold starts, and performance tuning.
- Learn monitoring with Application Insights, Azure Monitor, and log analytics.

### Tasks

#### 1. Hosting Plans Deep Comparison
- Study each hosting plan in detail:
  - **Consumption** — true serverless, scale-to-zero, pay-per-execution. What are the limits (timeout, memory, instances)?
  - **Flex Consumption** — what does it add over standard Consumption? How does always-ready instance count work?
  - **Premium (Elastic Premium)** — pre-warmed instances, VNet integration, unlimited duration. When does the cost make sense?
  - **Dedicated (App Service plan)** — running on reserved VMs. When would you choose this over Premium?
  - **Container Apps** — running functions in a container on Azure Container Apps. What new deployment and scaling patterns does this enable?
- Create a **decision flowchart**: given a workload's requirements (latency sensitivity, execution duration, VNet needs, budget), which plan should you choose?

#### 2. Scaling Behaviour & Cold Starts
- Research how **scale controller** works — how does it decide when to add/remove instances? What metrics does it watch per trigger type (queue length, event backlog, HTTP concurrency)?
- Investigate **cold starts** in depth: what causes them (host startup, language runtime init, dependency loading)? Measure or research typical cold start times by language and plan.
- Study mitigation strategies: pre-warmed instances (Premium), always-ready instances (Flex Consumption), and application-level techniques (keeping dependencies lean, using health checks).

#### 3. Monitoring & Observability
- Configure **Application Insights** for a deployed function app. Explore: live metrics stream, failure analysis, dependency tracking, and performance views.
- Write and run **KQL queries** in Log Analytics to answer questions like: What is the average execution duration? Which functions fail most? What are the P95 response times?
- Study **custom metrics and telemetry** — how to emit custom events, track business KPIs, and set up alerts for anomalies (e.g., sudden spike in failures or latency).

#### 4. Cost Analysis
- Research the **pricing model** for each hosting plan. Calculate estimated monthly cost for a sample workload (e.g., 1M executions/month, average 500ms duration, 256MB memory).
- Investigate cost optimisation strategies: right-sizing plans, using Consumption for bursty workloads, reserving capacity for predictable loads.

### Deliverable
- **Hosting plan decision guide** (flowchart/decision tree with reasoning).
- **Cold start findings** document with data, causes, and mitigation recommendations.
- **Monitoring walkthrough** showing Application Insights setup, KQL queries, and alert configuration.

---

## Week 8 — Synthesis, Final Report & Presentation

**Focus:** Integration, Final Deliverables & Knowledge Consolidation  

### Learning Objectives
- Synthesise all weekly research into a cohesive final report.
- Build an end-to-end reference architecture combining key learnings.
- Present findings and demonstrate working prototypes.

### Tasks

#### 1. End-to-End Reference Architecture
- Design a complete architecture that combines the key learnings from all weeks: Durable Functions orchestration for workflow, AI integration for intelligence, secure networking with VNet/private endpoints, and the right hosting plan for the workload.
- Document the architecture with a detailed diagram showing all components, data flows, and security boundaries. Annotate each design decision with reasoning.

#### 2. Final Research Report
- Write a comprehensive research report (15–20 pages) consolidating all 7 weeks of findings. Structure: Introduction → Core Concepts → Durable Functions → AI Integration → Networking & Security → Hosting & Monitoring → Reference Architecture → Conclusion & Recommendations.
- Include all diagrams, code snippets, and decision frameworks produced during the project.

#### 3. Demo & Presentation
- Select 2–3 key prototypes built during the project. Polish them for a live demo — ensure they are deployed, functional, and demonstrate different aspects (e.g., a Durable Functions workflow + an AI-powered function).
- Prepare a 20–30 minute presentation covering the research journey, key findings, challenges encountered, and recommendations for teams adopting Azure Functions.

### Deliverable
- **Final research report** (15–20 pages).
- **Reference architecture diagram** with annotations.
- **Live demo** of selected prototypes.
- **Presentation slide deck.**

---

## Resources

- [Azure Functions documentation](https://learn.microsoft.com/en-us/azure/azure-functions/)
- [Durable Functions documentation](https://learn.microsoft.com/en-us/azure/azure-functions/durable/)
- [Azure Functions OpenAI extension](https://learn.microsoft.com/en-us/azure/azure-functions/functions-bindings-openai)
- [Azure Functions networking](https://learn.microsoft.com/en-us/azure/azure-functions/functions-networking-options)
- [Azure Functions hosting plans](https://learn.microsoft.com/en-us/azure/azure-functions/functions-scale)
- [Azure Functions Core Tools](https://learn.microsoft.com/en-us/azure/azure-functions/functions-run-local)
