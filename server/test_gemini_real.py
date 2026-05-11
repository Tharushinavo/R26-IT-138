import json
import sys
from urllib import request
from urllib.error import HTTPError

API_KEY = "AIzaSyDtMzAtBoSKSg9dp6Ao-CBzunb4HJbDiwY"
MODEL = "gemini-flash-latest"

url = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent"
payload = {
    "contents": [{"parts": [{"text": "Return JSON: {\"test\": true}"}]}]
}

print(f"Testing {MODEL} with new key exactly as in curl...")
data = json.dumps(payload).encode("utf-8")
req = request.Request(url, data=data, method="POST")
req.add_header('Content-Type', 'application/json')
req.add_header('X-goog-api-key', API_KEY)

try:
    with request.urlopen(req, timeout=15) as res:
        body = json.loads(res.read().decode("utf-8"))
        text = body["candidates"][0]["content"]["parts"][0]["text"]
        print(f"[OK] {MODEL} API responded: {text}")
        sys.exit(0)
except HTTPError as exc:
    err = exc.read().decode('utf-8')
    print(f"[FAIL] HTTP {exc.code} for {MODEL} - {err[:500]}")
    sys.exit(1)
