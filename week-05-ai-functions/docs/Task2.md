# Task 2,Azure OpenAI Setup & Integration

## Part A: Provisioning Azure OpenAI

### Resource vs. Deployment vs. Model version

These three words get mixed up a lot. Here's the simple version:

- **Resource** = the "account" you create in Azure. It lives in a region (like East US) and is the thing you get billed for. Think of it like opening a bank branch.
- **Deployment** = a specific model made available inside that resource, under a name you choose. Think of it like a teller window inside the branch,you decide what service runs there.
- **Model version** = the exact version of the AI model (like GPT-4o "2024-08-06"). Versions get updated over time as OpenAI/Microsoft release improvements.

**Why this matters:** your code never talks to "GPT-4o" directly. It talks to your **deployment name** (e.g. `gpt-4o`, or `prod-chat`, whatever you called it). This means:

- You can change which model version is behind that deployment name later, without touching your code.
- You can have multiple deployments in one resource,e.g. one for chat, one for embeddings.
- If you rename a deployment, your code breaks until you update the config. If you just upgrade the model version behind an existing deployment, your code doesn't need to change at all.

### Creating the resource and deployments

```bash
# 1. Create a resource group (a folder to organize your Azure resources)
az group create -n rg-week5-ai -l eastus

# 2. Create the Azure OpenAI resource
az cognitiveservices account create \
  -n aoai-week5 -g rg-week5-ai -l eastus \
  --kind OpenAI --sku S0 \
  --custom-domain aoai-week5

# 3. Deploy a chat model (used for completions)
az cognitiveservices account deployment create \
  -n aoai-week5 -g rg-week5-ai \
  --deployment-name gpt-4o \
  --model-name gpt-4o --model-version "2024-08-06" \
  --model-format OpenAI --sku-capacity 10 --sku-name Standard

# 4. Deploy an embedding model (used for turning text into vectors)
az cognitiveservices account deployment create \
  -n aoai-week5 -g rg-week5-ai \
  --deployment-name text-embedding-3-small \
  --model-name text-embedding-3-small --model-version "1" \
  --model-format OpenAI --sku-capacity 10 --sku-name Standard
```

After this, you have one resource (`aoai-week5`) with two deployments inside it: `gpt-4o` and `text-embedding-3-small`.

### Authentication: key vs. managed identity

- **Key auth**,copy an API key from the resource and put it in your app settings. Simple, but the key is a secret you have to protect and rotate.
- **Managed identity**,your Function App gets its own identity in Azure, and you grant that identity permission (the `Cognitive Services OpenAI User` role) to call the Azure OpenAI resource. No key ever exists in your code or config.

Managed identity is the safer, recommended approach for anything beyond quick local testing.

```bash
az role assignment create \
  --assignee <function-app-principal-id> \
  --role "Cognitive Services OpenAI User" \
  --scope /subscriptions/<sub>/resourceGroups/rg-week5-ai/providers/Microsoft.CognitiveServices/accounts/aoai-week5
```

---

## Part B: Function 1,TextCompletion (with token limits, temperature, errors)

**Goal:** accept a prompt from the user, send it to Azure OpenAI, return the answer.

**Route:** `POST /api/complete`

**Body:** `{ "prompt": "...", "temperature": 0.7, "maxTokens": 500 }`

### How each requirement is handled

**Token limits.** `maxTokens` caps how long the model's answer can be. Left uncapped, a model can generate a very long (and costly) response. The function reads `maxTokens` from the request and passes it to the binding. In the validated version of the function, it's also clamped to a safe range (1–4000) so a bad or malicious request can't ask for an unreasonable amount of output.

**Temperature.** This controls how "creative" vs. "predictable" the answer is,`0` is focused and repeatable, higher values (`1`–`2`) are more varied. It's passed straight through from the request to the binding, also clamped (`0`–`2`) so bad input doesn't break the call.

**Error responses.** Two things can go wrong: (1) the request itself is invalid (missing prompt, bad temperature), or (2) Azure OpenAI itself fails (rate limit, timeout, bad deployment name). The function separates these:
- Invalid request → `400 Bad Request` with a clear message, before ever calling Azure OpenAI.
- Azure OpenAI call fails → `502 Bad Gateway`, since the Function itself worked fine but the upstream service didn't.

### Why validation happens in a separate step

The TextCompletion binding pulls its settings (prompt, temperature, maxTokens) directly from the incoming request *before* your function code even runs. That means you can't "fix" bad values inside the function body,by the time your code runs, the binding has already tried to use them. So the safe pattern is: validate and clamp the input first (in a plain HTTP handler), then only call the AI-bound function with values you already know are safe. This is why the project has two versions: `complete` (shows the direct binding) and `complete-safe` (shows the validated wrapper you'd actually use in production).

---

## Part C: Function 2,Embeddings + Storage

**Goal:** take a piece of text, turn it into an embedding vector, and save it somewhere so it can be searched later.

**Route:** `POST /api/embed`

**Body:** `{ "text": "..." }`

### How it works, step by step

1. The Embeddings input binding sends the text to the embedding model deployment and gets back a vector (a list of numbers representing the text's meaning).
2. The function generates a unique ID (`uuid`) for this piece of text.
3. The text, its ID, and its embedding are packaged into one JSON record.
4. That record is uploaded to a Blob Storage container called `embeddings`, using the Blob Storage SDK.

### Why the Blob *SDK* is used here instead of a Blob *output binding*

Normally you'd wire up a Blob output binding for this kind of thing,it's less code. But output binding paths (like `embeddings/{id}.json`) can only use values that exist *before* your function runs,like a route parameter. Here, the ID is a UUID generated *while the function is running*, so there's no way for the binding to know the file path in advance. That's why this function calls the Blob Storage SDK directly instead,it's the correct tool when the storage location depends on something computed at runtime.

### Where the data could go instead

- **Blob Storage** (what this function uses),simplest option, good for a small number of records or as a staging area before indexing.
- **Cosmos DB**,better if you need to query/filter embeddings later, or plan to scale to a large number of records with structured queries.
- **Azure AI Search**,the real destination for a RAG pipeline (covered in Task 4),this is a proper vector index built for similarity search, not just storage.

For this task, Blob Storage is enough to prove the embedding pipeline works end to end.

---

## Testing both functions locally

```bash
curl -X POST http://localhost:7071/api/complete \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Explain serverless computing in two sentences.", "temperature": 0.7, "maxTokens": 200}'

curl -X POST http://localhost:7071/api/embed \
  -H "Content-Type: application/json" \
  -d '{"text": "Azure Functions is a serverless compute service."}'
```

If both return a `200`/`201` with a JSON body, the pipeline is working: request → binding → Azure OpenAI → response/storage.