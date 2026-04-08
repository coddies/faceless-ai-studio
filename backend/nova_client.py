import base64
import json
import os
import random
import time
from typing import Optional

import boto3
from botocore.config import Config
import requests
import urllib.parse
from dotenv import load_dotenv

load_dotenv()

# ============================================================
# AWS BEDROCK UTILS
# ============================================================

def _get_bedrock_runtime_client(region: Optional[str] = None):
    """
    Build a Bedrock Runtime client. Defaults to the region in .env.
    """
    target_region = region or os.getenv("AWS_DEFAULT_REGION", "us-east-1")
    my_config = Config(
        region_name=target_region,
        retries={
            'max_attempts': 10,
            'mode': 'standard'
        }
    )
    
    ACCESS_KEY = os.getenv('AWS_ACCESS_KEY_ID')
    SECRET_KEY = os.getenv('AWS_SECRET_ACCESS_KEY')
    SESSION_TOKEN = os.getenv("AWS_SESSION_TOKEN")

    if ACCESS_KEY and SECRET_KEY:
        return boto3.client(
            "bedrock-runtime",
            config=my_config,
            aws_access_key_id=ACCESS_KEY,
            aws_secret_access_key=SECRET_KEY,
            aws_session_token=SESSION_TOKEN,
        )

    return boto3.client("bedrock-runtime", config=my_config)

def _save_image_locally(image_base64: str):
    """Saves generated image to outputs/generated_image.png"""
    try:
        output_dir = "outputs"
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        file_path = os.path.join(output_dir, "generated_image.png")
        with open(file_path, "wb") as f:
            f.write(base64.b64decode(image_base64))
        print(f"[nova_client] Image saved to {file_path}")
    except Exception as e:
        print(f"[nova_client] Failed to save image: {e}")

# ============================================================
# IMAGE GENERATION: Nova Canvas (Primary) / HF FLUX (Fallback)
# ============================================================

def call_hf_flux(prompt: str, width: int = 512, height: int = 512) -> str:
    """Fallback image generation using HuggingFace FLUX.1-schnell."""
    try:
        hf_token = os.getenv("HF_TOKEN")
        if not hf_token:
            return call_placeholder_image(prompt)

        url = "https://router.huggingface.co/together/v1/images/generations"
        headers = {
            "Authorization": f"Bearer {hf_token}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": "black-forest-labs/FLUX.1-schnell",
            "prompt": prompt,
            "width": width,
            "height": height,
            "steps": 4,
            "n": 1,
            "response_format": "b64_json"
        }

        print(f"[nova_client] Falling back to FLUX image for: {prompt[:30]}...")
        response = requests.post(url, headers=headers, json=payload, timeout=45)
        
        if response.status_code == 200:
            data = response.json()
            image_base64 = data["data"][0]["b64_json"]
            _save_image_locally(image_base64)
            print("[nova_client] Using HuggingFace FLUX ✅")
            return f"data:image/png;base64,{image_base64}"
        else:
            return call_placeholder_image(prompt)
    except Exception as e:
        return call_placeholder_image(prompt)

def call_placeholder_image(prompt: str) -> str:
    """Final fallback to Picsum."""
    try:
        r = requests.get('https://picsum.photos/1280/720', timeout=10)
        if r.status_code == 200:
            b64 = base64.b64encode(r.content).decode('utf-8')
            print("[nova_client] Using Picsum placeholder ✅")
            return f"data:image/jpeg;base64,{b64}"
    except:
        pass
    return "https://picsum.photos/1280/720"

def call_stability_ai(prompt: str, width: int = 512, height: int = 512) -> Optional[str]:
    """Fallback: Stability AI Core API."""
    api_key = os.getenv("STABILITY_API_KEY")
    if not api_key:
        return None
    try:
        url = "https://api.stability.ai/v2beta/stable-image/generate/core"
        headers = {"authorization": f"Bearer {api_key}", "accept": "image/*"}
        data = {"prompt": prompt, "output_format": "png"}
        
        print(f"[nova_client] Trying Stability AI for: {prompt[:30]}...")
        response = requests.post(url, headers=headers, files={"none": ""}, data=data)
        if response.status_code == 200:
            image_b64 = base64.b64encode(response.content).decode('utf-8')
            _save_image_locally(image_b64)
            print("[nova_client] Using Stability AI ✅")
            return f"data:image/png;base64,{image_b64}"
        else:
            print(f"[nova_client] Stability AI failed (Credits?): {response.text}")
            return None
    except Exception as e:
        print(f"[nova_client] Stability AI error: {e}")
        return None

