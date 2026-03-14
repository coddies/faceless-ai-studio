import base64
import json
import os
import random
import time
from typing import Optional

import boto3
from dotenv import load_dotenv

import requests
import urllib.parse

load_dotenv()

def call_stability_image(prompt: str, width: int = 1280, height: int = 720) -> str:
    """Image generation using Stability AI - Real AI images!"""
    try:
        api_key = os.getenv("STABILITY_API_KEY", "")
        if not api_key:
            print("[nova_client] STABILITY_API_KEY missing. Falling back to placeholder.")
            return call_placeholder_image(prompt)

        # Ensure aspect ratio logic matches Stability AI requirements
        # Core supports specific aspect ratios: 16:9, 1:1, 21:9, 2:3, 3:2, 4:5, 5:4, 9:16, 9:21
        # Determine aspect ratio string
        aspect_ratio = "16:9"
        if width == height:
            aspect_ratio = "1:1"
        elif height > width:
            aspect_ratio = "9:16"

        response = requests.post(
            "https://api.stability.ai/v2beta/stable-image/generate/core",
            headers={
                "authorization": f"Bearer {api_key}",
                "accept": "image/*"
            },
            files={"none": ''},
            data={
                "prompt": prompt,
                "output_format": "jpeg",
                "aspect_ratio": aspect_ratio
            },
            timeout=60
        )

        if response.status_code == 200:
            image_base64 = base64.b64encode(response.content).decode('utf-8')
            print("[nova_client] Using Stability AI ✅")
            return f"data:image/jpeg;base64,{image_base64}"
        else:
            print(f"[nova_client] Stability AI failed: {response.status_code} {response.text[:200]}. Falling back to placeholder.")
            return call_placeholder_image(prompt)

    except Exception as e:
        print(f"[nova_client] Stability AI error: {str(e)}. Falling back to placeholder.")
        return call_placeholder_image(prompt)

def call_placeholder_image(prompt: str) -> str:
    import urllib.parse, requests, base64
    # Try multiple free image APIs
    
    # Option 1: Picsum (random beautiful image)
    try:
        r = requests.get('https://picsum.photos/1280/720', timeout=30)
        if r.status_code == 200:
            b64 = base64.b64encode(r.content).decode('utf-8')
            print("[nova_client] Using Picsum placeholder ✅")
            return f"data:image/jpeg;base64,{b64}"
    except:
        pass
    
    # Option 2: Return a simple gradient placeholder
    return "https://picsum.photos/1280/720"

def _aws_region() -> str:
    return (
        os.getenv("AWS_REGION")
        or os.getenv("AWS_DEFAULT_REGION")
        or os.getenv("AWS_REGION_NAME")
        or "us-east-1"
    )


def _get_bedrock_runtime_client():
    """
    Build a Bedrock Runtime client using the default credential chain.
    If explicit AWS_* env vars exist, they will be used; otherwise boto3 will
    resolve credentials from shared config, IAM role, etc.
    """
    region = _aws_region()
    akid = os.getenv("AWS_ACCESS_KEY_ID")
    secret = os.getenv("AWS_SECRET_ACCESS_KEY")
    token = os.getenv("AWS_SESSION_TOKEN")

    if akid and secret:
        return boto3.client(
            "bedrock-runtime",
            region_name=region,
            aws_access_key_id=akid,
            aws_secret_access_key=secret,
            aws_session_token=token,
        )

    # Use default provider chain (supports ~/.aws/credentials, instance profile, etc.)
    return boto3.client("bedrock-runtime", region_name=region)


def _aws_hint() -> str:
    region = _aws_region()
    return (
        f"AWS credentials/region not configured for Bedrock. "
        f"Set `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY` (and optional `AWS_SESSION_TOKEN`) "
        f"and `AWS_REGION` (currently `{region}`), or configure the default AWS credential chain."
    )

def call_groq(prompt: str) -> str:
    from groq import Groq
    try:
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise Exception("GROQ_API_KEY is missing from environment")
        client_groq = Groq(api_key=api_key)
        completion = client_groq.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "system", "content": "You are Nova AI, a helpful YouTube content creation assistant."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=800,
            temperature=0.7
        )
        print("[nova_client] Using Groq Llama 3.1 ✅")
        return completion.choices[0].message.content.strip()
    except Exception as e:
        raise Exception(f"Groq API Error: {str(e)}")

