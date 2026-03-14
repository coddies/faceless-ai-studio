from nova_client import call_nova_pro, call_nova_canvas
import sys

def main():
    print("Testing Nova Pro...", flush=True)
    try:
        response = call_nova_pro("Reply with 'yes' if you can hear me.")
        print(f"Nova Pro Success: {response}", flush=True)
    except Exception as e:
        print(f"Nova Pro Error: {e}", flush=True)

    print("\nTesting Nova Canvas...", flush=True)
    try:
        response = call_nova_canvas("A simple red circle on a white background")
        if response.startswith("data:image/png;base64,"):
            print("Nova Canvas Success (Base64 Image received)", flush=True)
        else:
            print("Nova Canvas returned unexpected format.", flush=True)
    except Exception as e:
        print(f"Nova Canvas Error: {e}", flush=True)

if __name__ == "__main__":
    main()
