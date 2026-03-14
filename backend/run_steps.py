import boto3
import json
import subprocess
import sys

def run_step1():
    print("### STEP 1 - Configure AWS Credentials ###")

    subprocess.run(["aws", "configure", "set", "output", "json"])
    print("AWS configured.")
    result = subprocess.run(["aws", "sts", "get-caller-identity"], capture_output=True, text=True)
    print(result.stdout)
    if result.stderr:
        print("Error:", result.stderr)

def run_step2():
    print("### STEP 2 - Verify boto3 ###")
    try:
        import boto3
        print(f"boto3 OK: {boto3.__version__}")
    except ImportError:
        print("boto3 not found. Installing...")
        subprocess.run([sys.executable, "-m", "pip", "install", "boto3", "awscli"])

def run_step3():
    print("### STEP 3 - Test Nova Connection ###")
    try:
        client = boto3.client('bedrock-runtime', region_name='us-east-1')
        r = client.invoke_model(
            modelId='amazon.nova-pro-v1:0',
            body=json.dumps({'messages':[{'role':'user','content':[{'text':'Say hello in one line'}]}]})
        )
        print('Nova Pro OK:', json.loads(r['body'].read())['output']['message']['content'][0]['text'])
    except Exception as e:
        print("Nova Pro Error:", str(e))

run_step1()
run_step2()
run_step3()
