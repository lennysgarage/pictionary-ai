# game_server_client.py
# This script is a FastAPI server that acts as a proxy.
# It now uses a WebSocket to stream generation progress (step count and image) to the browser.
# --- Dependencies ---
# pip install "fastapi[all]" uvicorn websockets Pillow

import asyncio
import websockets
import base64
import io
import json
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse

# --- Configuration ---
AI_SERVER_URI = "ws://localhost:8000/ws/generate"
TOTAL_STEPS = 12 # The number of steps the AI server is configured to run

# --- FastAPI App Setup ---
app = FastAPI()


# --- 1. The NEW WebSocket Endpoint for the Browser ---
@app.websocket("/ws/stream-with-progress")
async def stream_with_progress(websocket: WebSocket):
    """
    Accepts a WebSocket connection from the browser.
    Receives a prompt, then acts as a client to the AI server.
    Streams back structured JSON data with step count and image data.
    """
    await websocket.accept()
    print("Browser client connected.")
    
    try:
        # Wait for the prompt from the browser client
        prompt = await websocket.receive_text()
        print(f"Received prompt from browser: '{prompt}'")
        
        # Now, connect to the actual AI server
        print(f"Connecting to AI Server at {AI_SERVER_URI}...")
        async with websockets.connect(AI_SERVER_URI) as ai_websocket:
            await ai_websocket.send(prompt)
            print("Prompt sent to AI server. Waiting for frames...")
            
            step_count = 0
            while True:
                message = await ai_websocket.recv()
                
                if message == "generation_complete":
                    print("Generation complete signal received from AI server.")
                    # Send a final status update to the browser
                    await websocket.send_json({"status": "complete", "total_steps": TOTAL_STEPS})
                    break
                
                # We received a new frame from the AI server
                step_count += 1
                
                # The message is a base64 string from the AI server
                image_base64 = message
                
                # Create a JSON object to send to the browser
                response_data = {
                    "step": step_count,
                    "total_steps": TOTAL_STEPS,
                    "image_b64": image_base64,
                }
                
                # Send the JSON data to the browser
                await websocket.send_json(response_data)
        
    except WebSocketDisconnect:
        print("Browser client disconnected.")
    except websockets.exceptions.ConnectionClosedError as e:
        print(f"Connection to AI server failed: {e}")
        # Inform the browser if the backend connection fails
        await websocket.send_json({"status": "error", "message": "Could not connect to the AI generation service."})
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        print("Closing connection with browser client.")
        

# --- 2. The HTML Frontend [UPDATED] ---
@app.get("/", response_class=HTMLResponse)
async def read_root():
    """
    Serves a basic HTML page with JavaScript to handle WebSocket communication.
    """
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>AI Image Stream</title>
        <style>
            body { font-family: sans-serif; background-color: #121212; color: #e0e0e0; display: flex; flex-direction: column; align-items: center; padding: 2em; }
            h1 { color: #ffffff; }
            #container { background-color: #1e1e1e; padding: 2em; border-radius: 12px; box-shadow: 0 4px 15px rgba(0,0,0,0.5); text-align: center; }
            input[type="text"] { width: 400px; padding: 10px; border-radius: 6px; border: 1px solid #444; background-color: #2e2e2e; color: #e0e0e0; font-size: 1em; }
            button { padding: 10px 20px; border: none; border-radius: 6px; background-color: #007bff; color: white; font-size: 1em; cursor: pointer; margin-left: 10px; }
            button:hover { background-color: #0056b3; }
            #image-container { margin-top: 2em; width: 512px; height: 512px; background-color: #2a2a2a; border: 1px solid #444; border-radius: 8px; display: flex; align-items: center; justify-content: center; overflow: hidden;}
            img { max-width: 100%; max-height: 100%; border-radius: 8px; }
            #status { margin-top: 1em; color: #aaa; font-size: 1.1em; font-weight: bold; min-height: 1.2em; }
        </style>
    </head>
    <body>
        <div id="container">
            <h1>Real-Time AI Image Generation Stream</h1>
            <form id="prompt-form">
                <input type="text" id="prompt-input" placeholder="Enter your prompt here..." required>
                <button type="submit">Generate</button>
            </form>
            <div id="image-container">
                <img id="stream-img" src="" alt="AI generated image stream will appear here.">
            </div>
            <p id="status">Enter a prompt and click "Generate" to start.</p>
        </div>

        <script>
            const form = document.getElementById('prompt-form');
            const input = document.getElementById('prompt-input');
            const img = document.getElementById('stream-img');
            const status = document.getElementById('status');
            
            let socket;

            form.addEventListener('submit', (event) => {
                event.preventDefault();
                const prompt = input.value;
                if (!prompt) return;

                // Close any existing socket
                if (socket) {
                    socket.close();
                }

                // Determine WebSocket protocol (ws or wss)
                const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
                const wsUrl = `${wsProtocol}//${window.location.host}/ws/stream-with-progress`;

                socket = new WebSocket(wsUrl);

                socket.onopen = () => {
                    console.log("WebSocket connected.");
                    status.textContent = "Connecting to AI server...";
                    socket.send(prompt);
                };

                socket.onmessage = (event) => {
                    const data = JSON.parse(event.data);
                    
                    if (data.image_b64) {
                        img.src = `data:image/png;base64,${data.image_b64}`;
                        status.textContent = `Generating... Step ${data.step} / ${data.total_steps}`;
                    } else if (data.status === 'complete') {
                        status.textContent = `Done! (Total Steps: ${data.total_steps})`;
                        socket.close();
                    } else if (data.status === 'error') {
                        status.textContent = `Error: ${data.message}`;
                        socket.close();
                    }
                };

                socket.onclose = () => {
                    console.log("WebSocket disconnected.");
                };

                socket.onerror = (error) => {
                    console.error("WebSocket error:", error);
                    status.textContent = "Error: Could not establish connection.";
                };
            });
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)
