import json
import base64
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def run_tests():
    print("--- STARTING ENDPOINT TESTS ---")

    # 1. GET /api/chat-history
    print("\n[1] Testing GET /api/chat-history...")
    res = client.get("/api/chat-history")
    print("Status:", res.status_code)
    if res.status_code == 200:
        print("Success! Keys:", res.json().get("grouped", {}).keys())
    else:
        print("Error:", res.text)

    # 2. POST /api/chat
    print("\n[2] Testing POST /api/chat...")
    res = client.post("/api/chat", json={
        "message": "Hello Nova AI, just saying hi!",
        "session_id": "test_session_123"
    })
    print("Status:", res.status_code)
    if res.status_code == 200:
        print("Reply:", res.json().get("reply", "")[:100], "...")
    else:
        print("Error:", res.text)

    # 3. GET /api/get-topics
    print("\n[3] Testing GET /api/get-topics...")
    res = client.get("/api/get-topics")
    print("Status:", res.status_code)
    if res.status_code == 200:
        topics = res.json().get("topics", [])
        print(f"Success! Got {len(topics)} topics. First:", topics[0]["title"] if topics else "None")
    else:
        print("Error:", res.text)

    # 4. POST /api/generate-script
    print("\n[4] Testing POST /api/generate-script...")
    res = client.post("/api/generate-script", json={
        "topic": "The history of the universe",
        "tone": "Educational",
        "length_words": 150
    })
    print("Status:", res.status_code)
    if res.status_code == 200:
        print("Script title:", res.json().get("title"))
        print("Script snippet:", res.json().get("script_content", "")[:100], "...")
    else:
        print("Error:", res.text)

    # 5. POST /api/generate-seo
    print("\n[5] Testing POST /api/generate-seo...")
    res = client.post("/api/generate-seo", json={
        "topic": "Why Black Holes are mysterious"
    })
    print("Status:", res.status_code)
    if res.status_code == 200:
        print("SEO Viral Title:", res.json().get("viral_title"))
        print("SEO Description length:", len(res.json().get("description", "")))
    else:
        print("Error:", res.text)

    # 6. POST /api/generate-audio
    print("\n[6] Testing POST /api/generate-audio...")
    res = client.post("/api/generate-audio", json={
        "text": "Hello! Welcome to this amazing video.",
        "voice_id": "Joanna"
    })
    print("Status:", res.status_code)
    if res.status_code == 200:
        print("Audio generated! Format:", res.json().get("format"))
    else:
        print("Error:", res.text)

    # 7. POST /api/regenerate-thumbnail
    print("\n[7] Testing POST /api/regenerate-thumbnail (Nova Canvas)...")
    res = client.post("/api/regenerate-thumbnail", json={
        "title": "A futuristic city in the clouds",
        "style": "cinematic"
    })
    print("Status:", res.status_code)
    if res.status_code == 200:
        print("Thumbnail URL length:", len(res.json().get("thumbnail_url", "")))
    else:
        print("Error:", res.text)

    # 8. POST /api/generate-scenes
    print("\n[8] Testing POST /api/generate-scenes (Multiple Canvas Calls)...")
    res = client.post("/api/generate-scenes", json={
        "script_segments": ["Establishing shot of a glowing neon futuristic city at night.", "A flying car zooms past a giant hologram"]
    })
    print("Status:", res.status_code)
    if res.status_code == 200:
        print(f"Generated {len(res.json().get('scenes', []))} scenes.")
    else:
        print("Error:", res.text)

    # 9. POST /api/generate-full-video
    print("\n[9] Testing POST /api/generate-full-video...")
    res = client.post("/api/generate-full-video", json={
        "title": "How Quantum Computers Work"
    })
    print("Status:", res.status_code)
    if res.status_code == 200:
        print("Full Video Data Title:", res.json().get("title"))
        print("Description Length:", len(res.json().get("description", "")))
    else:
        print("Error:", res.text)

    print("\n--- ALL TESTS FINISHED ---")

if __name__ == "__main__":
    run_tests()
