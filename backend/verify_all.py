import os
import json
import boto3
from botocore.config import Config
from dotenv import load_dotenv
from nova_client import call_nova_pro, call_nova_canvas

load_dotenv()

def verify_all_services():
    print("🚀 Starting Nova AI connectivity check for Hackathon...\n")
    
    # 1. Check AWS Credentials
    print("--- 👤 AWS Credentials Check ---")
    akid = os.getenv("AWS_ACCESS_KEY_ID")
    secret = os.getenv("AWS_SECRET_ACCESS_KEY")
    region = os.getenv("AWS_DEFAULT_REGION", "us-west-2")
    
    if akid and secret:
        print(f"✅ Credentials found in .env (Region: {region})")
        print(f"   ID: {akid[:6]}...{akid[-4:]}")
    else:
        print("❌ AWS Credentials missing or empty in .env!")
        return

    # 2. Test Nova Pro (Text)
    print("\n--- 📝 Testing Nova Pro (Text Generation) ---")
    try:
        response = call_nova_pro("Hello, simply say 'Nova Pro is Connected!'")
        print(f"✅ Response: {response}")
    except Exception as e:
        print(f"❌ Nova Pro Test Failed: {e}")

    # 3. Test Nova Canvas (Image)
    print("\n--- 🎨 Testing Nova Canvas (Image Generation) ---")
    try:
        # Minimal prompt for speed
        response = call_nova_canvas("A simple glowing light bulb", width=128, height=128)
        if response.startswith("data:image"):
            print("✅ Image generated successfully (Base64 received)!")
        else:
            print("❌ Unexpected response format from Canvas.")
    except Exception as e:
        print(f"❌ Nova Canvas Test Failed: {e}")

    print("\n--- 🎥 Done! All systems checked. ---")

if __name__ == "__main__":
    verify_all_services()
