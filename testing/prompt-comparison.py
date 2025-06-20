from sentence_transformers import SentenceTransformer, util
import torch

# 1. Load a pre-trained Sentence-BERT model.
#    'all-MiniLM-L6-v2' is a good, fast model that works well for general purposes.
#    Other models might be larger and more powerful but slower.
try:
    model = SentenceTransformer('all-MiniLM-L6-v2')
except Exception as e:
    print(f"Error loading model: {e}")
    print("Please ensure you have a working internet connection to download the model.")
    exit()

def calculate_similarity(prompt1: str, prompt2: str) -> float:
    """
    Calculates the semantic similarity between two prompts and returns it as a percentage.
    """
    if not prompt1 or not prompt2:
        return 0.0

    # 2. Generate embeddings for both prompts.
    #    The model converts each prompt into a 384-dimensional vector.
    embedding1 = model.encode(prompt1, convert_to_tensor=True)
    embedding2 = model.encode(prompt2, convert_to_tensor=True)

    # 3. Calculate the cosine similarity between the two embeddings.
    #    Cosine similarity measures the cosine of the angle between two vectors,
    #    which is a great way to measure how similar they are in direction (i.e., meaning).
    #    The result is a value between -1 and 1.
    cosine_score = util.cos_sim(embedding1, embedding2)

    # 4. Convert the similarity score to a percentage.
    #    The score from cos_sim is a tensor, so we get the value with .item()
    #    We'll normalize it from [-1, 1] to [0, 100]. A common way is to map [0,1] to [0,100].
    #    For most sentence transformers, negative scores are rare for typical sentences.
    #    So we can simply clamp the score at 0 and scale to 100.
    similarity_percentage = max(0, cosine_score.item()) * 100

    return similarity_percentage

# --- Example Usage ---

# Your example prompts
prompt_A = "Darth vader playing the drums"
prompt_B = "darhter vader drums"

similarity = calculate_similarity(prompt_A, prompt_B)
print(f"Prompt A: '{prompt_A}'")
print(f"Prompt B: '{prompt_B}'")
print(f"Similarity Score: {similarity:.2f}%")

print("-" * 20)

# Another example showing semantic understanding
prompt_C = "A photograph of a knight in shining armor"
prompt_D = "A picture of a medieval warrior with metal plates"

similarity_2 = calculate_similarity(prompt_C, prompt_D)
print(f"Prompt C: '{prompt_C}'")
print(f"Prompt D: '{prompt_D}'")
print(f"Similarity Score: {similarity_2:.2f}%")

print("-" * 20)

# Example with very different prompts
prompt_E = "A blue car is parked on the street"
prompt_F = "I am writing a python script"

similarity_3 = calculate_similarity(prompt_E, prompt_F)
print(f"Prompt E: '{prompt_E}'")
print(f"Prompt F: '{prompt_F}'")
print(f"Similarity Score: {similarity_3:.2f}%")