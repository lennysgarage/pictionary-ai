from diffusers import StableDiffusionXLPipeline, DiffusionPipeline
import torch
import os

output_dir = "generation_stream"
os.makedirs(output_dir, exist_ok=True)


def save_intermediate_image(pipe, step, timestep, callback_kwargs):
    """
    This is the new callback function that uses the modern API.
    """
    # Get the latents from the callback_kwargs dictionary
    latents = callback_kwargs["latents"]
    
    # Use the passed 'pipe' instance instead of a global variable
    image = pipe.image_processor.postprocess(pipe.vae.decode(latents / pipe.vae.config.scaling_factor, return_dict=False)[0])[0]
    
    image.save(f"{output_dir}/step_{step:03d}.png")
    
    # The callback must return the kwargs dictionary.
    return callback_kwargs



if torch.backends.mps.is_available():
    device = torch.device("mps")
    torch_dtype = torch.float16
    print("Using MPS (Apple Silicon GPU)")
else:
    device = torch.device("cpu")
    torch_dtype = torch.float32
    print("MPS not available, using CPU")


model_path = "./sd_xl_base_1.0.safetensors"

# might get some speedup from changing schedulers
pipeline = DiffusionPipeline.from_pretrained(
    "stable-diffusion-v1-5/stable-diffusion-v1-5", # so far this is the fastest model i could find.
    # "segmind/SSD-1B",
    torch_dtype=torch_dtype,
    use_safetensors=True,
)

# pipeline = StableDiffusionXLPipeline.from_single_file(
#     model_path,
#     torch_dtype=torch_dtype,
#     use_safetensors=True
# )

pipeline.to(device)
prompt = "An image of a crow in a tree"

final_image = pipeline(
    prompt,
    num_inference_steps=30,
    callback_on_step_end_steps=1,
    callback_on_step_end=save_intermediate_image
).images[0]

final_image.save("image5.png")