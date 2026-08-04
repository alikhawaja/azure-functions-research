import azure.functions as func
import logging

app = func.FunctionApp(http_auth_level=func.AuthLevel.ANONYMOUS)

#this uses a decorator, because we are already using python v2 which uses no function.json file for
#configuration hence it uses a decorator for the trigger and bindings


#this tells that the trigger type is of HTTP here 
#this route name in the decorater is what becomes part of the url of the function app code
#https://week1-az-effa-2026.azurewebsites.net/api/http_trigger?name=effa
#/api/http_trigger?name=effa this is the url path defined by router name passed in the decorator

@app.route(route="HTTP_trigger")
def HTTP_trigger(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Python HTTP trigger function processed a request.')


    #look for a name in the url query
    name = req.params.get('name')
    if not name:
        
        #then check for the name in the request body
        try:
            req_body = req.get_json()
        except ValueError:
            pass
        else:
            name = req_body.get('name')

    if name:
        return func.HttpResponse(f"Hello, {name}. This HTTP triggered function executed successfully.")
    else:
        return func.HttpResponse(
             "This HTTP triggered function executed successfully. Pass a name in the query string or in the request body for a personalized response.",
             status_code=200
        )

    
    
# this is the timer trigger that we are using over here
#it will run on a CRON expression  that has been defined below
# "0 */5 * * * *" means every 5 minutes as we have seconds-minutes-hours-day-month-dayofweek
#run on start up will make it run when started 
@app.timer_trigger(schedule="0 */5 * * * *", arg_name="myTimer",
                   run_on_startup=True)
def timer_function(myTimer: func.TimerRequest) -> None:
    logging.info('Timer trigger function ran!')

#this log ensures that each time the timmer trigger will run it will log that info
    

#this is another trigger known as a queue trigger
# runs whenever a new message arrives in the storage queue named "effaqueue"
# connection="AzureWebJobsStorage" tells it which storage account to look for which will get the new message

@app.queue_trigger(arg_name="msg", queue_name="effaqueue",
                   connection="AzureWebJobsStorage")

def queue_function(msg: func.QueueMessage) -> None:
    logging.info('Queue trigger processed a message: %s',
                 msg.get_body().decode('utf-8'))
    
#this ensures that the message which was received as raw bytes gets converted into readable text here
    

# This is the data pipeline that has been created where the trigger is of a queue and it leads to blob output binding
# reads a message from the queue "effaqueue", then writes it out to a blob (file)
    
# the @app.blob_output declares the output binding: where the returned data gets saved
@app.queue_trigger(arg_name="msg", queue_name="effaqueue",
                   connection="AzureWebJobsStorage")

@app.blob_output(arg_name="outputblob",
                 path="effa-output/{rand-guid}.txt",
                 #the path is where the blob file gets stored to
                 connection="AzureWebJobsStorage")

def pipeline_function(msg: func.QueueMessage, outputblob: func.Out[str]) -> None:
    message_text = msg.get_body().decode('utf-8')
    logging.info('Pipeline received message: %s', message_text)
    outputblob.set(message_text)
    logging.info('Pipeline wrote the message to a blob.')