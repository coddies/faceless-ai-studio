import boto3
import json
import os
import botocore.config
from dotenv import load_dotenv

# .env file se keys load karna
load_dotenv()

ACCESS_KEY = os.getenv('AWS_ACCESS_KEY_ID')
SECRET_KEY = os.getenv('AWS_SECRET_ACCESS_KEY')

# Client setup with .env keys and Retry Logic
cfg = botocore.config.Config(retries={'max_attempts': 10, 'mode': 'standard'})

client = boto3.client(
    service_name='bedrock-runtime',
    region_name='us-west-2',
    aws_access_key_id=ACCESS_KEY,
    aws_secret_access_key=SECRET_KEY,
    config=cfg
)

def test_nova():
    print("Testing Nova with .env credentials...")
    
    body = json.dumps({
        "taskType": "TEXT_IMAGE",
        "textToImageParams": {"text": "A high-tech coding robot, 4k, cinematic"},
        "imageGenerationConfig": {
            "numberOfImages": 1,
            "height": 512,
            "width": 512,
            "cfgScale": 8.0
        }
    })

    try:
        response = client.invoke_model(modelId="amazon.nova-canvas-v1:0", body=body)
        response_body = json.loads(response.get('body').read())
        
        # Check if image is in response
        if "images" in response_body:
            print("SUCCESS! Nova Canvas ne response de diya hai.")
            print(f"Base64 Preview: {response_body['images'][0][:50]}...")
        else:
            print("SUCCESS but no image found in response.")
            
    except Exception as e:
        print(f"FAILED: {str(e)}")

if __name__ == "__main__":
    test_nova()
