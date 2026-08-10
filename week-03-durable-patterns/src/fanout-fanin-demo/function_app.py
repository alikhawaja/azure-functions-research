import azure.functions as func
import azure.durable_functions as df


#this will create the durable function app
app = df.DFApp(http_auth_level=func.AuthLevel.ANONYMOUS)

#this is the code for Function-chaining where the functions are interdependent on each other

#the client function is an http trigger function that will start the orchestration process
@app.route(route="orchestrators/chaining") 
#this means the client is reachable from outside by sending api request to  api/orchestrators/chaining
@app.durable_client_input(client_name="client")
async def chaining_http_start(req: func.HttpRequest, client):
    input_data = req.get_json() if req.get_body() else {"value": "raw-input-123"}
    #this tells the client to start the chaining orchestrator
    instance_id = await client.start_new("chaining_orchestrator", None, input_data)
    response = client.create_check_status_response(req, instance_id)
    #this is the http-api orchestration pattern giving it a status poll/url to check the status of orchestration
    return response


# Orchestrator function defines the pipeline
@app.orchestration_trigger(context_name="context")
def chaining_orchestrator(context: df.DurableOrchestrationContext):
    input_data = context.get_input()

    #the classic function chaining where different activity functions are being called and are interdependent on one another
    step1_result = yield context.call_activity("normalize_data", input_data)
    step2_result = yield context.call_activity("enrich_data", step1_result)
    step3_result = yield context.call_activity("finalize_data", step2_result)
    #the yield over here is what allows checkpointing to take place 

    return step3_result


#this activity function will normalize the data 
@app.activity_trigger(input_name="data")
def normalize_data(data):
    value = data.get("value", "")
    return {"value": value.strip().lower(), "step": "normalized"}
#strip removes the trailing whitespaces and then lowercases them and returns the changed dict values


#this activity function will enrich the normalized data from the previous function
@app.activity_trigger(input_name="data")
def enrich_data(data):
    value = data.get("value", "")
    return {"value": value, "length": len(value), "step": "enriched"}


#finalize the last activity function based on the output received from enrich_data
@app.activity_trigger(input_name="data")
def finalize_data(data):
    return {
        "final_value": data.get("value"),
        "length": data.get("length"),
        "step": "finalized",
        "status": "complete"
    }
#this is the orchestration's final output


# THIS IS THE FAN-IN AND FAN-OUT PATTERN
# Take a list of items, process each one in parallel,
# then aggregate all the results into a single summary.


#the client function is the http trigger function that starts the fan-out/fan-in orchestration
@app.route(route="orchestrators/fanout")
@app.durable_client_input(client_name="client")
async def fanout_http_start(req: func.HttpRequest, client):
    try:
        body = req.get_json()
        items = body.get("items")
    except ValueError:
        items = None

    if not items:
        items = ["file1.txt", "file2.txt", "file3.txt", "file4.txt", "file5.txt"]

    instance_id = await client.start_new("fanout_orchestrator", None, items)
    response = client.create_check_status_response(req, instance_id)
    return response


#this orchestrator will now  fans out N activities and then fans in which means that it will aggregate
@app.orchestration_trigger(context_name="context")
def fanout_orchestrator(context: df.DurableOrchestrationContext):
    items = context.get_input()

    #this is FANOUT and it uses the call_activity schedule all activities in parallel like all files present in the items list
    parallel_tasks = [context.call_activity("process_item", item) for item in items]

    #this if FAN-IN and uses task_all for execution of the parallel tasks 
    results = yield context.task_all(parallel_tasks)

    summary = {
        "items_processed": len(results),
        "results": results,
        "total_size": sum(r["size"] for r in results)
    }
    return summary


#this is what enables and allows the fan-out and fan-in by allowing multiple items to be processed on their own in a loop
@app.activity_trigger(input_name="item")
def process_item(item):
    return {"item": item, "size": len(item) * 10, "status": "processed"}
