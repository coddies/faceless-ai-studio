import os
import requests
from dotenv import load_dotenv

load_dotenv()

def test_stability():
    api_key = os.getenv("STABILITY_API_KEY")
    if not api_key:
        print("❌ No STABILITY_API_KEY found")
        return

    print("🚀 Testing Stability AI Key...")
    
    # Using the 'Core' generation endpoint
    url = "https://api.stability.ai/v2beta/stable-image/generate/core"
    
    headers = {
        "authorization": f"Bearer {api_key}",
        "accept": "image/*"
    }
    
    data = {
        "prompt": "A beautiful cinematic digital art of a futuristic AI city",
        "output_format": "png"
    }
    
    try:
        response = requests.post(url, headers=headers, files={"none": ""}, data=data)
        if response.status_code == 200:
            print(f"✅ Stability AI Works! Image size: {len(response.content)} bytes")
            with open("test_stability.png", "wb") as f:
                f.write(response.content)
            print("Saved as test_stability.png")
        else:
            print(f"❌ Stability GPT Failed. Status: {response.status_code}")
            print(f"Error: {response.json()}")
    except Exception as e:
        print(f"❌ Stability Test Error: {e}")

if __name__ == "__main__":
    test_stability()
