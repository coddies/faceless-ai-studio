import boto3
import json

bedrock = boto3.client('bedrock-runtime', region_name='us-east-1')

def test_nova_pro():
    model_id = "amazon.nova-pro-v1:0"
    payload = {
        "messages": [
            {"role": "user", "content": [{"text": "Hello, simply say Hi"}]}
        ]
    }
    
    print("Testing converse API for Nova Pro...")
    try:
        response = bedrock.converse(
            modelId=model_id,
            messages=payload["messages"]
        )
        print("Success!", response['output']['message']['content'][0]['text'])
    except Exception as e:
        print("Converse failed:", e)

def test_nova_canvas():
    model_id = "amazon.nova-canvas-v1:0"
    body = {
        "taskType": "TEXT_IMAGE",
        "textToImageParams": {
            "text": "A beautiful sunset over the mountains"
        },
        "imageGenerationConfig": {
            "numberOfImages": 1,
            "width": 1024,
            "height": 1024,
            "cfgScale": 8.0
        }
    }
    print("\nTesting invoke_model for Nova Canvas...")
    try:
        response = bedrock.invoke_model(
            modelId=model_id,
            body=json.dumps(body),
            accept="application/json",
            contentType="application/json"
        )
        res_body = json.loads(response['body'].read().decode('utf-8'))
        print("Success! Got images:", len(res_body.get('images', [])))
    except Exception as e:
        print("Invoke failed:", e)

test_nova_pro()
test_nova_canvas()

