import os
from dotenv import load_dotenv

# Load .env keys
load_dotenv()

print('--- API Key Verification ---')
print('AWS Access Key: ', (os.getenv('AWS_ACCESS_KEY_ID') or 'MISSING')[:10] + '...')
print('Groq API Key:   ', (os.getenv('GROQ_API_KEY') or 'MISSING')[:10] + '...')
print('HF Token:       ', (os.getenv('HF_TOKEN') or 'MISSING')[:10] + '...')
print('Stability AI:  ', (os.getenv('STABILITY_API_KEY') or 'MISSING')[:10] + '...')
