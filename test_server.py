import os
import json
import requests
from dotenv import load_dotenv


load_dotenv()

TEST_SERVER_URL = os.getenv("TEST_SERVER_URL")
# Check if it's a placeholder or not set, default to localhost
if not TEST_SERVER_URL or TEST_SERVER_URL in ["https://your-render-url.onrender.com", "your-render-url.onrender.com"]:
    TEST_SERVER_URL = "http://127.0.0.1:8000"
    print("⚠️  TEST_SERVER_URL not set or is a placeholder.")
    print(f"   Defaulting to local server: {TEST_SERVER_URL}")
    print("   Make sure your server is running with: python main.py")
    print("   Or set TEST_SERVER_URL in your .env file to test a remote server.\n")

student_email = os.getenv("STUDENT_EMAIL", "example@student.com")
student_secret = os.getenv("STUDENT_SECRET", "placeholder_secret")

payload = {
    "email": student_email,
    "secret": student_secret,
    "url": "https://tds-llm-analysis.s-anand.net/demo"
}

print(f"\nSending POST request to: {TEST_SERVER_URL} (root path)\n")
print("Payload:")
print(json.dumps(payload, indent=2))

try:
    # POST to root (/) because main.py expects POST at "/"
    response = requests.post(TEST_SERVER_URL, json=payload, timeout=30)
    print("\nResponse Status Code:", response.status_code)
    try:
        print("Response JSON:")
        print(json.dumps(response.json(), indent=2))
    except:
        print("Raw Response:")
        print(response.text)

    if response.status_code == 200:
        print("\n✅ TEST PASSED: Server accepted the request.\n")
    else:
        print("\n❌ TEST FAILED: Server rejected the request.\n")

except requests.exceptions.ConnectionError as e:
    print("\n❌ CONNECTION ERROR: Could not connect to the server.")
    if "127.0.0.1" in TEST_SERVER_URL or "localhost" in TEST_SERVER_URL:
        print("   Make sure your server is running:")
        print("   Run: python main.py")
        print("   Or: uvicorn main:app --reload")
    else:
        print(f"   Check if the server at {TEST_SERVER_URL} is running and accessible.")
    print(f"   Error details: {e}")
except Exception as e:
    print("\n❌ ERROR:", e)
