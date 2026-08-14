"""
Week 4 - Task 3 (bullet 3): Durable Entity - Shopping Cart
==========================================================
A cute shopping cart entity (a "virtual actor") that holds items as state.

Demonstrates:
  - Entity addressing:  EntityId("ShoppingCart", "<cart-id>")
  - Signalling the entity (fire-and-forget "add_item")
  - Reading the entity's state
  - SERIALISED ACCESS: fire many "add_item" signals at once at the SAME cart,
    then read the state - every item is present, proving operations were
    processed one at a time (no lost updates).

Run locally:  func start   (Azurite must be running)

Endpoints:
  POST /api/cart/{cartId}/add        body: {"item": "apple", "qty": 2}
  GET  /api/cart/{cartId}            -> current cart contents
  POST /api/cart/{cartId}/concurrent -> fires 20 add_item signals at once (test)
"""

import asyncio
import logging
import azure.functions as func
import azure.durable_functions as df

myApp = df.DFApp(http_auth_level=func.AuthLevel.ANONYMOUS)


#this is the entity/virtual actor here
# Holds the cart as a dict: { item_name: quantity }
#process the orders in a serialised manner

#this is the entity function
@myApp.entity_trigger(context_name="context")
def ShoppingCart(context: df.DurableEntityContext):

    cart = context.get_state(lambda: {})
    #start with an empty cart here

    #name of the message sent to the entity function
    operation = context.operation_name

    if operation == "add_item":
        item = context.get_input()
        #item here represents the dict that has been sent
        #item = {"item": "apple", "qty": 2}.
        name = item["item"]
        qty = item.get("qty", 1)
        cart[name] = cart.get(name, 0) + qty
        #this updates the current state
        context.set_state(cart)

    elif operation == "remove_item":
        name = context.get_input()
        cart.pop(name, None)
        context.set_state(cart)

    elif operation == "clear":
        context.set_state({})

    elif operation == "get":
        context.set_result(cart)
    #this tells us the current state present                  



# CLIENT: add one item to a cart
#this is the fire and forget mechanism here 
# POST /api/cart/{cartId}/add   body: {"item": "apple", "qty": 2}

@myApp.route(route="cart/{cartId}/add", methods=["POST"])
@myApp.durable_client_input(client_name="client")
async def add_to_cart(req: func.HttpRequest, client):
    cart_id = req.route_params.get("cartId")
    item = req.get_json()

    entityId = df.EntityId("ShoppingCart", cart_id)
    await client.signal_entity(entityId, "add_item", item)

    return func.HttpResponse(
        f"Signalled cart '{cart_id}' to add {item}", status_code=202
    )

#this is an http-trigger client function that based on the entity-id if it the state exists it returns with the state
@myApp.route(route="cart/{cartId}", methods=["GET"])
@myApp.durable_client_input(client_name="client")
async def get_cart(req: func.HttpRequest, client):
    cart_id = req.route_params.get("cartId")
    entityId = df.EntityId("ShoppingCart", cart_id)

    state = await client.read_entity_state(entityId)
    contents = state.entity_state if state.entity_state_exists else {}

    return func.HttpResponse(
        body=str(contents), status_code=200, mimetype="application/json"
    )


#rhis is the concurrency test where we will fire 20 add_item signals AT ONCE to the SAME cart.
#If access is properly serialised the overall qty count will be 20.
# POST /api/cart/{cartId}/concurrent

@myApp.route(route="cart/{cartId}/concurrent", methods=["POST"])
@myApp.durable_client_input(client_name="client")
async def concurrent_test(req: func.HttpRequest, client):
    cart_id = req.route_params.get("cartId")
    entityId = df.EntityId("ShoppingCart", cart_id)


    await asyncio.gather(*[
        client.signal_entity(entityId, "add_item", {"item": "apple", "qty": 1})
        for _ in range(20)
    ])

    return func.HttpResponse(
        f"Fired 20 concurrent add_item signals at cart '{cart_id}'. "
        f"Now GET /api/cart/{cart_id} - apple qty should be 20 if serialised correctly.",
        status_code=202,
    )
