import os
import requests
import base64
from PIL import Image
from io import BytesIO
from datetime import datetime
from dotenv import load_dotenv
import argparse
import time

load_dotenv()

# Read environment variables
FOUNDRY_ENDPOINT = os.getenv("FOUNDRY_ENDPOINT")
FOUNDRY_API_KEY = os.getenv("FOUNDRY_API_KEY")
FOUNDRY_API_VERSION = os.getenv("FOUNDRY_API_VERSION")
FLUX_DEPLOYMENT_NAME = os.getenv("FLUX_DEPLOYMENT_NAME")
GPT_DEPLOYMENT_NAME = os.getenv("GPT_DEPLOYMENT_NAME")
# Note: We'll prompt the user for the input image path and the prompt at runtime
INPUT_IMAGE = None
PROMPT = None


if __name__ == "__main__":

    # Parse model selection argument
    parser = argparse.ArgumentParser(description="Image to Image Processing with AIFoundry")
    parser.add_argument("-model", "--model", dest="model", type=str, help="Model to use (must be either flux or gpt)")
    args = parser.parse_args()

    if args.model:
        model = args.model.lower()
    else:
        # Ask the user which model to use (gpt or flux). Default to gpt.
        while True:
            model_input = input("Select model to use ('gpt' or 'flux') [gpt]: ").strip().lower()
            if model_input == "":
                model = "gpt"
                break
            if model_input in ("gpt", "flux"):
                model = model_input
                break
            print("Invalid selection. Please enter 'gpt' or 'flux'.")

    if model == "gpt":
        deployment = GPT_DEPLOYMENT_NAME
    else:
        deployment = FLUX_DEPLOYMENT_NAME

    print(f"Using {deployment} model.")

    base_path = f'openai/deployments/{deployment}/images'
    params = f'?api-version={FOUNDRY_API_VERSION}'


    """
    Make edit request
    """

    edit_url = f"{FOUNDRY_ENDPOINT}{base_path}/edits{params}"
    # Prompt user for input image and prompt (do not read these from .env)
    default_prompt = "update this image to be set in a pirate era"

    # Look for a default image in the current directory
    image_extensions = ('.png', '.jpg', '.jpeg', '.bmp', '.gif', '.tiff', '.webp')
    default_image = None
    try:
        for entry in os.listdir(os.getcwd()):
            if entry.lower().endswith(image_extensions) and os.path.isfile(entry):
                default_image = entry
                break
    except Exception:
        default_image = None

    # Request input image path (loop until a valid file path is provided or the user quits)
    while True:
        if default_image:
            prompt_msg = f"Enter path to input image [{default_image}] (or type 'quit' to exit): "
        else:
            prompt_msg = "Enter path to input image (or type 'quit' to exit): "

        user_image = input(prompt_msg).strip()
        if user_image.lower() == "quit":
            print("Aborted by user.")
            exit(0)

        # If user pressed Enter and we have a default, use it
        if user_image == "" and default_image:
            user_image = default_image

        if user_image == "":
            print("Please provide a path to an image file.")
            continue

        # Expand user and relative paths
        user_image = os.path.expanduser(user_image)
        if not os.path.isabs(user_image):
            user_image = os.path.join(os.getcwd(), user_image)

        if os.path.isfile(user_image):
            INPUT_IMAGE = user_image
            break
        else:
            print(f"File not found: {user_image}")

    # Prompt for text prompt with a sensible default
    user_prompt = input(f"Enter prompt [{default_prompt}]: ").strip()
    PROMPT = user_prompt if user_prompt != "" else default_prompt

    request_body = {
        "prompt": PROMPT,
        "n": 1,
        "size": "1024x1024",
    }

    # Modify request body with model-specific parameters
    if model == "gpt":
        request_body["input_fidelity"] = "high"
        request_body["quality"] = "high"
    else:
        request_body["quality"] = "hd"

    try:
        files = {
            "image": (os.path.basename(INPUT_IMAGE), open(INPUT_IMAGE, "rb")),
        }
    except Exception as e:
        print(f"Failed to open image file '{INPUT_IMAGE}': {e}")
        exit(1)

    print(f"Sending request for image {INPUT_IMAGE} with prompt: {PROMPT} ...")

    # Time the HTTP request
    start = time.perf_counter()
    response = requests.post(
        edit_url,
        headers={'Api-Key': FOUNDRY_API_KEY, 'x-ms-model-mesh-model-name': deployment},
        data=request_body,
        files=files
    )
    elapsed_sec = time.perf_counter() - start
    print(f"Request completed in {elapsed_sec:.3f}s")

    response_json = response.json()


    """
    Save images
    """

    # Create output directory if it doesn't exist
    os.makedirs("generated", exist_ok=True)

    # Sanitize prompt for filename
    safe_prompt = PROMPT.replace(" ", "_")[:50]
    filename_prefix = os.path.join(
        "generated",
        f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{model}_{safe_prompt}"
    )

    try:
        for idx, item in enumerate(response_json['data']):
            b64_img = item['b64_json']
            filename = f"{filename_prefix}_{idx+1}.png"
            image = Image.open(BytesIO(base64.b64decode(b64_img)))
            image.show()
            image.save(filename)
            print(f"Image saved to: '{filename}'")
    except Exception as e:
        print(f"Error {e}:\n{response_json}")