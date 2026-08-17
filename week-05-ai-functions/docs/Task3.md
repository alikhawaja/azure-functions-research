# Task 3: Assistants & Conversational AI

## What problem does this solve?

TextCompletion (Task 2) is stateless: every call is a fresh question with no memory of earlier messages. A chatbot needs memory: it has to remember what the user said two messages ago. The Assistant bindings add that memory layer on top of the same chat model, without you writing any storage code yourself.

## The three Assistant bindings

### 1. `assistantCreate` (output binding)

Starts a new conversation session. You give it a `chatId` (any string you choose, like a session ID or user ID) and optional instructions (a system prompt describing how the assistant should behave). This is a one-time setup step per conversation: like opening a new chat thread.

### 2. `assistantPost` (input binding)

Sends a new message into an existing conversation. This is the core of the chatbot. Each time you call it:

1. It looks up the conversation history for that `chatId`.
2. It adds your new message to that history.
3. It sends the *whole* history (old messages + new one) to the chat model, so the model has full context.
4. It gets the model's reply back.
5. It saves both your message and the model's reply into storage, appended to the history.

Because it always sends the full history, the model can refer back to anything said earlier in the conversation: that's what "maintaining context across turns" actually means under the hood.

### 3. `assistantQuery` (input binding)

Reads back the saved conversation history for a `chatId`, without sending a new message. Useful for a client that wants to check "what has been said so far," or reload a conversation after refreshing the page. Supports a `timestampUTC` filter so you can ask for only messages *since* a certain time (a polling pattern).

## How state is stored across turns

Every conversation is identified by a `chatId` you choose. Each message: from the user and from the assistant: gets saved under that ID in a storage backend. By default this is **Azure Table Storage**, using the same storage account already configured for your Function App (`AzureWebJobsStorage`). This is set through `chatStorageConnectionSetting` and `collectionName` properties on the bindings, so it's configurable if you want a different storage account or table name.

Here's the key idea: **the binding does the read-append-write cycle for you.** Every time `assistantPost` runs, it:

- Reads the existing rows for that `chatId` from storage
- Adds the new user message + the model's response as new rows
- The next call repeats this, always building on what's already there

You never manually manage a message list or write to a database: the binding handles all of it behind the `assistantPost` call.

## Why this matters for multi-turn context

Language models don't actually "remember" anything between API calls: they only see what's in the current request. So "memory" in a chatbot really means: *resending the whole conversation history every single time.* The Assistant bindings automate that resend-the-history step. Without them, you'd have to manually store every message somewhere yourself and rebuild the message list before every single call to the chat model. The binding turns that into one line of code.

## The three-step conversation flow

1. **Create**: `PUT /api/chats/{chatId}` → `assistantCreate` sets up a new session.
2. **Post**: `POST /api/chats/{chatId}` with a message → `assistantPost` sends it, gets a reply, saves both.
3. **Query** (optional): `GET /api/chats/{chatId}` → `assistantQuery` reads back the full history.

Repeating step 2 with the same `chatId` is what makes it a real conversation instead of a series of one-off questions.

## What's implemented

`src/chatbot/function_app.py` implements all three routes above:

- `PUT /api/chats/{chatId}`: starts a new chat session with a system instruction
- `POST /api/chats/{chatId}`: sends a user message, returns the assistant's reply
- `GET /api/chats/{chatId}`: returns the full saved conversation history

Test it by creating a chat once, then posting two or three messages to the *same* `chatId`: the model's replies should reflect earlier turns in the conversation, proving the context is actually being maintained.