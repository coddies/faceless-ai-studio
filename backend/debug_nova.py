import os
import json
import boto3
from botocore.config import Config
from dotenv import load_dotenv

load_dotenv()

def debug_nova_pro():
    print("--- 🔍 NOVA PRO DEBUG START ---")
    REGION = "us-west-2"
    MODEL_ID = "amazon.nova-pro-v1:0"
    
    my_config = Config(
        region_name=REGION,
        retries={'max_attempts': 3, 'mode': 'standard'}
    )
    
    client = boto3.client(
        "bedrock-runtime",
        config=my_config,
        aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
        aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY')
    )

    # Simplified payload to check if format is the issue
    payload = {
        "messages": [
            {
                "role": "user",
                "content": [{"text": "Hello, respond with ONE word: success or fail."}]
            }
        ]
    }
    
    try:
        print(f"Calling model {MODEL_ID} in {REGION}...")
        response = client.invoke_model(
            modelId=MODEL_ID,
            body=json.dumps(payload)
        )
        res_body = json.loads(response['body'].read())
        print("✅ SUCCESS!")
        print("Response:", json.dumps(res_body, indent=2))
    except Exception as e:
        print(f"❌ FAILED with Error: {str(e)}")
        # If it's a ValidationException, print more info if possible
        if hasattr(e, 'response'):
             print("Full Error Response:", json.dumps(e.response, indent=2))

if __name__ == "__main__":
    debug_nova_pro()