def call_nova_pro(prompt: str) -> str:
    """Try AWS Nova Pro first, fallback to Llama 3.1 via Groq"""
    try:
        client = _get_bedrock_runtime_client()
        response = client.invoke_model(
            modelId="amazon.nova-pro-v1:0",
            body=json.dumps({"messages": [{"role": "user", "content": [{"text": prompt}]}]})
        )
        result = json.loads(response["body"].read())
        print("[nova_client] Using AWS Nova Pro ✅")
        return result["output"]["message"]["content"][0]["text"]
    except Exception as e:
        err_str = str(e)
        if "ThrottlingException" in err_str or "Too many tokens" in err_str or "AccessDenied" in err_str:
            print(f"[nova_client] AWS text generation failed: {err_str[:150]} - switching to Groq fallback...")
            return call_groq(prompt)
        print(f"[nova_client] AWS unexpected error: {err_str[:150]} - trying Groq fallback...")
        return call_groq(prompt)

def call_nova_canvas(
    prompt: str,
    negative_prompt: str = "person, face, blurry, text, watermark",
    *,
    width: int = 1280,
    height: int = 720,
    quality: str = "standard",
    number_of_images: int = 1,
    seed: Optional[int] = None,
    max_retries: int = 3,
) -> str:
    """
    Use AWS Nova Canvas for image generation.

    Returns a **base64 data URL string**: `data:image/png;base64,<...>`.
    Retries on throttling with exponential backoff.
    """
    if not prompt or not str(prompt).strip():
        raise Exception("Canvas prompt is empty.")

    client = _get_bedrock_runtime_client()
    chosen_seed = int(seed) if seed is not None else random.randint(1, 2_000_000_000)

    body = {
        "taskType": "TEXT_IMAGE",
        "textToImageParams": {"text": prompt, "negativeText": negative_prompt},
        "imageGenerationConfig": {
            "width": int(width),
            "height": int(height),
            "quality": quality,
            "numberOfImages": int(number_of_images),
            "seed": chosen_seed,
        },
    }

    last_err: Optional[Exception] = None
    for attempt in range(max_retries + 1):
        try:
            response = client.invoke_model(
                modelId="amazon.nova-canvas-v1:0",
                body=json.dumps(body),
            )
            result = json.loads(response["body"].read())
            images = result.get("images") or []
            if not images or not images[0]:
                raise Exception("AWS Canvas returned no images.")

            image_base64 = images[0]
            # Validate base64; will raise binascii.Error if invalid.
            base64.b64decode(image_base64, validate=True)
            print("[nova_client] Using AWS Nova Canvas ✅")
            return f"data:image/png;base64,{image_base64}"
        except Exception as e:
            last_err = e
            err_str = str(e)

            # Make credential/config errors clearer.
            if (
                "Unable to locate credentials" in err_str
                or "NoCredentialsError" in err_str
                or "UnrecognizedClientException" in err_str
                or "InvalidSignatureException" in err_str
                or "security token included in the request is invalid" in err_str.lower()
            ):
                raise Exception(f"AWS Canvas credential error. {_aws_hint()} Original error: {err_str}")

            # Retry only throttling / rate limit style failures.
            if "ThrottlingException" in err_str or "TooManyRequestsException" in err_str or "Rate exceeded" in err_str:
                if attempt < max_retries:
                    sleep_s = min(8.0, (2 ** attempt) + random.random())
                    print(f"[nova_client] Canvas throttled, retrying in {sleep_s:.1f}s (attempt {attempt+1}/{max_retries})...")
                    time.sleep(sleep_s)
                    continue
                else:
                    print(f"[nova_client] AWS Canvas Throttled. Trying Stability AI fallback...")
                    return call_stability_image(prompt, width, height)

            print(f"[nova_client] AWS Canvas generation failed: {err_str}. Trying Stability AI fallback...")
            return call_stability_image(prompt, width, height)

    print("[nova_client] Max retries reached. Trying Stability AI fallback...")
    return call_stability_image(prompt, width, height)