# Azure Functions — Deep Dive Research

**Project:** Supervised Research (SProj 2026-27-DCW)  
**Students:** Effa & Maham  
**Supervisor:** Dr. A. Khawaja  
**Duration:** 8 Weeks (July – August 2026)

## Repository Structure

```
├── week-01-fundamentals/        # Azure Functions overview, triggers, bindings
│   ├── src/                     # HTTP, Timer, Queue function apps
│   └── docs/                    # Summary docs, trigger catalogue
├── week-02-function-types/      # Orchestrator, Activity, Entity, Client
│   ├── src/                     # Code samples for each function type
│   └── docs/                    # Comparison matrix, replay walkthrough
├── week-03-durable-patterns/    # Chaining, fan-out/fan-in, async HTTP
│   ├── src/
│   │   ├── chaining-demo/       # Function chaining implementation
│   │   └── fanout-fanin-demo/   # Fan-out/fan-in implementation
│   └── docs/                    # Pattern catalogue, architecture diagrams
├── week-04-advanced-durable/    # Sub-orchestrations, error handling, entities
│   ├── src/
│   │   ├── sub-orchestration/
│   │   ├── error-handling/      # Retry policies, Saga/compensation
│   │   └── durable-entities/    # Counter, cart, or rate limiter
│   └── docs/                    # Error handling guide, versioning notes
├── week-05-ai-functions/        # Azure OpenAI integration
│   ├── src/
│   │   ├── text-completion/     # TextCompletion binding demo
│   │   └── embeddings/          # Embeddings binding demo
│   └── docs/                    # AI architecture diagram, RAG design
├── week-06-networking-security/ # VNet, private endpoints, managed identity
│   └── docs/                    # Networking matrix, security checklist
├── week-07-hosting-monitoring/  # Hosting plans, scaling, App Insights
│   └── docs/                    # Decision guide, cold start report, KQL queries
├── week-08-final/               # Synthesis and final deliverables
│   ├── report/                  # Final research report
│   ├── presentation/            # Slide deck
│   └── reference-architecture/  # End-to-end architecture diagrams
└── shared/                      # Cross-week shared resources
    ├── diagrams/                # Reusable architecture diagrams
    └── scripts/                 # Utility scripts (deploy, test, etc.)
```

## Getting Started

1. Clone this repository
2. Review the [Research Plan](docs/Azure-Functions-Research-Plan.md)
3. Install prerequisites:
   - [Azure Functions Core Tools v4](https://learn.microsoft.com/en-us/azure/azure-functions/functions-run-local)
   - [VS Code](https://code.visualstudio.com/) + [Azure Functions Extension](https://marketplace.visualstudio.com/items?itemName=ms-azuretools.vscode-azurefunctions)
   - [Azure CLI](https://learn.microsoft.com/en-us/cli/azure/install-azure-cli)
   - [Azurite](https://learn.microsoft.com/en-us/azure/storage/common/storage-use-azurite) (local storage emulator)
4. Start with `week-01-fundamentals/`

## Weekly Workflow

1. Read the week's section in the Research Plan
2. Create your function app(s) in the `src/` folder for that week
3. Write findings and deliverables in the `docs/` folder
4. Commit and push by end of week

## Key References

- [Azure Functions Documentation](https://learn.microsoft.com/en-us/azure/azure-functions/)
- [Durable Functions Documentation](https://learn.microsoft.com/en-us/azure/azure-functions/durable/)
- [Azure Functions OpenAI Extension](https://learn.microsoft.com/en-us/azure/azure-functions/functions-bindings-openai)
- [Azure Functions Networking](https://learn.microsoft.com/en-us/azure/azure-functions/functions-networking-options)
- [Azure Functions Hosting Plans](https://learn.microsoft.com/en-us/azure/azure-functions/functions-scale)
