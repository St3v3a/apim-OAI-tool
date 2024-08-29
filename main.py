from fastapi import FastAPI, Request, Form, HTTPException
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, StreamingResponse, JSONResponse, RedirectResponse
from openai import AzureOpenAI
import httpx
import json
import csv
import asyncio
from httpx import HTTPStatusError
import random
import os

app = FastAPI()
templates = Jinja2Templates(directory="templates")

# Load configuration from a file
def load_config():
    if os.path.exists('config.json'):
        with open('config.json', 'r') as f:
            return json.load(f)
    default_config = {
        "azure_endpoint": "https://apimukdev.azure-api.net/satest1/",
        "api_key": "20534bb7c598414189e64dab9fd1c21d",
        "api_version": "2024-06-01"
    }
    save_config(default_config)
    return default_config

# Save configuration to a file
def save_config(config):
    with open('config.json', 'w') as f:
        json.dump(config, f)

# Load the initial configuration
config = load_config()

class HeaderCapturingTransport(httpx.HTTPTransport):
    def __init__(self):
        super().__init__()
        self.last_headers = None

    def handle_request(self, request):
        print(f"Sending request: {request.method} {request.url}")
        print(f"Request headers: {request.headers}")
        resp = super().handle_request(request)
        self.last_headers = resp.headers
        print(f"Response status: {resp.status_code}")
        print(f"Response headers: {resp.headers}")
        return resp

custom_transport = HeaderCapturingTransport()

client = AzureOpenAI(
    azure_endpoint=config["azure_endpoint"],
    api_key=config["api_key"],
    api_version=config["api_version"],
    http_client=httpx.Client(transport=custom_transport)
)

def read_models():
    try:
        with open("models.txt", "r") as f:
            return [line.strip() for line in f if line.strip()]
    except FileNotFoundError:
        return []

def read_messages_from_csv():
    messages = []
    with open("messages.csv", "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            messages.append({
                "system": {"role": "system", "content": row["system_content"]},
                "user": {"role": "user", "content": row["user_content"]}
            })
    return messages

@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    models = read_models()
    return templates.TemplateResponse("index.html", {"request": request, "models": models})

@app.post("/chat")
async def chat(
    request: Request,
    model: str = Form(...),
    message: str = Form(None),
    mode: str = Form(...),
    iterations: int = Form(1)
):
    async def generate_response():
        try:
            print(f"Using model: {model}")  # Log the model being used
            
            if mode == "basic":
                messages = [
                    {"role": "system", "content": "You are a helpful assistant."},
                    {"role": "user", "content": message}
                ]
                iterations_to_run = 1
            else:  # advanced mode
                csv_messages = read_messages_from_csv()
                iterations_to_run = min(iterations, len(csv_messages))

            for i in range(iterations_to_run):
                if mode == "advanced":
                    row_messages = csv_messages[i]
                    messages = [row_messages["system"], row_messages["user"]]
                else:
                    messages = [
                        {"role": "system", "content": "You are a helpful assistant."},
                        {"role": "user", "content": message}
                    ]

                try:
                    response = client.chat.completions.create(
                        model=model,
                        messages=messages
                    )
                except HTTPStatusError as http_err:
                    error_message = f"HTTP error occurred: {http_err.response.status_code} {http_err.response.reason_phrase}"
                    print(error_message)
                    yield f"data: {json.dumps({'error': error_message, 'status_code': http_err.response.status_code})}\n\n"
                    continue
                except Exception as api_error:
                    error_message = f"API Error: {str(api_error)}"
                    print(error_message)
                    yield f"data: {json.dumps({'error': error_message})}\n\n"
                    continue

                ai_response = response.choices[0].message.content
                if mode == "advanced":
                    ai_response = ai_response.split('.')[0] + '.'  # Get only the first sentence

                total_tokens = response.usage.total_tokens
                backend_region = custom_transport.last_headers.get('x-ms-region', 'Not available')
                remaining_requests = custom_transport.last_headers.get('x-ratelimit-remaining-requests', 'Not available')
                remaining_tokens = custom_transport.last_headers.get('x-ratelimit-remaining-tokens', 'Not available')

                print(f"Response headers: {custom_transport.last_headers}")  # Log all headers

                yield f"data: {json.dumps({'iteration': i + 1, 'response': ai_response, 'total_tokens': total_tokens, 'backend_region': backend_region, 'remaining_requests': remaining_requests, 'remaining_tokens': remaining_tokens, 'model': model})}\n\n"

                await asyncio.sleep(0.1)  # Small delay to prevent flooding

        except Exception as e:
            error_message = f"General Error: {str(e)}"
            print(error_message)
            yield f"data: {json.dumps({'error': error_message})}\n\n"

    return StreamingResponse(generate_response(), media_type="text/event-stream")

@app.post("/randomize-csv")
async def randomize_csv():
    try:
        with open("messages.csv", "r") as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        
        random.shuffle(rows)
        
        with open("messages.csv", "w", newline='') as f:
            writer = csv.DictWriter(f, fieldnames=rows[0].keys())
            writer.writeheader()
            writer.writerows(rows)
        
        return JSONResponse(content={"message": "CSV content randomized successfully"})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/settings", response_class=HTMLResponse)
async def settings_page(request: Request):
    models = read_models()
    api_key = config["api_key"]
    masked_api_key = '*' * (len(api_key) - 6) + api_key[-6:]  # Mask all but last 6 digits
    return templates.TemplateResponse("settings.html", {
        "request": request, 
        "models": models,
        "azure_endpoint": config["azure_endpoint"],
        "api_key": masked_api_key,
        "api_version": config["api_version"]
    })

@app.post("/update_config")
async def update_config(
    azure_endpoint: str = Form(None),
    api_key: str = Form(None),
    api_version: str = Form(None)
):
    global client, config
    
    # Load the current configuration
    current_config = load_config()
    
    # Update only the fields that were provided
    if azure_endpoint:
        current_config["azure_endpoint"] = azure_endpoint
    if api_key and not api_key.startswith('*'):
        current_config["api_key"] = api_key
    if api_version:
        current_config["api_version"] = api_version
    
    # Save the updated configuration
    save_config(current_config)
    
    # Update the global config variable
    config = current_config
    
    # Reinitialize the client with new configuration
    client = AzureOpenAI(
        azure_endpoint=config["azure_endpoint"],
        api_key=config["api_key"],
        api_version=config["api_version"],
        http_client=httpx.Client(transport=custom_transport)
    )
    
    # Print the updated configuration for debugging
    print("Updated configuration:", config)
    
    return RedirectResponse(url="/settings", status_code=303)

@app.post("/add_model")
async def add_model(model: str = Form(...)):
    models = read_models()
    if model not in models:
        with open("models.txt", "a") as f:
            f.write(f"{model}\n")
    return RedirectResponse(url="/settings", status_code=303)

@app.post("/remove_model")
async def remove_model(model: str = Form(...)):
    models = read_models()
    if model in models:
        models.remove(model)
        with open("models.txt", "w") as f:
            for m in models:
                f.write(f"{m}\n")
    return RedirectResponse(url="/settings", status_code=303)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
