import base64
import json
import os
import random
import time
from typing import Optional

import requests
import urllib.parse
from dotenv import load_dotenv

load_dotenv()

# ============================================================
# IMAGE GENERATION: HuggingFace FLUX (Fast for Demo)
# ============================================================

def call_hf_flux(prompt: str, width: int = 512, height: int = 512) -> str:
    """
    Image generation using HuggingFace FLUX.1-schnell via Together API router.
    Fast and high quality for demo purposes.
    """
    try:
        hf_token = os.getenv("HF_TOKEN")
        if not hf_token:
            print("[nova_client] HF_TOKEN missing. Falling back to Picsum.")
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
            "steps": 4,  # Fast mode
            "n": 1,
            "response_format": "b64_json"
        }

        print(f"[nova_client] Generating FLUX image for: {prompt[:30]}...")
        response = requests.post(url, headers=headers, json=payload, timeout=45)
        
        if response.status_code == 200:
            data = response.json()
            image_base64 = data["data"][0]["b64_json"]
            
            # Save to outputs for record
            _save_image_locally(image_base64)
            
            print("[nova_client] Using HuggingFace FLUX ✅")
            return f"data:image/png;base64,{image_base64}"
        else:
            print(f"[nova_client] HF FLUX failed: {response.status_code} {response.text[:100]}")
            return call_placeholder_image(prompt)

    except Exception as e:
        print(f"[nova_client] HF FLUX Error: {str(e)}")
        return call_placeholder_image(prompt)

def call_placeholder_image(prompt: str) -> str:
    """Final fallback to Picsum (Fast, but static)"""
    try:
        # Try to get a real image from Picsum
        r = requests.get('https://picsum.photos/1280/720', timeout=10)
        if r.status_code == 200:
            b64 = base64.b64encode(r.content).decode('utf-8')
            print("[nova_client] Using Picsum placeholder ✅")
            return f"data:image/jpeg;base64,{b64}"
    except:
        pass
    return "https://picsum.photos/1280/720"

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
# TEXT GENERATION: Groq Llama 3.1 (Instant Response)
# ============================================================

def call_groq(prompt: str) -> str:
    """Instant text generation using Groq Llama 3.1"""
    from groq import Groq
    try:
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise Exception("GROQ_API_KEY is missing")
        
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
        print(f"[nova_client] Groq Error: {str(e)}")
        return f"Error generating text: {str(e)}"


# ============================================================
# MAIN ENTRY POINTS (Updated for Demo Speed)
# ============================================================

def call_nova_pro(prompt: str) -> str:
    """
    SKIPPING AWS NOVA PRO (Slow).
    Directly using Groq for instant demo responses.
    """
    return call_groq(prompt)

def call_nova_canvas(prompt: str, **kwargs) -> str:
    """
    SKIPPING AWS NOVA CANVAS / STABILITY (Slow/No Credits).
    Directly using HuggingFace FLUX for fast demo images.
    """
    # Force demo resolution for speed
    return call_hf_flux(prompt, width=512, height=512)