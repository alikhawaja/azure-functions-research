# Task 1 — Azure Functions OpenAI Extension

## What is this extension?

The [Azure Functions OpenAI extension](https://learn.microsoft.com/en-us/azure/azure-functions/functions-bindings-openai) lets your Azure Function talk to Azure OpenAI without writing SDK code yourself. You just add a "binding" to your function, and the extension handles the call for you.

It is still in **preview**. That means it works, but it can still change.

A binding in Azure Functions is a simple way to connect your code to another service. Instead of writing code to call an API, you just describe what you want (a prompt, a file, a search query) and the binding does the work in the background.

The extension gives you four main bindings:

1. TextCompletion
2. Embeddings
3. Semantic Search
4. Assistants

Let's go through each one.

---

## 1. TextCompletion input binding

**What it does:** sends a prompt to Azure OpenAI's chat/completion model and gives you back the text answer.

**How you use it:** you write a prompt like `"Who is {name}?"`. The `{name}` part gets filled in automatically from your request (like a route parameter). The binding sends this prompt to your chat model deployment and returns the response as a string.

**Example use case:** a simple "ask a question, get an answer" API endpoint.

**Key settings:**
- `ChatModel` (or `Model`) — which deployment to use (like `gpt-4o`)
- `Temperature` — how random/creative the answer is
- `MaxTokens` — the limit on how long the answer can be

This is the simplest binding. One prompt in, one answer out.

---

## 2. Embeddings input binding

**What it does:** turns text into a list of numbers (a vector). This vector represents the *meaning* of the text, not the exact words.

**Why this matters:** two sentences that mean similar things will have vectors that are close together, even if the words are different. This is the foundation of search-by-meaning (semantic search) instead of search-by-exact-word.

**How you use it:** give the binding some raw text (or a file), and it returns the embedding vector. You then usually save that vector somewhere, like Blob Storage or a vector database, so you can search it later.

**Example use case:** turning a document into a vector so it can be matched against future search queries.

---

## 3. Semantic Search binding

**What it does:** combines two steps in one binding — it turns your search query into an embedding, then searches a vector index (like Azure AI Search) for the closest matching content.

**Why it's useful:** without this binding, you'd have to call the embeddings API yourself, then separately call the search API, then combine the results. This binding does both in one call.

**How you use it:** you point the binding at your Azure AI Search index/collection, give it the query text, and it returns the top matching pieces of content.

**Example use case:** this is the core building block of RAG (Retrieval-Augmented Generation) — finding the right pieces of your own data to feed into a prompt.

---

## 4. Assistant bindings

Assistants are for chatbots — conversations with back-and-forth turns, not just single questions.

There are three parts:

- **`assistantPost`** — sends a new user message to the assistant, gets a response back, and **saves both the user message and the AI's reply into storage.** This is how the conversation history builds up over time.
- **`assistantQuery`** — reads back the saved conversation history for a given assistant/chat session. Useful if a client wants to check "what's happened so far" or poll for new messages.
- **`assistantSkillTrigger`** — lets you define custom functions the assistant can call, like "add a to-do item" or "look up an order." This works through function calling: the model decides when it needs to run one of these functions, and the extension routes the call to your code.

**How conversation state is stored:** each assistant/chat session has an ID. Every message (from the user and from the AI) gets saved under that ID in a storage backend — the default is Azure Table Storage (via the same storage account used by your Function App), though this is configurable via the `ChatStorageConnectionSetting` and `CollectionName` settings. Each time you call `assistantPost`, the extension pulls the existing history, adds the new exchange, and saves it back. That's what makes multi-turn conversations "remember" earlier turns without you writing that logic yourself.

---

## How the extension abstracts away direct REST/SDK calls

Normally, if you wanted to call Azure OpenAI yourself, you would need to:

- Set up an SDK client or write raw HTTP calls
- Handle authentication (API key or managed identity)
- Build the request body correctly
- Parse the JSON response
- Handle retries and errors

The extension does all of this behind the scenes. You just declare a binding with a few properties (prompt, model name, connection settings), and the extension:

- Reads your connection settings (`AzureOpenAI__endpoint`, `AzureOpenAI__credential`, etc.)
- Builds and sends the API request
- Waits for the response
- Converts the response into a simple object or string your function code can use directly

So your function code barely touches "AI plumbing" at all — it just receives a ready-to-use result.

---

## Benefits of using bindings

- **Less code.** No SDK setup, no manual request building.
- **Consistent pattern.** Bindings work the same way as other Azure Functions bindings you already know (Blob, Queue, HTTP), so it's an easy mental model.
- **Built-in prompt templating.** You can drop request values straight into a prompt string, like `"Who is {name}?"`.
- **Encourages secure defaults.** The extension is designed to work well with managed identity, which is safer than hardcoding API keys.
- **Combines steps.** Semantic Search does embedding + search in one binding instead of two separate calls.

## Limitations of using bindings

- **Still in preview.** Property names and behavior have changed between versions before. Not fully stable yet.
- **Less control.** No easy access to advanced features like streaming responses or fine-tuned retry logic — you're limited to what the binding exposes.
- **Python/PowerShell support is weaker.** They use a generic binding system (`generic_input_binding`) instead of dedicated, typed bindings like C# and Node.js get. This means less auto-complete and type-checking help.
- **Debugging is one step removed.** If something goes wrong, you're looking at extension-level errors, not a familiar SDK stack trace.
- **Complex logic still needs the SDK.** If you need to validate/clamp inputs, do custom retries, or use features like tool-calling, you'll likely end up writing extra code around the binding anyway, or dropping to the SDK entirely.

## When to use which

| Situation | Best choice |
|---|---|
| Simple prompt-in, answer-out endpoint | Binding (TextCompletion) |
| Turning text into vectors for storage | Binding (Embeddings) |
| RAG-style retrieval from your own data | Binding (Semantic Search) |
| Basic multi-turn chatbot | Binding (Assistants) |
| Streaming responses, custom retries, advanced control | Direct SDK call |
| Production system that can't tolerate breaking changes right now | Direct SDK call, or pin extension version carefully |

**Bottom line:** bindings are great for getting AI features working quickly with minimal code. For advanced or production-critical scenarios, you may still need to call the SDK directly, or mix both approaches in the same Function App.