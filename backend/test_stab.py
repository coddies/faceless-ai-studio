from nova_client import call_stability_image
try:
    result = call_stability_image('YouTube thumbnail tech video')
    print("SUCCESS| " + result[:50])
except Exception as e:
    print("FAILED|", str(e))
