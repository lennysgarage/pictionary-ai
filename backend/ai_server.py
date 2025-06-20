import torch
import asyncio
import base64
import io
import os

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from pydantic import BaseModel # NEW: For creating the request body model
from diffusers import LCMScheduler, AutoPipelineForText2Image

from sentence_transformers import SentenceTransformer, util


# --- 1. Server and Model Setup ---

app = FastAPI()

class ScoringRequest(BaseModel):
    prompt: str
    guess: str


print("Loading model... This may take a moment.")
if torch.backends.mps.is_available():
    device = torch.device("mps")
    torch_dtype = torch.float16 
    print("Using MPS (Apple Silicon GPU) with float16 precision for stability.")
    variant = "fp16"
else:
    device = torch.device("cpu")
    torch_dtype = torch.float32
    print("MPS not available, using CPU with float32 precision.")
    variant = "fp32"

pipeline = AutoPipelineForText2Image.from_pretrained(
    "stable-diffusion-v1-5/stable-diffusion-v1-5", 
    torch_dtype=torch_dtype,
    variant=variant,
    use_safetensors=True,
).to(device)


pipeline.scheduler = LCMScheduler.from_config(pipeline.scheduler.config)
print("Model loaded and configured with LCMScheduler.")

print("Loading and fusing LoRA for SDv1.5...")
pipeline.load_lora_weights("latent-consistency/lcm-lora-sdv1-5")

pipeline.fuse_lora()
print("LoRA for SDv1.5 fused successfully.")

print("Loading similarity scoring model...")
similarity_model = SentenceTransformer('all-MiniLM-L6-v2', device=device)
print("Similarity model loaded.")

# --- 2. NEW Scoring Endpoint ---

@app.post("/score/similarity")
async def score_similarity(request: ScoringRequest):
    """
    Receives a correct prompt and a user's guess, and returns a similarity score.
    """
    if not request.prompt or not request.guess:
        return {"score": 0.0}

    # Generate embeddings for both prompts
    embedding1 = similarity_model.encode(request.prompt, convert_to_tensor=True)
    embedding2 = similarity_model.encode(request.guess, convert_to_tensor=True)

    # Calculate cosine similarity
    cosine_score = util.cos_sim(embedding1, embedding2)

    # Normalize to a 0-100 scale
    similarity_percentage = max(0, cosine_score.item()) * 100

    print(f"Scoring: '{request.prompt}' vs '{request.guess}' -> {similarity_percentage:.2f}%")

    return {"score": similarity_percentage}


# --- 3. WebSocket Endpoint for Image Generation ---

@app.websocket("/ws/generate")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    print("Client connected.")
    
    # Get the current asyncio event loop to schedule tasks from another thread.
    main_loop = asyncio.get_running_loop()

    try:
        while True:
            prompt = await websocket.receive_text()
            print(f"Received prompt: '{prompt}'")

            # --- 3. The Corrected Callback Function ---
            # This is now a regular (synchronous) function, not async.
            def stream_intermediate_image(pipe, step, timestep, callback_kwargs):
                # Decode the latent to a PIL Image
                latents = callback_kwargs["latents"]
                image = pipe.image_processor.postprocess(
                    pipe.vae.decode(latents / pipe.vae.config.scaling_factor, return_dict=False)[0]
                )[0]

                # Convert the PIL Image to bytes in memory
                buffer = io.BytesIO()
                image.save(buffer, format="PNG")
                img_bytes = buffer.getvalue()

                # Encode the bytes to a Base64 string
                img_base64 = base64.b64encode(img_bytes).decode('utf-8')

                # --- THE FIX ---
                # Use asyncio.run_coroutine_threadsafe to schedule the async send
                # operation on the main event loop from this synchronous thread.
                asyncio.run_coroutine_threadsafe(
                    websocket.send_text(img_base64),
                    main_loop
                )
                
                return callback_kwargs

            # Run the synchronous pipeline in a separate thread.
            # This no longer blocks the server.
            await asyncio.to_thread(
                pipeline,
                prompt=prompt,
                num_inference_steps=4,
                guidance_scale=0,
                callback_on_step_end_steps=1,
                callback_on_step_end=stream_intermediate_image,
            )

            # Signal that the generation is complete using the same thread-safe method.
            # We wait for this one to finish to ensure the message is sent before we loop.
            await websocket.send_text("generation_complete")
            print("Generation complete. Sent end signal.")

    except WebSocketDisconnect:
        print("Client disconnected.")
    except Exception as e:
        print(f"An error occurred: {e}")
        await websocket.close(code=1011, reason=str(e))