def call_nova_canvas(
    prompt: str,
    negative_prompt: str = "person, face, blurry, text, watermark",
    width: int = 512,
    height: int = 512,
    **kwargs
) -> str:
    """Primary: HF FLUX. Secondary: Stability AI. Tertiary: AWS Nova Canvas."""
    try:
        return call_hf_flux(prompt, width, height)
    except Exception as e:
        print(f"[nova_client] HF FLUX failed: {e}. Trying Stability AI fallback...")
        
    # Try Stability AI
    stability_res = call_stability_ai(prompt, width, height)
    if stability_res:
        return stability_res
        
    print("[nova_client] Stability AI failed. Trying Nova Canvas fallback...")
    regions = [os.getenv("AWS_DEFAULT_REGION", "us-east-1"), "us-east-1", "us-west-2"]
    for reg in list(dict.fromkeys(regions)):
        try:
            client = _get_bedrock_runtime_client(region=reg)
            body = json.dumps({
                "taskType": "TEXT_IMAGE",
                "textToImageParams": {"text": prompt, "negativeText": negative_prompt},
                "imageGenerationConfig": {
                    "numberOfImages": 1,
                    "height": height,
                    "width": width,
                    "cfgScale": 8.0
                }
            })

            print(f"[nova_client] Generating Nova Canvas image in {reg}...")
            response = client.invoke_model(modelId="amazon.nova-canvas-v1:0", body=body)
            res_body = json.loads(response.get('body').read())
            
            if "images" in res_body:
                image_base64 = res_body['images'][0]
                _save_image_locally(image_base64)
                print(f"[nova_client] Success using Nova Canvas in {reg} ✅")
                return f"data:image/png;base64,{image_base64}"
        except Exception as ex:
            print(f"[nova_client] Nova Canvas failed in {reg}: {ex}")
            continue

    return call_placeholder_image(prompt)


# ============================================================
# TEXT GENERATION: Nova Pro (Primary) / Groq (Fallback)
# ============================================================

def call_groq(prompt: str) -> str:
    """Fallback text generation using Groq Llama 3.1."""
    from groq import Groq
    try:
        api_key = os.getenv("GROQ_API_KEY")
        client_groq = Groq(api_key=api_key)
        completion = client_groq.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "system", "content": "You are Nova AI, a helpful YouTube content creation assistant."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=1000,
            temperature=0.7
        )
        print("[nova_client] Using Groq Llama 3.1 ✅")
        return completion.choices[0].message.content.strip()
    except Exception as e:
        return f"Error: {str(e)}"

def call_nova_pro(prompt: str) -> str:
    """Primary: Groq Llama 3.1. Fallback: AWS Nova Pro (Dynamic Region)."""
    try:
        return call_groq(prompt)
    except Exception as e:
        print(f"[nova_client] Groq failed: {e}. Trying Nova Pro fallback...")

    regions = [os.getenv("AWS_DEFAULT_REGION", "us-east-1"), "us-west-2", "us-east-1"]
    for reg in list(dict.fromkeys(regions)):
        try:
            client = _get_bedrock_runtime_client(region=reg)
            print(f"[nova_client] Generating text with Nova Pro in {reg}...")
            
            response = client.converse(
                modelId="amazon.nova-pro-v1:0",
                messages=[{"role": "user", "content": [{"text": prompt}]}],
                inferenceConfig={"maxTokens": 1000, "temperature": 0.7}
            )
            
            result_text = response['output']['message']['content'][0]['text']
            print(f"[nova_client] Success using Nova Pro in {reg} ✅")
            return result_text
        except Exception as ex:
            print(f"[nova_client] Nova Pro failed in {reg}: {ex}")
            continue

    return f"Error: All text generation services failed."

# ============================================================
# VOICE GENERATION: Nova Sonic (Primary)
# ============================================================

def call_nova_sonic(text: str) -> Optional[str]:
    """
    Generate audio using AWS Nova Sonic on Bedrock. 
    Returns base64 encoded MP3 audio or raises exception for the fallback to catch.
    """
    regions = [os.getenv("AWS_DEFAULT_REGION", "us-east-1"), "us-east-1", "us-west-2"]
    for reg in list(dict.fromkeys(regions)):
        try:
            client = _get_bedrock_runtime_client(region=reg)
            body = json.dumps({"text": text[:3000]})

            print(f"[nova_client] Trying Nova Sonic in {reg}...")
            response = client.invoke_model(
                modelId="amazon.nova-sonic-v1:0",
                body=body,
                contentType="application/json",
                accept="audio/mpeg"
            )
            
            audio_bytes = response.get('body').read()
            if audio_bytes:
                print(f"[nova_client] Success using Nova Sonic in {reg} ✅")
                return base64.b64encode(audio_bytes).decode('utf-8')
        except Exception as e:
            print(f"[nova_client] Nova Sonic failed in {reg}: {e}")
            continue

    raise Exception("Nova Sonic failed in all regions")