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
INPUT_IMAGE = os.getenv("INPUT_IMAGE")
PROMPT = os.getenv("PROMPT")


if __name__ == "__main__":

    # Parse model selection argument
    parser = argparse.ArgumentParser(description="Image to Image Processing with AIFoundry")
    parser.add_argument("-model", "--model", dest="model", type=str, help="Model to use (must be either flux or gpt)")
    args = parser.parse_args()

    if args.model:
        model = args.model.lower()
        if model == "gpt":
            deployment = GPT_DEPLOYMENT_NAME
        else:
            deployment = FLUX_DEPLOYMENT_NAME
        print(f"Using {deployment} model.")
    else:
        model = "flux"
        deployment = FLUX_DEPLOYMENT_NAME
        print(f"No -model argument provided. Using {deployment} model.")

    base_path = f'openai/deployments/{deployment}/images'
    params = f'?api-version={FOUNDRY_API_VERSION}'


    """
    Make edit request
    """

    edit_url = f"{FOUNDRY_ENDPOINT}{base_path}/edits{params}"
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

    files = {
        "image": (INPUT_IMAGE, open(INPUT_IMAGE, "rb")),
    }

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

    filename_prefix = os.path.join(
        "generated",
        f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{model}_{PROMPT.replace(' ', '_')[:50]}"
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