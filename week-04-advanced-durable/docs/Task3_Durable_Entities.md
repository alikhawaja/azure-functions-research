# Task 3 — Durable Entities (Virtual Actors)

**Focus:** Durable Functions — Durable Entities, the Virtual Actor Model, and Serialised Access

---

## 1. The Virtual Actor Model

An entity function is a special kind of function designed for the **persistence of state**, generally called a **virtual actor**. An actor refers to any piece of code that has its own state and processes messages one by one, which is exactly what an entity function does.

Each entity has an **entity name** and an **entity ID**. The entity name tells us what type of entity we are talking about, and the entity ID identifies the specific instance of it. The state is stored within the entity function, and it receives messages one at a time.

### Comparison with traditional actor frameworks

When comparing a Durable Entity function with other actor frameworks (such as Orleans), they are inherently similar in one regard: whether it is a normal actor framework or a Durable Entity, both hold state, and any update to that state is made externally by sending a request, which is processed in a serial manner (one at a time).

The difference comes down to **where the state is stored, whether it persists, and whether we have to create it ourselves.**

A Durable Entity function is called a **virtual actor**, meaning we do not have to create or delete the state. It is persisted automatically and stored in storage on Microsoft Azure, so it is always persisted. You only have to **reference** the entity by using the entity name and the entity ID (the type of state and the specific instance), and this is used to retrieve it from storage. If it is not available, it gets created and then becomes available.

In a normal actor framework, by contrast, the entire state is held in **memory**. So in the case of a crash or failure, the state is lost because it was only in memory and could not be persisted — you would have to recreate it. With a virtual actor like an entity function, the state is always present in storage, so even in the case of a crash or failure it survives — it is durable and persistent.

### Signalling vs calling

An orchestrator (or client) can interact with an entity in two ways:

- **Signal** — send a message without waiting for any reply (fire-and-forget). You signal when the operation is a command and you don't need a response; this is faster and doesn't block.
- **Call** — send a message and wait for an answer back. You call when you actually need data back from the entity, such as querying its current value.

---

## 2. Serialised Access

When an entity function receives multiple requests at the same time, it must ensure every request is processed one by one in a **serial** manner, rather than allowing parallel execution. If multiple requests to the same entity were processed at the same time, it could produce an inaccurate result, and we want accuracy.

Every entity function has a unique **entity ID** and **entity name**. Based on that unique entity ID, each entity has its own **message queue** within the Task Hub on Microsoft Azure. This queue receives all the requests for that specific entity, and they queue up and are processed **one at a time, sequentially**.

However, if requests are made to two **different** entities — which may share the same entity name but have different entity IDs — those can be processed in **parallel**. The serial restriction (executing requests one by one) applies only to an entity with the **same entity ID**. So serialisation is per-entity-ID, which preserves accuracy for each individual entity while still allowing different entities to run concurrently.

This means the framework gives you thread-safe state without writing any locking code yourself.

---

## 3. Practical Entity — Shopping Cart

A shopping cart implemented as a Durable Entity. It holds its items as state (`{ item_name: quantity }`) and processes operations one at a time. This demonstrates entity addressing, signalling, reading state, and serialised access.

### The entity

```python
@myApp.entity_trigger(context_name="context")
def ShoppingCart(context: df.DurableEntityContext):
    cart = context.get_state(lambda: {})   # start with an empty cart if new
    operation = context.operation_name

    if operation == "add_item":
        item = context.get_input()
        name = item["item"]
        qty = item.get("qty", 1)
        cart[name] = cart.get(name, 0) + qty   # add to existing quantity
        context.set_state(cart)                 # save state back

    elif operation == "remove_item":
        name = context.get_input()
        cart.pop(name, None)
        context.set_state(cart)

    elif operation == "clear":
        context.set_state({})

    elif operation == "get":
        context.set_result(cart)                # return current contents
```

### Addressing and signalling the entity

```python
# Add one item (signal - fire and forget)
@myApp.route(route="cart/{cartId}/add", methods=["POST"])
@myApp.durable_client_input(client_name="client")
async def add_to_cart(req, client):
    cart_id = req.route_params.get("cartId")
    item = req.get_json()
    entityId = df.EntityId("ShoppingCart", cart_id)   # entity name + entity ID
    await client.signal_entity(entityId, "add_item", item)
    return func.HttpResponse(f"Signalled cart '{cart_id}' to add {item}", status_code=202)
```

### Concurrency test (verifying serialised access)

```python
@myApp.route(route="cart/{cartId}/concurrent", methods=["POST"])
@myApp.durable_client_input(client_name="client")
async def concurrent_test(req, client):
    cart_id = req.route_params.get("cartId")
    entityId = df.EntityId("ShoppingCart", cart_id)
    # Fire 20 "add one apple" signals concurrently at the SAME cart
    await asyncio.gather(*[
        client.signal_entity(entityId, "add_item", {"item": "apple", "qty": 1})
        for _ in range(20)
    ])
    return func.HttpResponse(f"Fired 20 concurrent add_item signals at cart '{cart_id}'.", status_code=202)
```

### Result

Firing 20 concurrent `add_item` signals at the same cart and then reading its state returns:

```json
{"apple": 20}
```

Every one of the 20 simultaneous operations was applied correctly — the total is exactly 20, with no lost updates. This proves that access to the entity was **serialised**: the operations were processed one at a time rather than overlapping. If access were not serialised, a race condition would produce a value lower than 20.
